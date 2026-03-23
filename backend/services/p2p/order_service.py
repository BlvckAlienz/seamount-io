# FILE: backend/services/p2p/order_service.py

import logging
import time
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from backend.dependencies import get_supabase_client

logger = logging.getLogger(__name__)

ORDER_TIMEOUT_MINS = 15


def _gen_order_number() -> str:
    """Generate a unique order number similar to Binance's format."""
    return f"{int(time.time() * 1000)}{random.randint(100, 999)}"


async def create_p2p_order(
    idempotency_key: str,
    listing_id: str,
    buyer_id: str,
    fiat_amount: float,
    payment_method: str
) -> Dict[str, Any]:
    """
    Create a P2P order.
    If the same idempotency_key arrives twice (e.g. network retry),
    we return the existing order instead of creating a duplicate.
    """
    supabase = get_supabase_client()

    # ── Idempotency check ─────────────────────────────────────
    existing = supabase.table("p2p_orders") \
        .select("*, p2p_listings(payment_details)") \
        .eq("idempotency_key", idempotency_key) \
        .limit(1) \
        .execute()

    if existing.data and len(existing.data) > 0:
        row = existing.data[0]
        logger.info(f"[P2P] Duplicate request — returning existing order: {idempotency_key}")
        return {
            "order": row,
            "payment_details": (row.get("p2p_listings") or {}).get("payment_details"),
            "is_duplicate": True
        }

    # ── Fetch and validate listing ────────────────────────────
    listing_res = supabase.table("p2p_listings") \
        .select("*, p2p_merchants(*)") \
        .eq("id", listing_id) \
        .eq("is_active", True) \
        .limit(1) \
        .execute()

    if not listing_res.data or len(listing_res.data) == 0:
        raise ValueError("Listing not available or inactive")

    listing = listing_res.data[0]

    if not (listing["min_order_fiat"] <= fiat_amount <= listing["max_order_fiat"]):
        raise ValueError(
            f"Amount must be between {listing['min_order_fiat']} "
            f"and {listing['max_order_fiat']} {listing['fiat_currency']}"
        )

    token_amount = fiat_amount / listing["price_per_token"]
    deadline = datetime.now(timezone.utc) + timedelta(minutes=ORDER_TIMEOUT_MINS)

    # ── Create order ──────────────────────────────────────────
    order_number = _gen_order_number()

    supabase.table("p2p_orders").insert({
        "idempotency_key": idempotency_key,
        "order_number": order_number,
        "listing_id": listing_id,
        "buyer_id": buyer_id,
        "merchant_id": listing["merchant_id"],
        "token": listing["token"],
        "fiat_currency": listing["fiat_currency"],
        "fiat_amount": fiat_amount,
        "token_amount": token_amount,
        "price_per_token": listing["price_per_token"],
        "payment_method": payment_method,
        "status": "payment_window",
        "payment_deadline": deadline.isoformat(),
        "platform_fee_bps": 30
    }).execute()

    # Fetch created order separately
    order_res = supabase.table("p2p_orders") \
        .select("*") \
        .eq("idempotency_key", idempotency_key) \
        .limit(1) \
        .execute()

    if not order_res.data or len(order_res.data) == 0:
        raise Exception("Order not found after insert")

    order = order_res.data[0]

    # ── Audit log ─────────────────────────────────────────────
    await _audit_log(
        order_id=order["id"],
        event_type="state_change",
        prev_status=None,
        new_status="payment_window",
        actor_id=buyer_id
    )

    # ── System message ────────────────────────────────────────
    supabase.table("p2p_messages").insert({
        "order_id": order["id"],
        "is_system": True,
        "message": (
            f"Order {order['order_number']} created. "
            f"Include this number as your payment reference. "
            f"Pay within {ORDER_TIMEOUT_MINS} minutes."
        )
    }).execute()

    logger.info(f"[P2P] Order created: {order['id']} | token: {order['token']}")

    # payment_details only returned here — never exposed in listing fetch
    return {
        "order": order,
        "payment_details": listing.get("payment_details"),
        "is_duplicate": False
    }


