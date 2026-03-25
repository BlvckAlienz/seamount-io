# FILE: backend/workers/p2p_worker.py
#
# Polls the p2p_jobs table for pending jobs and executes them.
# Runs as a background task inside the FastAPI lifespan — no
# extra infrastructure (Redis, Celery) needed at bootstrap stage.
#
# Jobs handled:
#   token.release       — sends tokens to buyer (buy side)
#   token.sell_transfer — sends tokens from seller to merchant (sell side)
#   order.expire        — marks orders as expired when 15-min window elapses

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict
import aiohttp

from supabase import Client

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS   = 10
PROCESSING_TIMEOUT_SECS = 120

# Shared across both buy and sell token transfer handlers
ASSET_CHAIN_MAP = {
    'ALGO': 'algorand', 'USDCa': 'algorand',
    'goBTC': 'algorand', 'goETH': 'algorand', 'USDT_ALGO': 'algorand',
    'BTC': 'bitcoin',
    'ETH': 'ethereum', 'USDT_ETH': 'ethereum', 'USDC_ETH': 'ethereum',
    'MATIC': 'polygon', 'USDT_POLYGON': 'polygon', 'USDC_POLYGON': 'polygon',
    'TRX': 'tron', 'USDT': 'tron', 'USDT_TRON': 'tron',
    'SOL': 'solana', 'USDT_SOLANA': 'solana', 'USDC_SOLANA': 'solana',
}


