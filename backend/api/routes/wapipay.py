# File: backend/api/routes/wapipay.py
"""
WapiPay Routes
  GET  /api/v1/wapipay/virtual-account      — get/create NGN virtual account
  POST /api/v1/wapipay/quote                — corridor quote
  POST /api/v1/wapipay/offramp/bank         — bank offramp
  POST /api/v1/wapipay/offramp/mobile       — mobile money offramp
  POST /api/v1/wapipay/webhook/collection   — virtual account funded webhook
  POST /api/v1/wapipay/webhook/payment      — payment order webhook
"""
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.config import get_settings
from backend.dependencies import get_current_user, get_db_service, get_audit_service
from backend.services.wapipay_service import WapiPayService

router = APIRouter(prefix="/wapipay", tags=["WapiPay"])
logger = logging.getLogger(__name__)


# ── Service factory ────────────────────────────────────────────────────────────

def _wapipay() -> WapiPayService:
    s = get_settings()
    missing = [k for k, v in {
        "WAPIPAY_CLIENT_ID":     getattr(s, "WAPIPAY_CLIENT_ID", None),
        "WAPIPAY_CLIENT_SECRET": getattr(s, "WAPIPAY_CLIENT_SECRET", None),
    }.items() if not v]
    if missing:
        raise HTTPException(500, f"WapiPay not configured. Missing: {', '.join(missing)}")
    secret_val = s.WAPIPAY_CLIENT_SECRET
    if hasattr(secret_val, "get_secret_value"):
        secret_val = secret_val.get_secret_value()
    return WapiPayService(
        client_id=s.WAPIPAY_CLIENT_ID,
        client_secret=secret_val,
        environment=getattr(s, "WAPIPAY_ENVIRONMENT", "sandbox"),
        webhook_secret=getattr(s, "WAPIPAY_WEBHOOK_SECRET", ""),
    )


# ── Request models ─────────────────────────────────────────────────────────────

class QuoteRequest(BaseModel):
    country: str
    currency: str
    amount: float
    channel_type: int = 175  # 1=bank, 175=mobile


class BankOfframpRequest(BaseModel):
    crypto_asset:       str
    crypto_amount:      float
    currency:           str
    country:            str
    account_number:     str
    account_name:       str
    bank_code:          str


class MobileOfframpRequest(BaseModel):
    crypto_asset:  str
    crypto_amount: float
    currency:      str
    country:       str
    phone_number:  str
    network:       str   # "MPESA" | "MTN" | etc.


# ── Virtual Account ────────────────────────────────────────────────────────────

@router.get("/virtual-account")
async def get_or_create_virtual_account(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_service),
):
    """
    Idempotent — returns existing NGN virtual account or creates one.
    Used by FundWalletModal (wapipay provider tab).
    """
    user_id = current_user["id"]

    # Check for existing
    existing = db.supabase.from_("wapipay_virtual_accounts") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("currency", "NGN") \
        .eq("status", "active") \
        .limit(1).execute()

    if existing.data:
        va = existing.data[0]
        return {
            "success":        True,
            "is_new":         False,
            "account_number": va["account_number"],
            "account_name":   va["account_name"],
            "bank_name":      va["bank_name"],
            "currency":       "NGN",
            "instruction":    "Transfer any amount to this account to top up your Seamount wallet.",
        }

    # Create new
    svc   = _wapipay()
    name  = f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip() or "Seamount User"
    email = current_user.get("email", "")

    result = await svc.create_virtual_account(user_id, name, email)
    if not result["success"]:
        raise HTTPException(503, f"Could not create virtual account: {result.get('error')}")

    raw = result["data"]
    # Normalise — WapiPay sandbox may return nested structure; adjust field names at go-live
    account_data = {
        "user_id":        user_id,
        "account_number": raw.get("accountNumber") or raw.get("account_number", ""),
        "account_name":   raw.get("accountName")   or raw.get("account_name", name),
        "bank_name":      raw.get("bankName")       or raw.get("bank_name", "WapiPay Bank"),
        "bank_code":      raw.get("bankCode")       or raw.get("bank_code", ""),
        "currency":       "NGN",
        "status":         "active",
        "raw_data":       raw,
    }

    try:
        db.supabase.from_("wapipay_virtual_accounts").insert(account_data).execute()
        logger.info("✅ Virtual account stored for user %s", user_id[:8])
    except Exception as e:
        logger.error("❌ Failed to store virtual account: %s", e)

    return {
        "success":        True,
        "is_new":         True,
        "account_number": account_data["account_number"],
        "account_name":   account_data["account_name"],
        "bank_name":      account_data["bank_name"],
        "currency":       "NGN",
        "instruction":    "Transfer any amount to this account to top up your Seamount wallet.",
    }


