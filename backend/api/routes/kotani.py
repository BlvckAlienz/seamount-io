# File: backend/api/routes/kotani.py
"""
Kotani Pay Routes
  POST /api/v1/kotani/onramp/quote       — rate quote with markup
  POST /api/v1/kotani/onramp/initialize  — mobile money STK push initiation
  POST /api/v1/kotani/offramp/quote      — offramp quote with markup
  POST /api/v1/kotani/offramp/initialize — crypto → mobile money offramp
  POST /api/v1/kotani/webhook            — Kotani event handler
  GET  /api/v1/kotani/networks/{currency} — supported mobile networks
  GET  /api/v1/kotani/transaction/{ref}  — transaction status

Fixed vs original:
  [1] onramp_quote:       get_onramp_rate(currency, token) → get_onramp_rate(currency, token, fiat_amount)
  [2] offramp_quote:      get_offramp_rate(token, currency) → get_offramp_rate(token, currency, crypto_amount)
  [3] onramp_initialize:  ensure_customer & initiate_onramp arg names aligned to new service signature
  [4] offramp_initialize: ensure_customer & initiate_offramp arg names aligned to new service signature
  [5] /telcos/{currency}: get_supported_telcos → get_supported_networks (renamed in service)
  [6] rate parsing:       use correct response fields (value, cryptoAmount, fiatAmount) with fallback chain
  [7] _seamount key:      offramp result now keyed under result["_seamount"] not top-level
"""
import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.config import get_settings
from backend.dependencies import get_current_user, get_db_service
from backend.services.ramp_router import get_kotani_service, MARKUP_PCT
from backend.services.kotani_service import SEAMOUNT_TO_KOTANI, KotaniError

router = APIRouter(prefix="/kotani", tags=["Kotani Pay"])
logger = logging.getLogger(__name__)

CALLBACK_BASE = "https://seamount-main.onrender.com/api/v1/kotani/webhook"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _svc():
    return get_kotani_service(get_settings())


def _customer_key(user_id: str) -> str:
    """Stable Kotani customer key derived from Seamount user_id."""
    return f"seamount_{user_id.replace('-', '')[:24]}"


def _parse_rate(rate_data: dict, field: str) -> Decimal:
    """
    Safely extract a numeric rate from Kotani rate response.
    Kotani returns: { value, cryptoAmount, fiatAmount, transactionAmount, fee }
    Falls back through likely field names; raises HTTPException if none found.
    """
    for key in (field, "value", "cryptoAmount", "fiatAmount", "rate"):
        v = rate_data.get(key)
        if v is not None:
            try:
                d = Decimal(str(v))
                if d > 0:
                    return d
            except Exception:
                continue
    logger.error("Cannot parse rate from Kotani response: %s", rate_data)
    raise HTTPException(502, "Invalid rate data received from Kotani.")


async def _wallet_for_asset(db, user_id: str, crypto_asset: str) -> str:
    from backend.services.moonpay_service import ASSET_TO_BLOCKCHAIN
    blockchain = ASSET_TO_BLOCKCHAIN.get(crypto_asset)
    if not blockchain:
        raise HTTPException(400, f"Unknown blockchain for asset: {crypto_asset}")
    if blockchain == "algorand":
        res = db.supabase.from_("user_wallets").select("algorand_address") \
            .eq("user_id", user_id).limit(1).execute()
        if not res.data:
            raise HTTPException(404, "Algorand wallet not found.")
        return res.data[0]["algorand_address"]
    res = db.supabase.from_("multi_chain_addresses").select("address") \
        .eq("user_id", user_id).eq("blockchain", blockchain).limit(1).execute()
    if not res.data:
        raise HTTPException(404, f"{blockchain} wallet not found.")
    return res.data[0]["address"]


# ── Request Models ─────────────────────────────────────────────────────────────

class OnrampQuoteReq(BaseModel):
    amount_fiat:  float
    currency:     str
    crypto_asset: str

