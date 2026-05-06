# File: backend/services/moonpay_service.py
"""
MoonPay Service — URL Signing, Webhook Verification, Asset Mapping
FIXED: Alphabetical param sort + quote() encoding for v3/verify_widget_signature
"""
import hmac
import hashlib
import base64
import logging
import time
from typing import Optional, Dict, Any
from urllib.parse import urlencode, quote

logger = logging.getLogger(__name__)

# ── Seamount Internal Key → MoonPay Currency Code ─────────────────────────────
SEAMOUNT_TO_MOONPAY: Dict[str, str] = {
    'ALGO':          'algo',
    'BTC':           'btc',
    'ETH':           'eth',
    'USDT_ETH':      'usdt',
    'USDC_ETH':      'usdc',
    'MATIC':         'pol_polygon',   # MATIC→POL migration
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

    # ── Core signing helpers ───────────────────────────────────────────────────

    def _build_query(self, params: Dict[str, Any]) -> str:
        """
        Build a URL query string that matches MoonPay's verification logic:
          1. Drop None values and stringify everything else
          2. Sort keys alphabetically  ← FIX: was insertion-order
          3. Encode with quote()       ← FIX: was quote_plus (spaces→+)

        MoonPay's /v3/verify_widget_signature does exactly the same on their
        side before computing the expected signature.
        """
        clean = {k: str(v) for k, v in params.items() if v is not None}
        return urlencode(sorted(clean.items()), quote_via=quote)

    def _sign(self, query_string: str) -> str:
        """
        HMAC-SHA256(?<query_string>, secret_key) → Base64.
        The leading '?' is required by MoonPay's spec.
        """
        mac = hmac.new(
            self.secret_key.encode('utf-8'),
            f"?{query_string}".encode('utf-8'),
            hashlib.sha256,
        )
        return base64.b64encode(mac.digest()).decode('utf-8')

    # ── Onramp ────────────────────────────────────────────────────────────────

    def generate_onramp_url(
        self,
        asset: str,
        wallet_address: str,
        email: Optional[str] = None,
        base_currency_code: Optional[str] = None,
        base_currency_amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generate signed MoonPay buy URL + params for Web SDK overlay."""
        if asset not in ONRAMP_ASSETS:
            raise ValueError(f"'{asset}' not supported for MoonPay onramp")

        moonpay_code = SEAMOUNT_TO_MOONPAY[asset]

        # Build params — all keys that MoonPay will see
        params: Dict[str, Any] = {
            'apiKey':        self.publishable_key,
            'colorCode':     '%230061FF',   # pre-encoded # to avoid double-encode
            'currencyCode':  moonpay_code,
            'theme':         'dark',
            'walletAddress': wallet_address,
        }
        # Optional params — only add if provided (absent keys never affect sig)
        if base_currency_amount and base_currency_amount > 0:
            params['baseCurrencyAmount'] = str(base_currency_amount)
        if base_currency_code:
            params['baseCurrencyCode'] = base_currency_code.lower()
        if email:
            params['email'] = email

        # Sign
        query_string = self._build_query(params)
        signature    = self._sign(query_string)

        # Full redirect URL (not used by SDK overlay, but useful for fallback)
        signed_url = (
            f"{MOONPAY_BUY_URL}?{query_string}"
            f"&signature={quote(signature, safe='')}"
        )

        logger.info(
            f"✅ MoonPay onramp signed | asset={asset} code={moonpay_code} "
            f"wallet={wallet_address[:10]}... qs_len={len(query_string)}"
        )

        # Return raw (un-URL-encoded) params for the JS SDK + signature
        raw_params = {
            'apiKey':        self.publishable_key,
            'colorCode':     '#0061FF',
            'currencyCode':  moonpay_code,
            'theme':         'dark',
            'walletAddress': wallet_address,
        }
        if base_currency_amount and base_currency_amount > 0:
            raw_params['baseCurrencyAmount'] = str(base_currency_amount)
        if base_currency_code:
            raw_params['baseCurrencyCode'] = base_currency_code.lower()
        if email:
            raw_params['email'] = email
        raw_params['signature'] = signature

        return {
            'url':          signed_url,
            'moonpay_code': moonpay_code,
            'asset':        asset,
            'params':       raw_params,
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
        """Generate signed MoonPay sell URL + params for Web SDK overlay."""
        if asset not in OFFRAMP_ASSETS:
            raise ValueError(
                f"'{asset}' not supported for MoonPay offramp. "
                f"ALGO cannot be sold via MoonPay."
            )

        moonpay_code = SEAMOUNT_TO_MOONPAY[asset]

        params: Dict[str, Any] = {
            'apiKey':              self.publishable_key,
            'baseCurrencyCode':    moonpay_code,
            'colorCode':           '%230061FF',
            'refundWalletAddress': wallet_address,
            'theme':               'dark',
            'walletAddress':       wallet_address,
        }
        if base_currency_amount and base_currency_amount > 0:
            params['baseCurrencyAmount'] = str(base_currency_amount)
        if email:
            params['email'] = email
        if quote_currency_code:
            params['quoteCurrencyCode'] = quote_currency_code.lower()

        query_string = self._build_query(params)
        signature    = self._sign(query_string)

        signed_url = (
            f"{MOONPAY_SELL_URL}?{query_string}"
            f"&signature={quote(signature, safe='')}"
        )

        logger.info(
            f"✅ MoonPay offramp signed | asset={asset} code={moonpay_code} "
            f"wallet={wallet_address[:10]}... qs_len={len(query_string)}"
        )

        raw_params = {
            'apiKey':              self.publishable_key,
            'baseCurrencyCode':    moonpay_code,
            'colorCode':           '#0061FF',
            'refundWalletAddress': wallet_address,
            'theme':               'dark',
            'walletAddress':       wallet_address,
        }
        if base_currency_amount and base_currency_amount > 0:
            raw_params['baseCurrencyAmount'] = str(base_currency_amount)
        if email:
            raw_params['email'] = email
        if quote_currency_code:
            raw_params['quoteCurrencyCode'] = quote_currency_code.lower()
        raw_params['signature'] = signature

        return {
            'url':          signed_url,
            'moonpay_code': moonpay_code,
            'asset':        asset,
            'params':       raw_params,
        }

    # ── Webhook Verification ───────────────────────────────────────────────────

    def verify_webhook(self, raw_body: bytes, signature_header: str) -> bool:
        """
        Verify MoonPay webhook signature.
        Header format: 't=<unix_ms>,s=<hmac_hex>'
        Rejects replays older than 5 minutes.
        """
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