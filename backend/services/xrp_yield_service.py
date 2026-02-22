# File: backend/services/xrp_yield_service.py
"""
XRP Yield Service — Seamount.io Phase 3 (AMM Yield Farming)

Architecture:
  - Seamount DeFi wallet holds ALL AMM LP tokens on-chain
  - Users hold proportional SHARES of Seamount's LP position (DB only)
  - Yield = (user_share / total_pool_share) * total_fees_earned
  - Distribution: daily cron → credits xrp_internal_balances

Supported pools:
  - RLUSD/XRP  (primary)
  - USDC/XRP   (secondary)

Flow:
  User deposits RLUSD → Seamount DeFi wallet enters AMM
  → LP tokens issued to DeFi wallet
  → User gets proportional share recorded in xrp_amm_positions
  → Daily: fees harvested, split pro-rata, credited to users
  → User withdraws → their share redeemed, RLUSD returned
"""

import asyncio
import logging
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SUPPORTED_POOLS = {
    "RLUSD/XRP": {"token": "RLUSD", "base": "XRP"},
    "USDC/XRP":  {"token": "USDC",  "base": "XRP"},
}

# Minimum deposit per pool (prevent dust positions)
MIN_DEPOSIT = {
    "RLUSD/XRP": Decimal("10.00"),
    "USDC/XRP":  Decimal("10.00"),
}

# XRP ratio for two-asset deposit (1 RLUSD ≈ this much XRP goes in alongside)
# This is approximate — actual ratio comes from pool state at deposit time
# DeFi wallet must hold enough XRP float to match deposits
XRP_RATIO_ESTIMATE = Decimal("0.40")  # ~$0.40 XRP per $1 RLUSD at deposit


