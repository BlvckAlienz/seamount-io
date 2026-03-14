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
        .maybe_single() \
        .execute()

    if existing.data:
        logger.info(f"[P2P] Duplicate request — returning existing order: {idempotency_key}")
        return {
            "order": existing.data,
            "payment_details": (existing.data.get("p2p_listings") or {}).get("payment_details"),
            "is_duplicate": True
        }

    # ── Fetch and validate listing ────────────────────────────
    listing_res = supabase.table("p2p_listings") \
        .select("*, p2p_merchants(*)") \
        .eq("id", listing_id) \
        .eq("is_active", True) \
        .maybe_single() \
        .execute()

    if not listing_res.data:
        raise ValueError("Listing not available or inactive")

    listing = listing_res.data

    if not (listing["min_order_fiat"] <= fiat_amount <= listing["max_order_fiat"]):
        raise ValueError(
            f"Amount must be between {listing['min_order_fiat']} "
            f"and {listing['max_order_fiat']} {listing['fiat_currency']}"
        )

    token_amount = fiat_amount / listing["price_per_token"]
    deadline = datetime.now(timezone.utc) + timedelta(minutes=ORDER_TIMEOUT_MINS)

    # ── Create order ──────────────────────────────────────────
    order_res = supabase.table("p2p_orders").insert({
        "idempotency_key": idempotency_key,
        "order_number": _gen_order_number(),
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
    }).select().execute()

    if not order_res.data:
        raise Exception("Failed to create order — no data returned from database")

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
        .maybe_single() \
        .execute()

    if not order_res.data:
        raise ValueError("Order not found or already processed")

    order = order_res.data

    # Check timer has not expired
    deadline = datetime.fromisoformat(order["payment_deadline"])
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > deadline:
        supabase.table("p2p_orders") \
            .update({"status": "cancelled", "updated_at": datetime.now(timezone.utc).isoformat()}) \
            .eq("id", order_id) \
            .execute()

        await _audit_log(order_id, "state_change", "payment_window", "cancelled", buyer_id)

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
        .maybe_single() \
        .execute()

    if not merchant_res.data:
        raise ValueError("Merchant profile not found")

    merchant_id = merchant_res.data["id"]

    order_res = supabase.table("p2p_orders") \
        .select("*") \
        .eq("id", order_id) \
        .eq("merchant_id", merchant_id) \
        .eq("status", "paid") \
        .maybe_single() \
        .execute()

    if not order_res.data:
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