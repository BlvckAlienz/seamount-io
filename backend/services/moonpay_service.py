# File: backend/services/moonpay_service.py
"""
MoonPay Service — URL Signing, Webhook Verification, Asset Mapping
MATIC→POL migration handled transparently here.
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
    # Algorand
    'ALGO':         'algo',
    # Bitcoin
    'BTC':          'btc',
    # Ethereum
    'ETH':          'eth',
    'USDT_ETH':     'usdt',
    'USDC_ETH':     'usdc',
    # Polygon — MATIC→POL migration: display stays 'MATIC', API uses 'pol_polygon'
    'MATIC':         'pol_polygon',
    'USDT_POLYGON':  'usdt_polygon',
    'USDC_POLYGON':  'usdc_polygon',
    # Tron
    'TRX':           'trx',
    'USDT_TRON':     'usdt_trx',
    # Solana
    'SOL':           'sol',
    'USDT_SOLANA':   'usdt_sol',
    'USDC_SOLANA':   'usdc_sol',
    # XRP / RLUSD
    'XRP':           'xrp',
    'RLUSD':         'rlusd_xrp',
}

# MoonPay → Seamount (for webhook parsing)
MOONPAY_TO_SEAMOUNT: Dict[str, str] = {v: k for k, v in SEAMOUNT_TO_MOONPAY.items()}

# Offramp-supported assets (ALGO excluded — MoonPay doesn't support ALGO sell)
OFFRAMP_ASSETS = frozenset({
    'BTC', 'ETH', 'USDT_ETH', 'USDC_ETH',
    'MATIC', 'USDT_POLYGON', 'USDC_POLYGON',
    'TRX', 'USDT_TRON',
    'SOL', 'USDT_SOLANA', 'USDC_SOLANA',
    'XRP', 'RLUSD',
})

# Onramp-supported assets (all above + ALGO)
ONRAMP_ASSETS = frozenset(SEAMOUNT_TO_MOONPAY.keys())

# Asset → blockchain (for wallet address lookup)
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

    def __init__(self, publishable_key: str, secret_key: str, webhook_key: str,
                 environment: str = "production"):
        self.publishable_key = publishable_key
        self.secret_key      = secret_key
        self.webhook_key     = webhook_key
        self.environment     = environment

    # ── URL Signing ────────────────────────────────────────────────────────────

    def _sign_query(self, query_string: str) -> str:
        """
        HMAC-SHA256 sign of '?<query_string>' using MoonPay secret key.
        MoonPay requires the leading '?' in the signed content.
        """
        sig = hmac.new(
            self.secret_key.encode('utf-8'),
            f"?{query_string}".encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(sig).decode('utf-8')

    def generate_onramp_url(
        self,
        asset: str,
        wallet_address: str,
        email: Optional[str] = None,
        base_currency_code: Optional[str] = None,
        base_currency_amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate signed MoonPay buy URL.
        MATIC transparently maps to pol_polygon.
        """
        if asset not in ONRAMP_ASSETS:
            raise ValueError(f"'{asset}' not supported for MoonPay onramp")

        moonpay_code = SEAMOUNT_TO_MOONPAY[asset]

        params: Dict[str, Any] = {
            'apiKey':        self.publishable_key,
            'currencyCode':  moonpay_code,
            'walletAddress': wallet_address,
            'colorCode':     '#0061FF',
            'theme':         'dark',
            'redirectURL':   'https://seamount.io/wallet',
        }
        if email:
            params['email'] = email
        if base_currency_code:
            params['baseCurrencyCode'] = base_currency_code.lower()
        if base_currency_amount and base_currency_amount > 0:
            params['baseCurrencyAmount'] = str(base_currency_amount)

        query_string = urlencode(params)
        signature    = self._sign_query(query_string)
        signed_url   = f"{MOONPAY_BUY_URL}?{query_string}&signature={quote(signature)}"

        logger.info(
            f"✅ MoonPay onramp URL generated | "
            f"asset={asset} moonpay_code={moonpay_code} "
            f"wallet={wallet_address[:10]}..."
        )
        return {
            'url':           signed_url,
            'moonpay_code':  moonpay_code,
            'asset':         asset,
            'params':        {**params, 'signature': signature},
        }

    def generate_offramp_url(
        self,
        asset: str,
        wallet_address: str,
        email: Optional[str] = None,
        quote_currency_code: Optional[str] = None,
        base_currency_amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate signed MoonPay sell URL.
        baseCurrencyCode = the crypto being sold.
        quoteCurrencyCode = the fiat to receive.
        """
        if asset not in OFFRAMP_ASSETS:
            raise ValueError(
                f"'{asset}' not supported for MoonPay offramp. "
                f"Note: ALGO cannot be sold via MoonPay."
            )

        moonpay_code = SEAMOUNT_TO_MOONPAY[asset]

        params: Dict[str, Any] = {
            'apiKey':              self.publishable_key,
            'baseCurrencyCode':    moonpay_code,
            'walletAddress':       wallet_address,
            'refundWalletAddress': wallet_address,  # refund if sell fails
            'colorCode':           '#0061FF',
            'theme':               'dark',
            'redirectURL':         'https://seamount.io/wallet',
        }
        if email:
            params['email'] = email
        if quote_currency_code:
            params['quoteCurrencyCode'] = quote_currency_code.lower()
        if base_currency_amount and base_currency_amount > 0:
            params['baseCurrencyAmount'] = str(base_currency_amount)

        query_string = urlencode(params)
        signature    = self._sign_query(query_string)
        signed_url   = f"{MOONPAY_SELL_URL}?{query_string}&signature={quote(signature)}"

        logger.info(
            f"✅ MoonPay offramp URL generated | "
            f"asset={asset} moonpay_code={moonpay_code} "
            f"wallet={wallet_address[:10]}..."
        )
        return {
            'url':          signed_url,
            'moonpay_code': moonpay_code,
            'asset':        asset,
            'params':       {**params, 'signature': signature},
        }

    # ── Webhook Verification ───────────────────────────────────────────────────

    def verify_webhook(self, raw_body: bytes, signature_header: str) -> bool:
        """
        Verify MoonPay webhook signature.
        Header format: 't=<unix_ms>,s=<hmac_hex>'
        Rejects replays older than 5 minutes.
        """
        try:
            parts = dict(p.split('=', 1) for p in signature_header.split(','))
            ts_ms = parts.get('t', '0')
            sig   = parts.get('s', '')

            # Replay guard
            age_seconds = abs(time.time() - int(ts_ms) / 1000)
            if age_seconds > 300:
                logger.warning(f"⚠️ MoonPay webhook too old: {age_seconds:.0f}s")
                return False

            signed_payload = f"{ts_ms}.{raw_body.decode('utf-8')}"
            expected = hmac.new(
                self.webhook_key.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            valid = hmac.compare_digest(expected, sig)
            if not valid:
                logger.warning("❌ MoonPay webhook signature mismatch")
            return valid

        except Exception as e:
            logger.error(f"❌ MoonPay webhook verification error: {e}")
            return False