class OnrampInitReq(BaseModel):
    amount_fiat:   float
    currency:      str
    crypto_asset:  str
    phone_number:  str
    network:       str          # e.g. MPESA, MTN — replaces telco_id
    account_name:  Optional[str] = None
    country_code:  Optional[str] = None  # ISO-2; auto-derived from currency if omitted

class OfframpQuoteReq(BaseModel):
    crypto_asset:  str
    crypto_amount: float
    currency:      str

class OfframpInitReq(BaseModel):
    crypto_asset:  str
    crypto_amount: float
    currency:      str
    phone_number:  str
    network:       str          # e.g. MPESA, MTN — replaces telco_id
    account_name:  Optional[str] = None
    country_code:  Optional[str] = None


# ── ONRAMP ─────────────────────────────────────────────────────────────────────

@router.post("/onramp/quote")
async def onramp_quote(
    req: OnrampQuoteReq,
    current_user: dict = Depends(get_current_user),
):
    """Return Kotani onramp rate with 2.5% markup applied to crypto received."""
    try:
        if req.crypto_asset not in SEAMOUNT_TO_KOTANI:
            raise HTTPException(400, f"Asset {req.crypto_asset} not supported by Kotani.")

        svc = _svc()
        _, token = SEAMOUNT_TO_KOTANI[req.crypto_asset]

        # FIX [1]: pass fiat_amount as third positional arg (POST body, not query params)
        rate_data = await svc.get_onramp_rate(req.currency, token, req.amount_fiat)

        # Kotani returns cryptoAmount = crypto you get for fiatAmount supplied
        # Use that directly; value = exchange rate per unit
        raw_rate     = _parse_rate(rate_data, "cryptoAmount")
        amount       = Decimal(str(req.amount_fiat))

        # gross_crypto is what Kotani would deliver; we present net after markup
        gross_crypto  = Decimal(str(rate_data.get("cryptoAmount", 0))) or (amount / raw_rate)
        markup_crypto = (gross_crypto * MARKUP_PCT).quantize(Decimal("0.000001"))
        net_crypto    = gross_crypto - markup_crypto

        return {
            "success":       True,
            "provider":      "kotani",
            "currency":      req.currency,
            "crypto_asset":  req.crypto_asset,
            "amount_fiat":   float(amount),
            "gross_crypto":  float(gross_crypto),
            "markup_pct":    float(MARKUP_PCT * 100),
            "markup_crypto": float(markup_crypto),
            "net_crypto":    float(net_crypto),
            "rate":          str(rate_data.get("value", raw_rate)),
            "rate_id":       rate_data.get("id"),   # pass back for locking on initialize
            "fee":           rate_data.get("fee"),
        }
    except HTTPException:
        raise
    except KotaniError as e:
        logger.error("Kotani onramp quote error: %s", e, exc_info=True)
        raise HTTPException(502, f"Quote failed: {e.message}")
    except Exception as e:
        logger.error("Kotani onramp quote error: %s", e, exc_info=True)
        raise HTTPException(500, f"Quote failed: {e}")


