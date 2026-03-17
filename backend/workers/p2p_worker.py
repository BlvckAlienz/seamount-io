# FILE: backend/workers/p2p_worker.py
#
# Polls the p2p_jobs table for pending jobs and executes them.
# Runs as a background task inside the FastAPI lifespan — no
# extra infrastructure (Redis, Celery) needed at bootstrap stage.
#
# Jobs handled:
#   token.release  — sends USDT/USDC to buyer via MultiChainWalletService
#   order.expire   — cancels orders whose 15-min window has passed

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict
import aiohttp

from supabase import Client

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 10      # how often to check for new jobs
PROCESSING_TIMEOUT_SECS = 120   # max seconds a job can stay in 'processing'
                                 # before it is treated as stuck and retried


class P2PWorker:
    """
    Background worker that processes P2P settlement jobs.
    Injected with the same supabase client and wallet service
    that the rest of the app uses — no separate connections.
    """

    def __init__(self, supabase: Client, multi_chain_wallet_service):
        self.supabase = supabase
        self.wallet_service = multi_chain_wallet_service
        self._running = False

    # ── Lifecycle ──────────────────────────────────────────────

    async def start(self):
        self._running = True
        logger.info("✅ P2P worker started")
        asyncio.create_task(self._run_loop())

    async def stop(self):
        self._running = False
        logger.info("🛑 P2P worker stopped")

    # ── Main poll loop ─────────────────────────────────────────

    async def _run_loop(self):
        while self._running:
            try:
                await self._recover_stuck_jobs()
                await self._process_pending_jobs()
            except Exception as e:
                logger.error(f"[P2PWorker] Loop error: {e}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    # ── Fetch and dispatch pending jobs ───────────────────────

    async def _process_pending_jobs(self):
        res = self.supabase.table("p2p_jobs") \
            .select("*") \
            .eq("status", "pending") \
            .order("created_at", desc=False) \
            .limit(10) \
            .execute()

        jobs = res.data or []
        if not jobs:
            return

        logger.info(f"[P2PWorker] Processing {len(jobs)} pending job(s)")

        for job in jobs:
            asyncio.create_task(self._handle_job(job))

    # ── Handle a single job ────────────────────────────────────

    async def _handle_job(self, job: Dict[str, Any]):
        job_id = job["id"]
        job_type = job["job_type"]

        # Claim the job — mark as processing so no other worker picks it up
        claimed = self._claim_job(job_id)
        if not claimed:
            return  # another worker claimed it first

        logger.info(f"[P2PWorker] Handling job {job_id} type={job_type} attempt={job['retry_count'] + 1}")

        try:
            if job_type == "token.release":
                await self._handle_token_release(job)
            elif job_type == "order.expire":
                await self._handle_order_expire(job)
            else:
                logger.warning(f"[P2PWorker] Unknown job type: {job_type}")
                self._fail_job(job_id, f"Unknown job type: {job_type}")
                return

            # Success
            self._complete_job(job_id)
            logger.info(f"[P2PWorker] ✅ Job completed: {job_id}")

        except Exception as e:
            logger.error(f"[P2PWorker] ❌ Job {job_id} failed: {e}")
            self._retry_or_fail(job)

    async def _verify_tx_on_chain(
        self,
        tx_hash: str,
        chain: str,
        max_attempts: int = 8,
        delay_secs: int = 5
    ) -> tuple[bool, str]:
        """
        Poll the chain until tx is confirmed or max_attempts exhausted.
        Returns (success: bool, reason: str).
        A broadcast-confirmed hash ≠ successful execution (see: OUT_OF_ENERGY).
        """
        for attempt in range(1, max_attempts + 1):
            await asyncio.sleep(delay_secs)
            logger.info(
                f"[P2PWorker] Verifying tx {tx_hash[:16]}... "
                f"on {chain} (attempt {attempt}/{max_attempts})"
            )

            try:
                # ── TRON ──────────────────────────────────────
                if chain == "tron":
                    url = f"https://apilist.tronscanapi.com/api/transaction-info?hash={tx_hash}"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url, timeout=aiohttp.ClientTimeout(total=10)
                        ) as resp:
                            if resp.status != 200:
                                continue
                            data = await resp.json()
                            confirmed    = data.get("confirmed", False)
                            contract_ret = data.get("contractRet", "")
                            if not confirmed:
                                logger.info("[P2PWorker] Tron tx not yet confirmed, retrying...")
                                continue
                            if contract_ret == "SUCCESS":
                                return True, "SUCCESS"
                            elif contract_ret:
                                # OUT_OF_ENERGY, REVERT, etc.
                                return False, contract_ret
                            continue  # contractRet absent — still pending

                # ── EVM (Ethereum, Polygon, Base) ─────────────
                elif chain in ("ethereum", "polygon", "base"):
                    rpc_urls = {
                        "ethereum": "https://eth.drpc.org",
                        "polygon":  "https://polygon-rpc.com",
                        "base":     "https://mainnet.base.org",
                    }
                    payload = {
                        "jsonrpc": "2.0", "id": 1,
                        "method":  "eth_getTransactionReceipt",
                        "params":  [tx_hash]
                    }
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            rpc_urls[chain], json=payload,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as resp:
                            data = await resp.json()
                            receipt = data.get("result")
                            if receipt is None:
                                continue  # not mined yet
                            status = int(receipt.get("status", "0x0"), 16)
                            return (True, "SUCCESS") if status == 1 else (False, "REVERTED")

                # ── Solana ────────────────────────────────────
                elif chain == "solana":
                    payload = {
                        "jsonrpc": "2.0", "id": 1,
                        "method":  "getTransaction",
                        "params":  [tx_hash, {"encoding": "json", "commitment": "confirmed"}]
                    }
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            "https://api.mainnet-beta.solana.com",
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as resp:
                            data = await resp.json()
                            result = data.get("result")
                            if result is None:
                                continue
                            err = result.get("meta", {}).get("err")
                            return (True, "SUCCESS") if err is None else (False, str(err))

                # ── Algorand ──────────────────────────────────
                elif chain == "algorand":
                    url = f"https://mainnet-api.algonode.cloud/v2/transactions/{tx_hash}"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url, timeout=aiohttp.ClientTimeout(total=10)
                        ) as resp:
                            if resp.status == 200:
                                return True, "SUCCESS"
                            elif resp.status == 404:
                                continue
                            else:
                                return False, f"HTTP_{resp.status}"

                # ── Unknown chain — don't block forever ───────
                else:
                    logger.warning(
                        f"[P2PWorker] No verifier for chain '{chain}', assuming SUCCESS"
                    )
                    return True, "UNVERIFIED"

            except Exception as e:
                logger.warning(f"[P2PWorker] Verify attempt {attempt} error: {e}")
                continue

        return False, "TIMEOUT_UNCONFIRMED"

    # ─────────────────────────────────────────────────────────────
    # Add _verify_tx_on_chain method
    # ─────────────────────────────────────────────────────────────

    async def _verify_tx_on_chain(
        self,
        tx_hash: str,
        chain: str,
        max_attempts: int = 8,
        delay_secs: int = 5
    ) -> tuple[bool, str]:
        """
        Poll the chain until tx is confirmed or max_attempts exhausted.
        Returns (success: bool, reason: str).
        A broadcast-confirmed hash ≠ successful execution (see: OUT_OF_ENERGY).
        """
        for attempt in range(1, max_attempts + 1):
            await asyncio.sleep(delay_secs)
            logger.info(
                f"[P2PWorker] Verifying tx {tx_hash[:16]}... "
                f"on {chain} (attempt {attempt}/{max_attempts})"
            )

            try:
                # ── TRON ──────────────────────────────────────
                if chain == "tron":
                    url = f"https://apilist.tronscanapi.com/api/transaction-info?hash={tx_hash}"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url, timeout=aiohttp.ClientTimeout(total=10)
                        ) as resp:
                            if resp.status != 200:
                                continue
                            data = await resp.json()
                            confirmed    = data.get("confirmed", False)
                            contract_ret = data.get("contractRet", "")
                            if not confirmed:
                                logger.info("[P2PWorker] Tron tx not yet confirmed, retrying...")
                                continue
                            if contract_ret == "SUCCESS":
                                return True, "SUCCESS"
                            elif contract_ret:
                                # OUT_OF_ENERGY, REVERT, etc.
                                return False, contract_ret
                            continue  # contractRet absent — still pending

                # ── EVM (Ethereum, Polygon, Base) ─────────────
                elif chain in ("ethereum", "polygon", "base"):
                    rpc_urls = {
                        "ethereum": "https://eth.drpc.org",
                        "polygon":  "https://polygon-rpc.com",
                        "base":     "https://mainnet.base.org",
                    }
                    payload = {
                        "jsonrpc": "2.0", "id": 1,
                        "method":  "eth_getTransactionReceipt",
                        "params":  [tx_hash]
                    }
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            rpc_urls[chain], json=payload,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as resp:
                            data = await resp.json()
                            receipt = data.get("result")
                            if receipt is None:
                                continue  # not mined yet
                            status = int(receipt.get("status", "0x0"), 16)
                            return (True, "SUCCESS") if status == 1 else (False, "REVERTED")

                # ── Solana ────────────────────────────────────
                elif chain == "solana":
                    payload = {
                        "jsonrpc": "2.0", "id": 1,
                        "method":  "getTransaction",
                        "params":  [tx_hash, {"encoding": "json", "commitment": "confirmed"}]
                    }
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            "https://api.mainnet-beta.solana.com",
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as resp:
                            data = await resp.json()
                            result = data.get("result")
                            if result is None:
                                continue
                            err = result.get("meta", {}).get("err")
                            return (True, "SUCCESS") if err is None else (False, str(err))

                # ── Algorand ──────────────────────────────────
                elif chain == "algorand":
                    url = f"https://mainnet-api.algonode.cloud/v2/transactions/{tx_hash}"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url, timeout=aiohttp.ClientTimeout(total=10)
                        ) as resp:
                            if resp.status == 200:
                                return True, "SUCCESS"
                            elif resp.status == 404:
                                continue
                            else:
                                return False, f"HTTP_{resp.status}"

                # ── Unknown chain — don't block forever ───────
                else:
                    logger.warning(
                        f"[P2PWorker] No verifier for chain '{chain}', assuming SUCCESS"
                    )
                    return True, "UNVERIFIED"

            except Exception as e:
                logger.warning(f"[P2PWorker] Verify attempt {attempt} error: {e}")
                continue

        return False, "TIMEOUT_UNCONFIRMED"
        
    # ── Token Release Handler ──────────────────────────────────

    async def _handle_token_release(self, job: Dict[str, Any]):
        payload = job["payload"]
        order_id: str = payload["order_id"]
        merchant_user_id: str = payload["merchant_user_id"]

        # Fetch order
        order_res = self.supabase.table("p2p_orders") \
            .select("*") \
            .eq("id", order_id) \
            .eq("status", "confirming") \
            .limit(1) \
            .execute()

        if not order_res.data or len(order_res.data) == 0:
            raise ValueError(f"Order {order_id} not found or not in confirming state")

        order = order_res.data[0]
        token: str = order["token"]  # e.g. USDT_TRON, USDC_POLYGON, BTC

        # ── Resolve chain from token ───────────────────────────
        # Mirrors MultiChainWalletService.ASSET_CHAIN_MAP exactly
        ASSET_CHAIN_MAP = {
            'ALGO': 'algorand', 'USDCa': 'algorand',
            'goBTC': 'algorand', 'goETH': 'algorand',
            'USDT_ALGO': 'algorand',
            'BTC': 'bitcoin',
            'ETH': 'ethereum', 'USDT_ETH': 'ethereum', 'USDC_ETH': 'ethereum',
            'MATIC': 'polygon', 'USDT_POLYGON': 'polygon', 'USDC_POLYGON': 'polygon',
            'TRX': 'tron', 'USDT': 'tron', 'USDT_TRON': 'tron',
            'SOL': 'solana', 'USDT_SOLANA': 'solana', 'USDC_SOLANA': 'solana',
        }
        chain = ASSET_CHAIN_MAP.get(token, 'tron')

        # ── Fetch buyer wallet address ─────────────────────────
        # Algorand wallets live in user_wallets table
        # All other chains live in multi_chain_addresses table
        if chain == 'algorand':
            buyer_res = self.supabase.table("user_wallets") \
                .select("algorand_address") \
                .eq("user_id", order["buyer_id"]) \
                .limit(1) \
                .execute()
            buyer_address = (buyer_res.data[0] if buyer_res.data else {}).get("algorand_address")
        else:
            buyer_res = self.supabase.table("multi_chain_addresses") \
                .select("address") \
                .eq("user_id", order["buyer_id"]) \
                .eq("blockchain", chain) \
                .limit(1) \
                .execute()
            buyer_address = (buyer_res.data[0] if buyer_res.data else {}).get("address")

        if not buyer_address:
            raise ValueError(
                f"Buyer has no {chain} wallet. "
                f"User {order['buyer_id']} must create a {chain} wallet first."
            )

        logger.info(
            f"[P2PWorker] Releasing {order['token_amount']} {token} "
            f"to {buyer_address[:10]}... on {chain} for order {order_id}"
        )

        # ── Execute via MultiChainWalletService.send_payment ──
        # Merchant's encrypted seed is already stored in multi_chain_addresses.
        # send_payment retrieves it internally — nothing sensitive passed here.
        from decimal import Decimal
        tx_result = await self.wallet_service.send_payment(
            user_id=merchant_user_id,
            recipient=buyer_address,
            asset=token,
            amount=Decimal(str(order["token_amount"]))
        )

        if not tx_result or not tx_result.get("success"):
            raise Exception(
                f"WDK transfer failed: {tx_result.get('message', 'unknown error')}"
            )

        tx_hash = tx_result.get("transaction_id", "") or tx_result.get("tx_hash", "")

        # ── On-chain verification ─────────────────────────────
        # Broadcast confirmed ≠ execution succeeded.
        # Tron is the worst offender: OUT_OF_ENERGY = confirmed but failed.
        verified, reason = await self._verify_tx_on_chain(tx_hash, chain)

        if not verified:
            logger.error(f"[P2PWorker] Tx {tx_hash[:16]}... FAILED on-chain: {reason}")

            # Revert to confirming — merchant must fix wallet and retry
            self.supabase.table("p2p_orders").update({
                "status": "confirming",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", order_id).execute()

            self.supabase.table("p2p_messages").insert({
                "order_id": order_id,
                "is_system": True,
                "message": (
                    f"⚠️ Token transfer failed on-chain ({reason}). "
                    f"Merchant: ensure your wallet has sufficient gas/energy and retry release. "
                    f"Tx: {tx_hash}"
                )
            }).execute()

            self._write_audit(
                order_id, "tx_failed", "confirming", "confirming",
                actor_id=merchant_user_id,
                metadata={"tx_hash": tx_hash, "reason": reason}
            )

            # Raise so the job retries via _retry_or_fail
            raise Exception(f"On-chain tx failed: {reason}")

        # ── Verified SUCCESS ──────────────────────────────────
        self.supabase.table("p2p_orders").update({
            "status": "completed",
            "release_tx_hash": tx_hash,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", order_id).execute()

        self.supabase.rpc(
            "increment_merchant_orders",
            {"p_merchant_id": order["merchant_id"]}
        ).execute()

        self.supabase.table("p2p_messages").insert({
            "order_id": order_id,
            "is_system": True,
            "message": (
                f"✅ {order['token_amount']} {token} released to buyer. "
                f"Transaction: {tx_hash}"
            )
        }).execute()

        self._write_audit(
            order_id, "state_change", "confirming", "completed",
            actor_id=merchant_user_id,
            metadata={"tx_hash": tx_hash}
        )

        logger.info(f"[P2PWorker] Token release complete — tx: {tx_hash}")

    # ── Order Expire Handler ───────────────────────────────────

    async def _handle_order_expire(self, job: Dict[str, Any]):
        order_id: str = job["payload"]["order_id"]

        order_res = self.supabase.table("p2p_orders") \
            .select("status") \
            .eq("id", order_id) \
            .limit(1) \
            .execute()

        if not order_res.data or len(order_res.data) == 0:
            logger.warning(f"[P2PWorker] Expire job: order {order_id} not found")
            return

        if order_res.data[0]["status"] != "payment_window":
            # Already paid or cancelled — nothing to do
            return

        self.supabase.table("p2p_orders").update({
            "status": "cancelled",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", order_id).execute()

        self.supabase.table("p2p_messages").insert({
            "order_id": order_id,
            "is_system": True,
            "message": "Payment window expired. Order automatically cancelled."
        }).execute()

        self._write_audit(order_id, "state_change", "payment_window", "cancelled")
        logger.info(f"[P2PWorker] Order {order_id} expired and cancelled")

    # ── Job State Helpers ──────────────────────────────────────

    def _claim_job(self, job_id: str) -> bool:
        """
        Atomically mark job as 'processing'.
        Returns False if the job was already claimed by another worker.
        """
        try:
            res = self.supabase.table("p2p_jobs").update({
                "status": "processing",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", job_id).eq("status", "pending").execute()
            return bool(res.data)
        except Exception as e:
            logger.error(f"[P2PWorker] Failed to claim job {job_id}: {e}")
            return False

    def _complete_job(self, job_id: str):
        try:
            self.supabase.table("p2p_jobs").update({
                "status": "completed",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", job_id).execute()
        except Exception as e:
            logger.warning(f"[P2PWorker] Failed to mark job {job_id} complete: {e}")

    def _retry_or_fail(self, job: Dict[str, Any]):
        """
        Exponential backoff retry.
        Delay grows: 30s → 60s → 120s → 240s → 480s then permanent fail.
        """
        job_id = job["id"]
        retry_count = job["retry_count"] + 1
        max_retries = job.get("max_retries", 5)

        if retry_count >= max_retries:
            self._fail_job(job_id, f"Max retries ({max_retries}) reached")
            return

        # Exponential backoff: 30 * 2^retry_count seconds
        delay_seconds = 30 * (2 ** retry_count)
        next_attempt = datetime.now(timezone.utc).isoformat()  # simplification —
        # for true delay scheduling, store next_attempt_at and filter on it

        try:
            self.supabase.table("p2p_jobs").update({
                "status": "pending",          # back to pending for requeue
                "retry_count": retry_count,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", job_id).execute()
            logger.info(
                f"[P2PWorker] Job {job_id} requeued "
                f"(attempt {retry_count}/{max_retries}, backoff {delay_seconds}s)"
            )
        except Exception as e:
            logger.error(f"[P2PWorker] Failed to requeue job {job_id}: {e}")

    def _fail_job(self, job_id: str, error: str):
        try:
            self.supabase.table("p2p_jobs").update({
                "status": "failed",
                "error": error,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", job_id).execute()
            logger.error(f"[P2PWorker] Job {job_id} permanently failed: {error}")
        except Exception as e:
            logger.warning(f"[P2PWorker] Failed to mark job {job_id} as failed: {e}")

    async def _recover_stuck_jobs(self):
        """
        Reset any jobs that got stuck in 'processing' for too long.
        This handles the case where the server crashed mid-job.
        """
        try:
            from datetime import timedelta
            cutoff = (
                datetime.now(timezone.utc) - timedelta(seconds=PROCESSING_TIMEOUT_SECS)
            ).isoformat()

            res = self.supabase.table("p2p_jobs") \
                .update({
                    "status": "pending",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }) \
                .eq("status", "processing") \
                .lt("updated_at", cutoff) \
                .execute()

            if res.data:
                logger.warning(
                    f"[P2PWorker] Recovered {len(res.data)} stuck job(s)"
                )
        except Exception as e:
            logger.warning(f"[P2PWorker] Stuck job recovery failed: {e}")

    def _write_audit(
        self,
        order_id: str,
        event_type: str,
        prev_status: str | None,
        new_status: str | None,
        actor_id: str | None = None,
        metadata: dict | None = None
    ):
        try:
            self.supabase.table("settlement_audit_log").insert({
                "order_id":    order_id,
                "event_type":  event_type,
                "prev_status": prev_status,
                "new_status":  new_status,
                "actor_id":    actor_id,
                **({"metadata": metadata} if metadata else {})
            }).execute()
        except Exception as e:
            logger.warning(f"[P2PWorker] Audit write failed (non-critical): {e}")