# File: backend/services/wapipay_credit_worker.py
"""
WapiPay Credit Worker
Polls wapipay_transactions WHERE type='onramp' AND status='pending_credit',
converts NGN → USDT, credits wallet_balances, marks completed.

Self-healing: retries on failure up to MAX_RETRIES, then flags for manual review.
Concurrency-safe: atomic compare-and-swap claim before crediting.
"""
import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

MAX_RETRIES     = 5
POLL_INTERVAL_S = 30
BATCH_LIMIT     = 20

# 🚨 PLACEHOLDER — confirm real WapiPay VA fee with their team, then update.
WAPIPAY_ONRAMP_FEE_RATE = Decimal("0.015")  # 1.5%


class WapiPayCreditWorker:
    def __init__(self, db_service, oracle_service):
        self.db      = db_service
        self.oracle  = oracle_service
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("✅ WapiPay credit worker started (poll every %ss)", POLL_INTERVAL_S)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("✅ WapiPay credit worker stopped")

    async def _loop(self):
        while self._running:
            try:
                await self._process_batch()
            except Exception as e:
                logger.error("❌ WapiPay credit worker batch failed: %s", e, exc_info=True)
            await asyncio.sleep(POLL_INTERVAL_S)

    async def _process_batch(self):
        result = self.db.supabase.from_("wapipay_transactions") \
            .select("*") \
            .eq("type", "onramp") \
            .eq("status", "pending_credit") \
            .lt("retry_count", MAX_RETRIES) \
            .limit(BATCH_LIMIT) \
            .execute()

        rows = result.data or []
        if not rows:
            return

        logger.info("💳 WapiPay credit worker: %s pending credit(s)", len(rows))
        for row in rows:
            await self._credit_one(row)

    async def _credit_one(self, row: dict):
        tx_id   = row["id"]
        user_id = row.get("user_id")
        amount  = Decimal(str(row.get("amount", 0)))

        if not user_id:
            logger.warning("⚠️ WapiPay tx %s has no matched user_id — cannot credit. Flagging.", tx_id)
            await self._mark_failed(tx_id, row.get("retry_count", 0), "No user_id matched to virtual account")
            return

        # 🚨 Atomic claim — prevents double-credit if multiple instances run
        claimed = self.db.supabase.from_("wapipay_transactions") \
            .update({"status": "crediting", "updated_at": datetime.now().isoformat()}) \
            .eq("id", tx_id) \
            .eq("status", "pending_credit") \
            .execute()

        if not claimed.data:
            logger.info("⚠️ WapiPay tx %s already claimed by another worker — skipping", tx_id)
            return

        try:
            usdt_amount = await self._convert_ngn_to_usdt(amount)

            # Credit ledger balance (same pattern as Paystack/Flutterwave onramp)
            bal = self.db.supabase.from_("wallet_balances") \
                .select("usdt_balance").eq("user_id", user_id).limit(1).execute()

            current = Decimal(str(bal.data[0].get("usdt_balance", 0))) if bal.data else Decimal("0")
            new_balance = current + usdt_amount

            self.db.supabase.from_("wallet_balances") \
                .update({"usdt_balance": float(new_balance), "updated_at": "NOW()"}) \
                .eq("user_id", user_id).execute()

            self.db.supabase.from_("wapipay_transactions") \
                .update({
                    "status":          "completed",
                    "credited_amount": float(usdt_amount),
                    "credited_asset":  "USDT",
                    "updated_at":      datetime.now().isoformat(),
                }) \
                .eq("id", tx_id).execute()

            logger.info(
                "✅ WapiPay credit complete: tx=%s user=%s %s NGN → %s USDT",
                tx_id, str(user_id)[:8], amount, usdt_amount
            )

        except Exception as e:
            retry_count = row.get("retry_count", 0) + 1
            logger.error("❌ WapiPay credit failed (attempt %s/%s) tx=%s: %s", retry_count, MAX_RETRIES, tx_id, e)

            if retry_count >= MAX_RETRIES:
                await self._mark_failed(tx_id, retry_count, str(e))
            else:
                # Revert to pending_credit so next poll retries
                self.db.supabase.from_("wapipay_transactions") \
                    .update({
                        "status":      "pending_credit",
                        "retry_count": retry_count,
                        "last_error":  str(e),
                        "updated_at":  datetime.now().isoformat(),
                    }) \
                    .eq("id", tx_id).execute()

    async def _mark_failed(self, tx_id: str, retry_count: int, error: str):
        self.db.supabase.from_("wapipay_transactions") \
            .update({
                "status":      "credit_failed",
                "retry_count": retry_count,
                "last_error":  error,
                "updated_at":  datetime.now().isoformat(),
            }) \
            .eq("id", tx_id).execute()
        logger.critical("🚨 WapiPay tx %s marked credit_failed after %s attempts — MANUAL REVIEW NEEDED: %s",
                         tx_id, retry_count, error)

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _convert_ngn_to_usdt(self, ngn_amount: Decimal) -> Decimal:
        """NGN → USD (forex) → USDT (1:1 with USD), fee deducted."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.exchangerate-api.com/v4/latest/USD",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Forex API returned {resp.status}")
                data = await resp.json()
                ngn_per_usd = Decimal(str(data["rates"]["NGN"]))

        gross_usd = ngn_amount / ngn_per_usd
        fee       = gross_usd * WAPIPAY_ONRAMP_FEE_RATE
        net_usd   = gross_usd - fee
        return net_usd.quantize(Decimal("0.000001"))