@router.post("/onramp/initialize")
async def onramp_initialize(
    req: OnrampInitReq,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_service),
):
    """
    Initiate Kotani onramp: triggers mobile money STK push on user's phone.
    Crypto delivered to user's on-chain wallet after payment confirmation.
    """
    try:
        if req.crypto_asset not in SEAMOUNT_TO_KOTANI:
            raise HTTPException(400, f"Asset {req.crypto_asset} not supported by Kotani.")

        from backend.services.kotani_service import CURRENCY_TO_COUNTRY
        svc          = _svc()
        wallet_addr  = await _wallet_for_asset(db, current_user["id"], req.crypto_asset)
        ref_id       = f"KOTANI_ONRAMP_{uuid.uuid4().hex[:16].upper()}"
        country_code = req.country_code or CURRENCY_TO_COUNTRY.get(req.currency.upper(), "")

        if not country_code:
            raise HTTPException(400, f"Cannot resolve country_code for currency {req.currency}. Pass it explicitly.")

        account_name = req.account_name or f"Seamount User {req.phone_number[-4:]}"

        # FIX [3]: new ensure_customer signature — phone_number, country_code, network, account_name
        await svc.ensure_customer(
            phone_number=req.phone_number,
            country_code=country_code,
            network=req.network,
            account_name=account_name,
            first_name=current_user.get("first_name", ""),
            last_name=current_user.get("last_name", ""),
            email=current_user.get("email", ""),
        )

        # FIX [3]: new initiate_onramp signature — receiver_address, network_provider, account_name
        result = await svc.initiate_onramp(
            reference_id=ref_id,
            fiat_amount=Decimal(str(req.amount_fiat)),
            fiat_currency=req.currency,
            crypto_asset=req.crypto_asset,
            receiver_address=wallet_addr,
            phone_number=req.phone_number,
            network_provider=req.network,
            account_name=account_name,
            callback_url=CALLBACK_BASE,
        )

        db.supabase.from_("onramp_transactions").insert({
            "id":                  ref_id,
            "user_id":             current_user["id"],
            "type":                "onramp",
            "status":              "pending_payment",
            "provider":            "kotani",
            "provider_name":       "Kotani Pay",
            "currency":            req.currency,
            "crypto_asset":        req.crypto_asset,
            "amount_fiat":         req.amount_fiat,
            "markup_pct":          float(MARKUP_PCT * 100),
            "seamount_fee":        0,
            "net_to_user":         req.amount_fiat,
            "wallet_address":      wallet_addr,
            "checkout_url":        None,
            "user_email":          current_user.get("email", ""),
            "user_country":        country_code,
            "kotani_reference_id": ref_id,
            "created_at":          datetime.now().isoformat(),
        }).execute()

        return {
            "success":     True,
            "tx_id":       ref_id,
            "provider":    "kotani",
            "pay_in_type": "stk_push",
            "pay_in_details": {
                "message":      f"Check your phone ({req.phone_number}) and approve the {req.network} payment request.",
                "phone_number": req.phone_number,
                "network":      req.network,
                "amount":       req.amount_fiat,
                "currency":     req.currency,
            },
            "status": result.get("status", "PENDING"),
        }

    except HTTPException:
        raise
    except KotaniError as e:
        logger.error("Kotani onramp init error: %s", e, exc_info=True)
        raise HTTPException(502, f"Onramp initialization failed: {e.message}")
    except Exception as e:
        logger.error("Kotani onramp init error: %s", e, exc_info=True)
        raise HTTPException(500, f"Onramp initialization failed: {e}")


# ── OFFRAMP ────────────────────────────────────────────────────────────────────

@router.post("/offramp/quote")
async def offramp_quote(
    req: OfframpQuoteReq,
    current_user: dict = Depends(get_current_user),
):
    """Return Kotani offramp quote with 2.5% markup deducted from crypto sent."""
    try:
        if req.crypto_asset not in SEAMOUNT_TO_KOTANI:
            raise HTTPException(400, f"Asset {req.crypto_asset} not supported by Kotani.")

        svc = _svc()
        _, token = SEAMOUNT_TO_KOTANI[req.crypto_asset]

        # FIX [2]: pass crypto_amount as third positional arg (POST body, not query params)
        rate_data = await svc.get_offramp_rate(token, req.currency, req.crypto_amount)

        # Kotani returns fiatAmount = fiat the recipient gets for cryptoAmount supplied
        raw_rate      = _parse_rate(rate_data, "fiatAmount")
        crypto_gross  = Decimal(str(req.crypto_amount))
        markup_crypto = (crypto_gross * MARKUP_PCT).quantize(Decimal("0.000001"))
        net_crypto    = crypto_gross - markup_crypto

        # fiatAmount from Kotani is for the gross crypto; scale down for net
        gross_fiat = Decimal(str(rate_data.get("fiatAmount", 0))) or (crypto_gross * raw_rate)
        net_fiat   = gross_fiat * (net_crypto / crypto_gross) if crypto_gross else Decimal(0)

        return {
            "success":         True,
            "provider":        "kotani",
            "crypto_asset":    req.crypto_asset,
            "currency":        req.currency,
            "gross_crypto":    float(crypto_gross),
            "markup_pct":      float(MARKUP_PCT * 100),
            "markup_crypto":   float(markup_crypto),
            "net_crypto_sent": float(net_crypto),
            "gross_fiat":      float(gross_fiat),
            "net_fiat":        float(net_fiat),
            "rate":            str(rate_data.get("value", raw_rate)),
            "rate_id":         rate_data.get("id"),
            "fee":             rate_data.get("fee"),
        }
    except HTTPException:
        raise
    except KotaniError as e:
        logger.error("Kotani offramp quote error: %s", e, exc_info=True)
        raise HTTPException(502, f"Quote failed: {e.message}")
    except Exception as e:
        logger.error("Kotani offramp quote error: %s", e, exc_info=True)
        raise HTTPException(500, f"Quote failed: {e}")


