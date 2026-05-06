# File: backend/services/moonpay_service.py
"""
MoonPay Service — URL Signing, Webhook Verification, Asset Mapping
DEBUG VERSION: Full signature trace in logs
"""
import hmac
import hashlib
import base64
import logging
import time
from typing import Optional, Dict, Any
from urllib.parse import urlencode, quote

logger = logging.getLogger(__name__)

SEAMOUNT_TO_MOONPAY: Dict[str, str] = {
    'ALGO':          'algo',
    'BTC':           'btc',
    'ETH':           'eth',
    'USDT_ETH':      'usdt',
    'USDC_ETH':      'usdc',
    'MATIC':         'pol_polygon',
    'USDT_POLYGON':  'usdt_polygon',
    'USDC_POLYGON':  'usdc_polygon',
    'TRX':           'trx',
    'USDT_TRON':     'usdt_trx',
    'SOL':           'sol',
    'USDT_SOLANA':   'usdt_sol',
    'USDC_SOLANA':   'usdc_sol',
    'XRP':           'xrp',
    'RLUSD':         'rlusd_xrp',
}

MOONPAY_TO_SEAMOUNT: Dict[str, str] = {v: k for k, v in SEAMOUNT_TO_MOONPAY.items()}

OFFRAMP_ASSETS = frozenset({
    'BTC', 'ETH', 'USDT_ETH', 'USDC_ETH',
    'MATIC', 'USDT_POLYGON', 'USDC_POLYGON',
    'TRX', 'USDT_TRON',
    'SOL', 'USDT_SOLANA', 'USDC_SOLANA',
    'XRP', 'RLUSD',
})

ONRAMP_ASSETS = frozenset(SEAMOUNT_TO_MOONPAY.keys())

ASSET_TO_BLOCKCHAIN: Dict[str, str] = {
    'ALGO':         'algorand',
    'BTC':          'bitcoin',
    'ETH':          'ethereum',
    'USDT_ETH':     'ethereum',
    'USDC_ETH':     'ethereum',
    'MATIC':        'polygon',
    'USDT_POLYGON': 'polygon',
    'USDC_POLYGON': 'polygon',
    'TRX':          'tron',
    'USDT_TRON':    'tron',
    'SOL':          'solana',
    'USDT_SOLANA':  'solana',
    'USDC_SOLANA':  'solana',
    'XRP':          'xrp',
    'RLUSD':        'xrp',
}

MOONPAY_BUY_URL  = "https://buy.moonpay.com"
MOONPAY_SELL_URL = "https://sell.moonpay.com"


