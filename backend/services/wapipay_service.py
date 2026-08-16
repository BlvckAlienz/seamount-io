# File: backend/services/wapipay_service.py
"""
WapiPay Service — Token Manager, Route Registry, Core API
Covers: Virtual Account (NGN onramp), Bank Payment, Mobile Payment, Rates
"""
import asyncio
import base64
import hashlib
import hmac
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import aiohttp
from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt,
    wait_exponential, before_sleep_log
)

logger = logging.getLogger(__name__)

# ── MCCMNC lookup: currency → mobile network codes ─────────────────────────
MCCMNC_MAP: Dict[str, Dict[str, str]] = {
    "KES": {"MPESA": "63902", "AIRTEL": "63903"},
    "UGX": {"MTN": "64110", "AIRTEL": "64101"},
    "TZS": {"MPESA": "64002", "AIRTEL": "64004", "TIGO": "64003"},
    "RWF": {"MTN": "63501", "AIRTEL": "63502"},
    "ZMW": {"MTN": "64502", "AIRTEL": "64501", "ZAMTEL": "64503"},
    "GHS": {"MTN": "62001", "VODAFONE": "62002", "AIRTELTIGO": "62006"},
    "XOF": {"ORANGE": "61002", "MTN": "61401"},
    "XAF": {"ORANGE": "62401", "MTN": "62401"},
}

WAPIPAY_SANDBOX = "https://sandbox-test.wapipay.com"
WAPIPAY_PROD    = "https://api.wapipay.com"  # confirm with WapiPay docs at go-live


class WapiPayTokenManager:
    """Singleton token manager. Thread-safe, self-healing, 60s buffer on refresh."""

    def __init__(self, client_id: str, client_secret: str, base_url: str):
        self._client_id     = client_id
        self._client_secret = client_secret
        self._base_url      = base_url
        self._token: Optional[str] = None
        self._expires_at: float    = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        async with self._lock:
            if self._token and time.time() < (self._expires_at - 60):
                return self._token
            await self._refresh()
            return self._token  # type: ignore

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _refresh(self) -> None:
        creds  = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()
        headers = {
            "Authorization": f"Basic {creds}",
            "Content-Type":  "application/x-www-form-urlencoded",
            "Accept":        "application/json",
        }
        payload = {
            "grant_type":    "client_credentials",
            "client_id":     self._client_id,
            "client_secret": self._client_secret,
            "scope":         "read write",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}/connect/token",
                headers=headers,
                data=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise Exception(f"WapiPay auth failed [{resp.status}]: {body}")
                data            = await resp.json()
                self._token     = data["access_token"]
                self._expires_at = time.time() + data.get("expires_in", 3600)
                logger.info("✅ WapiPay token refreshed, expires in %ss", data.get("expires_in"))