# ── Quote ──────────────────────────────────────────────────────────────────────

@router.post("/quote")
async def get_quote(req: QuoteRequest):
    """Corridor quote — fee-inclusive. No auth needed for preview."""
    svc = _wapipay()
    result = await svc.get_corridor_quote(
        country=req.country,
        channel_type=req.channel_type,
        amount=req.amount,
        currency=req.currency,
    )
    if not result["success"]:
        raise HTTPException(503, result.get("error", "Quote failed"))
    return result


# ── Offramp: Bank ──────────────────────────────────────────────────────────────

@router.post("/offramp/bank")
async def bank_offramp(
    req: BankOfframpRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_service),
    audit_service=Depends(get_audit_service),
):
    user_id   = current_user["id"]
    reference = f"WP_BANK_{user_id[:8]}_{int(datetime.now().timestamp())}"

    # Load compliance profile
    profile = db.supabase.from_("user_compliance_profiles") \
        .select("*").eq("user_id", user_id).limit(1).execute()
    if not profile.data:
        raise HTTPException(400, "Compliance profile required. Please complete KYC first.")
    p = profile.data[0]

    svc = _wapipay()
    result = await svc.bank_payment(
        amount=req.crypto_amount,  # converted to fiat upstream by offramp route — pass fiat here
        currency=req.currency,
        country=req.country,
        account_number=req.account_number,
        account_name=req.account_name,
        bank_swift_or_code=req.bank_code,
        remitter_name=f"{current_user.get('first_name','')} {current_user.get('last_name','')}".strip(),
        remitter_id=p.get("id_number", ""),
        remitter_phone=p.get("phone_number", ""),
        reference=reference,
    )

    if not result["success"]:
        raise HTTPException(503, f"WapiPay bank payment failed: {result.get('error')}")

    # Record transaction
    tx_id = str(uuid.uuid4())
    try:
        db.supabase.from_("wapipay_transactions").insert({
            "id":                 tx_id,
            "user_id":            user_id,
            "type":               "offramp",
            "status":             "processing",
            "originator_id":      reference,
            "amount":             req.crypto_amount,
            "currency":           req.currency,
            "crypto_asset":       req.crypto_asset,
            "recipient_details":  {"account_number": req.account_number, "bank_code": req.bank_code},
            "provider_response":  result["data"],
            "created_at":         datetime.now().isoformat(),
        }).execute()
    except Exception as e:
        logger.error("❌ Failed to record wapipay tx: %s", e)

    return {"success": True, "transaction_id": tx_id, "reference": reference, "status": "processing"}


# ── Offramp: Mobile ────────────────────────────────────────────────────────────