class MoonPayService:

    def __init__(
        self,
        publishable_key: str,
        secret_key: str,
        webhook_key: str,
        environment: str = "production",
    ):
        self.publishable_key = publishable_key
        self.secret_key      = secret_key
        self.webhook_key     = webhook_key
        self.environment     = environment

        # ✅ Log key health at init — shows up in Render on every cold start
        pk_preview = publishable_key[:8] if publishable_key else "MISSING"
        sk_len     = len(secret_key) if secret_key else 0
        wk_len     = len(webhook_key) if webhook_key else 0
        logger.info(
            f"🔑 MoonPayService init | "
            f"publishable_key={pk_preview}... | "
            f"secret_key_len={sk_len} | "
            f"webhook_key_len={wk_len} | "
            f"env={environment}"
        )
        if sk_len == 0:
            logger.error("❌ MOONPAY_SECRET_KEY is empty — ALL signatures will fail")
        if wk_len == 0:
            logger.error("❌ MOONPAY_WEBHOOK_KEY is empty — webhook verification disabled")

    # ── Core helpers ───────────────────────────────────────────────────────────

    def _build_query(self, params: Dict[str, Any]) -> str:
        """
        Alphabetically sorted, quote()-encoded query string.
        MoonPay's verify_widget_signature does the same sort before checking HMAC.
        """
        clean = {k: str(v) for k, v in sorted(params.items()) if v is not None}
        qs = urlencode(clean, quote_via=quote)
        logger.debug(f"📋 _build_query sorted keys: {list(clean.keys())}")
        logger.debug(f"📋 _build_query result: {qs[:200]}")
        return qs

    def _sign(self, query_string: str) -> str:
        """HMAC-SHA256(?<qs>, secret_key) → Base64."""
        to_sign = f"?{query_string}"
        mac = hmac.new(
            self.secret_key.encode('utf-8'),
            to_sign.encode('utf-8'),
            hashlib.sha256,
        )
        sig = base64.b64encode(mac.digest()).decode('utf-8')
        logger.debug(f"✍️  _sign | to_sign_len={len(to_sign)} | sig_preview={sig[:16]}...")
        return sig

    # ── Onramp ────────────────────────────────────────────────────────────────

    def generate_onramp_url(
        self,
        asset: str,
        wallet_address: str,
        email: Optional[str] = None,
        base_currency_code: Optional[str] = None,
        base_currency_amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        if asset not in ONRAMP_ASSETS:
            raise ValueError(f"'{asset}' not supported for MoonPay onramp")

        moonpay_code = SEAMOUNT_TO_MOONPAY[asset]

        # ── Build the params that get signed ──────────────────────────────────
        # CRITICAL: These must exactly match what the JS SDK sends to MoonPay.
        # Do NOT include colorCode or theme — they are cosmetic and NOT signed.
        signed_params: Dict[str, Any] = {
            'apiKey':        self.publishable_key,
            'currencyCode':  moonpay_code,
            'walletAddress': wallet_address,
        }
        if base_currency_amount and base_currency_amount > 0:
            signed_params['baseCurrencyAmount'] = str(base_currency_amount)
        if base_currency_code:
            signed_params['baseCurrencyCode'] = base_currency_code.lower()
        if email:
            signed_params['email'] = email

        query_string = self._build_query(signed_params)
        signature    = self._sign(query_string)

        # ── Full URL (for redirect fallback) ──────────────────────────────────
        signed_url = (
            f"{MOONPAY_BUY_URL}?{query_string}"
            f"&signature={quote(signature, safe='')}"
        )

        # ── Params returned to JS SDK ─────────────────────────────────────────
        # Add cosmetic params AFTER signing — they are NOT part of the HMAC
        sdk_params = {
            **signed_params,
            'colorCode': '#0061FF',
            'theme':     'dark',
            'signature': signature,
        }

        # ── FULL TRACE LOG (visible in Render logs) ───────────────────────────
        logger.info("=" * 60)
        logger.info(f"🌙 MoonPay ONRAMP signature trace")
        logger.info(f"   asset          : {asset}")
        logger.info(f"   moonpay_code   : {moonpay_code}")
        logger.info(f"   wallet         : {wallet_address[:12]}...")
        logger.info(f"   signed_params  : {sorted(signed_params.keys())}")
        logger.info(f"   query_string   : {query_string}")
        logger.info(f"   signed_string  : ?{query_string[:80]}...")
        logger.info(f"   signature      : {signature[:20]}...")
        logger.info(f"   sdk_param_keys : {sorted(sdk_params.keys())}")
        logger.info("=" * 60)

        return {
            'url':          signed_url,
            'moonpay_code': moonpay_code,
            'asset':        asset,
            'params':       sdk_params,
        }

    # ── Offramp ───────────────────────────────────────────────────────────────

    def generate_offramp_url(
        self,
        asset: str,
        wallet_address: str,
        email: Optional[str] = None,
        quote_currency_code: Optional[str] = None,
        base_currency_amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        if asset not in OFFRAMP_ASSETS:
            raise ValueError(
                f"'{asset}' not supported for MoonPay offramp. "
                f"ALGO cannot be sold via MoonPay."
            )

        moonpay_code = SEAMOUNT_TO_MOONPAY[asset]

        signed_params: Dict[str, Any] = {
            'apiKey':              self.publishable_key,
            'baseCurrencyCode':    moonpay_code,
            'refundWalletAddress': wallet_address,
            'walletAddress':       wallet_address,
        }
        if base_currency_amount and base_currency_amount > 0:
            signed_params['baseCurrencyAmount'] = str(base_currency_amount)
        if email:
            signed_params['email'] = email
        if quote_currency_code:
            signed_params['quoteCurrencyCode'] = quote_currency_code.lower()

        query_string = self._build_query(signed_params)
        signature    = self._sign(query_string)

        signed_url = (
            f"{MOONPAY_SELL_URL}?{query_string}"
            f"&signature={quote(signature, safe='')}"
        )

        sdk_params = {
            **signed_params,
            'colorCode': '#0061FF',
            'theme':     'dark',
            'signature': signature,
        }

        logger.info("=" * 60)
        logger.info(f"🌙 MoonPay OFFRAMP signature trace")
        logger.info(f"   asset          : {asset}")
        logger.info(f"   moonpay_code   : {moonpay_code}")
        logger.info(f"   wallet         : {wallet_address[:12]}...")
        logger.info(f"   signed_params  : {sorted(signed_params.keys())}")
        logger.info(f"   query_string   : {query_string}")
        logger.info(f"   signed_string  : ?{query_string[:80]}...")
        logger.info(f"   signature      : {signature[:20]}...")
        logger.info(f"   sdk_param_keys : {sorted(sdk_params.keys())}")
        logger.info("=" * 60)

        return {
            'url':          signed_url,
            'moonpay_code': moonpay_code,
            'asset':        asset,
            'params':       sdk_params,
        }

    # ── Webhook Verification ───────────────────────────────────────────────────

    def verify_webhook(self, raw_body: bytes, signature_header: str) -> bool:
        try:
            parts  = dict(p.split('=', 1) for p in signature_header.split(','))
            ts_ms  = parts.get('t', '0')
            sig    = parts.get('s', '')

            age_seconds = abs(time.time() - int(ts_ms) / 1000)
            if age_seconds > 300:
                logger.warning(f"⚠️ MoonPay webhook too old: {age_seconds:.0f}s")
                return False

            signed_payload = f"{ts_ms}.{raw_body.decode('utf-8')}"
            expected = hmac.new(
                self.webhook_key.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256,
            ).hexdigest()

            valid = hmac.compare_digest(expected, sig)
            if not valid:
                logger.warning("❌ MoonPay webhook signature mismatch")
            return valid

        except Exception as e:
            logger.error(f"❌ MoonPay webhook verification error: {e}")
            return False