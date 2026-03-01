# File: backend/services/xrp_payment_service.py
"""
XRP Payment Service — Seamount.io Phase 2

─── FEE MODEL ─────────────────────────────────────────────────────────────────
Withdrawal fee = base + (pct% × amount), clamped between min and max.

  RLUSD / USDC:  $0.50 base + 0.5% │ min $0.50 │ max $10.00
  XRP:            0.1  base + 1.0% │ min  0.10 │ max  10.00

Examples:
  $10    RLUSD → $0.50 + $0.05  = $0.55
  $100   RLUSD → $0.50 + $0.50  = $1.00
  $1,000 RLUSD → $0.50 + $5.00  = $5.50
  $5,000 RLUSD → capped          = $10.00
  10 XRP       → 0.1  + 0.1     = 0.20 XRP
  1,000 XRP    → capped          = 10.0 XRP

Fee stays in Seamount's hot wallet automatically — no extra collection tx needed.
────────────────────────────────────────────────────────────────────────────────
"""

import asyncio
import logging
import os
import traceback as tb
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Minimum withdrawal amounts ───────────────────────────────────────────────
MIN_WITHDRAWAL = {
    "RLUSD": Decimal("1.00"),
    "USDC":  Decimal("1.00"),
    "XRP":   Decimal("0.10"),
}

# ─── Fee schedule: (base, pct_rate, min_fee, max_fee) ─────────────────────────
FEE_SCHEDULE: Dict[str, Tuple[Decimal, Decimal, Decimal, Decimal]] = {
    "RLUSD": (Decimal("0.50"), Decimal("0.005"), Decimal("0.50"), Decimal("10.00")),
    "USDC":  (Decimal("0.50"), Decimal("0.005"), Decimal("0.50"), Decimal("10.00")),
    "XRP":   (Decimal("0.10"), Decimal("0.010"), Decimal("0.10"), Decimal("10.00")),
}

SUPPORTED_SYMBOLS = {"RLUSD", "USDC", "XRP"}
STARTING_TAG = 10001


def calculate_withdrawal_fee(symbol: str, amount: Decimal) -> Decimal:
    """
    base + pct% of amount, clamped [min, max].
    Fee stays in hot wallet — no extra tx required.
    """
    if symbol not in FEE_SCHEDULE:
        return Decimal("0")
    base, pct_rate, min_fee, max_fee = FEE_SCHEDULE[symbol]
    raw = base + (amount * pct_rate)
    fee = max(min_fee, min(raw, max_fee))
    return fee.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)


def fee_breakdown(symbol: str, amount: Decimal) -> Dict[str, str]:
    """Human-readable fee breakdown for API responses and UI."""
    fee = calculate_withdrawal_fee(symbol, amount)
    total = (amount + fee).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
    _, pct, min_f, max_f = FEE_SCHEDULE.get(
        symbol, (Decimal(0), Decimal(0), Decimal(0), Decimal(0))
    )
    return {
        "amount":         str(amount.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)),
        "fee":            str(fee),
        "fee_pct":        f"{float(pct) * 100:.1f}%",
        "total_deducted": str(total),
        "fee_note":       (
            f"Seamount fee: {float(pct)*100:.1f}% of amount "
            f"(min {min_f} {symbol}, max {max_f} {symbol}). "
            "Retained in hot wallet automatically."
        ),
    }


