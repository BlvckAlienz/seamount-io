# File: backend/services/busha_service.py
"""
Busha API Service
Handles onramp (fiat → crypto) and offramp (crypto → fiat).
Onramp uses two-step markup: collect gross fiat → convert base amount → keep spread.
Offramp: sell crypto → pay net fiat to recipient → keep markup in balance.
"""
import logging
import aiohttp
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

BUSHA_SANDBOX_URL = "https://api.sandbox.busha.so"
BUSHA_PROD_URL    = "https://api.busha.so"

# Seamount internal asset code → Busha currency code
SEAMOUNT_TO_BUSHA: Dict[str, str] = {
    "USDT_TRON":    "USDT",
    "USDT_ETH":     "USDT",
    "USDT_POLYGON": "USDT",
    "USDC_ETH":     "USDC",
    "USDC_POLYGON": "USDC",
    "USDC_SOLANA":  "USDC",
    "ETH":          "ETH",
    "BTC":          "BTC",
    "MATIC":        "MATIC",
    "SOL":          "SOL",
    "TRX":          "TRX",
    "USDT_SOLANA":  "USDT",
}

# Seamount asset → Busha network string
SEAMOUNT_TO_BUSHA_NETWORK: Dict[str, str] = {
    "USDT_TRON":    "TRX",
    "USDT_ETH":     "ERC20",
    "USDT_POLYGON": "POLYGON",
    "USDC_ETH":     "ERC20",
    "USDC_POLYGON": "POLYGON",
    "USDC_SOLANA":  "SOL",
    "ETH":          "ETH",
    "BTC":          "BTC",
    "MATIC":        "POLYGON",
    "SOL":          "SOL",
    "TRX":          "TRX",
    "USDT_SOLANA":  "SOL",
}

DEFAULT_MARKUP_PCT = Decimal("0.025")  # 2.5%