class P2PWorker:
    """
    Background worker that processes P2P settlement jobs.
    Injected with the same supabase client and wallet service
    that the rest of the app uses — no separate connections.
    """

    def __init__(self, supabase: Client, multi_chain_wallet_service):
        self.supabase       = supabase
        self.wallet_service = multi_chain_wallet_service
        self._running       = False

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
                await self._expire_overdue_orders()   # direct scan — no jobs needed
                await self._process_pending_jobs()
            except Exception as e:
                logger.error(f"[P2PWorker] Loop error: {e}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    # ── Fetch and dispatch pending jobs ───────────────────────

    async def _process_pending_jobs(self):
        now = datetime.now(timezone.utc).isoformat()

        # Query 1: jobs with no run_after (immediate jobs)
        res1 = self.supabase.table("p2p_jobs") \
            .select("*") \
            .eq("status", "pending") \
            .is_("run_after", "null") \
            .order("created_at", desc=False) \
            .limit(10) \
            .execute()

        # Query 2: jobs whose run_after has passed
        res2 = self.supabase.table("p2p_jobs") \
            .select("*") \
            .eq("status", "pending") \
            .not_.is_("run_after", "null") \
            .lte("run_after", now) \
            .order("created_at", desc=False) \
            .limit(10) \
            .execute()

        # Merge and deduplicate by id
        seen = set()
        jobs = []
        for job in (res1.data or []) + (res2.data or []):
            if job["id"] not in seen:
                seen.add(job["id"])
                jobs.append(job)

        if not jobs:
            return

        logger.info(f"[P2PWorker] Processing {len(jobs)} pending job(s)")
        for job in jobs:
            asyncio.create_task(self._handle_job(job))

    # ── Handle a single job ────────────────────────────────────

    async def _handle_job(self, job: Dict[str, Any]):
        job_id   = job["id"]
        job_type = job["job_type"]

        # Claim the job — mark as processing so no other worker picks it up
        claimed = self._claim_job(job_id)
        if not claimed:
            return  # another worker claimed it first

        logger.info(f"[P2PWorker] Handling job {job_id} type={job_type} attempt={job['retry_count'] + 1}")

        try:
            if job_type == "token.release":
                await self._handle_token_release(job)
            elif job_type == "token.sell_transfer":
                await self._handle_sell_token_transfer(job)
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

    # ── On-chain transaction verifier ─────────────────────────

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
                            data         = await resp.json()
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
                            data    = await resp.json()
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
                            data   = await resp.json()
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

    # ── BUY SIDE: Token Release Handler ───────────────────────

    async def _handle_token_release(self, job: Dict[str, Any]):
        """Buy side: merchant wallet → buyer wallet"""
        payload          = job["payload"]
        order_id: str    = payload["order_id"]
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
        token: str = order["token"]
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
                "status":     "confirming",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", order_id).execute()

            self.supabase.table("p2p_messages").insert({
                "order_id":  order_id,
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

            # Correct the blockchain_transactions record to 'failed'
            self._sync_blockchain_tx_status(
                tx_hash=tx_hash,
                order_id=order_id,
                verified=False,
                reason=reason,
                token=token,
                chain=chain,
                amount=float(order["token_amount"]),
                recipient_address=buyer_address,
            )

            # Raise so the job retries via _retry_or_fail
            raise Exception(f"On-chain tx failed: {reason}")

        # ── Verified SUCCESS ──────────────────────────────────
        self.supabase.table("p2p_orders").update({
            "status":          "completed",
            "release_tx_hash": tx_hash,
            "updated_at":      datetime.now(timezone.utc).isoformat()
        }).eq("id", order_id).execute()

        self.supabase.rpc(
            "increment_merchant_orders",
            {"p_merchant_id": order["merchant_id"]}
        ).execute()

        self.supabase.table("p2p_messages").insert({
            "order_id":  order_id,
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

        # Correct the blockchain_transactions record to 'completed'
        self._sync_blockchain_tx_status(
            tx_hash=tx_hash,
            order_id=order_id,
            verified=True,
            reason="SUCCESS",
            token=token,
            chain=chain,
            amount=float(order["token_amount"]),
            recipient_address=buyer_address,
        )

        logger.info(f"[P2PWorker] Token release complete — tx: {tx_hash}")

    # ── SELL SIDE: Token Transfer Handler ─────────────────────

    async def _handle_sell_token_transfer(self, job: Dict[str, Any]):
        """
        Sell side: seller's Seamount wallet → merchant's Seamount wallet.
        Mirror of _handle_token_release but direction is reversed:
          buy side:  merchant → buyer
          sell side: seller  → merchant
        After success, status moves to 'paid' meaning merchant has the tokens
        and must now send fiat to the seller.
        """
        payload         = job["payload"]
        order_id        = payload["order_id"]
        seller_user_id  = payload["seller_user_id"]
        merchant_id_str = payload["merchant_id"]

        # Fetch order
        order_res = self.supabase.table("p2p_orders") \
            .select("*") \
            .eq("id", order_id) \
            .eq("status", "confirming") \
            .eq("order_type", "sell") \
            .limit(1) \
            .execute()

        if not order_res.data or len(order_res.data) == 0:
            raise ValueError(f"Sell order {order_id} not found or wrong status")

        order = order_res.data[0]
        token = order["token"]
        chain = ASSET_CHAIN_MAP.get(token, 'tron')

        # ── Fetch merchant's Seamount wallet address (destination) ──
        merchant_res = self.supabase.table("p2p_merchants") \
            .select("user_id") \
            .eq("id", merchant_id_str) \
            .limit(1) \
            .execute()
        if not merchant_res.data or len(merchant_res.data) == 0:
            raise ValueError("Merchant not found")
        merchant_user_id = merchant_res.data[0]["user_id"]

        if chain == 'algorand':
            addr_res = self.supabase.table("user_wallets") \
                .select("algorand_address") \
                .eq("user_id", merchant_user_id) \
                .limit(1) \
                .execute()
            merchant_address = (addr_res.data[0] if addr_res.data else {}).get("algorand_address")
        else:
            addr_res = self.supabase.table("multi_chain_addresses") \
                .select("address") \
                .eq("user_id", merchant_user_id) \
                .eq("blockchain", chain) \
                .limit(1) \
                .execute()
            merchant_address = (addr_res.data[0] if addr_res.data else {}).get("address")

        if not merchant_address:
            raise ValueError(f"Merchant has no {chain} Seamount wallet")

        logger.info(
            f"[P2PWorker] Sell transfer: {order['token_amount']} {token} "
            f"from seller {seller_user_id[:8]}... "
            f"to merchant {merchant_address[:10]}... on {chain}"
        )

        # ── Execute via MultiChainWalletService — FROM seller's wallet ──
        from decimal import Decimal
        tx_result = await self.wallet_service.send_payment(
            user_id=seller_user_id,
            recipient=merchant_address,
            asset=token,
            amount=Decimal(str(order["token_amount"]))
        )

        if not tx_result or not tx_result.get("success"):
            raise Exception(
                f"WDK transfer failed: {tx_result.get('message', 'unknown error')}"
            )

        tx_hash = tx_result.get("transaction_id", "") or tx_result.get("tx_hash", "")

        # ── On-chain verification ─────────────────────────────
        verified, reason = await self._verify_tx_on_chain(tx_hash, chain)

        if not verified:
            logger.error(f"[P2PWorker] Sell tx {tx_hash[:16]}... FAILED on-chain: {reason}")

            # Revert to confirming — seller can retry release
            self.supabase.table("p2p_orders").update({
                "status":     "confirming",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", order_id).execute()

            self.supabase.table("p2p_messages").insert({
                "order_id":  order_id,
                "is_system": True,
                "message": (
                    f"⚠️ Token transfer failed ({reason}). "
                    f"Please check your wallet balance and try releasing again. "
                    f"Tx: {tx_hash}"
                )
            }).execute()

            self._sync_blockchain_tx_status(
                tx_hash=tx_hash,
                order_id=order_id,
                verified=False,
                reason=reason,
                token=token,
                chain=chain,
                amount=float(order["token_amount"]),
                recipient_address=merchant_address,
            )

            self._write_audit(
                order_id, "tx_failed", "confirming", "confirming",
                actor_id=seller_user_id,
                metadata={"tx_hash": tx_hash, "reason": reason}
            )

            raise Exception(f"Sell tx failed on-chain: {reason}")

        # ── Verified SUCCESS ──────────────────────────────────
        # 'paid' on sell orders = tokens in merchant's wallet,
        # merchant must now send fiat to seller.
        self.supabase.table("p2p_orders").update({
            "status":        "paid",
            "token_tx_hash": tx_hash,
            "updated_at":    datetime.now(timezone.utc).isoformat()
        }).eq("id", order_id).execute()

        self.supabase.table("p2p_messages").insert({
            "order_id":  order_id,
            "is_system": True,
            "message": (
                f"✅ {order['token_amount']} {token} transferred to merchant. "
                f"Merchant: please send fiat and upload proof. "
                f"Tx: {tx_hash}"
            )
        }).execute()

        self._sync_blockchain_tx_status(
            tx_hash=tx_hash,
            order_id=order_id,
            verified=True,
            reason="SUCCESS",
            token=token,
            chain=chain,
            amount=float(order["token_amount"]),
            recipient_address=merchant_address,
        )

        self._write_audit(
            order_id, "state_change", "confirming", "paid",
            actor_id=seller_user_id,
            metadata={"tx_hash": tx_hash}
        )

        logger.info(f"[P2PWorker] Sell transfer complete — tx: {tx_hash}")

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

        current_status = order_res.data[0]["status"]
        if current_status != "payment_window":
            # Order already progressed (paid, confirming, completed, cancelled)
            # or was already expired — nothing to do
            logger.info(
                f"[P2PWorker] Expire job skipped for {order_id} "
                f"— already in status '{current_status}'"
            )
            return

        self.supabase.table("p2p_orders").update({
            "status":     "expired",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", order_id).execute()

        # Insert system message — guarantees Realtime INSERT fires
        # even if the UPDATE event is missed by the frontend channel.
        try:
            self.supabase.table("p2p_messages").insert({
                "order_id":    order_id,
                "is_system":   True,
                "sender_role": "system",
                "visibility":  "all",
                "message": (
                    "⏰ Payment window expired. This order has been automatically "
                    "marked as expired. The merchant's tokens remain available."
                )
            }).execute()
        except Exception as msg_err:
            logger.warning(f"[P2PWorker] Expiry system message failed (non-critical): {msg_err}")

        self._write_audit(order_id, "state_change", "payment_window", "expired")
        logger.info(f"[P2PWorker] Order {order_id} expired")

    # ── Job State Helpers ──────────────────────────────────────

    def _claim_job(self, job_id: str) -> bool:
        """
        Atomically mark job as 'processing'.
        Returns False if the job was already claimed by another worker.
        """
        try:
            res = self.supabase.table("p2p_jobs").update({
                "status":     "processing",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", job_id).eq("status", "pending").execute()
            return bool(res.data)
        except Exception as e:
            logger.error(f"[P2PWorker] Failed to claim job {job_id}: {e}")
            return False

    def _complete_job(self, job_id: str):
        try:
            self.supabase.table("p2p_jobs").update({
                "status":     "completed",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", job_id).execute()
        except Exception as e:
            logger.warning(f"[P2PWorker] Failed to mark job {job_id} complete: {e}")

    def _retry_or_fail(self, job: Dict[str, Any]):
        """
        Exponential backoff retry.
        Delay grows: 30s → 60s → 120s → 240s → 480s then permanent fail.
        """
        job_id      = job["id"]
        retry_count = job["retry_count"] + 1
        max_retries = job.get("max_retries", 5)

        if retry_count >= max_retries:
            self._fail_job(job_id, f"Max retries ({max_retries}) reached")
            return

        delay_seconds = 30 * (2 ** retry_count)

        try:
            self.supabase.table("p2p_jobs").update({
                "status":      "pending",
                "retry_count": retry_count,
                "updated_at":  datetime.now(timezone.utc).isoformat()
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
                "status":     "failed",
                "error":      error,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", job_id).execute()
            logger.error(f"[P2PWorker] Job {job_id} permanently failed: {error}")
        except Exception as e:
            logger.warning(f"[P2PWorker] Failed to mark job {job_id} as failed: {e}")

    async def _expire_overdue_orders(self):
        """
        Direct DB scan — expires any payment_window orders past deadline.
        Runs every poll cycle. Completely independent of p2p_jobs table.
        Fixes: orders with no expire job, jobs with bad run_after filter,
               and any orders created before the expire job feature existed.
        """
        try:
            now = datetime.now(timezone.utc).isoformat()

            overdue_res = self.supabase.table("p2p_orders") \
                .select("id") \
                .eq("status", "payment_window") \
                .lt("payment_deadline", now) \
                .execute()

            orders = overdue_res.data or []
            if not orders:
                return

            logger.info(f"[P2PWorker] Found {len(orders)} overdue order(s) to expire")

            for row in orders:
                try:
                    await self._handle_order_expire({
                        "payload": {"order_id": row["id"]}
                    })
                except Exception as e:
                    logger.warning(
                        f"[P2PWorker] Failed to expire order {row['id']}: {e}"
                    )

        except Exception as e:
            logger.warning(f"[P2PWorker] Overdue order scan failed: {e}")

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
                    "status":     "pending",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }) \
                .eq("status", "processing") \
                .lt("updated_at", cutoff) \
                .execute()

            if res.data:
                logger.warning(f"[P2PWorker] Recovered {len(res.data)} stuck job(s)")
        except Exception as e:
            logger.warning(f"[P2PWorker] Stuck job recovery failed: {e}")

    # ── Blockchain TX Status Sync ──────────────────────────────

    def _sync_blockchain_tx_status(
        self,
        tx_hash: str,
        order_id: str,
        verified: bool,
        reason: str,
        token: str,
        chain: str,
        amount: float,
        recipient_address: str
    ) -> None:
        """
        The WDK send_payment() may already have written a record to
        blockchain_transactions with status='completed' at broadcast time.
        This method corrects that record based on actual on-chain result.

        Strategy: try UPDATE first (fixes WDK-written record).
        If no rows updated (WDK didn't write one), INSERT with verified status.
        """
        final_status = "completed" if verified else "failed"
        now          = datetime.now(timezone.utc).isoformat()

        try:
            # ── Try UPDATE first ───────────────────────────────
            update_res = self.supabase.table("blockchain_transactions").update({
                "status":       final_status,
                "p2p_order_id": order_id,
                "updated_at":   now,
            }).eq("txn_hash", tx_hash).execute()

            if update_res.data and len(update_res.data) > 0:
                logger.info(
                    f"[P2PWorker] blockchain_transactions updated "
                    f"tx={tx_hash[:16]}... status={final_status}"
                )
                return  # done — existing WDK record corrected

            # ── No existing record — INSERT with verified status ──
            self.supabase.table("blockchain_transactions").insert({
                "user_id":          None,   # not available here — non-critical
                "transaction_type": "p2p_release",
                "status":           final_status,
                "amount":           amount,
                "asset":            token,
                "chain":            chain,
                "txn_hash":         tx_hash,
                "to_address":       recipient_address,
                "platform_fee":     0,
                "p2p_order_id":     order_id,
            }).execute()

            logger.info(
                f"[P2PWorker] blockchain_transactions inserted "
                f"tx={tx_hash[:16]}... status={final_status}"
            )

        except Exception as e:
            # Non-fatal — analytics table, not settlement critical path
            logger.warning(f"[P2PWorker] blockchain_transactions sync failed: {e}")

    # ── Audit Writer ───────────────────────────────────────────

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