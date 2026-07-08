# File: backend/api/routes/wapipay_webhooks.py
"""
WapiPay Webhooks — mounted at the exact paths already registered
on the WapiPay dashboard:
  POST /webhooks/wapipay/collections   (virtual account funded — onramp)
  POST /webhooks/wapipay/payouts       (bank/mobile payment order status — offramp)
"""
import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.dependencies import get_db_service
from backend.services.wapipay_service import WapiPayService
from backend.config import get_settings

router = APIRouter(prefix="/webhooks/wapipay", tags=["WapiPay Webhooks"])
logger = logging.getLogger(__name__)


def _wapipay() -> WapiPayService:
    s = get_settings()
    secret_val = getattr(s, "WAPIPAY_CLIENT_SECRET", None)
    if hasattr(secret_val, "get_secret_value"):
        secret_val = secret_val.get_secret_value()
    return WapiPayService(
        client_id=getattr(s, "WAPIPAY_CLIENT_ID", ""),
        client_secret=secret_val or "",
        environment=getattr(s, "WAPIPAY_ENVIRONMENT", "sandbox"),
        webhook_secret=getattr(s, "WAPIPAY_WEBHOOK_SECRET", ""),
    )


@router.post("/collections")
async def collections_webhook(request: Request, db=Depends(get_db_service)):
    """Virtual account funded (NGN onramp). Return 200 fast; credit async."""
    raw = await request.body()
    sig = request.headers.get("x-wapipay-signature", "")
    svc = _wapipay()

    if sig and not svc.verify_webhook(raw, sig):
        logger.warning("❌ Collections webhook: invalid signature")
        raise HTTPException(401, "Invalid signature")

    payload    = json.loads(raw)
    session_id = payload.get("TransactionId") or payload.get("sessionId", "")
    amount     = float(payload.get("Amount", 0))
    account_no = payload.get("AccountNumber", "")

    logger.info("📨 WapiPay collections webhook: session=%s amount=%s", session_id, amount)

    exists = db.supabase.from_("wapipay_transactions") \
        .select("id").eq("session_id", session_id).limit(1).execute()
    if exists.data:
        logger.info("⚠️ Duplicate collections webhook %s — ignoring", session_id)
        return {"status": "ok"}

    va = db.supabase.from_("wapipay_virtual_accounts") \
        .select("user_id").eq("account_number", account_no).limit(1).execute()
    user_id = va.data[0]["user_id"] if va.data else None

    try:
        db.supabase.from_("wapipay_transactions").insert({
            "id":           str(uuid.uuid4()),
            "user_id":      user_id,
            "type":         "onramp",
            "status":       "pending_credit",
            "session_id":   session_id,
            "amount":       amount,
            "currency":     "NGN",
            "webhook_data": payload,
            "created_at":   datetime.now().isoformat(),
        }).execute()
        logger.info("✅ Collections webhook queued for credit: %s NGN → user %s", amount, str(user_id)[:8] if user_id else "?")
    except Exception as e:
        logger.error("❌ Failed to queue collections credit: %s", e)

    return {"status": "ok"}


@router.post("/payouts")
async def payouts_webhook(request: Request, db=Depends(get_db_service)):
    """
    Payment order status (offramp — bank + mobile).
    🚨 Express Deposit sends 2 callbacks — only the terminal status matters;
    we just overwrite status each time so the last write naturally wins.
    """
    raw = await request.body()
    sig = request.headers.get("x-wapipay-signature", "")
    svc = _wapipay()

    if sig and not svc.verify_webhook(raw, sig):
        logger.warning("❌ Payouts webhook: invalid signature")
        raise HTTPException(401, "Invalid signature")

    payload    = json.loads(raw)
    originator = payload.get("originatorConversationId", "")
    status_raw = str(payload.get("status", "")).lower()
    status     = "completed" if "success" in status_raw or "complete" in status_raw else \
                 "failed"    if "fail"    in status_raw or "error"    in status_raw else \
                 "processing"

    logger.info("📨 WapiPay payouts webhook: originator=%s status=%s", originator, status)

    try:
        db.supabase.from_("wapipay_transactions") \
            .update({
                "status":       status,
                "webhook_data": payload,
                "updated_at":   datetime.now().isoformat(),
            }) \
            .eq("originator_id", originator) \
            .execute()
    except Exception as e:
        logger.error("❌ Failed to update payouts webhook status: %s", e)

    return {"status": "ok"}