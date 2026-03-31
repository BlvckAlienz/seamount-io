# FILE: backend/api/routes/p2p.py
# Full updated file — adds receipt upload, cancel order, and GET order endpoints

import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.dependencies import get_multi_chain_wallet_service
from backend.dependencies import get_current_user, get_supabase_client
from backend.services.p2p.order_service import (
    create_p2p_order,
    confirm_payment_sent,
    merchant_confirm_and_release,
    create_sell_order,
    seller_authorize_token_release,   # ← replaces seller_confirm_token_sent
    merchant_confirm_fiat_sent,
    seller_confirm_fiat_received,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/p2p", tags=["P2P Trading"])


# ── MERCHANT REGISTRATION ─────────────────────────────────────

class RegisterMerchantRequest(BaseModel):
    display_name: str

class PaymentMethodsRequest(BaseModel):
    merchant_id: str
    payment_methods: List[Dict[str, Any]]

class CreateListingRequest(BaseModel):
    merchant_id: str
    token: str
    fiat_currency: str
    price_per_token: float
    min_order_fiat: float
    max_order_fiat: float
    available_amount: float
    payment_methods: List[str]
    payment_details: Dict[str, Any]
    terms: Optional[str] = None

class OnlineStatusRequest(BaseModel):
    is_online: bool


# ── POST /api/p2p/merchants/register ─────────────────────────
@router.post("/merchants/register")
async def register_merchant(
    payload: RegisterMerchantRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    try:
        user_id = current_user["id"]

        # Check if already a merchant — return existing profile
        existing = supabase.table("p2p_merchants") \
            .select("id") \
            .eq("user_id", user_id) \
            .limit(1) \
            .execute()

        if existing.data and len(existing.data) > 0:
            existing_merchant = existing.data[0]
            existing_status = existing_merchant.get("status", "pending")

            # Approved merchants cannot re-register
            if existing_status == "approved":
                return {
                    "success": True,
                    "merchant_id": existing_merchant["id"],
                    "already_exists": True
                }

            # Rejected merchants can reapply — reset to pending
            if existing_status == "rejected":
                supabase.table("p2p_merchants").update({
                    "status": "pending",
                    "display_name": payload.display_name,
                    "is_online": False,
                    "verified": False,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", existing_merchant["id"]).execute()

                logger.info(f"[P2P] Merchant reapplication submitted: {user_id}")
                return {
                    "success": True,
                    "merchant_id": existing_merchant["id"],
                    "reapplied": True
                }

            # Pending — already waiting for review
            if existing_status == "pending":
                return {
                    "success": True,
                    "merchant_id": existing_merchant["id"],
                    "already_exists": True
                }

        # INSERT — no chaining
        supabase.table("p2p_merchants").insert({
            "user_id": user_id,
            "display_name": payload.display_name,
            "verified": False,
            "is_online": False,
            "status": "pending"
        }).execute()

        # Fetch separately — .limit(1) not .single()
        created = supabase.table("p2p_merchants") \
            .select("id") \
            .eq("user_id", user_id) \
            .limit(1) \
            .execute()

        if not created.data or len(created.data) == 0:
            raise Exception("Merchant record not found after insert")

        logger.info(f"[P2P] Merchant registered: {user_id}")
        return {"success": True, "merchant_id": created.data[0]["id"]}

    except Exception as e:
        logger.error(f"[P2P] Merchant registration error: {e}")
        raise HTTPException(status_code=500, detail="Failed to register merchant")


# ── POST /api/p2p/merchants/payment-methods ──────────────────
@router.post("/merchants/payment-methods")
async def save_payment_methods(
    payload: PaymentMethodsRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    try:
        # Verify ownership
        m = supabase.table("p2p_merchants") \
            .select("id") \
            .eq("id", payload.merchant_id) \
            .eq("user_id", current_user["id"]) \
            .limit(1) \
            .execute()
        if not m.data or len(m.data) == 0:
            raise HTTPException(status_code=403, detail="Access denied")

        # Store as metadata on merchant profile
        supabase.table("p2p_merchants").update({
            "payment_methods_config": payload.payment_methods,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", payload.merchant_id).execute()

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[P2P] Payment methods save error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save payment methods")


# ── GET /api/p2p/merchants/me ─────────────────────────────────
@router.get("/merchants/me")
async def get_my_merchant_profile(
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    try:
        res = supabase.table("p2p_merchants") \
            .select("*") \
            .eq("user_id", current_user["id"]) \
            .limit(1) \
            .execute()

        if not res.data or len(res.data) == 0:
            return {"success": False, "merchant": None}

        return {"success": True, "merchant": res.data[0]}
    except Exception as e:
        logger.error(f"[P2P] Get merchant profile error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch merchant profile")


# ── PATCH /api/p2p/merchants/me/online ───────────────────────
@router.patch("/merchants/me/online")
async def update_online_status(
    payload: OnlineStatusRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    try:
        supabase.table("p2p_merchants").update({
            "is_online": payload.is_online
        }).eq("user_id", current_user["id"]).execute()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update status")


# ── GET /api/p2p/merchants/{merchant_id}/listings ────────────
@router.get("/merchants/{merchant_id}/listings")
async def get_merchant_listings(
    merchant_id: str,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    try:
        # Verify ownership
        m = supabase.table("p2p_merchants") \
            .select("id").eq("id", merchant_id) \
            .eq("user_id", current_user["id"]) \
            .limit(1).execute()
        if not m.data or len(m.data) == 0:
            raise HTTPException(status_code=403, detail="Access denied")

        res = supabase.table("p2p_listings") \
            .select("*") \
            .eq("merchant_id", merchant_id) \
            .order("created_at", desc=True) \
            .execute()

        return {"success": True, "listings": res.data or []}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch listings")


# ── GET /api/p2p/merchants/{merchant_id}/orders ──────────────
@router.get("/merchants/{merchant_id}/orders")
async def get_merchant_orders(
    merchant_id: str,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    try:
        m = supabase.table("p2p_merchants") \
            .select("id").eq("id", merchant_id) \
            .eq("user_id", current_user["id"]) \
            .limit(1).execute()
        if not m.data or len(m.data) == 0:
            raise HTTPException(status_code=403, detail="Access denied")

        res = supabase.table("p2p_orders") \
            .select("*") \
            .eq("merchant_id", merchant_id) \
            .order("created_at", desc=True) \
            .execute()

        return {"success": True, "orders": res.data or []}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch orders")


# ── POST /api/p2p/listings ────────────────────────────────────
@router.post("/listings")
async def create_listing(
    payload: CreateListingRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    try:
        # ── Verify merchant ownership ──────────────────────────
        m = supabase.table("p2p_merchants") \
            .select("id") \
            .eq("id", payload.merchant_id) \
            .eq("user_id", current_user["id"]) \
            .limit(1) \
            .execute()

        if not m.data or len(m.data) == 0:
            raise HTTPException(status_code=403, detail="Access denied")

        # m.data is a LIST — access with [0]
        merchant_id = m.data[0]["id"]

        # ── INSERT ─────────────────────────────────────────────
        supabase.table("p2p_listings").insert({
            "merchant_id": payload.merchant_id,
            "token": payload.token,
            "fiat_currency": payload.fiat_currency,
            "price_per_token": payload.price_per_token,
            "min_order_fiat": payload.min_order_fiat,
            "max_order_fiat": payload.max_order_fiat,
            "available_amount": payload.available_amount,
            "payment_methods": payload.payment_methods,
            "payment_details": payload.payment_details,
            "terms": payload.terms,
            "is_active": True
        }).execute()

        # ── Fetch created row separately ───────────────────────
        created = supabase.table("p2p_listings") \
            .select("*") \
            .eq("merchant_id", merchant_id) \
            .eq("token", payload.token) \
            .eq("fiat_currency", payload.fiat_currency) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        if not created.data or len(created.data) == 0:
            raise Exception("Listing not found after insert")

        # created.data is a LIST — access with [0]
        listing = created.data[0]

        logger.info(f"[P2P] Listing created: {listing['id']}")
        return {"success": True, "listing": listing}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[P2P] Create listing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create listing")


# ── PATCH /api/p2p/listings/{listing_id}/toggle ──────────────
@router.patch("/listings/{listing_id}/toggle")
async def toggle_listing(
    listing_id: str,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    try:
        listing = supabase.table("p2p_listings") \
            .select("id, is_active, merchant_id") \
            .eq("id", listing_id) \
            .limit(1).execute()

        if not listing.data or len(listing.data) == 0:
            raise HTTPException(status_code=404, detail="Listing not found")

        m = supabase.table("p2p_merchants") \
            .select("id").eq("id", listing.data[0]["merchant_id"]) \
            .eq("user_id", current_user["id"]) \
            .limit(1).execute()
        if not m.data or len(m.data) == 0:
            raise HTTPException(status_code=403, detail="Access denied")

        new_status = not listing.data[0]["is_active"]
        supabase.table("p2p_listings").update({
            "is_active": new_status
        }).eq("id", listing_id).execute()

        return {"success": True, "is_active": new_status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to toggle listing")


# ── DELETE /api/p2p/listings/{listing_id} ────────────────────
@router.delete("/listings/{listing_id}")
async def delete_listing(
    listing_id: str,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    try:
        listing = supabase.table("p2p_listings") \
            .select("id, merchant_id").eq("id", listing_id) \
            .limit(1).execute()

        if not listing.data or len(listing.data) == 0:
            raise HTTPException(status_code=404, detail="Listing not found")

        m = supabase.table("p2p_merchants") \
            .select("id").eq("id", listing.data[0]["merchant_id"]) \
            .eq("user_id", current_user["id"]) \
            .limit(1).execute()
        if not m.data or len(m.data) == 0:
            raise HTTPException(status_code=403, detail="Access denied")

        supabase.table("p2p_listings").delete().eq("id", listing_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete listing")
    
class UpdateListingRequest(BaseModel):
    price_per_token:  Optional[float] = None
    min_order_fiat:   Optional[float] = None
    max_order_fiat:   Optional[float] = None
    available_amount: Optional[float] = None
    terms:            Optional[str]   = None

@router.patch("/listings/{listing_id}/price")
async def update_listing(
    listing_id: str,
    payload: UpdateListingRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Merchant updates price and/or limits on any listing (buy or sell).
    Only non-None fields are updated — partial update safe.
    Registered early (before sell routes) to guarantee route registration.
    """
    try:
        # Verify ownership via merchant join
        listing_res = supabase.table("p2p_listings") \
            .select("id, merchant_id") \
            .eq("id", listing_id) \
            .limit(1).execute()

        if not listing_res.data:
            raise HTTPException(status_code=404, detail="Listing not found")

        merchant_res = supabase.table("p2p_merchants") \
            .select("id") \
            .eq("id", listing_res.data[0]["merchant_id"]) \
            .eq("user_id", current_user["id"]) \
            .limit(1).execute()

        if not merchant_res.data:
            raise HTTPException(status_code=403, detail="Access denied")

        # Build update dict — only fields explicitly provided
        updates: dict = {
            k: v for k, v in {
                "price_per_token":  payload.price_per_token,
                "min_order_fiat":   payload.min_order_fiat,
                "max_order_fiat":   payload.max_order_fiat,
                "available_amount": payload.available_amount,
                "terms":            payload.terms,
            }.items() if v is not None
        }

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Validate min < max if both provided
        if "min_order_fiat" in updates and "max_order_fiat" in updates:
            if updates["min_order_fiat"] >= updates["max_order_fiat"]:
                raise HTTPException(
                    status_code=400,
                    detail="min_order_fiat must be less than max_order_fiat"
                )

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        supabase.table("p2p_listings") \
            .update(updates) \
            .eq("id", listing_id) \
            .execute()

        logger.info(
            f"[P2P] Listing {listing_id} updated by {current_user['id']}: "
            f"{list(updates.keys())}"
        )
        return {"success": True, "updated_fields": list(updates.keys())}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[P2P] Update listing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update listing")


# ── REQUEST MODELS ────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    idempotency_key: str
    listing_id: str
    fiat_amount: float
    payment_method: str


# ── GET /api/p2p/orders/{order_id} ───────────────────────────
# Fetch a single order (buyer or merchant only).
# Frontend uses Supabase Realtime for live updates,
# this endpoint is used for the initial page load.
@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    try:
        result = supabase.table("p2p_orders") \
            .select("*, p2p_merchants(*), p2p_listings(payment_details)") \
            .eq("id", order_id) \
            .limit(1) \
            .execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Order not found")

        order = result.data[0]
        user_id = current_user["id"]

        # Verify caller is buyer or merchant — no peeking at other people's orders
        merchant_user_id = (order.get("p2p_merchants") or {}).get("user_id")
        if order["buyer_id"] != user_id and merchant_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return {"success": True, "order": order}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[P2P] Get order error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch order")


# ── POST /api/p2p/orders ─────────────────────────────────────
@router.post("/orders")
async def create_order(
    payload: CreateOrderRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        result = await create_p2p_order(
            idempotency_key=payload.idempotency_key,
            listing_id=payload.listing_id,
            buyer_id=current_user["id"],
            fiat_amount=payload.fiat_amount,
            payment_method=payload.payment_method
        )
        return {
            "success": True,
            "order": result["order"],
            "payment_details": result["payment_details"],
            "is_duplicate": result["is_duplicate"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[P2P] Create order error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create order")


# ── POST /api/p2p/orders/receipt-upload ──────────────────────
# Buyer uploads payment receipt image.
# Mirrors the compliance.py upload pattern exactly:
#   supabase.storage.from_("p2p-receipts").upload(path, file_bytes)
@router.post("/orders/receipt-upload")
async def upload_receipt(
    file: UploadFile = File(...),
    order_id: str = Form(...),
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    try:
        user_id = current_user["id"]

        # Verify order belongs to buyer and is in payment_window
        order_res = supabase.table("p2p_orders") \
            .select("id, status, buyer_id") \
            .eq("id", order_id) \
            .eq("buyer_id", user_id) \
            .limit(1) \
            .execute()

        if not order_res.data or len(order_res.data) == 0:
            raise HTTPException(status_code=404, detail="Order not found")

        if order_res.data[0]["status"] != "payment_window":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot upload receipt for order in '{order_res.data[0]['status']}' status"
            )

        # Read file
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/webp", "application/pdf"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Use: JPEG, PNG, WebP, or PDF"
            )

        # Build storage path — mirrors compliance.py pattern
        file_ext = (file.filename or "receipt").split(".")[-1]
        file_path = f"{user_id}/receipts/{uuid.uuid4()}.{file_ext}"

        # Upload to Supabase storage bucket
        try:
            upload_response = supabase.storage.from_("p2p-receipts").upload(
                path=file_path,
                file=file_bytes,
                file_options={"content-type": file.content_type}
            )
            if hasattr(upload_response, "error") and upload_response.error:
                raise Exception(f"Storage error: {upload_response.error}")
        except Exception as storage_err:
            logger.error(f"[P2P] Storage upload failed: {storage_err}")
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")

        # Get public URL — same pattern as compliance.py
        try:
            file_url = supabase.storage.from_("p2p-receipts").get_public_url(file_path)
        except Exception:
            project_ref = supabase.url.split("//")[1].split(".")[0]
            file_url = f"https://{project_ref}.supabase.co/storage/v1/object/public/p2p-receipts/{file_path}"

        # Update order with receipt URL and advance status to 'paid'
        await confirm_payment_sent(
            order_id=order_id,
            buyer_id=user_id,
            receipt_url=file_url
        )

        logger.info(f"[P2P] Receipt uploaded for order {order_id}")
        return {"success": True, "receipt_url": file_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[P2P] Receipt upload error: {e}")
        raise HTTPException(status_code=500, detail="Receipt upload failed")


# ── PATCH /api/p2p/orders/{order_id}/release ─────────────────
@router.patch("/orders/{order_id}/release")
async def release_tokens(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        result = await merchant_confirm_and_release(
            order_id=order_id,
            merchant_user_id=current_user["id"]
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[P2P] Release tokens error: {e}")
        raise HTTPException(status_code=500, detail="Failed to release tokens")


# ── PATCH /api/p2p/orders/{order_id}/cancel ──────────────────
# Buyer cancels an order in payment_window status.
@router.patch("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    try:
        user_id = current_user["id"]

        order_res = supabase.table("p2p_orders") \
            .select("id, status, buyer_id") \
            .eq("id", order_id) \
            .eq("buyer_id", user_id) \
            .limit(1) \
            .execute()

        if not order_res.data or len(order_res.data) == 0:
            raise HTTPException(status_code=404, detail="Order not found")

        if order_res.data[0]["status"] != "payment_window":
            raise HTTPException(
                status_code=400,
                detail="Only orders in payment_window can be cancelled"
            )

        from datetime import datetime, timezone
        supabase.table("p2p_orders").update({
            "status": "cancelled",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", order_id).execute()

        supabase.table("p2p_messages").insert({
            "order_id": order_id,
            "is_system": True,
            "message": "Buyer cancelled the order."
        }).execute()

        # Audit
        supabase.table("settlement_audit_log").insert({
            "order_id": order_id,
            "event_type": "state_change",
            "prev_status": "payment_window",
            "new_status": "cancelled",
            "actor_id": user_id
        }).execute()

        logger.info(f"[P2P] Order {order_id} cancelled by buyer")
        return {"success": True, "message": "Order cancelled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[P2P] Cancel order error: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel order")

# ── New Pydantic models ───────────────────────────────────────

class CreateSellOrderRequest(BaseModel):
    idempotency_key: str
    listing_id: str
    fiat_amount: float
    payment_method: str
    payout_details: Dict[str, Any]


class SellerTokenSentRequest(BaseModel):
    token_tx_hash: str


class CreateSellListingRequest(BaseModel):
    merchant_id: str
    token: str
    fiat_currency: str
    price_per_token: float
    min_order_fiat: float
    max_order_fiat: float
    available_amount: float          # available fiat to deploy
    payment_methods: List[str]
    payment_details: Dict[str, Any]  # how merchant pays fiat to sellers
    merchant_receive_address: Optional[str] = None
    terms: Optional[str] = None


# ── GET /api/p2p/sell/listings ────────────────────────────────
@router.get("/sell/listings")
async def get_sell_listings(
    token: Optional[str] = None,
    fiat_currency: Optional[str] = None,
    supabase=Depends(get_supabase_client)
):
    """Public — returns active sell listings (merchants buying tokens)."""
    try:
        query = supabase.table("p2p_listings") \
            .select("*, p2p_merchants(display_name,verified,total_orders,completion_rate,avg_release_time_mins,is_online)") \
            .eq("listing_type", "sell") \
            .eq("is_active", True) \
            .order("created_at", desc=True)

        if token:
            query = query.eq("token", token)
        if fiat_currency:
            query = query.eq("fiat_currency", fiat_currency)

        res = query.execute()
        return {"success": True, "listings": res.data or []}
    except Exception as e:
        logger.error(f"[P2P] Get sell listings error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch sell listings")


# ── POST /api/p2p/sell/listings ───────────────────────────────
@router.post("/sell/listings")
async def create_sell_listing(
    payload: CreateSellListingRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """Merchant creates a sell listing (they want to buy tokens, will pay fiat)."""
    try:
        m = supabase.table("p2p_merchants") \
            .select("id, status") \
            .eq("id", payload.merchant_id) \
            .eq("user_id", current_user["id"]) \
            .limit(1).execute()
        if not m.data:
            raise HTTPException(status_code=403, detail="Access denied")
        if m.data[0].get("status") != "approved":
            raise HTTPException(status_code=403, detail="Merchant account not approved")

        supabase.table("p2p_listings").insert({
            "merchant_id":              payload.merchant_id,
            "listing_type":             "sell",
            "token":                    payload.token,
            "fiat_currency":            payload.fiat_currency,
            "price_per_token":          payload.price_per_token,
            "min_order_fiat":           payload.min_order_fiat,
            "max_order_fiat":           payload.max_order_fiat,
            "available_amount":         payload.available_amount,
            "payment_methods":          payload.payment_methods,
            "payment_details":          payload.payment_details,
            "merchant_receive_address": payload.merchant_receive_address,
            "terms":                    payload.terms,
            "is_active":                True,
        }).execute()

        created = supabase.table("p2p_listings") \
            .select("*") \
            .eq("merchant_id", payload.merchant_id) \
            .eq("listing_type", "sell") \
            .eq("token", payload.token) \
            .order("created_at", desc=True) \
            .limit(1).execute()

        if not created.data:
            raise Exception("Listing not found after insert")

        return {"success": True, "listing": created.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[P2P] Create sell listing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create sell listing")


# ── POST /api/p2p/sell/orders ─────────────────────────────────
@router.post("/sell/orders")
async def create_sell_order_endpoint(
    payload: CreateSellOrderRequest,
    current_user: dict = Depends(get_current_user),
    wallet_service=Depends(get_multi_chain_wallet_service),
    supabase=Depends(get_supabase_client)
):
    try:
        user_id = current_user["id"]

        # ── Balance pre-check ─────────────────────────────────
        # Resolve which chain/token the listing uses
        listing_res = supabase.table("p2p_listings") \
            .select("token, price_per_token") \
            .eq("id", payload.listing_id) \
            .limit(1).execute()

        if not listing_res.data:
            raise HTTPException(status_code=404, detail="Listing not found")

        token        = listing_res.data[0]["token"]
        token_needed = payload.fiat_amount / listing_res.data[0]["price_per_token"]

        # Fetch live balances from Seamount wallet
        try:
            balances     = await wallet_service.get_user_balances(user_id)
            assets       = {a["symbol"]: a["balance"] for a in balances.get("assets", [])}
            token_symbol = token.split("_")[0]   # e.g. USDT_TRON → USDT

            # Check both the full key (e.g. USDT_TRON) and the base symbol (USDT)
            available = assets.get(token, assets.get(token_symbol, 0))

            if available < token_needed:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Insufficient balance. You need {token_needed:.6f} {token_symbol} "
                        f"but your Seamount wallet only has {available:.6f} {token_symbol}. "
                        f"Please buy or deposit {token_symbol} to your wallet first."
                    )
                )
        except HTTPException:
            raise
        except Exception as bal_err:
            # Balance check failed — log but don't block order creation
            logger.warning(f"[P2P] Balance pre-check failed (non-blocking): {bal_err}")

        # ── Create order ──────────────────────────────────────
        result = await create_sell_order(
            idempotency_key=payload.idempotency_key,
            listing_id=payload.listing_id,
            seller_id=user_id,
            fiat_amount=payload.fiat_amount,
            payment_method=payload.payment_method,
            payout_details=payload.payout_details,
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[P2P] Create sell order error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create sell order")

# ── PATCH /api/p2p/sell/orders/{order_id}/token-sent ─────────
@router.patch("/sell/orders/{order_id}/release-tokens")
async def seller_release_tokens(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Seller authorises Seamount to transfer their tokens to the merchant."""
    try:
        from backend.services.p2p.order_service import seller_authorize_token_release
        result = await seller_authorize_token_release(
            order_id=order_id,
            seller_id=current_user["id"],
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[P2P] Seller release tokens error: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate token transfer")


# ── POST /api/p2p/sell/orders/{order_id}/fiat-proof ──────────
@router.post("/sell/orders/{order_id}/fiat-proof")
async def upload_fiat_proof(
    order_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """Merchant uploads proof of fiat payment."""
    try:
        merchant_res = supabase.table("p2p_merchants") \
            .select("id").eq("user_id", current_user["id"]).limit(1).execute()
        if not merchant_res.data:
            raise HTTPException(status_code=403, detail="Merchant not found")
        merchant_id = merchant_res.data[0]["id"]

        order_res = supabase.table("p2p_orders") \
            .select("id, status, order_type") \
            .eq("id", order_id).eq("merchant_id", merchant_id) \
            .eq("order_type", "sell").limit(1).execute()
        if not order_res.data:
            raise HTTPException(status_code=404, detail="Order not found")
        if order_res.data[0]["status"] != "paid":
            raise HTTPException(status_code=400, detail="Order not in correct state for fiat proof")

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="File is empty")

        file_ext  = (file.filename or "proof").split(".")[-1]
        file_path = f"{current_user['id']}/fiat-proofs/{uuid.uuid4()}.{file_ext}"

        supabase.storage.from_("p2p-receipts").upload(
            path=file_path, file=file_bytes,
            file_options={"content-type": file.content_type}
        )

        try:
            file_url = supabase.storage.from_("p2p-receipts").get_public_url(file_path)
        except Exception:
            project_ref = supabase.url.split("//")[1].split(".")[0]
            file_url = f"https://{project_ref}.supabase.co/storage/v1/object/public/p2p-receipts/{file_path}"

        from backend.services.p2p.order_service import merchant_confirm_fiat_sent
        result = await merchant_confirm_fiat_sent(
            order_id=order_id,
            merchant_user_id=current_user["id"],
            fiat_proof_url=file_url,
        )
        return {"success": True, "fiat_proof_url": file_url, **result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[P2P] Fiat proof upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload fiat proof")


# ── PATCH /api/p2p/sell/orders/{order_id}/fiat-received ──────
@router.patch("/sell/orders/{order_id}/fiat-received")
async def seller_fiat_received(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        from backend.services.p2p.order_service import seller_confirm_fiat_received
        result = await seller_confirm_fiat_received(
            order_id=order_id,
            seller_id=current_user["id"],
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[P2P] Seller fiat received error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete order") 

@router.patch("/sell/orders/{order_id}/cancel")
async def cancel_sell_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """Seller cancels a sell order still in payment_window."""
    try:
        user_id = current_user["id"]

        order_res = supabase.table("p2p_orders") \
            .select("id, status, buyer_id, order_type") \
            .eq("id", order_id) \
            .eq("buyer_id", user_id) \
            .eq("order_type", "sell") \
            .limit(1).execute()

        if not order_res.data:
            raise HTTPException(status_code=404, detail="Order not found")

        if order_res.data[0]["status"] != "payment_window":
            raise HTTPException(
                status_code=400,
                detail="Only orders awaiting token release can be cancelled"
            )

        supabase.table("p2p_orders").update({
            "status":     "cancelled",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", order_id).execute()

        supabase.table("p2p_messages").insert({
            "order_id": order_id, "is_system": True,
            "message":  "Seller cancelled the order."
        }).execute()

        supabase.table("settlement_audit_log").insert({
            "order_id":    order_id,
            "event_type":  "state_change",
            "prev_status": "payment_window",
            "new_status":  "cancelled",
            "actor_id":    user_id
        }).execute()

        logger.info(f"[P2P] Sell order {order_id} cancelled by seller")
        return {"success": True, "message": "Order cancelled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[P2P] Cancel sell order error: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel order")
