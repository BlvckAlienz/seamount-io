# File: backend/services/kotani_service.py
"""
Kotani Pay API Service
Handles mobile-money onramp/offramp for GHS, UGX, TZS, RWF, ZMW, XOF, XAF, KES.
Markup model:
  Onramp  → crypto delivered to user wallet; markup from fiat overage via rate presentation.
  Offramp → deduct markup from crypto before forwarding to Kotani.
"""
import hmac
import hashlib
import logging
import aiohttp
from decimal import Decimal
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

KOTANI_SANDBOX_URL = "https://sandbox-api.kotanipay.com"
KOTANI_PROD_URL    = "https://api.kotanipay.com"

# Seamount asset → (chain, token) for Kotani
SEAMOUNT_TO_KOTANI: Dict[str, tuple] = {
    "USDT_POLYGON": ("POLYGON", "USDT"),
    "USDC_POLYGON": ("POLYGON", "USDC"),
    "USDT_TRON":    ("TRON",    "USDT"),
    "USDT_ETH":     ("ETHEREUM","USDT"),
    "USDC_ETH":     ("ETHEREUM","USDC"),
    "ETH":          ("ETHEREUM","ETH"),
    "BTC":          ("BITCOIN", "BTC"),
    "SOL":          ("SOLANA",  "SOL"),
    "USDT_SOLANA":  ("SOLANA",  "USDT"),
}

# fiat currency → supported telco IDs
CURRENCY_TO_TELCOS: Dict[str, list] = {
    "KES": ["MPESA", "AIRTEL"],
    "GHS": ["MTN", "VODAFONE", "AIRTELTIGO"],
    "UGX": ["MTN", "AIRTEL"],
    "TZS": ["MPESA", "AIRTEL", "TIGO"],
    "RWF": ["MTN", "AIRTEL"],
    "ZMW": ["MTN", "AIRTEL", "ZAMTEL"],
    "XOF": ["ORANGE", "MTN"],
    "XAF": ["ORANGE", "MTN"],
}

DEFAULT_MARKUP_PCT = Decimal("0.025")  # 2.5%