@router.post("/offramp/initialize")
async def offramp_initialize(
    req: OfframpInitReq,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_service),
):
    """Execute crypto → mobile money offramp via Kotani."""
    try:
        if req.crypto_asset not in SEAMOUNT_TO_KOTANI:
            raise HTTPException(400, f"Asset {req.crypto_asset} not supported by Kotani.")

        from backend.services.kotani_service import CURRENCY_TO_COUNTRY
        svc          = _svc()
        ref_id       = f"KOTANI_OFFRAMP_{uuid.uuid4().hex[:16].upper()}"
        country_code = req.country_code or CURRENCY_TO_COUNTRY.get(req.currency.upper(), "")

        if not country_code:
            raise HTTPException(400, f"Cannot resolve country_code for currency {req.currency}. Pass it explicitly.")

        account_name = req.account_name or f"Seamount User {req.phone_number[-4:]}"
        sender_addr  = await _wallet_for_asset(db, current_user["id"], req.crypto_asset)

        # FIX [4]: new ensure_customer signature
        await svc.ensure_customer(
            phone_number=req.phone_number,
            country_code=country_code,
            network=req.network,
            account_name=account_name,
            first_name=current_user.get("first_name", ""),
            last_name=current_user.get("last_name", ""),
            email=current_user.get("email", ""),
        )

        # FIX [4]: new initiate_offramp signature — network_provider, account_name; no customer_key
        result = await svc.initiate_offramp(
            reference_id=ref_id,
            crypto_amount=Decimal(str(req.crypto_amount)),
            fiat_currency=req.currency,
            crypto_asset=req.crypto_asset,
            phone_number=req.phone_number,
            network_provider=req.network,
            account_name=account_name,
            callback_url=CALLBACK_BASE,
            markup_pct=MARKUP_PCT,
            sender_address=sender_addr,
        )

        # FIX [7]: fee breakdown is now under result["_seamount"]
        seamount     = result.get("_seamount", {})
        markup_crypto = seamount.get("markup_crypto", 0.0)
        net_crypto    = seamount.get("net_crypto_sent", float(req.crypto_amount))

        db.supabase.from_("offramp_transactions").insert({
            "id":                  ref_id,
            "user_id":             current_user["id"],
            "type":                "offramp",
            "status":              "processing",
            "provider":            "kotani",
            "crypto_asset":        req.crypto_asset,
            "crypto_amount":       req.crypto_amount,
            "seamount_fee":        markup_crypto,
            "net_crypto_amount":   net_crypto,
            "fiat_currency":       req.currency,
            "fiat_amount":         0,
            "gross_fiat_amount":   0,
            "net_fiat_amount":     0,
            "markup_pct":          float(MARKUP_PCT * 100),
            "markup_amount":       markup_crypto,
            "country":             country_code,
            "payment_method":      "mobile_money",
            "kotani_reference_id": ref_id,
            "recipient_details": {
                "phone_number": req.phone_number,
                "network":      req.network,
            },
            "estimated_settlement": "2-10 minutes",
            "created_at":           datetime.now().isoformat(),
        }).execute()

        return {
            "success":              True,
            "tx_id":                ref_id,
            "provider":             "kotani",
            "status":               "processing",
            "net_crypto_sent":      net_crypto,
            "estimated_settlement": "2-10 minutes",
        }

    except HTTPException:
        raise
    except KotaniError as e:
        logger.error("Kotani offramp init error: %s", e, exc_info=True)
        raise HTTPException(502, f"Offramp failed: {e.message}")
    except Exception as e:
        logger.error("Kotani offramp init error: %s", e, exc_info=True)
        raise HTTPException(500, f"Offramp failed: {e}")