class XRPPaymentService:

    def __init__(self, supabase_client, xrp_service, settings=None):
        self.supabase = supabase_client
        self.xrp = xrp_service
        from backend.config import get_settings
        self.settings = settings or get_settings()
        logger.info("✅ XRPPaymentService initialized")

    # ─── HELPERS ──────────────────────────────────────────────────────────────

    def _get_hot_wallet(self) -> str:
        addr = (
            getattr(self.settings, 'XRP_HOT_WALLET_ADDRESS', None)
            or os.getenv('XRP_HOT_WALLET_ADDRESS', '')
        )
        if not addr:
            raise RuntimeError("XRP_HOT_WALLET_ADDRESS not set in environment variables.")
        return addr

    async def _assign_xrp_destination_tag(self, user_id: str) -> int:
        try:
            result = await asyncio.to_thread(
                lambda: self.supabase
                .table("xrp_destination_tags")
                .select("destination_tag")
                .order("destination_tag", desc=True)
                .limit(1)
                .execute()
            )
            next_tag = (int(result.data[0]['destination_tag']) + 1) if result.data else STARTING_TAG
            if next_tag > 4_294_967_295:
                raise RuntimeError("Destination tag pool exhausted")
            logger.info(f"🏷️  Next destination tag: {next_tag}")
            return next_tag
        except Exception as e:
            logger.error(f"❌ _assign_xrp_destination_tag failed: {e}")
            raise

    # ─── DEPOSIT INFO ─────────────────────────────────────────────────────────

    async def get_deposit_info(self, user_id: str) -> Dict[str, Any]:
        try:
            result = await asyncio.to_thread(
                lambda: self.supabase
                .table("xrp_destination_tags")
                .select("destination_tag, hot_wallet, created_at")
                .eq("user_id", user_id)
                .execute()
            )

            if not result.data:
                logger.info(f"No tag for {user_id[:8]}... — auto-assigning")
                tag = await self._assign_xrp_destination_tag(user_id)
                hot_wallet = self._get_hot_wallet()
                await asyncio.to_thread(
                    lambda: self.supabase
                    .table("xrp_destination_tags")
                    .upsert(
                        {
                            "user_id": user_id,
                            "destination_tag": tag,
                            "hot_wallet": hot_wallet,
                            "created_at": datetime.utcnow().isoformat(),
                        },
                        on_conflict="user_id"
                    )
                    .execute()
                )
                logger.info(f"✅ Assigned tag {tag} → user {user_id[:8]}...")
            else:
                tag = int(result.data[0]['destination_tag'])
                hot_wallet = result.data[0].get('hot_wallet') or self._get_hot_wallet()

            return {
                "success": True,
                "deposit_address": hot_wallet,
                "destination_tag": tag,
                "network": "XRP Ledger (XRPL)",
                "supported_assets": ["RLUSD", "USDC", "XRP"],
                "warning": (
                    "⚠️ You MUST include your Destination Tag when sending. "
                    "Deposits without the correct tag cannot be credited."
                ),
                "instructions": [
                    f"Send RLUSD, USDC, or XRP to: {hot_wallet}",
                    f"Set Destination Tag to: {tag}",
                    "Both fields are required. Missing tag = unrecoverable funds.",
                    "Min deposit: 1.00 RLUSD / 1.00 USDC / 0.1 XRP",
                    "Settlement: ~3-5 seconds on XRPL.",
                ],
            }

        except Exception as e:
            logger.error(f"❌ get_deposit_info failed for {user_id}: {e}\n{tb.format_exc()}")
            raise

    # ─── BALANCES ─────────────────────────────────────────────────────────────

    async def get_balance(self, user_id: str, symbol: str) -> Decimal:
        symbol = symbol.upper()
        if symbol not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Unsupported symbol: {symbol}")
        result = await asyncio.to_thread(
            lambda: self.supabase
            .table("xrp_internal_balances")
            .select("balance")
            .eq("user_id", user_id)
            .eq("symbol", symbol)
            .execute()
        )
        return Decimal(str(result.data[0]['balance'])) if result.data else Decimal("0")

    async def get_all_balances(self, user_id: str) -> Dict[str, str]:
        result = await asyncio.to_thread(
            lambda: self.supabase
            .table("xrp_internal_balances")
            .select("symbol, balance")
            .eq("user_id", user_id)
            .execute()
        )
        balances = {s: "0.00" for s in SUPPORTED_SYMBOLS}
        if result.data:
            for row in result.data:
                balances[row['symbol']] = str(Decimal(str(row['balance'])))
        return balances

    # ─── TAG RESOLVER ─────────────────────────────────────────────────────────

    async def get_user_by_destination_tag(self, tag: int) -> str:
        result = await asyncio.to_thread(
            lambda: self.supabase
            .table("xrp_destination_tags")
            .select("user_id")
            .eq("destination_tag", tag)
            .execute()
        )
        if not result.data:
            raise ValueError(
                f"No Seamount account found for destination tag {tag}. "
                "Ask the recipient to check their XRP page for their tag number."
            )
        return result.data[0]['user_id']

    # ─── FEE QUOTE (call before withdrawal to show user the cost) ─────────────

    async def get_withdrawal_quote(self, symbol: str, amount: Decimal) -> Dict[str, Any]:
        symbol = symbol.upper()
        if symbol not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Unsupported symbol: {symbol}")
        if amount < MIN_WITHDRAWAL.get(symbol, Decimal("1")):
            raise ValueError(f"Minimum withdrawal: {MIN_WITHDRAWAL[symbol]} {symbol}")
        bd = fee_breakdown(symbol, amount)
        _, pct, min_f, max_f = FEE_SCHEDULE[symbol]
        return {
            "success": True,
            **bd,
            "fee_schedule": (
                f"{float(pct)*100:.1f}% of amount + base, "
                f"min {min_f} {symbol}, max {max_f} {symbol}"
            ),
        }

    # ─── INTERNAL TRANSFER (P2P — zero fee, DB-only) ──────────────────────────

    async def internal_transfer(
        self,
        sender_id: str,
        recipient_id: str,
        symbol: str,
        amount: Decimal,
        memo: Optional[str] = None,
    ) -> Dict[str, Any]:
        symbol = symbol.upper()

        if symbol not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Unsupported asset: {symbol}")
        if amount <= Decimal("0"):
            raise ValueError("Amount must be greater than zero")
        if sender_id == recipient_id:
            raise ValueError("Cannot transfer to yourself")

        amount = amount.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)

        sender_balance = await self.get_balance(sender_id, symbol)
        if sender_balance < amount:
            raise ValueError(
                f"Insufficient {symbol}. Have: {sender_balance}, Need: {amount}"
            )

        recipient_check = await asyncio.to_thread(
            lambda: self.supabase
            .table("xrp_destination_tags")
            .select("user_id")
            .eq("user_id", recipient_id)
            .execute()
        )
        if not recipient_check.data:
            raise ValueError("Recipient has no active XRP account on Seamount")

        now = datetime.utcnow().isoformat()

        try:
            await asyncio.to_thread(
                lambda: self.supabase.rpc("update_xrp_balance", {
                    "p_user_id": sender_id,
                    "p_symbol": symbol,
                    "p_delta": float(-amount),
                }).execute()
            )
            await asyncio.to_thread(
                lambda: self.supabase.rpc("update_xrp_balance", {
                    "p_user_id": recipient_id,
                    "p_symbol": symbol,
                    "p_delta": float(amount),
                }).execute()
            )
        except Exception as e:
            logger.error(f"❌ internal_transfer RPC failed: {e}")
            raise RuntimeError(f"Transfer failed: {e}")

        tx_meta = {"memo": memo, "type": "internal_p2p", "fee": "0.00"}
        sender_row = {
            "user_id": sender_id,
            "tx_type": "internal_transfer",
            "symbol": symbol,
            "amount": float(-amount),
            "to_address": f"internal:{recipient_id}",
            "status": "confirmed",
            "metadata": tx_meta,
            "created_at": now,
        }
        recipient_row = {
            "user_id": recipient_id,
            "tx_type": "internal_transfer",
            "symbol": symbol,
            "amount": float(amount),
            "from_address": f"internal:{sender_id}",
            "status": "confirmed",
            "metadata": tx_meta,
            "created_at": now,
        }
        for label, row in [("sender", sender_row), ("recipient", recipient_row)]:
            try:
                captured = dict(row)
                await asyncio.to_thread(
                    lambda r=captured: self.supabase
                    .table("xrp_transactions")
                    .insert(r)
                    .execute()
                )
                logger.info(
                    f"✅ TX logged [{label}]: {row['amount']} {symbol} | "
                    f"user {row['user_id'][:8]}..."
                )
            except Exception as log_err:
                logger.error(
                    f"🚨 TX LOG FAILED [{label}] {row['user_id'][:8]}: "
                    f"{log_err}\n{tb.format_exc()}"
                )

        logger.info(f"✅ Transfer: {amount} {symbol} | {sender_id[:8]}→{recipient_id[:8]} | fee: $0")
        return {
            "success": True,
            "type": "internal_transfer",
            "symbol": symbol,
            "amount": str(amount),
            "fee": "0.00",
            "memo": memo,
            "settled_at": now,
            "settlement": "instant (internal ledger)",
        }

    # ─── EXTERNAL WITHDRAWAL (on-chain) ───────────────────────────────────────

    async def withdraw(
        self,
        user_id: str,
        symbol: str,
        amount: Decimal,
        destination_address: str,
        destination_tag: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Fee flow (fully automatic — no extra tx needed):
          1. user_balance  -= (amount + fee)       ← deducted upfront
          2. hot_wallet sends `amount` → recipient ← XRPL tx
          3. `fee` stays in hot_wallet             ← Seamount revenue
        """
        symbol = symbol.upper()

        if symbol not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Unsupported asset: {symbol}")
        if amount < MIN_WITHDRAWAL.get(symbol, Decimal("1")):
            raise ValueError(f"Minimum withdrawal: {MIN_WITHDRAWAL[symbol]} {symbol}")
        if not destination_address.startswith("r") or len(destination_address) < 25:
            raise ValueError("Invalid XRPL address (must start with 'r', min 25 chars)")
        if self.xrp is None:
            raise RuntimeError(
                "On-chain withdrawals unavailable: xrpl-py not installed."
            )

        # ── Dynamic fee ──
        fee = calculate_withdrawal_fee(symbol, amount)
        amount = amount.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
        total_deducted = (amount + fee).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
        bd = fee_breakdown(symbol, amount)

        logger.info(
            f"💸 Withdrawal: {amount} {symbol} | fee: {fee} | total: {total_deducted}"
        )

        balance = await self.get_balance(user_id, symbol)
        if balance < total_deducted:
            raise ValueError(
                f"Insufficient {symbol}. Need {total_deducted} "
                f"(amount {amount} + fee {fee}). Have: {balance}"
            )

        # Pre-debit
        await asyncio.to_thread(
            lambda: self.supabase.rpc("update_xrp_balance", {
                "p_user_id": user_id,
                "p_symbol": symbol,
                "p_delta": float(-total_deducted),
            }).execute()
        )

        now = datetime.utcnow().isoformat()
        await asyncio.to_thread(
            lambda: self.supabase.table("xrp_transactions").insert({
                "user_id": user_id,
                "tx_type": "withdrawal",
                "symbol": symbol,
                "amount": float(-amount),
                "to_address": destination_address,
                "destination_tag": destination_tag,
                "status": "pending",
                "metadata": {
                    "fee":            bd["fee"],
                    "fee_pct":        bd["fee_pct"],
                    "total_deducted": bd["total_deducted"],
                    "fee_note":       bd["fee_note"],
                },
                "created_at": now,
            }).execute()
        )

        try:
            if symbol == "XRP":
                result = await self.xrp.send_xrp(
                    destination=destination_address,
                    amount_xrp=amount,
                    destination_tag=destination_tag,
                )
            else:
                result = await self.xrp.send_stablecoin(
                    symbol=symbol,
                    destination=destination_address,
                    amount=amount,
                    destination_tag=destination_tag,
                )

            tx_hash = result.get("tx_hash")
            await asyncio.to_thread(
                lambda: self.supabase.table("xrp_transactions")
                .update({
                    "tx_hash": tx_hash,
                    "status": "confirmed",
                    "ledger_index": result.get("ledger_index"),
                })
                .eq("user_id", user_id)
                .eq("status", "pending")
                .eq("to_address", destination_address)
                .execute()
            )

            network = getattr(self.settings, 'XRP_NETWORK', 'mainnet')
            base_url = "https://testnet.xrpl.org" if network == "testnet" else "https://xrpl.org"
            logger.info(
                f"✅ Withdrawal confirmed: {amount} {symbol} → "
                f"{destination_address[:10]}... | fee kept: {fee} {symbol} | tx: {tx_hash}"
            )

            return {
                "success": True,
                "type": "withdrawal",
                "symbol": symbol,
                "amount_sent": str(amount),
                "fee": str(fee),
                "fee_pct": bd["fee_pct"],
                "total_deducted": str(total_deducted),
                "destination": destination_address,
                "destination_tag": destination_tag,
                "tx_hash": tx_hash,
                "status": "confirmed",
                "settled_at": datetime.utcnow().isoformat(),
                "explorer_url": f"{base_url}/transactions/{tx_hash}",
                "fee_note": bd["fee_note"],
            }

        except Exception as chain_err:
            # Full refund on failure — including the fee
            logger.error(f"❌ Withdrawal failed — refunding {total_deducted} {symbol}: {chain_err}")
            try:
                await asyncio.to_thread(
                    lambda: self.supabase.rpc("update_xrp_balance", {
                        "p_user_id": user_id,
                        "p_symbol": symbol,
                        "p_delta": float(total_deducted),
                    }).execute()
                )
                await asyncio.to_thread(
                    lambda: self.supabase.table("xrp_transactions")
                    .update({"status": "failed", "metadata": {"error": str(chain_err)}})
                    .eq("user_id", user_id)
                    .eq("status", "pending")
                    .eq("to_address", destination_address)
                    .execute()
                )
                logger.info(f"✅ Full refund: {total_deducted} {symbol} → {user_id[:8]}...")
            except Exception as refund_err:
                logger.critical(
                    f"🚨 REFUND FAILED: user={user_id} "
                    f"amount={total_deducted} {symbol} | {refund_err}"
                )
            raise RuntimeError(f"Withdrawal failed: {chain_err}")

    # ─── TRANSACTION HISTORY ──────────────────────────────────────────────────

    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            query = (
                self.supabase.table("xrp_transactions")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
            )
            if symbol:
                query = query.eq("symbol", symbol.upper())
            result = await asyncio.to_thread(lambda: query.execute())
            return {
                "success": True,
                "transactions": result.data or [],
                "count": len(result.data or []),
                "limit": limit,
                "offset": offset,
            }
        except Exception as e:
            logger.error(f"❌ get_transaction_history failed for {user_id}: {e}")
            raise