class XRPYieldService:
    """
    Manages Seamount's AMM yield farming positions and user share accounting.
    """

    def __init__(self, supabase_client, xrp_defi_service, xrp_payment_service, settings=None):
        self.supabase = supabase_client
        self.defi = xrp_defi_service
        self.payments = xrp_payment_service
        from backend.config import get_settings
        self.settings = settings or get_settings()
        logger.info("✅ XRPYieldService initialized")

    # ─── POOL INFO ────────────────────────────────────────────────────────────

    async def get_pool_stats(self, pool: str = "RLUSD/XRP") -> Dict[str, Any]:
        """
        Return live pool stats from XRPL + Seamount's total position in that pool.
        """
        if pool not in SUPPORTED_POOLS:
            raise ValueError(f"Unsupported pool: {pool}. Choose from {list(SUPPORTED_POOLS)}")

        symbol = SUPPORTED_POOLS[pool]["token"]

        # Get on-chain pool state
        pool_info = await self.defi.get_pool_info(symbol)

        # Get Seamount's total LP position in this pool
        seamount_position = await asyncio.to_thread(
            lambda: self.supabase.table("xrp_amm_positions")
            .select("lp_token_share, token_deposited, xrp_deposited, yield_earned")
            .eq("pool", pool)
            .eq("status", "active")
            .execute()
        )

        total_deposited = sum(
            Decimal(str(r.get("token_deposited", 0)))
            for r in (seamount_position.data or [])
        )
        total_yield = sum(
            Decimal(str(r.get("yield_earned", 0)))
            for r in (seamount_position.data or [])
        )
        active_positions = len(seamount_position.data or [])

        trading_fee_pct = None
        if pool_info:
            fee_raw = pool_info.get("trading_fee", 0)
            trading_fee_pct = float(Decimal(str(fee_raw)) / 100000 * 100)

        return {
            "success": True,
            "pool": pool,
            "on_chain": {
                "available": pool_info is not None,
                "trading_fee_pct": trading_fee_pct,
                "amm_account": pool_info.get("account") if pool_info else None,
            },
            "seamount_position": {
                "active_user_positions": active_positions,
                "total_token_deposited": str(total_deposited),
                "total_yield_distributed": str(total_yield),
            },
            "minimum_deposit": str(MIN_DEPOSIT.get(pool, Decimal("10"))),
            "asset": symbol,
        }

    # ─── DEPOSIT INTO YIELD POOL ──────────────────────────────────────────────

    async def deposit(
        self,
        user_id: str,
        pool: str,
        token_amount: Decimal,
    ) -> Dict[str, Any]:
        """
        User deposits RLUSD or USDC into an AMM yield pool.

        Steps:
        1. Validate user has sufficient internal balance
        2. Debit user's internal balance
        3. Seamount DeFi wallet deposits into on-chain AMM
        4. Record user's LP share in xrp_amm_positions
        5. Log transaction
        """
        if pool not in SUPPORTED_POOLS:
            raise ValueError(f"Unsupported pool: {pool}")

        symbol = SUPPORTED_POOLS[pool]["token"]
        token_amount = token_amount.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)

        if token_amount < MIN_DEPOSIT.get(pool, Decimal("10")):
            raise ValueError(
                f"Minimum deposit for {pool}: {MIN_DEPOSIT[pool]} {symbol}"
            )

        # ── Check user balance ──
        user_balance = await self.payments.get_balance(user_id, symbol)
        if user_balance < token_amount:
            raise ValueError(
                f"Insufficient {symbol} balance. "
                f"Available: {user_balance}, Requested: {token_amount}"
            )

        # ── Get current pool state for XRP ratio ──
        pool_info = await self.defi.get_pool_info(symbol)
        xrp_needed = self._estimate_xrp_needed(token_amount, pool_info)

        # ── Debit user internal balance ──
        await asyncio.to_thread(
            lambda: self.supabase.rpc("update_xrp_balance", {
                "p_user_id": user_id,
                "p_symbol": symbol,
                "p_delta": float(-token_amount),
            }).execute()
        )

        now = datetime.utcnow().isoformat()

        # ── Submit two-asset AMM deposit from DeFi wallet ──
        try:
            deposit_result = await self.defi.deposit_to_pool(
                symbol=symbol,
                token_amount=token_amount,
                xrp_amount=xrp_needed,
            )
            tx_hash = deposit_result.get("tx_hash")

            # ── Calculate share: user's deposit / total pool deposits ──
            # Get total currently in this pool from all users
            existing = await asyncio.to_thread(
                lambda: self.supabase.table("xrp_amm_positions")
                .select("token_deposited")
                .eq("pool", pool)
                .eq("status", "active")
                .execute()
            )
            total_before = sum(
                Decimal(str(r["token_deposited"]))
                for r in (existing.data or [])
            )
            total_after = total_before + token_amount
            user_share = (token_amount / total_after).quantize(
                Decimal("0.000000000001"), rounding=ROUND_DOWN
            )

            # ── Record position ──
            position = await asyncio.to_thread(
                lambda: self.supabase.table("xrp_amm_positions").insert({
                    "user_id": user_id,
                    "pool": pool,
                    "token_deposited": float(token_amount),
                    "xrp_deposited": float(xrp_needed),
                    "lp_token_share": float(user_share),
                    "status": "active",
                    "entry_tx_hash": tx_hash,
                    "yield_earned": 0,
                    "created_at": now,
                    "updated_at": now,
                }).execute()
            )

            position_id = position.data[0]["id"] if position.data else None

            # ── Log transaction ──
            await asyncio.to_thread(
                lambda: self.supabase.table("xrp_transactions").insert({
                    "user_id": user_id,
                    "tx_hash": tx_hash,
                    "tx_type": "amm_deposit",
                    "symbol": symbol,
                    "amount": float(token_amount),
                    "status": "confirmed",
                    "metadata": {
                        "pool": pool,
                        "xrp_paired": str(xrp_needed),
                        "lp_share": str(user_share),
                        "position_id": position_id,
                    },
                    "created_at": now,
                }).execute()
            )

            logger.info(
                f"✅ AMM deposit: {token_amount} {symbol} | pool={pool} | "
                f"share={user_share} | user={user_id[:8]}... | tx={tx_hash}"
            )

            return {
                "success": True,
                "pool": pool,
                "token_deposited": str(token_amount),
                "xrp_paired": str(xrp_needed),
                "lp_share": str(user_share),
                "position_id": position_id,
                "tx_hash": tx_hash,
                "status": "active",
                "message": f"Successfully deposited {token_amount} {symbol} into {pool} pool",
            }

        except Exception as e:
            # Refund user on AMM failure
            logger.error(f"❌ AMM deposit failed — refunding user {user_id[:8]}...: {e}")
            try:
                await asyncio.to_thread(
                    lambda: self.supabase.rpc("update_xrp_balance", {
                        "p_user_id": user_id,
                        "p_symbol": symbol,
                        "p_delta": float(token_amount),
                    }).execute()
                )
            except Exception as refund_err:
                logger.critical(f"🚨 REFUND FAILED: user={user_id} amount={token_amount} {symbol}: {refund_err}")
            raise RuntimeError(f"AMM deposit failed: {e}")

    # ─── WITHDRAW FROM YIELD POOL ─────────────────────────────────────────────

    async def withdraw(
        self,
        user_id: str,
        position_id: str,
    ) -> Dict[str, Any]:
        """
        Withdraw a user's full AMM position.
        Redeems LP tokens from DeFi wallet, credits RLUSD back to user.
        """
        # ── Fetch position ──
        pos_result = await asyncio.to_thread(
            lambda: self.supabase.table("xrp_amm_positions")
            .select("*")
            .eq("id", position_id)
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        )

        if not pos_result.data:
            raise ValueError("Position not found or already withdrawn")

        position = pos_result.data[0]
        pool = position["pool"]
        symbol = SUPPORTED_POOLS[pool]["token"]
        lp_share = Decimal(str(position["lp_token_share"]))
        deposited = Decimal(str(position["token_deposited"]))
        yield_earned = Decimal(str(position.get("yield_earned", 0)))

        # ── Get DeFi wallet LP token balance for this pool ──
        pool_info = await self.defi.get_pool_info(symbol)
        if not pool_info:
            raise RuntimeError(f"Cannot reach {pool} pool on XRPL")

        # ── Calculate LP tokens to redeem (user's share of total) ──
        # Get total LP share across all active positions for this pool
        all_positions = await asyncio.to_thread(
            lambda: self.supabase.table("xrp_amm_positions")
            .select("lp_token_share")
            .eq("pool", pool)
            .eq("status", "active")
            .execute()
        )
        total_share = sum(
            Decimal(str(r["lp_token_share"]))
            for r in (all_positions.data or [])
        )

        # Get DeFi wallet LP token balance from pool
        lp_token_info = pool_info.get("lp_token", {})
        defi_lp_balance = Decimal(str(lp_token_info.get("value", "0")))

        # This user's LP tokens = their share * total LP tokens held by DeFi wallet
        user_lp_tokens = (
            (lp_share / total_share * defi_lp_balance)
            if total_share > 0
            else Decimal("0")
        ).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)

        now = datetime.utcnow().isoformat()

        # ── Redeem LP tokens from AMM ──
        try:
            withdraw_result = await self.defi.withdraw_from_pool(
                symbol=symbol,
                lp_token_amount=str(user_lp_tokens),
            )
            tx_hash = withdraw_result.get("tx_hash")

            # ── Credit user: principal + any accrued yield ──
            total_return = deposited + yield_earned
            await asyncio.to_thread(
                lambda: self.supabase.rpc("update_xrp_balance", {
                    "p_user_id": user_id,
                    "p_symbol": symbol,
                    "p_delta": float(total_return),
                }).execute()
            )

            # ── Mark position as withdrawn ──
            await asyncio.to_thread(
                lambda: self.supabase.table("xrp_amm_positions")
                .update({
                    "status": "withdrawn",
                    "exit_tx_hash": tx_hash,
                    "updated_at": now,
                })
                .eq("id", position_id)
                .execute()
            )

            # ── Log transaction ──
            await asyncio.to_thread(
                lambda: self.supabase.table("xrp_transactions").insert({
                    "user_id": user_id,
                    "tx_hash": tx_hash,
                    "tx_type": "amm_withdrawal",
                    "symbol": symbol,
                    "amount": float(total_return),
                    "status": "confirmed",
                    "metadata": {
                        "pool": pool,
                        "principal": str(deposited),
                        "yield_earned": str(yield_earned),
                        "lp_tokens_redeemed": str(user_lp_tokens),
                        "position_id": position_id,
                    },
                    "created_at": now,
                }).execute()
            )

            logger.info(
                f"✅ AMM withdrawal: {total_return} {symbol} returned to user "
                f"{user_id[:8]}... | pool={pool} | tx={tx_hash}"
            )

            return {
                "success": True,
                "pool": pool,
                "principal_returned": str(deposited),
                "yield_earned": str(yield_earned),
                "total_returned": str(total_return),
                "symbol": symbol,
                "tx_hash": tx_hash,
                "status": "withdrawn",
            }

        except Exception as e:
            logger.error(f"❌ AMM withdrawal failed for position {position_id}: {e}")
            raise RuntimeError(f"Withdrawal failed: {e}")

    # ─── USER POSITIONS ───────────────────────────────────────────────────────

    async def get_user_positions(self, user_id: str) -> Dict[str, Any]:
        """Return all active AMM positions for a user with current yield."""
        result = await asyncio.to_thread(
            lambda: self.supabase.table("xrp_amm_positions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        positions = result.data or []

        # Enrich with estimated APY from pool
        enriched = []
        pool_cache = {}
        for pos in positions:
            pool = pos["pool"]
            if pool not in pool_cache:
                pool_cache[pool] = await self.defi.get_pool_apy(
                    SUPPORTED_POOLS[pool]["token"]
                )
            pos["estimated_apy_pct"] = (
                float(pool_cache[pool] * 100) if pool_cache[pool] else None
            )
            pos["days_active"] = (
                (datetime.utcnow() - datetime.fromisoformat(
                    pos["created_at"].replace("Z", "")
                )).days
                if pos.get("created_at") else 0
            )
            enriched.append(pos)

        total_deposited = sum(
            Decimal(str(p.get("token_deposited", 0)))
            for p in enriched if p.get("status") == "active"
        )
        total_yield = sum(
            Decimal(str(p.get("yield_earned", 0)))
            for p in enriched
        )

        return {
            "success": True,
            "positions": enriched,
            "summary": {
                "total_deposited_usd": str(total_deposited),
                "total_yield_earned_usd": str(total_yield),
                "active_positions": sum(1 for p in enriched if p.get("status") == "active"),
            },
        }

    # ─── YIELD DISTRIBUTION (Daily Cron) ──────────────────────────────────────

    async def distribute_yield(self, pool: str = "RLUSD/XRP") -> Dict[str, Any]:
        """
        Calculate and distribute AMM trading fees to all active depositors.
        Called daily by cron job. Pro-rata distribution by LP share.

        In production: compare DeFi wallet's current LP token value vs
        recorded deposits to measure fees earned. For Phase 3 we use
        pool fee rate × estimated daily volume as a conservative estimate
        until we have 30-day rolling volume data from an XRPL data API.
        """
        if pool not in SUPPORTED_POOLS:
            raise ValueError(f"Unsupported pool: {pool}")

        symbol = SUPPORTED_POOLS[pool]["token"]

        # ── Get all active positions for this pool ──
        positions_result = await asyncio.to_thread(
            lambda: self.supabase.table("xrp_amm_positions")
            .select("*")
            .eq("pool", pool)
            .eq("status", "active")
            .execute()
        )

        positions = positions_result.data or []
        if not positions:
            logger.info(f"No active positions in {pool} — skipping yield distribution")
            return {"distributed": 0, "recipients": 0, "pool": pool}

        # ── Get pool fee rate ──
        pool_info = await self.defi.get_pool_info(symbol)
        trading_fee = Decimal(str(pool_info.get("trading_fee", 500))) / 100000  # e.g. 500 = 0.5%

        # ── Estimate daily yield per unit deposited ──
        # Conservative: assume pool turns over 10% of its liquidity daily
        # Real implementation: pull 24h volume from XRPL data API
        daily_turnover_rate = Decimal("0.10")
        daily_fee_rate = trading_fee * daily_turnover_rate  # e.g. 0.5% * 10% = 0.05% daily

        total_share = sum(Decimal(str(p["lp_token_share"])) for p in positions)
        if total_share == 0:
            return {"distributed": 0, "recipients": 0, "pool": pool}

        distributed_count = 0
        total_distributed = Decimal("0")
        now = datetime.utcnow().isoformat()

        for pos in positions:
            try:
                deposited = Decimal(str(pos["token_deposited"]))
                yield_amount = (deposited * daily_fee_rate).quantize(
                    Decimal("0.000001"), rounding=ROUND_HALF_UP
                )

                if yield_amount <= Decimal("0.000001"):
                    continue  # Skip dust

                user_id = pos["user_id"]

                # Credit yield to user's internal balance
                await asyncio.to_thread(
                    lambda uid=user_id, ya=yield_amount: self.supabase.rpc(
                        "update_xrp_balance", {
                            "p_user_id": uid,
                            "p_symbol": symbol,
                            "p_delta": float(ya),
                        }
                    ).execute()
                )

                # Update position yield_earned
                new_yield = Decimal(str(pos.get("yield_earned", 0))) + yield_amount
                await asyncio.to_thread(
                    lambda pid=pos["id"], ny=new_yield: self.supabase.table("xrp_amm_positions")
                    .update({"yield_earned": float(ny), "updated_at": now})
                    .eq("id", pid)
                    .execute()
                )

                # Log as yield_credit transaction
                await asyncio.to_thread(
                    lambda uid=user_id, ya=yield_amount: self.supabase.table("xrp_transactions").insert({
                        "user_id": uid,
                        "tx_type": "yield_credit",
                        "symbol": symbol,
                        "amount": float(ya),
                        "status": "confirmed",
                        "metadata": {"pool": pool, "daily_fee_rate": str(daily_fee_rate)},
                        "created_at": now,
                    }).execute()
                )

                # Record in yield_distributions audit table
                await asyncio.to_thread(
                    lambda uid=user_id, ya=yield_amount: self.supabase.table("xrp_yield_distributions").insert({
                        "user_id": uid,
                        "pool": pool,
                        "symbol": symbol,
                        "amount": float(ya),
                        "distribution_date": now[:10],  # YYYY-MM-DD
                        "created_at": now,
                    }).execute()
                )

                total_distributed += yield_amount
                distributed_count += 1

            except Exception as e:
                logger.error(f"❌ Yield distribution failed for position {pos.get('id')}: {e}")

        logger.info(
            f"✅ Yield distributed: {total_distributed} {symbol} "
            f"to {distributed_count} users | pool={pool}"
        )

        return {
            "success": True,
            "pool": pool,
            "symbol": symbol,
            "total_distributed": str(total_distributed),
            "recipients": distributed_count,
            "distribution_date": now[:10],
            "daily_fee_rate": str(daily_fee_rate),
        }

    # ─── HELPERS ──────────────────────────────────────────────────────────────

    def _estimate_xrp_needed(
        self, token_amount: Decimal, pool_info: Optional[Dict]
    ) -> Decimal:
        """
        Estimate XRP needed to pair with token deposit in two-asset AMM deposit.
        Uses live pool ratio if available, falls back to hardcoded estimate.
        """
        if pool_info:
            try:
                # Pool balances give us the current ratio
                # asset1 = XRP side, asset2 = token side
                xrp_pool = Decimal(str(pool_info.get("amount", "0")))  # in drops
                token_pool = Decimal(str(pool_info.get("amount2", {}).get("value", "1")))
                if token_pool > 0 and xrp_pool > 0:
                    xrp_drops_per_token = xrp_pool / token_pool
                    xrp_needed = (token_amount * xrp_drops_per_token / 1_000_000)
                    return xrp_needed.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            except Exception:
                pass

        # Fallback: static estimate
        return (token_amount * XRP_RATIO_ESTIMATE).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )