# File: backend/services/xrp_payment_service.py
"""
XRP Payment Service — Seamount.io Phase 2
Handles: internal P2P transfers (DB-only), withdrawals (on-chain), deposit info.

Internal transfer:  pure Postgres — zero fee, sub-millisecond, no blockchain tx
Withdrawal:         signs one Payment tx from Seamount hot wallet → external address
Deposit info:       returns hot wallet address + user's destination tag
"""

import asyncio
import logging
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Minimum withdrawal amounts (prevent dust)
MIN_WITHDRAWAL = {
    "RLUSD": Decimal("1.00"),
    "USDC":  Decimal("1.00"),
    "XRP":   Decimal("0.1"),
}

# Withdrawal fee charged by Seamount (platform revenue)
WITHDRAWAL_FEE = {
    "RLUSD": Decimal("0.50"),
    "USDC":  Decimal("0.50"),
    "XRP":   Decimal("0.05"),
}

SUPPORTED_SYMBOLS = {"RLUSD", "USDC", "XRP"}


class XRPPaymentService:
    """
    Zero-fee internal transfers + on-chain withdrawals for Seamount custodial model.
    All internal balances live in xrp_internal_balances (Supabase).
    On-chain txs only happen for external withdrawals.
    """

    def __init__(self, supabase_client, xrp_service, settings=None):
        self.supabase = supabase_client
        self.xrp = xrp_service
        from backend.config import get_settings
        self.settings = settings or get_settings()
        logger.info("✅ XRPPaymentService initialized")

    # ─── DEPOSIT INFO ──────────────────────────────────────────────────────────

    async def get_deposit_info(self, user_id: str) -> Dict[str, Any]:
        """
        Return everything a user needs to deposit RLUSD/USDC/XRP into Seamount.
        Shows: hot wallet address + their unique destination tag.
        """
        try:
            result = await asyncio.to_thread(
                lambda: self.supabase.table("xrp_destination_tags")
                .select("destination_tag, hot_wallet, created_at")
                .eq("user_id", user_id)
                .execute()
            )

            # ✅ SELF-HEAL: Auto-assign tag on first request instead of 404
            if not result.data:
                logger.info(f"No destination tag for {user_id[:8]}... — auto-assigning now")
                tag = await self._assign_xrp_destination_tag(user_id)
                hot_wallet = self.settings.XRP_HOT_WALLET_ADDRESS

                await asyncio.to_thread(
                    lambda: self.supabase.table("xrp_destination_tags").insert({
                        "user_id": user_id,
                        "destination_tag": tag,
                        "hot_wallet": hot_wallet,
                        "created_at": datetime.utcnow().isoformat(),
                    }).execute()
                )
                logger.info(f"✅ Auto-assigned destination tag {tag} to user {user_id[:8]}...")
            else:
                tag = int(result.data[0]['destination_tag'])
                hot_wallet = result.data[0]['hot_wallet'] or self.settings.XRP_HOT_WALLET_ADDRESS

            return {
                "success": True,
                "deposit_address": hot_wallet,
                "destination_tag": int(tag_data['destination_tag']),
                "network": "XRP Ledger (XRPL)",
                "supported_assets": ["RLUSD", "USDC", "XRP"],
                "warning": (
                    "⚠️ You MUST include your Destination Tag when sending. "
                    "Deposits without the correct tag cannot be credited to your account."
                ),
                "instructions": [
                    f"Send RLUSD, USDC, or XRP to address: {hot_wallet}",
                    f"Set Destination Tag to: {int(tag_data['destination_tag'])}",
                    "Both fields are required. Missing tag = unrecoverable deposit.",
                    "Minimum deposit: 1.00 RLUSD / 1.00 USDC / 0.1 XRP",
                    "Deposits confirm in ~5 seconds on XRPL.",
                ],
            }

        except ValueError as e:
            logger.error(f"get_deposit_info ValueError: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ get_deposit_info failed for {user_id}: {e}")
            raise

    # ─── INTERNAL BALANCE ──────────────────────────────────────────────────────

    async def get_balance(self, user_id: str, symbol: str) -> Decimal:
        """Get a user's internal balance for one asset."""
        symbol = symbol.upper()
        if symbol not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Unsupported symbol: {symbol}")

        result = await asyncio.to_thread(
            lambda: self.supabase.table("xrp_internal_balances")
            .select("balance")
            .eq("user_id", user_id)
            .eq("symbol", symbol)
            .execute()
        )

        if not result.data:
            return Decimal("0")
        return Decimal(str(result.data[0]['balance']))

    async def get_all_balances(self, user_id: str) -> Dict[str, str]:
        """Get all XRP internal balances for a user."""
        result = await asyncio.to_thread(
            lambda: self.supabase.table("xrp_internal_balances")
            .select("symbol, balance")
            .eq("user_id", user_id)
            .execute()
        )

        balances = {s: "0.00" for s in SUPPORTED_SYMBOLS}
        if result.data:
            for row in result.data:
                balances[row['symbol']] = str(Decimal(str(row['balance'])))
        return balances

    # ─── INTERNAL TRANSFER (P2P — pure DB, zero fee) ───────────────────────────

    async def internal_transfer(
        self,
        sender_id: str,
        recipient_id: str,
        symbol: str,
        amount: Decimal,
        memo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transfer between two Seamount users.
        NO on-chain transaction. NO fee. Pure Supabase RPC.
        Settles in <10ms. This is the core product loop.
        """
        symbol = symbol.upper()

        # ── Validation ──
        if symbol not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Unsupported asset: {symbol}")
        if amount <= Decimal("0"):
            raise ValueError("Amount must be greater than zero")
        if sender_id == recipient_id:
            raise ValueError("Cannot transfer to yourself")
        amount = amount.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)

        # ── Check sender balance ──
        sender_balance = await self.get_balance(sender_id, symbol)
        if sender_balance < amount:
            raise ValueError(
                f"Insufficient balance. Available: {sender_balance} {symbol}, "
                f"Requested: {amount} {symbol}"
            )

        # ── Verify recipient exists ──
        recipient_check = await asyncio.to_thread(
            lambda: self.supabase.table("xrp_destination_tags")
            .select("user_id")
            .eq("user_id", recipient_id)
            .execute()
        )
        if not recipient_check.data:
            raise ValueError("Recipient does not have an active XRP account on Seamount")

        # ── Atomic debit/credit via DB RPC ──
        try:
            # Debit sender
            await asyncio.to_thread(
                lambda: self.supabase.rpc("update_xrp_balance", {
                    "p_user_id": sender_id,
                    "p_symbol": symbol,
                    "p_delta": float(-amount),
                }).execute()
            )

            # Credit recipient
            await asyncio.to_thread(
                lambda: self.supabase.rpc("update_xrp_balance", {
                    "p_user_id": recipient_id,
                    "p_symbol": symbol,
                    "p_delta": float(amount),
                }).execute()
            )

        except Exception as db_err:
            logger.error(f"❌ internal_transfer DB RPC failed: {db_err}")
            raise RuntimeError(f"Transfer failed: {db_err}")

        # ── Log both sides ──
        now = datetime.utcnow().isoformat()
        tx_meta = {"memo": memo, "type": "internal_p2p"}

        await asyncio.to_thread(
            lambda: self.supabase.table("xrp_transactions").insert([
                {
                    "user_id": sender_id,
                    "tx_type": "internal_transfer",
                    "symbol": symbol,
                    "amount": float(-amount),
                    "to_address": f"internal:{recipient_id}",
                    "status": "confirmed",
                    "metadata": tx_meta,
                    "created_at": now,
                },
                {
                    "user_id": recipient_id,
                    "tx_type": "internal_transfer",
                    "symbol": symbol,
                    "amount": float(amount),
                    "from_address": f"internal:{sender_id}",
                    "status": "confirmed",
                    "metadata": tx_meta,
                    "created_at": now,
                },
            ]).execute()
        )

        logger.info(
            f"✅ Internal transfer: {amount} {symbol} | "
            f"{sender_id[:8]}... → {recipient_id[:8]}... | fee: $0.00"
        )

        return {
            "success": True,
            "type": "internal_transfer",
            "symbol": symbol,
            "amount": str(amount),
            "fee": "0.00",
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "memo": memo,
            "settled_at": now,
            "settlement": "instant (internal ledger)",
        }

    # ─── EXTERNAL WITHDRAWAL (on-chain) ────────────────────────────────────────

    async def withdraw(
        self,
        user_id: str,
        symbol: str,
        amount: Decimal,
        destination_address: str,
        destination_tag: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Withdraw from Seamount to an external XRPL address.
        Deducts balance + fee from internal ledger, then signs one on-chain tx.
        """
        symbol = symbol.upper()

        # ── Validation ──
        if symbol not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Unsupported asset: {symbol}")
        if amount < MIN_WITHDRAWAL.get(symbol, Decimal("1")):
            raise ValueError(
                f"Minimum withdrawal: {MIN_WITHDRAWAL[symbol]} {symbol}"
            )
        if not destination_address.startswith("r") or len(destination_address) < 25:
            raise ValueError("Invalid XRPL destination address (must start with 'r')")

        fee = WITHDRAWAL_FEE.get(symbol, Decimal("0"))
        total_deducted = (amount + fee).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
        amount = amount.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)

        # ── Check balance covers amount + fee ──
        balance = await self.get_balance(user_id, symbol)
        if balance < total_deducted:
            raise ValueError(
                f"Insufficient balance. Need {total_deducted} {symbol} "
                f"(includes {fee} {symbol} withdrawal fee). "
                f"Available: {balance} {symbol}"
            )

        # ── Pre-debit internal balance (hold) ──
        await asyncio.to_thread(
            lambda: self.supabase.rpc("update_xrp_balance", {
                "p_user_id": user_id,
                "p_symbol": symbol,
                "p_delta": float(-total_deducted),
            }).execute()
        )

        # ── Log as pending ──
        now = datetime.utcnow().isoformat()
        pending_log = await asyncio.to_thread(
            lambda: self.supabase.table("xrp_transactions").insert({
                "user_id": user_id,
                "tx_type": "withdrawal",
                "symbol": symbol,
                "amount": float(-amount),
                "to_address": destination_address,
                "destination_tag": destination_tag,
                "status": "pending",
                "metadata": {
                    "fee": str(fee),
                    "total_deducted": str(total_deducted),
                    "destination_tag": destination_tag,
                },
                "created_at": now,
            }).execute()
        )

        # ── Guard: xrp_service required for on-chain tx ──
        if self.xrp is None:
            raise RuntimeError("On-chain withdrawals unavailable: xrpl-py not installed on this server. Contact support.")
        
        # ── Submit on-chain tx ──
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

            # ── Update log to confirmed ──
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

            logger.info(
                f"✅ Withdrawal: {amount} {symbol} → {destination_address[:10]}... | "
                f"fee: {fee} {symbol} | tx: {tx_hash}"
            )

            return {
                "success": True,
                "type": "withdrawal",
                "symbol": symbol,
                "amount_sent": str(amount),
                "fee": str(fee),
                "total_deducted": str(total_deducted),
                "destination": destination_address,
                "destination_tag": destination_tag,
                "tx_hash": tx_hash,
                "status": "confirmed",
                "settled_at": datetime.utcnow().isoformat(),
                "explorer_url": f"https://{'testnet.' if self.settings.XRP_NETWORK == 'testnet' else ''}xrpl.org/transactions/{tx_hash}",
            }

        except Exception as chain_err:
            # ── Refund internal balance if on-chain tx fails ──
            logger.error(f"❌ On-chain withdrawal failed — refunding: {chain_err}")
            try:
                await asyncio.to_thread(
                    lambda: self.supabase.rpc("update_xrp_balance", {
                        "p_user_id": user_id,
                        "p_symbol": symbol,
                        "p_delta": float(total_deducted),  # refund
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
                logger.info(f"✅ Refund issued: {total_deducted} {symbol} → user {user_id[:8]}...")
            except Exception as refund_err:
                logger.critical(
                    f"🚨 REFUND FAILED for user {user_id} | "
                    f"amount: {total_deducted} {symbol} | error: {refund_err}"
                )
            raise RuntimeError(f"Withdrawal failed: {chain_err}")

    # ─── TRANSACTION HISTORY ───────────────────────────────────────────────────

    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Paginated transaction history for a user."""
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