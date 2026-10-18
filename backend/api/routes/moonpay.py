# File: backend/api/routes/moonpay.py
"""
MoonPay Routes
  POST /api/v1/moonpay/url/onramp   — signed buy URL
  POST /api/v1/moonpay/url/offramp  — signed sell URL
  POST /api/v1/moonpay/webhook      — MoonPay event handler
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.config import get_settings
from backend.dependencies import get_current_user, get_db_service
from backend.services.moonpay_service import (
    MoonPayService, ASSET_TO_BLOCKCHAIN, OFFRAMP_ASSETS, ONRAMP_ASSETS
)
from backend.services.moonpay_service import MoonPayService

from fastapi import Body

router = APIRouter(prefix="/moonpay", tags=["MoonPay"])
logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _moonpay_service() -> MoonPayService:
    s = get_settings()

    missing = [
        k for k, v in {
            'MOONPAY_PUBLISHABLE_KEY': s.MOONPAY_PUBLISHABLE_KEY,
            'MOONPAY_SECRET_KEY':      s.MOONPAY_SECRET_KEY,
            'MOONPAY_WEBHOOK_KEY':     s.MOONPAY_WEBHOOK_KEY,
        }.items() if not v
    ]
    if missing:
        logger.error(f"❌ MoonPay env vars not set: {missing}")
        raise HTTPException(
            500,
            f"MoonPay not configured. Missing env vars: {', '.join(missing)}"
        )

    return MoonPayService(
        publishable_key=s.MOONPAY_PUBLISHABLE_KEY,
        secret_key=s.MOONPAY_SECRET_KEY.get_secret_value(),
        webhook_key=s.MOONPAY_WEBHOOK_KEY.get_secret_value(),
        environment=s.MOONPAY_ENVIRONMENT,
    )

# ── Debug endpoint — REMOVE BEFORE GO-LIVE ────────────────────────────────────

@router.get("/debug/signature-test")
async def debug_signature_test(
    db=Depends(get_db_service),
    current_user: dict = Depends(get_current_user),
):
    """
    🔍 SIGNATURE DEBUG ENDPOINT
    Generates a test signature and returns full trace.
    Logs everything to Render. Remove before production go-live.
    GET /api/v1/moonpay/debug/signature-test
    """
    import os
    from backend.config import get_settings

    s = get_settings()

    # ── Key health check ──────────────────────────────────────────
    pub_key    = s.MOONPAY_PUBLISHABLE_KEY or ""
    secret_key = s.MOONPAY_SECRET_KEY
    webhook_key= s.MOONPAY_WEBHOOK_KEY

    # Handle SecretStr
    sk_value = secret_key.get_secret_value() if hasattr(secret_key, 'get_secret_value') else (secret_key or "")
    wk_value = webhook_key.get_secret_value() if hasattr(webhook_key, 'get_secret_value') else (webhook_key or "")

    key_health = {
        "publishable_key_present": bool(pub_key),
        "publishable_key_preview": pub_key[:12] + "..." if pub_key else "MISSING",
        "publishable_key_length":  len(pub_key),
        "secret_key_present":      bool(sk_value),
        "secret_key_length":       len(sk_value),
        "webhook_key_present":     bool(wk_value),
        "webhook_key_length":      len(wk_value),
        "environment":             getattr(s, 'MOONPAY_ENVIRONMENT', 'unknown'),
    }

    logger.info(f"🔍 DEBUG /debug/signature-test | key_health={key_health}")

    if not pub_key or not sk_value:
        logger.error("❌ DEBUG: Keys missing — cannot generate test signature")
        return {
            "status":     "error",
            "key_health": key_health,
            "error":      "Keys missing. Check Render environment variables.",
        }

    # ── Generate test signature ───────────────────────────────────
    try:
        svc = MoonPayService(
            publishable_key=pub_key,
            secret_key=sk_value,
            webhook_key=wk_value,
            environment=getattr(s, 'MOONPAY_ENVIRONMENT', 'production'),
        )

        # Use a fixed test wallet to isolate signature logic
        test_wallet = "UBNIXQOQQPMCRRUMISBYYHPOZ7B4N6G7ZBDAQHRGKWJNBN6QSPQ7XGGOGE"
        result = svc.generate_onramp_url(
            asset="USDT_TRON",
            wallet_address=test_wallet,
        )

        # Reproduce the exact string that was signed
        from urllib.parse import urlencode, quote as url_quote
        signed_params = {
            'apiKey':        pub_key,
            'currencyCode':  'usdt_trx',
            'walletAddress': test_wallet,
        }
        clean = {k: str(v) for k, v in sorted(signed_params.items())}
        qs = urlencode(clean, quote_via=url_quote)
        signed_string = f"?{qs}"

        logger.info(f"🔍 DEBUG test signed_string : {signed_string}")
        logger.info(f"🔍 DEBUG test signature     : {result['params']['signature']}")
        logger.info(f"🔍 DEBUG test sdk_params    : {result['params']}")

        return {
            "status":           "ok",
            "key_health":       key_health,
            "test_asset":       "USDT_TRON",
            "signed_params_keys": sorted(signed_params.keys()),
            "query_string":     qs,
            "signed_string":    signed_string,
            "signature_preview":result['params']['signature'][:20] + "...",
            "sdk_params_keys":  sorted(result['params'].keys()),
            "instruction": (
                "Copy the full signed_string to "
                "https://www.freeformatter.com/hmac-generator.html "
                "with your secret key to verify the HMAC matches."
            ),
        }

    except Exception as e:
        logger.error(f"❌ DEBUG signature test failed: {e}", exc_info=True)
        return {
            "status":     "error",
            "key_health": key_health,
            "error":      str(e),
        }

async def _resolve_wallet_address(db, user_id: str, asset: str) -> str:
    """
    Look up user's wallet address for the asset's blockchain.
    MATIC → polygon chain → EVM address.
    """
    blockchain = ASSET_TO_BLOCKCHAIN.get(asset)
    if not blockchain:
        raise HTTPException(400, f"Unknown blockchain for asset: {asset}")

    try:
        if blockchain == 'algorand':
            res = db.supabase.from_('user_wallets') \
                .select('algorand_address') \
                .eq('user_id', user_id) \
                .limit(1).execute()
            if not res.data:
                raise HTTPException(
                    404,
                    "Algorand wallet not found. Please create your wallet first."
                )
            return res.data[0]['algorand_address']

        else:
            res = db.supabase.from_('multi_chain_addresses') \
                .select('address') \
                .eq('user_id', user_id) \
                .eq('blockchain', blockchain) \
                .limit(1).execute()
            if not res.data:
                raise HTTPException(
                    404,
                    f"{blockchain.title()} wallet not found. "
                    f"Please create your wallet first."
                )
            return res.data[0]['address']

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Wallet lookup failed for {asset}/{blockchain}: {e}")
        raise HTTPException(500, "Wallet lookup failed")


def _record_tx(db, tx_id: str, user_id: str, tx_type: str, asset: str,
               moonpay_code: str, wallet: str, fiat_currency: Optional[str],
               fiat_amount: Optional[float]) -> None:
    """Insert pending transaction record. Non-fatal on failure."""
    try:
        db.supabase.from_('moonpay_transactions').insert({
            'id':                   tx_id,
            'user_id':              user_id,
            'type':                 tx_type,
            'status':               'pending',
            'crypto_asset':         asset,
            'moonpay_currency_code': moonpay_code,
            'fiat_currency':        fiat_currency,
            'fiat_amount':          fiat_amount,
            'wallet_address':       wallet,
            'created_at':           datetime.now().isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"❌ Failed to record MoonPay transaction (non-fatal): {e}")


# ── Request Models ─────────────────────────────────────────────────────────────

class OnrampUrlRequest(BaseModel):
    asset: str
    base_currency_code:   Optional[str]   = None
    base_currency_amount: Optional[float] = None


class OfframpUrlRequest(BaseModel):
    asset: str
    quote_currency_code:  Optional[str]   = None   # fiat to receive
    base_currency_amount: Optional[float] = None   # crypto amount to sell


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/url/onramp")
async def get_onramp_url(
    req: OnrampUrlRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_service),
):
    """Generate signed MoonPay buy URL for authenticated user."""
    if req.asset not in ONRAMP_ASSETS:
        raise HTTPException(
            400,
            f"'{req.asset}' is not MoonPay-supported for onramp. "
            f"Note: Algorand-wrapped assets (goBTC, goETH, USDCa) are not supported."
        )

    try:
        wallet  = await _resolve_wallet_address(db, current_user['id'], req.asset)
        svc     = _moonpay_service()
        result  = svc.generate_onramp_url(
            asset=req.asset,
            wallet_address=wallet,
            email=current_user.get('email'),
            base_currency_code=req.base_currency_code,
            base_currency_amount=req.base_currency_amount,
        )

        tx_id = f"MP_BUY_{current_user['id'][:8]}_{int(datetime.now().timestamp())}"
        _record_tx(db, tx_id, current_user['id'], 'buy',
                   req.asset, result['moonpay_code'], wallet,
                   req.base_currency_code, req.base_currency_amount)

        return {
            'success':         True,
            'transaction_id':  tx_id,
            'url':             result['url'],
            'params':          result['params'],
            'asset':           req.asset,
            'moonpay_code':    result['moonpay_code'],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ MoonPay onramp URL failed: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to generate buy URL: {str(e)}")


@router.post("/url/offramp")
async def get_offramp_url(
    req: OfframpUrlRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_service),
):
    """Generate signed MoonPay sell URL for authenticated user."""
    if req.asset not in OFFRAMP_ASSETS:
        raise HTTPException(
            400,
            f"'{req.asset}' is not MoonPay-supported for offramp. "
            f"ALGO cannot be sold via MoonPay — swap to another asset first."
        )

    try:
        wallet  = await _resolve_wallet_address(db, current_user['id'], req.asset)
        svc     = _moonpay_service()
        result  = svc.generate_offramp_url(
            asset=req.asset,
            wallet_address=wallet,
            email=current_user.get('email'),
            quote_currency_code=req.quote_currency_code,
            base_currency_amount=req.base_currency_amount,
        )

        tx_id = f"MP_SELL_{current_user['id'][:8]}_{int(datetime.now().timestamp())}"
        _record_tx(db, tx_id, current_user['id'], 'sell',
                   req.asset, result['moonpay_code'], wallet,
                   req.quote_currency_code, req.base_currency_amount)

        return {
            'success':        True,
            'transaction_id': tx_id,
            'url':            result['url'],
            'params':         result['params'],
            'asset':          req.asset,
            'moonpay_code':   result['moonpay_code'],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ MoonPay offramp URL failed: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to generate sell URL: {str(e)}")


@router.post("/webhook")
async def moonpay_webhook(
    request: Request,
    db=Depends(get_db_service),
):
    """
    Handle MoonPay transaction webhooks.
    Register URL in MoonPay Dashboard → Developers → Webhooks:
    https://seamount-main.onrender.com/api/v1/moonpay/webhook
    """
    raw_body   = await request.body()
    sig_header = request.headers.get('moonpay-signature-v2', '')

    try:
        svc = _moonpay_service()

        # Verify signature (skip if header absent — useful in sandbox)
        if sig_header and not svc.verify_webhook(raw_body, sig_header):
            logger.warning("❌ MoonPay webhook: invalid signature rejected")
            raise HTTPException(401, "Invalid webhook signature")

        import json
        payload    = json.loads(raw_body)
        event_type = payload.get('type', '')
        data       = payload.get('data', {})

        logger.info(f"📨 MoonPay webhook: {event_type}")

        # Dispatch
        await {
            'transaction_created':      _on_buy_created,
            'transaction_updated':      _on_buy_updated,
            'transaction_failed':       _on_buy_failed,
            'sell_transaction_created': _on_sell_created,
            'sell_transaction_updated': _on_sell_updated,
            'sell_transaction_failed':  _on_sell_failed,
        }.get(event_type, _on_unhandled)(data, db, event_type)

        return {'status': 'ok'}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ MoonPay webhook error: {e}", exc_info=True)
        # Return 200 to prevent MoonPay retry storms; log for investigation
        return {'status': 'error', 'message': str(e)}


# ── Webhook Handlers ───────────────────────────────────────────────────────────

async def _on_buy_created(data: dict, db, _event: str):
    mp_id  = data.get('id')
    wallet = data.get('walletAddress', '')
    code   = data.get('currency', {}).get('code', '')
    logger.info(f"🆕 MoonPay buy created: {mp_id} | {code} → {wallet[:10]}...")
    await _update_by_wallet(db, wallet, 'buy', 'created', mp_id, data)


async def _on_buy_updated(data: dict, db, _event: str):
    mp_id  = data.get('id')
    status = data.get('status', '')
    wallet = data.get('walletAddress', '')
    crypto_amount = data.get('quoteCurrencyAmount')
    fiat_amount   = data.get('baseCurrencyAmount')
    logger.info(f"🔄 MoonPay buy updated: {mp_id} | status={status}")
    await _update_by_wallet(db, wallet, 'buy', status, mp_id, data,
                            extra={'crypto_amount': crypto_amount, 'fiat_amount': fiat_amount})


async def _on_buy_failed(data: dict, db, _event: str):
    mp_id  = data.get('id')
    reason = data.get('failureReason', 'Unknown')
    wallet = data.get('walletAddress', '')
    logger.warning(f"❌ MoonPay buy failed: {mp_id} | {reason}")
    await _update_by_wallet(db, wallet, 'buy', 'failed', mp_id, data,
                            extra={'failure_reason': reason})


async def _on_sell_created(data: dict, db, _event: str):
    mp_id  = data.get('id')
    wallet = data.get('walletAddress', '')
    logger.info(f"🆕 MoonPay sell created: {mp_id}")
    await _update_by_wallet(db, wallet, 'sell', 'created', mp_id, data)


async def _on_sell_updated(data: dict, db, _event: str):
    mp_id  = data.get('id')
    status = data.get('status', '')
    wallet = data.get('walletAddress', '')
    logger.info(f"🔄 MoonPay sell updated: {mp_id} | status={status}")
    await _update_by_wallet(db, wallet, 'sell', status, mp_id, data)


async def _on_sell_failed(data: dict, db, _event: str):
    mp_id  = data.get('id')
    reason = data.get('failureReason', 'Unknown')
    wallet = data.get('walletAddress', '')
    logger.warning(f"❌ MoonPay sell failed: {mp_id} | {reason}")
    await _update_by_wallet(db, wallet, 'sell', 'failed', mp_id, data,
                            extra={'failure_reason': reason})


async def _on_unhandled(data: dict, db, event_type: str):
    logger.info(f"ℹ️ Unhandled MoonPay event: {event_type}")


async def _update_by_wallet(
    db, wallet_address: str, tx_type: str, status: str,
    moonpay_tx_id: str, webhook_data: dict, extra: Optional[dict] = None
):
    """
    Update moonpay_transactions record.
    Match by wallet_address + type + pending status first,
    then fall back to upsert by moonpay_tx_id.
    """
    try:
        update_payload = {
            'status':       status,
            'moonpay_tx_id': moonpay_tx_id,
            'webhook_data': webhook_data,
            'updated_at':   datetime.now().isoformat(),
        }
        if extra:
            update_payload.update(extra)

        # Try to find existing pending record by wallet
        if wallet_address:
            res = db.supabase.from_('moonpay_transactions') \
                .select('id') \
                .eq('wallet_address', wallet_address) \
                .eq('type', tx_type) \
                .in_('status', ['pending', 'created']) \
                .limit(1).execute()

            if res.data:
                db.supabase.from_('moonpay_transactions') \
                    .update(update_payload) \
                    .eq('id', res.data[0]['id']) \
                    .execute()
                logger.info(f"✅ Updated moonpay_tx by wallet: {res.data[0]['id']}")
                return

        # Fallback: upsert by moonpay_tx_id
        db.supabase.from_('moonpay_transactions') \
            .upsert({**update_payload, 'type': tx_type}, on_conflict='moonpay_tx_id') \
            .execute()
        logger.info(f"✅ Upserted moonpay_tx by moonpay_tx_id: {moonpay_tx_id}")

    except Exception as e:
        logger.error(f"❌ Failed to update MoonPay transaction: {e}")

@router.post("/sign")
async def sign_url(
    query_string: str = Body(..., embed=True),
    db=Depends(get_db_service),
):
    """
    Receives a raw query string generated by the MoonPay SDK,
    signs it, and returns the signature.
    """
    svc = _moonpay_service()
    signature = svc._sign(query_string)
    return {"success": True, "signature": signature}