@router.post("/offramp/mobile")
async def mobile_offramp(
    req: MobileOfframpRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_service),
):
    user_id   = current_user["id"]
    reference = f"WP_MOB_{user_id[:8]}_{int(datetime.now().timestamp())}"

    profile = db.supabase.from_("user_compliance_profiles") \
        .select("*").eq("user_id", user_id).limit(1).execute()
    if not profile.data:
        raise HTTPException(400, "KYC required before withdrawing.")
    p = profile.data[0]

    svc    = _wapipay()
    result = await svc.mobile_payment(
        amount=req.crypto_amount,
        currency=req.currency,
        country=req.country,
        phone_number=req.phone_number,
        network=req.network,
        recipient_name=current_user.get("first_name", "User"),
        remitter_name=f"{current_user.get('first_name','')} {current_user.get('last_name','')}".strip(),
        remitter_id=p.get("id_number", ""),
        remitter_phone=p.get("phone_number", ""),
        reference=reference,
    )

    if not result["success"]:
        raise HTTPException(503, f"WapiPay mobile payment failed: {result.get('error')}")

    tx_id = str(uuid.uuid4())
    try:
        db.supabase.from_("wapipay_transactions").insert({
            "id":                tx_id,
            "user_id":           user_id,
            "type":              "offramp",
            "status":            "processing",
            "originator_id":     reference,
            "amount":            req.crypto_amount,
            "currency":          req.currency,
            "crypto_asset":      req.crypto_asset,
            "recipient_details": {"phone": req.phone_number, "network": req.network},
            "provider_response": result["data"],
            "created_at":        datetime.now().isoformat(),
        }).execute()
    except Exception as e:
        logger.error("❌ Failed to record wapipay tx: %s", e)

    return {"success": True, "transaction_id": tx_id, "reference": reference, "status": "processing"}


# ── Webhooks ───────────────────────────────────────────────────────────────────

@router.post("/webhook/collection")
async def webhook_collection(request: Request, db=Depends(get_db_service)):
    """
    Virtual account funded (NGN onramp).
    WapiPay calls this when funds hit the virtual account.
    🚨 IMPORTANT: Return 200 immediately; credit async.
    """
    raw      = await request.body()
    sig      = request.headers.get("x-wapipay-signature", "")
    svc      = _wapipay()

    if sig and not svc.verify_webhook(raw, sig):
        logger.warning("❌ WapiPay collection webhook: invalid signature")
        raise HTTPException(401, "Invalid signature")

    import json
    payload = json.loads(raw)
    logger.info("📨 WapiPay collection webhook: %s", payload.get("TransactionId", "?"))

    session_id = payload.get("TransactionId") or payload.get("sessionId", "")
    amount     = float(payload.get("Amount", 0))
    account_no = payload.get("AccountNumber", "")

    # Deduplicate
    exists = db.supabase.from_("wapipay_transactions") \
        .select("id").eq("session_id", session_id).limit(1).execute()
    if exists.data:
        logger.info("⚠️ Duplicate webhook for session %s — ignoring", session_id)
        return {"status": "ok"}

    # Find user by virtual account
    va = db.supabase.from_("wapipay_virtual_accounts") \
        .select("user_id").eq("account_number", account_no).limit(1).execute()
    user_id = va.data[0]["user_id"] if va.data else None

    # Record pending credit — background job handles actual wallet credit
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
        logger.info("✅ Collection webhook queued for credit: %s NGN → user %s", amount, str(user_id)[:8] if user_id else "?")
    except Exception as e:
        logger.error("❌ Failed to queue webhook credit: %s", e)

    return {"status": "ok"}


@router.post("/webhook/payment")
async def webhook_payment(request: Request, db=Depends(get_db_service)):
    """
    Payment order status update (offramp).
    WapiPay sends 2 callbacks for Express Deposit — only trust the second.
    """
    raw     = await request.body()
    sig     = request.headers.get("x-wapipay-signature", "")
    svc     = _wapipay()

    if sig and not svc.verify_webhook(raw, sig):
        raise HTTPException(401, "Invalid signature")

    import json
    payload    = json.loads(raw)
    session_id = payload.get("systemConversationId") or payload.get("TransactionId", "")
    status_raw = str(payload.get("status", "")).lower()
    status     = "completed" if "success" in status_raw or "complete" in status_raw else \
                 "failed"    if "fail"    in status_raw or "error"    in status_raw else \
                 "processing"

    logger.info("📨 WapiPay payment webhook: session=%s status=%s", session_id, status)

    try:
        db.supabase.from_("wapipay_transactions") \
            .update({
                "status":       status,
                "webhook_data": payload,
                "updated_at":   datetime.now().isoformat(),
            }) \
            .eq("originator_id", payload.get("originatorConversationId", "")) \
            .execute()
    except Exception as e:
        logger.error("❌ Failed to update payment webhook status: %s", e)

    return {"status": "ok"}