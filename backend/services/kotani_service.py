# File: backend/services/kotani_service.py
"""
Kotani Pay API Service — Production Ready
Handles mobile-money onramp/offramp for KES, GHS, UGX, TZS, RWF, ZMW, XOF, XAF.

Markup model:
  Onramp  → markup via rate presentation (quoted rate includes Seamount spread).
  Offramp → deduct markup from crypto before forwarding net amount to Kotani.

Key fixes vs. original:
  [1] Rate endpoints: GET /rates/onramp-rate → POST /rate/onramp  (wrong method + path)
  [2] Rate endpoints: GET /rates/offramp-rate → POST /rate/offramp (wrong method + path)
  [3] Rate request body: {currency, token} → {from, to, fiatAmount|cryptoAmount}
  [4] Customer endpoint: POST /customer → POST /customer/mobile-money
  [5] Customer body: camelCase → snake_case fields per OpenAPI spec
  [6] Onramp body: walletAddress → receiverAddress, mobileMoneyReceiver → mobileMoney
  [7] Onramp mobile sub-body: telcoId → providerNetwork, added accountName
  [8] Offramp mobile sub-body: telcoId → networkProvider, added accountName
  [9] hmac.new: added explicit msg= and digestmod= kwargs (Python 3.x safety)
  [10] Retry logic with exponential backoff on 429 / transient 5xx
"""

import hmac
import hashlib
import logging
import asyncio
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple

import aiohttp

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

KOTANI_SANDBOX_URL = "https://sandbox-api.kotanipay.com"
KOTANI_PROD_URL    = "https://api.kotanipay.com"

# Seamount internal asset key → (Kotani chain, Kotani token)
SEAMOUNT_TO_KOTANI: Dict[str, Tuple[str, str]] = {
    "USDT_POLYGON": ("POLYGON",  "USDT"),
    "USDC_POLYGON": ("POLYGON",  "USDC"),
    "USDT_TRON":    ("TRON",     "USDT"),
    "USDT_ETH":     ("ETHEREUM", "USDT"),
    "USDC_ETH":     ("ETHEREUM", "USDC"),
    "ETH":          ("ETHEREUM", "ETH"),
    "BTC":          ("BITCOIN",  "BTC"),
    "SOL":          ("SOLANA",   "SOL"),
    "USDT_SOLANA":  ("SOLANA",   "USDT"),
    "USDT_BASE":    ("BASE",     "USDT"),
    "USDC_BASE":    ("BASE",     "USDC"),
}

# Fiat currency → ISO-2 country code (for customer creation)
CURRENCY_TO_COUNTRY: Dict[str, str] = {
    "KES": "KE",
    "GHS": "GH",
    "UGX": "UG",
    "TZS": "TZ",
    "RWF": "RW",
    "ZMW": "ZM",
    "XOF": "SN",  # Senegal as default XOF; override at call site if needed
    "XAF": "CM",  # Cameroon as default XAF; override at call site if needed
    "NGN": "NG",
    "ZAR": "ZA",
}

# Fiat currency → supported network providers
CURRENCY_TO_NETWORKS: Dict[str, list] = {
    "KES": ["MPESA", "AIRTEL"],
    "GHS": ["MTN", "VODAFONE", "AIRTELTIGO"],
    "UGX": ["MTN", "AIRTEL"],
    "TZS": ["MPESA", "AIRTEL", "TIGO", "HALOPESA", "VODACOM"],
    "RWF": ["MTN", "AIRTEL"],
    "ZMW": ["MTN", "AIRTEL", "ZAMTEL"],
    "XOF": ["ORANGE", "MTN", "MOOV", "WAVE", "FREE"],
    "XAF": ["ORANGE", "MTN"],
    "NGN": ["MTN", "AIRTEL"],
    "ZAR": ["MTN"],
}

DEFAULT_MARKUP_PCT = Decimal("0.025")   # 2.5 %
_MAX_RETRIES       = 3
_RETRY_STATUSES    = {429, 500, 502, 503, 504}


# ── Service ────────────────────────────────────────────────────────────────────

