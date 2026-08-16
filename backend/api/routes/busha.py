# File: backend/api/routes/busha.py
"""
Busha Routes
  POST /api/v1/busha/onramp/quote       — live quote with markup
  POST /api/v1/busha/onramp/initialize  — step 1: create temp bank account
  POST /api/v1/busha/onramp/convert     — step 2: execute crypto conversion (post-deposit)
  POST /api/v1/busha/offramp/quote      — offramp quote with markup
  POST /api/v1/busha/offramp/initialize — create recipient + execute full offramp
  POST /api/v1/busha/webhook            — Busha transfer event handler
  GET  /api/v1/busha/transaction/{id}   — transaction status
"""
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.config import get_settings
from backend.dependencies import get_current_user, get_db_service
from backend.services.ramp_router import get_busha_service, MARKUP_PCT

router = APIRouter(prefix="/busha", tags=["Busha"])
logger = logging.getLogger(__name__)

CALLBACK_BASE = "https://seamount-api.onrender.com/api/v1/busha/webhook"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _svc():
    return get_busha_service(get_settings())


async def _wallet_for_asset(db, user_id: str, crypto_asset: str) -> str:
    """Resolve user wallet address for the given asset's blockchain."""
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


def _tx_id(prefix: str, user_id: str) -> str:
    return f"{prefix}_{user_id[:8]}_{int(datetime.now().timestamp())}"


# ── Request Models ─────────────────────────────────────────────────────────────

class OnrampQuoteReq(BaseModel):
    amount_fiat:  float
    currency:     str
    crypto_asset: str

class OnrampInitReq(BaseModel):
    amount_fiat:  float
    currency:     str
    crypto_asset: str

class OnrampConvertReq(BaseModel):
    tx_id: str   # onramp_transactions.id

class OfframpQuoteReq(BaseModel):
    crypto_asset:  str
    crypto_amount: float
    currency:      str

class OfframpInitReq(BaseModel):
    crypto_asset:    str
    crypto_amount:   float
    currency:        str
    # Bank recipient details
    bank_code:       Optional[str] = None
    account_number:  Optional[str] = None
    account_name:    Optional[str] = None
    # M-Pesa (KES only)
    phone_number:    Optional[str] = None


# ── ONRAMP ─────────────────────────────────────────────────────────────────────