async def confirm_payment_sent(
    order_id: str,
    buyer_id: str,
    receipt_url: str
) -> Dict[str, Any]:
    """
    Buyer confirms they have sent payment and uploads receipt.
    Validates the 15-min window has not expired.
    """
    supabase = get_supabase_client()

    order_res = supabase.table("p2p_orders") \
        .select("*") \
        .eq("id", order_id) \
        .eq("buyer_id", buyer_id) \
        .eq("status", "payment_window") \
        .limit(1) \
        .execute()

    if not order_res.data or len(order_res.data) == 0:
        raise ValueError("Order not found or already processed")

    order = order_res.data[0]

    # Check timer has not expired
    deadline = datetime.fromisoformat(order["payment_deadline"])
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > deadline:
        # CHANGE: 'cancelled' → 'expired' to match the dedicated expired status
        supabase.table("p2p_orders") \
            .update({"status": "expired", "updated_at": datetime.now(timezone.utc).isoformat()}) \
            .eq("id", order_id) \
            .execute()

        await _audit_log(order_id, "state_change", "payment_window", "expired", buyer_id)

        raise ValueError("Payment window expired. Order has been cancelled.")

    # Update to paid
    supabase.table("p2p_orders").update({
        "status": "paid",
        "payment_receipt_url": receipt_url,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", order_id).execute()

    await _audit_log(order_id, "state_change", "payment_window", "paid", buyer_id)

    supabase.table("p2p_messages").insert({
        "order_id": order_id,
        "is_system": True,
        "message": "Buyer confirmed payment and uploaded receipt. Please verify and release tokens."
    }).execute()

    logger.info(f"[P2P] Payment confirmed by buyer: {order_id}")
    return {"message": "Payment confirmed. Awaiting merchant release."}


async def merchant_confirm_and_release(
    order_id: str,
    merchant_user_id: str
) -> Dict[str, Any]:
    """
    Merchant confirms payment received and triggers token release.
    Actual WDK transfer runs via the job worker (backend/workers/p2pWorkers).
    """
    supabase = get_supabase_client()

    # Verify the caller is the merchant on this order
    merchant_res = supabase.table("p2p_merchants") \
        .select("id") \
        .eq("user_id", merchant_user_id) \
        .limit(1) \
        .execute()

    if not merchant_res.data or len(merchant_res.data) == 0:
        raise ValueError("Merchant profile not found")

    merchant_id = merchant_res.data[0]["id"]

    order_res = supabase.table("p2p_orders") \
        .select("*") \
        .eq("id", order_id) \
        .eq("merchant_id", merchant_id) \
        .eq("status", "paid") \
        .limit(1) \
        .execute()

    if not order_res.data or len(order_res.data) == 0:
        raise ValueError("Order not found or not in paid state")

    # Move to confirming — worker handles the WDK transfer
    supabase.table("p2p_orders").update({
        "status": "confirming",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", order_id).execute()

    await _audit_log(order_id, "state_change", "paid", "confirming", merchant_user_id)

    # Enqueue token release job
    # Worker in backend/workers/p2pWorkers picks this up with retries
    await _enqueue_token_release(order_id, merchant_user_id)

    supabase.table("p2p_messages").insert({
        "order_id": order_id,
        "is_system": True,
        "message": "Merchant confirmed payment. Token release in progress..."
    }).execute()

    logger.info(f"[P2P] Token release enqueued for order: {order_id}")
    return {"message": "Token release in progress"}


# ── HELPERS ───────────────────────────────────────────────────

async def _audit_log(
    order_id: str,
    event_type: str,
    prev_status: str | None,
    new_status: str | None,
    actor_id: str | None = None,
    metadata: dict | None = None
) -> None:
    """Write an immutable audit event. Never raises — audit failure must not break the main flow."""
    try:
        supabase = get_supabase_client()
        supabase.table("settlement_audit_log").insert({
            "order_id": order_id,
            "event_type": event_type,
            "prev_status": prev_status,
            "new_status": new_status,
            "actor_id": actor_id,
            "metadata": metadata or {}
        }).execute()
    except Exception as e:
        logger.warning(f"[P2P] Audit log write failed (non-critical): {e}")


async def _enqueue_token_release(order_id: str, merchant_user_id: str) -> None:
    """
    Enqueue a token release job into the p2p_jobs table.
    The worker process polls this table and executes the WDK transfer.
    Using Supabase table as job queue keeps infrastructure minimal —
    no extra Redis or external queue service required at bootstrap stage.
    """
    try:
        supabase = get_supabase_client()
        supabase.table("p2p_jobs").insert({
            "job_type": "token.release",
            "payload": {
                "order_id": order_id,
                "merchant_user_id": merchant_user_id
            },
            "status": "pending",
            "retry_count": 0,
            "max_retries": 5
        }).execute()
        logger.info(f"[P2P] Job enqueued: token.release for order {order_id}")
    except Exception as e:
        logger.error(f"[P2P] Failed to enqueue token release job: {e}")
        raise


# ══════════════════════════════════════════════════════════════
# SELL SIDE
# ══════════════════════════════════════════════════════════════

async def create_sell_order(
    idempotency_key: str,
    listing_id: str,
    seller_id: str,
    fiat_amount: float,
    payment_method: str,
    payout_details: dict,
) -> Dict[str, Any]:
    """
    User sells tokens to merchant for fiat.
    Tokens move via Seamount wallet infrastructure (same as buy side, reversed).
    seller_id stored in buyer_id column for schema compatibility.
    """
    supabase = get_supabase_client()

    existing = supabase.table("p2p_orders") \
        .select("*").eq("idempotency_key", idempotency_key).limit(1).execute()
    if existing.data:
        return {"order": existing.data[0], "is_duplicate": True}

    listing_res = supabase.table("p2p_listings") \
        .select("*, p2p_merchants(*)") \
        .eq("id", listing_id).eq("is_active", True).eq("listing_type", "sell") \
        .limit(1).execute()
    if not listing_res.data:
        raise ValueError("Listing not available or inactive")

    listing = listing_res.data[0]
    if not (listing["min_order_fiat"] <= fiat_amount <= listing["max_order_fiat"]):
        raise ValueError(
            f"Amount must be between {listing['min_order_fiat']} "
            f"and {listing['max_order_fiat']} {listing['fiat_currency']}"
        )

    token_amount = fiat_amount / listing["price_per_token"]
    deadline     = datetime.now(timezone.utc) + timedelta(minutes=ORDER_TIMEOUT_MINS)
    order_number = _gen_order_number()

    supabase.table("p2p_orders").insert({
        "idempotency_key":       idempotency_key,
        "order_number":          order_number,
        "listing_id":            listing_id,
        "buyer_id":              seller_id,        # seller stored in buyer_id
        "merchant_id":           listing["merchant_id"],
        "token":                 listing["token"],
        "fiat_currency":         listing["fiat_currency"],
        "fiat_amount":           fiat_amount,
        "token_amount":          token_amount,
        "price_per_token":       listing["price_per_token"],
        "payment_method":        payment_method,
        "status":                "payment_window",
        "order_type":            "sell",
        "payment_deadline":      deadline.isoformat(),
        "platform_fee_bps":      0,
        "seller_payout_method":  payment_method,
        "seller_payout_details": payout_details,
    }).execute()

    order_res = supabase.table("p2p_orders") \
        .select("*").eq("idempotency_key", idempotency_key).limit(1).execute()
    if not order_res.data:
        raise Exception("Order not found after insert")
    order = order_res.data[0]

    await _audit_log(order["id"], "state_change", None, "payment_window", seller_id)

    supabase.table("p2p_messages").insert({
        "order_id": order["id"], "is_system": True,
        "message": (
            f"Sell order {order_number} created. "
            f"Click 'Release Tokens' to send "
            f"{token_amount:.6f} {listing['token'].split('_')[0]} "
            f"to the merchant via Seamount. "
            f"You have {ORDER_TIMEOUT_MINS} minutes."
        )
    }).execute()

    logger.info(f"[P2P] Sell order created: {order['id']}")
    return {"order": order, "is_duplicate": False}


async def seller_authorize_token_release(
    order_id: str,
    seller_id: str,
) -> Dict[str, Any]:
    """
    Seller authorises Seamount to move their tokens to the merchant.
    Enqueues a worker job — mirrors buy side merchant_confirm_and_release.
    Replaces old seller_confirm_token_sent (external wallet approach removed).
    """
    supabase = get_supabase_client()

    order_res = supabase.table("p2p_orders") \
        .select("*") \
        .eq("id", order_id).eq("buyer_id", seller_id) \
        .eq("status", "payment_window").eq("order_type", "sell") \
        .limit(1).execute()
    if not order_res.data:
        raise ValueError("Order not found or already processed")

    order = order_res.data[0]
    deadline = datetime.fromisoformat(order["payment_deadline"])
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > deadline:
        supabase.table("p2p_orders").update({
            "status":     "expired",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", order_id).execute()
        raise ValueError("Payment window expired. Order cancelled.")

    # Move to confirming — worker handles the transfer
    supabase.table("p2p_orders").update({
        "status":     "confirming",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", order_id).execute()

    await _audit_log(order_id, "state_change", "payment_window", "confirming", seller_id)

    # Enqueue sell token transfer job
    supabase.table("p2p_jobs").insert({
        "job_type": "token.sell_transfer",
        "payload": {
            "order_id":       order_id,
            "seller_user_id": seller_id,
            "merchant_id":    order["merchant_id"],
        },
        "status":      "pending",
        "retry_count": 0,
        "max_retries": 5,
    }).execute()

    supabase.table("p2p_messages").insert({
        "order_id": order_id, "is_system": True,
        "message": "Token transfer initiated via Seamount. Please wait for on-chain confirmation..."
    }).execute()

    logger.info(f"[P2P] Sell token transfer enqueued: {order_id}")
    return {"message": "Token transfer in progress. Merchant will be notified upon receipt."}


async def merchant_confirm_fiat_sent(
    order_id: str,
    merchant_user_id: str,
    fiat_proof_url: str,
) -> Dict[str, Any]:
    """Merchant has received tokens and sent fiat. Uploads proof."""
    supabase = get_supabase_client()

    merchant_res = supabase.table("p2p_merchants") \
        .select("id").eq("user_id", merchant_user_id).limit(1).execute()
    if not merchant_res.data:
        raise ValueError("Merchant profile not found")
    merchant_id = merchant_res.data[0]["id"]

    # Tokens confirmed received = status is 'paid' on sell orders
    order_res = supabase.table("p2p_orders") \
        .select("*") \
        .eq("id", order_id) \
        .eq("merchant_id", merchant_id) \
        .eq("status", "paid") \
        .eq("order_type", "sell") \
        .limit(1).execute()

    if not order_res.data:
        raise ValueError("Order not found or not in correct state")

    order = order_res.data[0]
    payout_method = order.get("seller_payout_method", "account")

    supabase.table("p2p_orders").update({
        "status":          "confirming",
        "fiat_proof_url":  fiat_proof_url,
        "updated_at":      datetime.now(timezone.utc).isoformat()
    }).eq("id", order_id).execute()

    await _audit_log(order_id, "state_change", "paid", "confirming", merchant_user_id)

    supabase.table("p2p_messages").insert({
        "order_id": order_id, "is_system": True,
        "message": (
            f"Merchant has sent fiat payment. "
            f"Check your {payout_method} account and confirm receipt below."
        )
    }).execute()

    logger.info(f"[P2P] Merchant confirmed fiat sent: {order_id}")
    return {"message": "Fiat payment sent. Waiting for seller to confirm receipt."}


async def seller_confirm_fiat_received(
    order_id: str,
    seller_id: str,
) -> Dict[str, Any]:
    """Seller confirms fiat received — order complete."""
    supabase = get_supabase_client()

    order_res = supabase.table("p2p_orders") \
        .select("*") \
        .eq("id", order_id) \
        .eq("buyer_id", seller_id) \
        .eq("status", "confirming") \
        .eq("order_type", "sell") \
        .limit(1).execute()

    if not order_res.data:
        raise ValueError("Order not found")

    order = order_res.data[0]

    supabase.table("p2p_orders").update({
        "status":     "completed",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", order_id).execute()

    supabase.rpc("increment_merchant_orders", {"p_merchant_id": order["merchant_id"]}).execute()
    await _audit_log(order_id, "state_change", "confirming", "completed", seller_id)

    supabase.table("p2p_messages").insert({
        "order_id": order_id, "is_system": True,
        "message": "✅ Seller confirmed fiat receipt. Order completed successfully!"
    }).execute()

    logger.info(f"[P2P] Sell order completed: {order_id}")
    return {"message": "Order completed successfully."}