# ── WEBHOOK ────────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def kotani_webhook(request: Request, db = Depends(get_db_service)):
    """
    Handle Kotani signed webhook events.
    Register this URL in Kotani dashboard → Settings → Webhooks.
    """
    raw = await request.body()
    sig = request.headers.get("x-kotani-signature", "")
    evt = request.headers.get("x-kotani-event",     "")

    try:
        svc = _svc()
        if sig and not svc.verify_webhook(raw, sig):
            logger.warning("Kotani webhook signature invalid")
            raise HTTPException(401, "Invalid webhook signature")

        data    = json.loads(raw)
        event   = data.get("event", evt)
        payload = data.get("data", data)
        ref_id  = payload.get("referenceId") or payload.get("reference_id", "")

        logger.info("Kotani webhook: %s | ref=%s", event, ref_id)

        if event == "transaction.onramp.status.updated":
            deposit_status = payload.get("depositStatus", "")
            onchain_status = payload.get("onchainStatus", "")

            new_status = {
                ("SUCCESSFUL", "SUCCESSFUL"): "completed",
                ("SUCCESSFUL", "IN_PROGRESS"): "processing",
                ("FAILED",     ""):            "failed",
                ("CANCELLED",  ""):            "failed",
            }.get((deposit_status, onchain_status), "processing")

            update = {
                "status":               new_status,
                "webhook_data":         data,
                "webhook_received_at":  datetime.now().isoformat(),
            }
            if new_status == "completed":
                update["completed_at"] = datetime.now().isoformat()
            elif new_status == "failed":
                update["failed_at"] = datetime.now().isoformat()

            db.supabase.from_("onramp_transactions").update(update) \
                .eq("kotani_reference_id", ref_id).execute()

        elif event == "transaction.offramp.status.updated":
            status = payload.get("status", "")
            new_status = {
                "SUCCESSFUL": "completed",
                "FAILED":     "failed",
                "REVERSED":   "failed",
            }.get(status, "processing")

            update = {
                "status":            new_status,
                "fiat_amount":       float(payload.get("fiatAmount", 0)),
                "gross_fiat_amount": float(payload.get("fiatAmount", 0)),
                "net_fiat_amount":   float(payload.get("fiatTransactionAmount", 0)),
                "webhook_data":      data,
            }
            if new_status == "completed":
                update["completed_at"] = datetime.now().isoformat()
            elif new_status == "failed":
                update["failed_at"] = datetime.now().isoformat()

            db.supabase.from_("offramp_transactions").update(update) \
                .eq("kotani_reference_id", ref_id).execute()

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Kotani webhook error: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}


# ── UTILITIES ──────────────────────────────────────────────────────────────────

@router.get("/networks/{currency}")
async def get_networks(currency: str):
    """Return supported mobile money networks for a given fiat currency."""
    from backend.services.kotani_service import KotaniService
    networks = KotaniService.get_supported_networks(currency)
    if not networks:
        raise HTTPException(400, f"No mobile money networks known for {currency}.")
    return {"success": True, "currency": currency, "networks": networks}


# Backward-compat alias — remove once frontend is updated
@router.get("/telcos/{currency}")
async def get_telcos(currency: str):
    return await get_networks(currency)


@router.get("/transaction/{ref_id}")
async def get_transaction(
    ref_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_service),
):
    for table in ("onramp_transactions", "offramp_transactions"):
        res = db.supabase.from_(table).select("*") \
            .eq("kotani_reference_id", ref_id) \
            .eq("user_id", current_user["id"]).limit(1).execute()
        if res.data:
            return {"success": True, "transaction": res.data[0]}
    raise HTTPException(404, "Transaction not found.")