class WapiPayService:
    """
    Core WapiPay service.
    Single instance — inject via dependency.
    """

    def __init__(
        self,
        client_id:     str,
        client_secret: str,
        environment:   str = "sandbox",
        webhook_secret: str = "",
    ):
        self._base_url      = WAPIPAY_SANDBOX if environment == "sandbox" else WAPIPAY_PROD
        self._webhook_secret = webhook_secret
        self._token_mgr     = WapiPayTokenManager(client_id, client_secret, self._base_url)
        self._route_cache:  Dict[str, Any] = {}
        self._route_cache_ts: float        = 0.0
        logger.info("🌍 WapiPayService init | env=%s | base=%s", environment, self._base_url)

    # ── Internal helpers ────────────────────────────────────────────────────

    async def _headers(self) -> Dict[str, str]:
        token = await self._token_mgr.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _post(self, path: str, body: Dict) -> Dict:
        headers = await self._headers()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}{path}",
                headers=headers,
                json=body,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                if resp.status == 401:
                    # Force token refresh and retry once
                    self._token_mgr._token = None
                    headers = await self._headers()
                    raise aiohttp.ClientError("401 — forcing token refresh")
                logger.debug("POST %s → %s", path, resp.status)
                return data

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True
    )
    async def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        headers = await self._headers()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._base_url}{path}",
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
                logger.debug("GET %s → %s", path, resp.status)
                return data

    # ── Route Registry ───────────────────────────────────────────────────────

    async def get_routes(self, force_refresh: bool = False) -> Dict:
        """
        Fetch & cache assigned transaction routes.
        Cache TTL: 6 hours. Call at startup and via background job.
        """
        if not force_refresh and self._route_cache and (
            time.time() - self._route_cache_ts < 21600
        ):
            return self._route_cache

        try:
            data = await self._get("/v1/transaction-routes/assigned-routes")
            self._route_cache    = data
            self._route_cache_ts = time.time()
            logger.info("✅ WapiPay routes refreshed: %s routes", len(data) if isinstance(data, list) else "?")
            return data
        except Exception as e:
            logger.error("❌ Route refresh failed: %s", e)
            if self._route_cache:
                logger.warning("⚠️ Using stale route cache")
                return self._route_cache
            raise

    async def _get_route_id(self, country: str, channel_type: int) -> Tuple[str, str]:
        """
        Returns (routeId, transactionTypeId) for a given country+channel.
        channel_type: 1=bank, 175=mobile
        🚨 This MUST succeed before any payment order is built.
        """
        routes = await self.get_routes()
        route_list = routes if isinstance(routes, list) else routes.get("data", [])
        for r in route_list:
            if (
                r.get("countryCode", "").upper() == country.upper()
                and r.get("channelType") == channel_type
            ):
                return r["routeId"], r.get("transactionTypeId", "")
        raise ValueError(
            f"No WapiPay route for country={country} channel={channel_type}. "
            f"Contact WapiPay to enable this corridor."
        )

    # ── Rates ────────────────────────────────────────────────────────────────

    async def get_rates(self) -> Dict:
        return await self._get("/v1/rates/fetch")

    async def get_charges(self, transaction_type_id: str) -> Dict:
        return await self._get(
            "/v1/charge/fetch-charges",
            params={"transactionTypeId": transaction_type_id}
        )

    async def get_corridor_quote(
        self,
        country: str,
        channel_type: int,
        amount: float,
        currency: str,
    ) -> Dict:
        """
        Full quote: rates + charges for a corridor.
        Returns unified quote dict for frontend.
        """
        try:
            _, tx_type_id = await self._get_route_id(country, channel_type)
            rates    = await self.get_rates()
            charges  = await self.get_charges(tx_type_id) if tx_type_id else {}

            charge_amount = float(charges.get("chargeAmount", 0))
            charge_pct    = float(charges.get("chargePercentage", 0))
            fee           = charge_amount + (amount * charge_pct / 100)
            net_amount    = amount - fee

            return {
                "success":       True,
                "gross_amount":  amount,
                "fee":           round(fee, 2),
                "net_amount":    round(net_amount, 2),
                "currency":      currency,
                "charge_detail": charges,
                "rates":         rates,
            }
        except Exception as e:
            logger.error("❌ WapiPay corridor quote failed: %s", e)
            return {"success": False, "error": str(e)}

    # ── Account Validation ────────────────────────────────────────────────────

    async def validate_account(
        self,
        account_number: str,
        institution_code: str,
        account_type: int = 2,  # 1=mobile, 2=bank
        currency: str = "NGN",
        country: str = "NG",
        callback_url: str = "",
    ) -> Dict:
        trace = str(uuid.uuid4())
        body = {
            "type":                   account_type,
            "systemTraceAuditNumber": trace,
            "primaryAccountNumber":   account_number,
            "institutionCode":        institution_code,
            "callBackUrl":            callback_url or "https://seamount-api.onrender.com/webhooks/wapipay/payouts",
            "callBackFormat":         "JSON",
            "ccy":                    currency,
            "countryCode":            country,
        }
        try:
            result = await self._post("/v1/account/validate", body)
            logger.info("✅ WapiPay account validation sent: %s", trace)
            return {"success": True, "trace": trace, "data": result}
        except Exception as e:
            logger.error("❌ Account validation failed: %s", e)
            return {"success": False, "error": str(e)}

    # ── Virtual Account (NGN Onramp) ─────────────────────────────────────────

    async def create_virtual_account(
        self,
        user_id: str,
        user_name: str,
        user_email: str,
    ) -> Dict:
        """
        Create a persistent NGN virtual account for a user.
        Returns account details to display in FundWalletModal.
        """
        originator_id = f"VA_{user_id[:8]}_{int(time.time())}"
        body = {
            "originatorConversationId": originator_id,
            "accountName":              user_name,
            "email":                    user_email,
            "callBackUrl":              "https://seamount-api.onrender.com/webhooks/wapipay/collections",
            "callBackFormat":           "JSON",
            "ccy":                      "NGN",
            "countryCode":              "NG",
        }
        try:
            result = await self._post(
                "/nigeria-services/api/v1/virtual-account/create", body
            )
            logger.info("✅ WapiPay virtual account created for user %s", user_id[:8])
            return {"success": True, "data": result, "originator_id": originator_id}
        except Exception as e:
            logger.error("❌ Virtual account creation failed for %s: %s", user_id[:8], e)
            return {"success": False, "error": str(e)}

    # ── Express Deposit (EA Mobile Onramp — STK push) ────────────────────────

    async def express_deposit(
        self,
        short_code: str,
        amount: float,
        phone_number: str,
        account_no: str,
        originator_id: str,
        description: str,
        callback_url: str,
    ) -> Dict:
        body = {
            "ShortCode":               short_code,
            "Amount":                  str(amount),
            "PhoneNumber":             phone_number,
            "AccountNo":               account_no,
            "TransactionDesc":         description,
            "OriginatorConversationId": originator_id,
            "CallBackUrl":             callback_url,
        }
        try:
            result = await self._post("/v1/payment-order/express-deposit", body)
            logger.info("✅ Express deposit initiated: %s → %s", amount, phone_number)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error("❌ Express deposit failed: %s", e)
            return {"success": False, "error": str(e)}

    # ── Bank Payment Order (Offramp) ──────────────────────────────────────────

    async def bank_payment(
        self,
        amount:           float,
        currency:         str,
        country:          str,
        account_number:   str,
        account_name:     str,
        bank_swift_or_code: str,
        remitter_name:    str,
        remitter_id:      str,
        remitter_phone:   str,
        remitter_source_of_funds: str,
        reference:        str,
    ) -> Dict:
        route_id, _ = await self._get_route_id(country, 1)  # 1 = bank
        originator_id = f"BANK_{reference}"
        body = {
            "originatorConversationId": originator_id,
            "paymentNotes":             f"Seamount withdrawal {reference}",
            "remitter": {
                "name":           remitter_name,
                "phoneNumber":    remitter_phone,
                "idNumber":       remitter_id,
                "sourceOfFunds":  remitter_source_of_funds,
            },
            "recipient": {
                "name":                 account_name,
                "primaryAccountNumber": account_number,
                "institutionIdentifier": bank_swift_or_code,
                "ccy":                  currency,
                "country":              country,
            },
            "transaction": {
                "routeId":               route_id,
                "channelType":           1,
                "amount":                amount,
                "reference":             reference,
                "systemTraceAuditNumber": str(uuid.uuid4()),
            },
            "metaDataList": [
                {"key": "platform", "value": "seamount"}
            ],
        }
        try:
            result = await self._post("/v1/payment-order/new-order", body)
            logger.info("✅ WapiPay bank payment initiated: %s %s", amount, currency)
            return {"success": True, "data": result, "originator_id": originator_id}
        except Exception as e:
            logger.error("❌ Bank payment failed: %s", e)
            return {"success": False, "error": str(e)}

    # ── Mobile Payment Order (Offramp) ────────────────────────────────────────

    async def mobile_payment(
        self,
        amount:        float,
        currency:      str,
        country:       str,
        phone_number:  str,
        network:       str,   # e.g. "MPESA", "MTN"
        recipient_name: str,
        remitter_name: str,
        remitter_id:   str,
        remitter_phone: str,
        remitter_address: str,
        remitter_country: str,
        remitter_source_of_funds: str,
        reference:     str,
    ) -> Dict:
        route_id, _ = await self._get_route_id(country, 175)  # 175 = mobile
        mccmnc       = MCCMNC_MAP.get(currency, {}).get(network.upper(), "")
        originator_id = f"MOB_{reference}"
        body = {
            "originatorConversationId": originator_id,
            "remitter": {
                "name":        remitter_name,
                "phoneNumber": remitter_phone,
                "idNumber":    remitter_id,
                "country":     remitter_country,
                "ccy":         840,  # USD numeric ISO
                "sourceOfFunds": remitter_source_of_funds,
                "address":     remitter_address,
            },
            "recipient": {
                "name":                 recipient_name,
                "primaryAccountNumber": phone_number,
                "mccmnc":               mccmnc,
                "ccy":                  currency,
                "country":              country,
                "purpose":              "Personal Remittance",
            },
            "transaction": {
                "routeId":               route_id,
                "ChannelType":           175,
                "amount":                amount,
                "reference":             reference,
                "systemTraceAuditNumber": str(uuid.uuid4()),
            },
            "metaDataList": [
                {"key": "platform", "value": "seamount"}
            ],
        }
        try:
            result = await self._post("/v1/payment-order/new-order", body)
            logger.info("✅ WapiPay mobile payment initiated: %s %s → %s", amount, currency, phone_number)
            return {"success": True, "data": result, "originator_id": originator_id}
        except Exception as e:
            logger.error("❌ Mobile payment failed: %s", e)
            return {"success": False, "error": str(e)}

    # ── Webhook Verification ──────────────────────────────────────────────────

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        """
        🚨 WapiPay webhook signature method TBD — confirm with WapiPay support.
        Currently permissive (logs mismatch but doesn't block).
        Replace with real HMAC once WapiPay confirms their method.
        """
        if not self._webhook_secret or not signature:
            logger.warning("⚠️ WapiPay webhook: no secret configured, skipping sig check")
            return True  # permissive until WapiPay confirms sig method
        try:
            expected = hmac.new(
                self._webhook_secret.encode(),
                raw_body,
                hashlib.sha256,
            ).hexdigest()
            valid = hmac.compare_digest(expected, signature)
            if not valid:
                logger.warning("❌ WapiPay webhook signature mismatch")
            return valid
        except Exception as e:
            logger.error("❌ Webhook verification error: %s", e)
            return False