@router.post("/onramp/quote")
async def onramp_quote(
    req: OnrampQuoteReq,
    current_user: dict = Depends(get_current_user),
):
    """Return live quote: how much crypto the user receives after 2.5% markup."""
    try:
        svc         = _svc()
        base_amount = Decimal(str(req.amount_fiat))
        markup      = (base_amount * MARKUP_PCT).quantize(Decimal("0.01"))
        gross       = base_amount + markup

        # Probe Busha for the conversion rate (NGN→USDT etc.)
        from backend.services.busha_service import SEAMOUNT_TO_BUSHA
        busha_code = SEAMOUNT_TO_BUSHA.get(req.crypto_asset)
        if not busha_code:
            raise HTTPException(400, f"Asset {req.crypto_asset} not supported by Busha.")

        quote = await svc.create_quote(
            source_currency=req.currency,
            target_currency=busha_code,
            source_amount=str(base_amount),
        )

        return {
            "success":        True,
            "provider":       "busha",
            "currency":       req.currency,
            "crypto_asset":   req.crypto_asset,
            "base_amount":    float(base_amount),
            "markup_pct":     float(MARKUP_PCT * 100),
            "markup_amount":  float(markup),
            "gross_amount":   float(gross),   # what user pays
            "crypto_amount":  float(quote["target_amount"]),
            "rate":           quote["rate"]["rate"],
            "expires_at":     quote.get("expires_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Busha onramp quote error: {e}", exc_info=True)
        raise HTTPException(500, f"Quote failed: {e}")


@router.post("/onramp/initialize")
async def onramp_initialize(
    req: OnrampInitReq,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_service),
):
    """
    Step 1: Create Busha temporary bank account for gross fiat collection.
    Returns bank account details the user must transfer to manually.
    """
    try:
        svc        = _svc()
        base_amt   = Decimal(str(req.amount_fiat))
        wallet_addr = await _wallet_for_asset(db, current_user["id"], req.crypto_asset)

        transfer, gross, markup = await svc.initiate_onramp_deposit(
            fiat_currency=req.currency,
            fiat_amount=base_amt,
            markup_pct=MARKUP_PCT,
        )

        tx_id = _tx_id("BUSHA_ONRAMP", current_user["id"])
        pay_in = transfer.get("pay_in", {})

        db.supabase.from_("onramp_transactions").insert({
            "id":                       tx_id,
            "user_id":                  current_user["id"],
            "type":                     "onramp",
            "status":                   "pending_payment",
            "provider":                 "busha",
            "provider_name":            "Busha",
            "currency":                 req.currency,
            "crypto_asset":             req.crypto_asset,
            "amount_fiat":              float(base_amt),
            "gross_fiat_amount":        float(gross),
            "markup_amount":            float(markup),
            "markup_pct":               float(MARKUP_PCT * 100),
            "seamount_fee":             float(markup),
            "net_to_user":              float(base_amt),
            "wallet_address":           wallet_addr,
            "checkout_url":             None,
            "user_email":               current_user.get("email", ""),
            "user_country":             req.currency[:2],
            "busha_deposit_transfer_id": transfer["id"],
            "pay_in_details":           pay_in,
            "created_at":               datetime.now().isoformat(),
        }).execute()

        return {
            "success":      True,
            "tx_id":        tx_id,
            "provider":     "busha",
            "pay_in_type":  "bank_account",
            "pay_in_details": {
                "account_number": pay_in.get("recipient_details", {}).get("account_number"),
                "account_name":   pay_in.get("recipient_details", {}).get("account_name"),
                "bank_name":      pay_in.get("recipient_details", {}).get("bank_name"),
                "amount":         float(gross),
                "currency":       req.currency,
                "expires_at":     pay_in.get("expires_at"),
                "reference":      transfer["id"],
            },
            "gross_amount": float(gross),
            "markup":       float(markup),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Busha onramp init error: {e}", exc_info=True)
        raise HTTPException(500, f"Onramp initialization failed: {e}")


@router.post("/onramp/convert")
async def onramp_convert(
    req: OnrampConvertReq,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_service),
):
    """
    Step 2: Execute fiat→crypto conversion after deposit confirmed.
    Called by webhook handler; can also be called manually by admin.
    """
    try:
        res = db.supabase.from_("onramp_transactions") \
            .select("*").eq("id", req.tx_id).limit(1).execute()
        if not res.data:
            raise HTTPException(404, "Transaction not found.")
        tx = res.data[0]

        if tx["status"] not in ("deposit_confirmed", "pending_conversion"):
            raise HTTPException(400, f"Cannot convert from status: {tx['status']}")

        svc = _svc()
        transfer = await svc.execute_onramp_conversion(
            fiat_currency=tx["currency"],
            base_amount=Decimal(str(tx["amount_fiat"])),
            crypto_asset=tx["crypto_asset"],
        )

        db.supabase.from_("onramp_transactions").update({
            "status":                  "processing",
            "busha_conv_transfer_id":  transfer["id"],
        }).eq("id", req.tx_id).execute()

        return {"success": True, "conversion_transfer_id": transfer["id"]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Busha onramp convert error: {e}", exc_info=True)
        raise HTTPException(500, f"Conversion failed: {e}")


# ── OFFRAMP ────────────────────────────────────────────────────────────────────

@router.post("/offramp/quote")
async def offramp_quote(
    req: OfframpQuoteReq,
    current_user: dict = Depends(get_current_user),
):
    """Return live offramp quote with markup deducted from gross fiat."""
    try:
        svc   = _svc()
        quote = await svc.get_offramp_rate(
            crypto_asset=req.crypto_asset,
            fiat_currency=req.currency,
            crypto_amount=Decimal(str(req.crypto_amount)),
            markup_pct=MARKUP_PCT,
        )
        return {"success": True, "provider": "busha", **quote}
    except Exception as e:
        logger.error(f"Busha offramp quote error: {e}", exc_info=True)
        raise HTTPException(500, f"Quote failed: {e}")


@router.post("/offramp/initialize")
async def offramp_initialize(
    req: OfframpInitReq,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_service),
):
    """Create bank/M-Pesa recipient and execute full offramp in one call."""
    try:
        svc = _svc()

        # Determine recipient type from currency
        if req.currency == "NGN":
            if not all([req.bank_code, req.account_number, req.account_name]):
                raise HTTPException(400, "bank_code, account_number, account_name required for NGN.")
            recipient = await svc.create_recipient(
                "ngn_bank",
                currency="NGN",
                country_code="NG",
                bank_code=req.bank_code,
                account_number=req.account_number,
                account_name=req.account_name,
            )
        elif req.currency == "KES":
            if not req.phone_number:
                raise HTTPException(400, "phone_number required for KES.")
            recipient = await svc.create_recipient(
                "mpesa_mobile_money",
                account_name=current_user.get("first_name", "User"),
                phone_number=req.phone_number,
            )
        else:
            raise HTTPException(400, f"Busha offramp does not support {req.currency}.")

        # Get net fiat (gross - markup)
        quote_data = await svc.get_offramp_rate(
            crypto_asset=req.crypto_asset,
            fiat_currency=req.currency,
            crypto_amount=Decimal(str(req.crypto_amount)),
            markup_pct=MARKUP_PCT,
        )
        net_fiat = Decimal(quote_data["net_fiat"])

        crypto_transfer, payout_transfer = await svc.execute_offramp(
            crypto_asset=req.crypto_asset,
            crypto_amount=Decimal(str(req.crypto_amount)),
            fiat_currency=req.currency,
            recipient_id=recipient["id"],
            net_fiat=net_fiat,
        )

        tx_id = _tx_id("BUSHA_OFFRAMP", current_user["id"])
        db.supabase.from_("offramp_transactions").insert({
            "id":                       tx_id,
            "user_id":                  current_user["id"],
            "type":                     "offramp",
            "status":                   "processing",
            "provider":                 "busha",
            "crypto_asset":             req.crypto_asset,
            "crypto_amount":            float(req.crypto_amount),
            "seamount_fee":             float(Decimal(quote_data["markup_amount"])),
            "net_crypto_amount":        float(req.crypto_amount),
            "fiat_currency":            req.currency,
            "fiat_amount":              float(Decimal(quote_data["gross_fiat"])),
            "gross_fiat_amount":        float(Decimal(quote_data["gross_fiat"])),
            "net_fiat_amount":          float(net_fiat),
            "markup_pct":               float(MARKUP_PCT * 100),
            "markup_amount":            float(Decimal(quote_data["markup_amount"])),
            "country":                  req.currency[:2],
            "payment_method":           "bank_transfer" if req.currency == "NGN" else "mobile_money",
            "busha_crypto_transfer_id": crypto_transfer["id"],
            "busha_payout_transfer_id": payout_transfer["id"],
            "recipient_details":        {
                "account_number": req.account_number,
                "bank_code":      req.bank_code,
                "phone_number":   req.phone_number,
            },
            "estimated_settlement": "5-15 minutes",
            "created_at":           datetime.now().isoformat(),
        }).execute()

        return {
            "success":               True,
            "tx_id":                 tx_id,
            "provider":              "busha",
            "status":                "processing",
            "net_fiat":              float(net_fiat),
            "currency":              req.currency,
            "estimated_settlement":  "5-15 minutes",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Busha offramp init error: {e}", exc_info=True)
        raise HTTPException(500, f"Offramp failed: {e}")


# ── WEBHOOK ────────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def busha_webhook(request: Request, db = Depends(get_db_service)):
    """
    Handle Busha transfer webhooks.
    Events: transfer.funds_received, transfer.completed, transfer.failed
    Register URL in Busha dashboard → Settings → Webhooks:
    https://seamount-api.onrender.com/api/v1/busha/webhook
    """
    try:
        raw  = await request.body()
        data = json.loads(raw)
        event       = data.get("event", "")
        transfer_id = data.get("data", {}).get("id", "")
        status      = data.get("data", {}).get("status", "")

        logger.info(f"Busha webhook: {event} | transfer={transfer_id} | status={status}")

        if event == "transfer.funds_received":
            # Deposit confirmed → trigger crypto conversion
            res = db.supabase.from_("onramp_transactions") \
                .select("id, currency, crypto_asset, amount_fiat") \
                .eq("busha_deposit_transfer_id", transfer_id) \
                .limit(1).execute()

            if res.data:
                tx = res.data[0]
                db.supabase.from_("onramp_transactions").update({
                    "status":              "deposit_confirmed",
                    "deposit_confirmed_at": datetime.now().isoformat(),
                    "webhook_data":        data,
                }).eq("id", tx["id"]).execute()

                # Auto-trigger conversion
                svc = _svc()
                try:
                    conv = await svc.execute_onramp_conversion(
                        fiat_currency=tx["currency"],
                        base_amount=Decimal(str(tx["amount_fiat"])),
                        crypto_asset=tx["crypto_asset"],
                    )
                    db.supabase.from_("onramp_transactions").update({
                        "status":                 "processing",
                        "busha_conv_transfer_id": conv["id"],
                    }).eq("id", tx["id"]).execute()
                    logger.info(f"✅ Auto-conversion triggered for {tx['id']}: {conv['id']}")
                except Exception as conv_err:
                    logger.error(f"❌ Auto-conversion failed for {tx['id']}: {conv_err}")
                    db.supabase.from_("onramp_transactions").update({
                        "status": "pending_conversion"
                    }).eq("id", tx["id"]).execute()

        elif event == "transfer.completed":
            # Could be conversion completion or payout completion
            for table in ("onramp_transactions", "offramp_transactions"):
                col = "busha_conv_transfer_id" if table == "onramp_transactions" \
                      else "busha_payout_transfer_id"
                res = db.supabase.from_(table).select("id") \
                    .eq(col, transfer_id).limit(1).execute()
                if res.data:
                    db.supabase.from_(table).update({
                        "status":       "completed",
                        "completed_at": datetime.now().isoformat(),
                        "webhook_data": data,
                    }).eq("id", res.data[0]["id"]).execute()
                    logger.info(f"✅ {table} {res.data[0]['id']} completed")
                    break

        elif event == "transfer.failed":
            for table, col in [
                ("onramp_transactions",  "busha_deposit_transfer_id"),
                ("onramp_transactions",  "busha_conv_transfer_id"),
                ("offramp_transactions", "busha_crypto_transfer_id"),
                ("offramp_transactions", "busha_payout_transfer_id"),
            ]:
                res = db.supabase.from_(table).select("id") \
                    .eq(col, transfer_id).limit(1).execute()
                if res.data:
                    db.supabase.from_(table).update({
                        "status":    "failed",
                        "failed_at": datetime.now().isoformat(),
                        "webhook_data": data,
                    }).eq("id", res.data[0]["id"]).execute()
                    logger.warning(f"⚠️ {table} {res.data[0]['id']} failed")
                    break

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Busha webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}  # 200 always to stop retries


# ── STATUS ─────────────────────────────────────────────────────────────────────

@router.get("/transaction/{tx_id}")
async def get_transaction(
    tx_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_service),
):
    for table in ("onramp_transactions", "offramp_transactions"):
        res = db.supabase.from_(table).select("*") \
            .eq("id", tx_id).eq("user_id", current_user["id"]).limit(1).execute()
        if res.data:
            return {"success": True, "transaction": res.data[0], "table": table}
    raise HTTPException(404, "Transaction not found.")