class BushaService:

    def __init__(self, secret_key: str, environment: str = "sandbox"):
        self.secret_key = secret_key
        self.base_url   = BUSHA_SANDBOX_URL if environment == "sandbox" else BUSHA_PROD_URL
        self._headers   = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type":  "application/json",
        }
        logger.info(f"BushaService init | env={environment} | base={self.base_url}")

    # ── HTTP helpers ───────────────────────────────────────────────────────────

    async def _post(self, path: str, body: dict, extra_headers: dict = None) -> dict:
        headers = {**self._headers, **(extra_headers or {})}
        url = f"{self.base_url}{path}"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    url, json=body, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as r:
                    data = await r.json()
                    logger.info(f"Busha POST {path} → {r.status} | {data.get('message','')}")
                    if r.status not in (200, 201):
                        raise Exception(
                            f"Busha {path} HTTP {r.status}: {data.get('message', str(data))}"
                        )
                    return data
        except aiohttp.ClientError as e:
            logger.error(f"Busha network error {path}: {e}")
            raise Exception(f"Busha API unreachable: {e}")

    async def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    url, params=params, headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    data = await r.json()
                    if r.status != 200:
                        raise Exception(
                            f"Busha GET {path} HTTP {r.status}: {data.get('message', str(data))}"
                        )
                    return data
        except aiohttp.ClientError as e:
            logger.error(f"Busha network error GET {path}: {e}")
            raise Exception(f"Busha API unreachable: {e}")

    # ── Core quote + transfer ──────────────────────────────────────────────────

    async def create_quote(
        self,
        source_currency: str,
        target_currency: str,
        source_amount:   str,
        pay_in:          Optional[dict] = None,
        pay_out:         Optional[dict] = None,
    ) -> dict:
        body: Dict[str, Any] = {
            "source_currency": source_currency.upper(),
            "target_currency": target_currency.upper(),
            "source_amount":   str(source_amount),
        }
        if pay_in:  body["pay_in"]  = pay_in
        if pay_out: body["pay_out"] = pay_out
        resp = await self._post("/v1/quotes", body)
        return resp["data"]

    async def create_transfer(self, quote_id: str) -> dict:
        resp = await self._post("/v1/transfers", {"quote_id": quote_id})
        return resp["data"]

    async def get_transfer(self, transfer_id: str) -> dict:
        resp = await self._get(f"/v1/transfers/{transfer_id}")
        return resp["data"]

    # ── Recipient management ───────────────────────────────────────────────────

    async def create_recipient(self, recipient_type: str, **kwargs) -> dict:
        """
        Create a payout recipient.
        recipient_type: "ngn_bank" | "mpesa_mobile_money"
        Returns dict with `id` field.
        """
        body = {"type": recipient_type, **kwargs}
        resp = await self._post(
            "/v1/recipients", body,
            extra_headers={"X-BU-VERSION": "2025-07-11"},
        )
        return resp["data"]

    # ── ONRAMP: fiat → crypto (two-step markup) ───────────────────────────────

    async def initiate_onramp_deposit(
        self,
        fiat_currency: str,
        fiat_amount:   Decimal,
        markup_pct:    Decimal = DEFAULT_MARKUP_PCT,
    ) -> Tuple[dict, Decimal, Decimal]:
        """
        Step 1 of 2: Create temporary bank account for gross fiat collection.
        Returns (transfer_data, gross_amount, markup_amount).
        Call execute_onramp_conversion() after deposit webhook confirms.
        """
        markup_amount = (fiat_amount * markup_pct).quantize(Decimal("0.01"))
        gross_amount  = fiat_amount + markup_amount

        logger.info(
            f"Busha onramp deposit | {fiat_currency} "
            f"base={fiat_amount} markup={markup_amount} gross={gross_amount}"
        )

        # NGN→NGN quote just to get the temp bank account details
        quote    = await self.create_quote(
            source_currency=fiat_currency,
            target_currency=fiat_currency,
            source_amount=str(gross_amount),
            pay_in={"type": "temporary_bank_account"},
        )
        transfer = await self.create_transfer(quote["id"])
        return transfer, gross_amount, markup_amount

    async def execute_onramp_conversion(
        self,
        fiat_currency: str,
        base_amount:   Decimal,
        crypto_asset:  str,
    ) -> dict:
        """
        Step 2 of 2: Convert base fiat (from balance) to crypto.
        Called after Busha webhook confirms deposit received.
        """
        busha_code = SEAMOUNT_TO_BUSHA.get(crypto_asset)
        if not busha_code:
            raise ValueError(f"Asset not supported by Busha: {crypto_asset}")

        logger.info(
            f"Busha onramp conversion | {fiat_currency} {base_amount} → {busha_code}"
        )

        quote    = await self.create_quote(
            source_currency=fiat_currency,
            target_currency=busha_code,
            source_amount=str(base_amount),
            pay_in={"type": "balance"},
            pay_out={"type": "balance"},
        )
        return await self.create_transfer(quote["id"])

    # ── OFFRAMP: crypto → fiat ─────────────────────────────────────────────────

    async def get_offramp_rate(
        self,
        crypto_asset:  str,
        fiat_currency: str,
        crypto_amount: Decimal,
        markup_pct:    Decimal = DEFAULT_MARKUP_PCT,
    ) -> Dict[str, Any]:
        """
        Probe Busha for offramp rate and compute user-facing quote.
        Markup deducted from gross fiat → user receives less fiat.
        """
        busha_code = SEAMOUNT_TO_BUSHA.get(crypto_asset)
        if not busha_code:
            raise ValueError(f"Asset not supported by Busha: {crypto_asset}")

        quote = await self.create_quote(
            source_currency=busha_code,
            target_currency=fiat_currency.upper(),
            source_amount=str(crypto_amount),
        )

        gross_fiat    = Decimal(str(quote["target_amount"]))
        markup_amount = (gross_fiat * markup_pct).quantize(Decimal("0.01"))
        net_fiat      = gross_fiat - markup_amount

        return {
            "probe_quote_id": quote["id"],
            "busha_rate":     quote["rate"]["rate"],
            "gross_fiat":     str(gross_fiat),
            "markup_amount":  str(markup_amount),
            "net_fiat":       str(net_fiat),
            "markup_pct":     str(markup_pct * 100),
            "crypto_amount":  str(crypto_amount),
            "fiat_currency":  fiat_currency,
            "expires_at":     quote.get("expires_at"),
        }

    async def execute_offramp(
        self,
        crypto_asset:  str,
        crypto_amount: Decimal,
        fiat_currency: str,
        recipient_id:  str,
        net_fiat:      Decimal,
    ) -> Tuple[dict, dict]:
        """
        Execute offramp: sell crypto → gross fiat lands in balance
        → pay net fiat to recipient → markup stays in balance.
        Returns (crypto_transfer, payout_transfer).
        """
        busha_code = SEAMOUNT_TO_BUSHA.get(crypto_asset)
        if not busha_code:
            raise ValueError(f"Asset not supported by Busha: {crypto_asset}")

        # Step 1: sell crypto, land fiat in balance
        sell_quote = await self.create_quote(
            source_currency=busha_code,
            target_currency=fiat_currency.upper(),
            source_amount=str(crypto_amount),
            pay_in={"type": "balance"},
            pay_out={"type": "balance"},
        )
        crypto_transfer = await self.create_transfer(sell_quote["id"])
        logger.info(f"Busha offramp sell executed: {crypto_transfer['id']}")

        # Step 2: pay net fiat to recipient (markup stays in balance)
        payout_quote = await self.create_quote(
            source_currency=fiat_currency.upper(),
            target_currency=fiat_currency.upper(),
            source_amount=str(net_fiat),
            pay_in={"type": "balance"},
            pay_out={"type": "bank_transfer", "recipient_id": recipient_id},
        )
        payout_transfer = await self.create_transfer(payout_quote["id"])
        logger.info(f"Busha offramp payout executed: {payout_transfer['id']}")

        return crypto_transfer, payout_transfer