class KotaniService:

    def __init__(
        self,
        api_key:        str,
        webhook_secret: str = "",
        environment:    str = "sandbox",
    ):
        self.api_key        = api_key
        self.webhook_secret = webhook_secret
        self.base_url       = KOTANI_SANDBOX_URL if environment == "sandbox" else KOTANI_PROD_URL
        self._headers       = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        }
        logger.info(f"KotaniService init | env={environment}")

    # ── HTTP helpers ───────────────────────────────────────────────────────────

    async def _post(self, path: str, body: dict) -> dict:
        url = f"{self.base_url}/api/v3{path}"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    url, json=body, headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as r:
                    data = await r.json()
                    logger.info(f"Kotani POST {path} → {r.status} | {data.get('message','')}")
                    if not data.get("success"):
                        raise Exception(f"Kotani {path}: {data.get('message', str(data))}")
                    return data
        except aiohttp.ClientError as e:
            logger.error(f"Kotani network error POST {path}: {e}")
            raise Exception(f"Kotani API unreachable: {e}")

    async def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}/api/v3{path}"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    url, params=params, headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    data = await r.json()
                    if not data.get("success"):
                        raise Exception(f"Kotani GET {path}: {data.get('message', str(data))}")
                    return data
        except aiohttp.ClientError as e:
            logger.error(f"Kotani network error GET {path}: {e}")
            raise Exception(f"Kotani API unreachable: {e}")

    # ── Customer management ────────────────────────────────────────────────────

    async def ensure_customer(
        self,
        customer_key:  str,
        phone_number:  str,
        first_name:    str = "User",
        last_name:     str = "",
    ) -> dict:
        """Idempotent: create Kotani customer or ignore duplicate."""
        try:
            resp = await self._post("/customer", {
                "customerKey":  customer_key,
                "phoneNumber":  phone_number,
                "firstName":    first_name,
                "lastName":     last_name,
            })
            return resp.get("data", {})
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                logger.info(f"Kotani customer {customer_key} already exists — skipping create")
                return {"customerKey": customer_key}
            raise

    # ── Rates ──────────────────────────────────────────────────────────────────

    async def get_onramp_rate(
        self,
        fiat_currency: str,
        token:         str = "USDT",
    ) -> dict:
        """Returns rate data from Kotani (fiat → crypto)."""
        resp = await self._get(
            "/rates/onramp-rate",
            params={"currency": fiat_currency.upper(), "token": token},
        )
        return resp.get("data", resp)

    async def get_offramp_rate(
        self,
        token:         str,
        fiat_currency: str,
    ) -> dict:
        """Returns rate data from Kotani (crypto → fiat)."""
        resp = await self._get(
            "/rates/offramp-rate",
            params={"token": token, "currency": fiat_currency.upper()},
        )
        return resp.get("data", resp)

    # ── ONRAMP: mobile money → crypto ─────────────────────────────────────────

    async def initiate_onramp(
        self,
        reference_id:   str,
        fiat_amount:    Decimal,
        fiat_currency:  str,
        crypto_asset:   str,
        wallet_address: str,
        phone_number:   str,
        telco_id:       str,
        customer_key:   str,
        callback_url:   str,
    ) -> dict:
        """
        Initiate Kotani onramp: customer pays mobile money → crypto delivered to wallet.
        Markup is handled via rate presentation (quote endpoint returns marked-up rate).
        """
        chain_token = SEAMOUNT_TO_KOTANI.get(crypto_asset)
        if not chain_token:
            raise ValueError(f"Asset not supported by Kotani: {crypto_asset}")
        chain, token = chain_token

        body = {
            "referenceId":  reference_id,
            "amount":       int(fiat_amount),   # Kotani expects integer fiat
            "currency":     fiat_currency.upper(),
            "chain":        chain,
            "token":        token,
            "walletAddress": wallet_address,
            "customerKey":  customer_key,
            "mobileMoneyReceiver": {
                "phoneNumber": phone_number,
                "telcoId":     telco_id.upper(),
            },
            "callbackUrl": callback_url,
        }
        resp = await self._post("/onramp", body)
        return resp.get("data", resp)

    async def get_onramp_status(self, reference_id: str) -> dict:
        resp = await self._get(f"/onramp/{reference_id}")
        return resp.get("data", resp)

    # ── OFFRAMP: crypto → mobile money ────────────────────────────────────────

    async def initiate_offramp(
        self,
        reference_id:  str,
        crypto_amount: Decimal,
        fiat_currency: str,
        crypto_asset:  str,
        phone_number:  str,
        telco_id:      str,
        customer_key:  str,
        callback_url:  str,
        markup_pct:    Decimal = DEFAULT_MARKUP_PCT,
    ) -> Dict[str, Any]:
        """
        Initiate Kotani offramp: deduct markup from crypto, forward net to Kotani.
        Customer receives fiat via mobile money.
        """
        chain_token = SEAMOUNT_TO_KOTANI.get(crypto_asset)
        if not chain_token:
            raise ValueError(f"Asset not supported by Kotani: {crypto_asset}")
        chain, token = chain_token

        markup_crypto = (crypto_amount * markup_pct).quantize(Decimal("0.000001"))
        net_crypto    = crypto_amount - markup_crypto

        logger.info(
            f"Kotani offramp | {crypto_asset} "
            f"gross={crypto_amount} markup={markup_crypto} net={net_crypto}"
        )

        body = {
            "referenceId":  reference_id,
            "cryptoAmount": float(net_crypto),
            "currency":     fiat_currency.upper(),
            "chain":        chain,
            "token":        token,
            "customerKey":  customer_key,
            "mobileMoneyReceiver": {
                "phoneNumber": phone_number,
                "telcoId":     telco_id.upper(),
            },
            "callbackUrl": callback_url,
        }
        resp = await self._post("/offramp", body)
        return {
            **(resp.get("data", resp)),
            "gross_crypto":    float(crypto_amount),
            "markup_crypto":   float(markup_crypto),
            "net_crypto_sent": float(net_crypto),
            "markup_pct":      float(markup_pct * 100),
        }

    async def get_offramp_status(self, reference_id: str) -> dict:
        resp = await self._get(f"/offramp/{reference_id}")
        return resp.get("data", resp)

    # ── Webhook verification ───────────────────────────────────────────────────

    def verify_webhook(self, raw_body: bytes, signature_header: str) -> bool:
        """Verify X-Kotani-Signature HMAC-SHA256."""
        if not self.webhook_secret:
            logger.warning("Kotani webhook secret not set — skipping signature check")
            return True
        try:
            payload      = raw_body.decode("utf-8")
            expected_sig = "sha256=" + hmac.new(
                self.webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256,
            ).hexdigest()
            valid = hmac.compare_digest(expected_sig, signature_header.strip())
            if not valid:
                logger.warning("❌ Kotani webhook signature mismatch")
            return valid
        except Exception as e:
            logger.error(f"Kotani webhook verify error: {e}")
            return False

    @staticmethod
    def get_supported_telcos(currency: str) -> list:
        return CURRENCY_TO_TELCOS.get(currency.upper(), [])