class KotaniService:
    """
    Async wrapper around the Kotani Pay API v3.
    Thread-safe; create one instance per process and reuse it.
    """

    def __init__(
        self,
        api_key:        str,
        webhook_secret: str = "",
        environment:    str = "sandbox",
    ) -> None:
        self.api_key        = api_key
        self.webhook_secret = webhook_secret
        self.base_url       = (
            KOTANI_SANDBOX_URL if environment == "sandbox" else KOTANI_PROD_URL
        )
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        }
        logger.info("KotaniService init | env=%s | base=%s", environment, self.base_url)

    # ── HTTP helpers ───────────────────────────────────────────────────────────

    async def _request(
        self,
        method:  str,
        path:    str,
        *,
        body:    Optional[dict] = None,
        params:  Optional[dict] = None,
    ) -> dict:
        """
        Generic HTTP request with retry + exponential backoff.
        Raises KotaniError on non-success responses.
        """
        url      = f"{self.base_url}/api/v3{path}"
        attempt  = 0
        last_exc = None

        while attempt < _MAX_RETRIES:
            attempt += 1
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method,
                        url,
                        json=body,
                        params=params,
                        headers=self._headers,
                        timeout=aiohttp.ClientTimeout(total=20),
                    ) as resp:
                        # Always try to parse JSON; fall back to text on failure
                        try:
                            data = await resp.json(content_type=None)
                        except Exception:
                            text = await resp.text()
                            raise KotaniError(
                                path,
                                resp.status,
                                f"Non-JSON response: {text[:300]}",
                            )

                        logger.debug(
                            "Kotani %s %s → %s | %s",
                            method, path, resp.status, data.get("message", ""),
                        )

                        # Retry on transient server errors
                        if resp.status in _RETRY_STATUSES and attempt < _MAX_RETRIES:
                            retry_after = data.get("data", {}).get("retryAfter", 2 ** attempt)
                            logger.warning(
                                "Kotani %s %s | status=%s — retry %s/%s in %ss",
                                method, path, resp.status, attempt, _MAX_RETRIES, retry_after,
                            )
                            await asyncio.sleep(min(float(retry_after), 30.0))
                            continue

                        if not data.get("success"):
                            raise KotaniError(
                                path,
                                resp.status,
                                data.get("message", str(data)),
                                data.get("data"),
                            )

                        return data

            except KotaniError:
                raise  # propagate immediately — these are API-level errors
            except aiohttp.ClientError as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning(
                    "Kotani network error %s %s (attempt %s/%s): %s — retrying in %ss",
                    method, path, attempt, _MAX_RETRIES, exc, wait,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(wait)

        raise KotaniError(path, 0, f"Max retries exhausted: {last_exc}")

    async def _post(self, path: str, body: dict) -> dict:
        return await self._request("POST", path, body=body)

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        return await self._request("GET", path, params=params)

    # ── Customer management ────────────────────────────────────────────────────

    async def ensure_customer(
        self,
        phone_number:  str,
        country_code:  str,
        network:       str,
        account_name:  str,
        first_name:    str = "",
        last_name:     str = "",
        email:         str = "",
    ) -> dict:
        """
        Idempotent: create a Kotani mobile-money customer or swallow duplicate.
        Returns the customer data dict.

        POST /api/v3/customer/mobile-money
        Required: phone_number, country_code
        """
        payload: Dict[str, Any] = {
            "phone_number": phone_number,
            "country_code": country_code.upper(),
            "network":      network.upper(),
            "account_name": account_name,
        }
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if email:
            payload["email"] = email

        try:
            resp = await self._post("/customer/mobile-money", payload)
            return resp.get("data", {})
        except KotaniError as exc:
            msg = str(exc).lower()
            if "already exists" in msg or "duplicate" in msg or "exists" in msg:
                logger.info(
                    "Kotani customer already exists | phone=%s country=%s — skipping create",
                    phone_number, country_code,
                )
                return {"phone_number": phone_number, "country_code": country_code}
            raise

    # ── Rates ──────────────────────────────────────────────────────────────────

    async def get_onramp_rate(
        self,
        fiat_currency: str,
        token:         str,
        fiat_amount:   float,
    ) -> dict:
        """
        Fetch onramp exchange rate: fiat → crypto.

        POST /api/v3/rate/onramp
        Body: { from: fiat_currency, to: stablecoin, fiatAmount: number }
        Returns: { from, to, value, id, fiatAmount, cryptoAmount, transactionAmount, fee }
        """
        resp = await self._post(
            "/rate/onramp",
            {
                "from":       fiat_currency.upper(),
                "to":         token.upper(),
                "fiatAmount": float(fiat_amount),
            },
        )
        return resp.get("data", resp)

    async def get_offramp_rate(
        self,
        token:         str,
        fiat_currency: str,
        crypto_amount: float,
    ) -> dict:
        """
        Fetch offramp exchange rate: crypto → fiat.

        POST /api/v3/rate/offramp
        Body: { from: stablecoin, to: fiat_currency, cryptoAmount: number }
        Returns: { from, to, value, id, fiatAmount, cryptoAmount, transactionAmount, fee }
        """
        resp = await self._post(
            "/rate/offramp",
            {
                "from":         token.upper(),
                "to":           fiat_currency.upper(),
                "cryptoAmount": float(crypto_amount),
            },
        )
        return resp.get("data", resp)

    # ── ONRAMP: mobile money → crypto ──────────────────────────────────────────

    async def initiate_onramp(
        self,
        reference_id:    str,
        fiat_amount:     Decimal,
        fiat_currency:   str,
        crypto_asset:    str,
        receiver_address: str,
        phone_number:    str,
        network_provider: str,
        account_name:    str,
        callback_url:    str,
        rate_id:         Optional[str] = None,
        fiat_wallet_id:  Optional[str] = None,
    ) -> dict:
        """
        Initiate onramp: customer pays fiat via mobile money → crypto sent to wallet.

        POST /api/v3/onramp
        Markup is applied via rate presentation upstream (quoted rate embeds spread).

        Args:
            reference_id:     Unique idempotency key for this transaction.
            fiat_amount:      Amount in fiat the customer will pay (integer, no decimals).
            fiat_currency:    ISO fiat code e.g. KES, GHS.
            crypto_asset:     Seamount asset key e.g. USDT_POLYGON.
            receiver_address: On-chain wallet address to receive crypto.
            phone_number:     Customer's mobile money phone number.
            network_provider: Mobile network e.g. MPESA, MTN.
            account_name:     Customer's registered account name on the network.
            callback_url:     Publicly reachable HTTPS endpoint for status callbacks.
            rate_id:          Optional. Lock the rate from get_onramp_rate().
            fiat_wallet_id:   Optional. Link to a specific integrator fiat wallet.
        """
        chain, token = _resolve_asset(crypto_asset)

        body: Dict[str, Any] = {
            "referenceId":     reference_id,
            "fiatAmount":      int(fiat_amount),
            "currency":        fiat_currency.upper(),
            "chain":           chain,
            "token":           token,
            "receiverAddress": receiver_address,
            "callbackUrl":     callback_url,
            "mobileMoney": {
                "phoneNumber":     phone_number,
                "accountName":     account_name,
                "providerNetwork": network_provider.upper(),
            },
        }
        if rate_id:
            body["rateId"] = rate_id
        if fiat_wallet_id:
            body["fiatWalletId"] = fiat_wallet_id

        logger.info(
            "Kotani onramp | ref=%s amount=%s %s → %s",
            reference_id, fiat_amount, fiat_currency, crypto_asset,
        )
        resp = await self._post("/onramp", body)
        return resp.get("data", resp)

    async def get_onramp_status(self, reference_id: str) -> dict:
        """GET /api/v3/onramp/:referenceId"""
        resp = await self._get(f"/onramp/{reference_id}")
        return resp.get("data", resp)

    async def get_onramp_crypto_status(self, reference_id: str) -> dict:
        """GET /api/v3/onramp/crypto/:referenceId — crypto delivery status"""
        resp = await self._get(f"/onramp/crypto/{reference_id}")
        return resp.get("data", resp)

    # ── OFFRAMP: crypto → mobile money ────────────────────────────────────────

    async def initiate_offramp(
        self,
        reference_id:     str,
        crypto_amount:    Decimal,
        fiat_currency:    str,
        crypto_asset:     str,
        phone_number:     str,
        network_provider: str,
        account_name:     str,
        callback_url:     str,
        markup_pct:       Decimal = DEFAULT_MARKUP_PCT,
        sender_address:   Optional[str] = None,
        rate_id:          Optional[str] = None,
        refund_address:   Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Initiate offramp: customer sends crypto → receives fiat via mobile money.
        Seamount markup is deducted from crypto before forwarding net to Kotani.

        POST /api/v3/offramp

        Args:
            reference_id:     Unique idempotency key.
            crypto_amount:    Gross crypto amount from the customer.
            fiat_currency:    Target fiat ISO code e.g. KES.
            crypto_asset:     Seamount asset key e.g. USDT_POLYGON.
            phone_number:     Recipient's mobile money number.
            network_provider: Mobile network e.g. MPESA, MTN.
            account_name:     Recipient's registered account name.
            callback_url:     HTTPS endpoint for status callbacks.
            markup_pct:       Seamount fee as a decimal fraction (default 2.5%).
            sender_address:   Optional on-chain sender address for audit trail.
            rate_id:          Optional locked rate ID from get_offramp_rate().
            refund_address:   Optional on-chain address for automatic crypto refunds.
        """
        chain, token = _resolve_asset(crypto_asset)

        markup_crypto = (crypto_amount * markup_pct).quantize(Decimal("0.000001"))
        net_crypto    = crypto_amount - markup_crypto

        logger.info(
            "Kotani offramp | ref=%s %s gross=%s markup=%s(%s%%) net=%s",
            reference_id, crypto_asset,
            crypto_amount, markup_crypto, float(markup_pct * 100), net_crypto,
        )

        body: Dict[str, Any] = {
            "referenceId":  reference_id,
            "cryptoAmount": float(net_crypto),
            "currency":     fiat_currency.upper(),
            "chain":        chain,
            "token":        token,
            "callbackUrl":  callback_url,
            "mobileMoneyReceiver": {
                "phoneNumber":   phone_number,
                "accountName":   account_name,
                "networkProvider": network_provider.upper(),
            },
        }
        if sender_address:
            body["senderAddress"] = sender_address
        if rate_id:
            body["rateId"] = rate_id
        if refund_address:
            body["refund_config"] = {"address": refund_address}

        resp = await self._post("/offramp", body)
        data = resp.get("data", resp)

        # Augment response with Seamount fee breakdown for internal audit
        return {
            **data,
            "_seamount": {
                "gross_crypto":    float(crypto_amount),
                "markup_crypto":   float(markup_crypto),
                "net_crypto_sent": float(net_crypto),
                "markup_pct":      float(markup_pct * 100),
            },
        }

    async def get_offramp_status(self, reference_id: str) -> dict:
        """GET /api/v3/offramp/:referenceId"""
        resp = await self._get(f"/offramp/{reference_id}")
        return resp.get("data", resp)

    async def get_offramp_refund_status(self, reference_id: str) -> dict:
        """GET /api/v3/offramp/refund-status/:referenceId"""
        resp = await self._get(f"/offramp/refund-status/{reference_id}")
        return resp.get("data", resp)

    async def retry_offramp_refund(self, reference_id: str) -> dict:
        """POST /api/v3/offramp/retry-refund/:referenceId"""
        resp = await self._post(f"/offramp/retry-refund/{reference_id}", {})
        return resp.get("data", resp)

    async def cancel_offramp(self, reference_id: str) -> dict:
        """GET /api/v3/offramp/cancel/:referenceId — only works while PENDING"""
        resp = await self._get(f"/offramp/cancel/{reference_id}")
        return resp.get("data", resp)

    # ── Wallets ────────────────────────────────────────────────────────────────

    async def list_fiat_wallets(self) -> list:
        """GET /api/v3/wallets/fiat"""
        resp = await self._get("/wallets/fiat")
        return resp.get("data", [])

    async def get_fiat_wallet_by_currency(self, currency: str) -> dict:
        """GET /api/v3/wallets/fiat/currency — filter by currency"""
        resp = await self._get(
            "/wallets/fiat/currency",
            params={"currency": currency.upper()},
        )
        return resp.get("data", resp)

    async def transfer_deposit_to_payout(
        self, wallet_id: str, amount: float
    ) -> dict:
        """
        POST /api/v3/wallets/fiat/:walletId/transfer-deposit-balance
        Moves funds from deposit balance to payout balance so withdrawals can proceed.
        """
        resp = await self._post(
            f"/wallets/fiat/{wallet_id}/transfer-deposit-balance",
            {"amount": amount},
        )
        return resp.get("data", resp)

    # ── Webhook verification ───────────────────────────────────────────────────

    def verify_webhook(self, raw_body: bytes, signature_header: str) -> bool:
        """
        Verify X-Kotani-Signature HMAC-SHA256 for signed webhook delivery.

        Algorithm:
          1. Parse JSON body, remove 'signature' field.
          2. Compute sha256=HMAC-SHA256(secret, JSON.stringify({event, data})).
          3. Compare with header using timing-safe comparison.

        Without a webhook_secret configured, all webhooks pass through (log warning).
        """
        if not self.webhook_secret:
            logger.warning(
                "Kotani webhook secret not configured — skipping signature verification. "
                "Set KOTANI_WEBHOOK_SECRET in production."
            )
            return True

        try:
            import json

            body_str = raw_body.decode("utf-8")
            payload  = json.loads(body_str)

            # Strip body-level signature field per Kotani spec
            payload.pop("signature", None)

            canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

            expected = "sha256=" + hmac.new(
                key=self.webhook_secret.encode("utf-8"),
                msg=canonical.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).hexdigest()

            valid = hmac.compare_digest(
                expected,
                signature_header.strip(),
            )
            if not valid:
                logger.warning(
                    "Kotani webhook signature mismatch | "
                    "expected=%s... received=%s...",
                    expected[:20], signature_header[:20],
                )
            return valid

        except Exception as exc:
            logger.error("Kotani webhook verification error: %s", exc, exc_info=True)
            return False

    def parse_webhook_event(self, raw_body: bytes) -> Dict[str, Any]:
        """
        Parse and lightly validate a signed webhook payload.
        Returns the full payload dict.
        Raises ValueError on malformed input.
        """
        import json
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"Malformed webhook body: {exc}") from exc

        event = payload.get("event")
        data  = payload.get("data")
        if not event or data is None:
            raise ValueError(
                f"Webhook payload missing 'event' or 'data' fields: {payload}"
            )
        return payload

    # ── Utility ────────────────────────────────────────────────────────────────

    @staticmethod
    def get_supported_networks(currency: str) -> list:
        """Return the list of supported mobile networks for a given fiat currency."""
        return CURRENCY_TO_NETWORKS.get(currency.upper(), [])

    @staticmethod
    def get_country_code(currency: str) -> Optional[str]:
        """Return ISO-2 country code for a fiat currency."""
        return CURRENCY_TO_COUNTRY.get(currency.upper())

    @staticmethod
    def generate_reference_id(prefix: str = "SMT") -> str:
        """Generate a collision-resistant reference ID."""
        return f"{prefix}-{uuid.uuid4().hex[:16].upper()}"


# ── Custom exception ───────────────────────────────────────────────────────────

class KotaniError(Exception):
    """Raised when Kotani Pay returns a non-success response."""

    def __init__(
        self,
        path:       str,
        status:     int,
        message:    str,
        detail:     Any = None,
    ) -> None:
        self.path    = path
        self.status  = status
        self.message = message
        self.detail  = detail
        super().__init__(f"Kotani [{status}] {path}: {message}")


# ── Internal helpers ───────────────────────────────────────────────────────────

def _resolve_asset(crypto_asset: str) -> Tuple[str, str]:
    """Resolve a Seamount asset key to (Kotani chain, Kotani token). Raises ValueError if unknown."""
    result = SEAMOUNT_TO_KOTANI.get(crypto_asset)
    if not result:
        supported = ", ".join(SEAMOUNT_TO_KOTANI.keys())
        raise ValueError(
            f"Unsupported crypto asset: '{crypto_asset}'. Supported: {supported}"
        )
    return result