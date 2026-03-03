# backend/services/wdk_protocols_service.py
"""
WDK Protocols Service
─────────────────────
Orchestrates Velora Swap, USDT0 Bridge, Aave Lending,
MoonPay Fiat, and Tether Price Rates — all via the
Node.js WDK service endpoints added in wdk-protocols.js.

Each method:
  - Looks up the user's wallet seed (decrypted)
  - Converts amounts to base units
  - Calls the appropriate WDK client method
  - Logs to Supabase for audit trail
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import uuid4

from backend.wdk_client import WDKClient
from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

# ── EVM Token contract addresses (mainnet) ────────────────────────
EVM_TOKEN_CONTRACTS = {
    'ethereum': {
        'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'USDC': '0xA0b86991c6218b36c1d19D4a2e9eb0cE3606eB48',
        'USDT0': '0x0000000000000000000000000000000000000000',  # Replace with actual USDT0 addr
    },
    'polygon': {
        'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
        'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
    }
}

TOKEN_DECIMALS = {'USDT': 6, 'USDC': 6, 'USDT0': 6, 'WETH': 18, 'ETH': 18}


def _to_base_units(amount: Decimal, decimals: int) -> int:
    return int(amount * (10 ** decimals))


class WDKProtocolsService:

    def __init__(self, wdk_client: WDKClient, db_service: DatabaseService):
        self.wdk = wdk_client
        self.db  = db_service

    # ─────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────

    async def _get_user_seed(self, user_id: str, chain: str) -> tuple[str, str]:
        """Returns (plaintext_seed, wallet_address) for user+chain."""
        from backend.services.seed_encryption_service import SeedEncryptionService
        enc = SeedEncryptionService()

        wallets = await self.db.client.table('wallets') \
            .select('encrypted_seed, address') \
            .eq('user_id', user_id) \
            .eq('chain', chain) \
            .limit(1) \
            .execute()

        if not wallets.data:
            raise ValueError(f"No {chain} wallet found for user {user_id}")

        encrypted_seed = wallets.data[0]['encrypted_seed']
        address        = wallets.data[0]['address']
        plaintext_seed = enc.decrypt_seed(encrypted_seed)
        return plaintext_seed, address

    async def _log_transaction(
        self,
        user_id: str,
        tx_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Persist transaction record to Supabase (best-effort)."""
        try:
            record = {
                'id':         str(uuid4()),
                'user_id':    user_id,
                'tx_type':    tx_type,
                'created_at': datetime.utcnow().isoformat(),
                **data
            }
            await self.db.client.table('wdk_protocol_transactions') \
                .insert(record) \
                .execute()
        except Exception as e:
            logger.warning(f"⚠️ Failed to log {tx_type} transaction: {e}")

    def _get_contract(self, chain: str, token: str) -> str:
        contracts = EVM_TOKEN_CONTRACTS.get(chain, {})
        addr = contracts.get(token.upper())
        if not addr:
            raise ValueError(f"No contract address for {token} on {chain}")
        return addr

    # ─────────────────────────────────────────────────────────────
    # SWAP (Velora EVM)
    # ─────────────────────────────────────────────────────────────

    async def swap(
        self,
        user_id:    str,
        token_in:   str,        # e.g. 'USDT'
        token_out:  str,        # e.g. 'USDC'
        amount_in:  Decimal,
        chain:      str = 'ethereum',
        account_index: int = 0
    ) -> Dict[str, Any]:
        """Execute Velora EVM token swap for user."""
        logger.info(f"🔄 WDK Swap: {amount_in} {token_in} → {token_out} on {chain}")

        plaintext_seed, address = await self._get_user_seed(user_id, chain)

        token_in_addr  = self._get_contract(chain, token_in)
        token_out_addr = self._get_contract(chain, token_out)
        decimals       = TOKEN_DECIMALS.get(token_in.upper(), 6)
        amount_base    = _to_base_units(amount_in, decimals)

        result = await self.wdk.wdk_swap(
            plaintext_seed = plaintext_seed,
            account_index  = account_index,
            token_in       = token_in_addr,
            token_out      = token_out_addr,
            amount_in      = amount_base,
            chain          = chain
        )

        await self._log_transaction(user_id, 'swap', {
            'chain':      chain,
            'token_in':   token_in,
            'token_out':  token_out,
            'amount_in':  float(amount_in),
            'tx_hash':    result.get('tx_hash'),
            'fee':        result.get('fee', '0'),
            'status':     'completed'
        })

        logger.info(f"✅ Swap complete: {result.get('tx_hash')}")
        return result

    # ─────────────────────────────────────────────────────────────
    # BRIDGE (USDT0 EVM)
    # ─────────────────────────────────────────────────────────────

    async def bridge(
        self,
        user_id:      str,
        token:        str,          # e.g. 'USDT'
        amount:       Decimal,
        target_chain: str,          # e.g. 'ton'
        recipient:    str,          # recipient address on target chain
        source_chain: str = 'ethereum',
        account_index: int = 0
    ) -> Dict[str, Any]:
        """Bridge USDT0 across chains for user."""
        logger.info(
            f"🌉 WDK Bridge: {amount} {token} "
            f"{source_chain} → {target_chain}"
        )

        plaintext_seed, _ = await self._get_user_seed(user_id, source_chain)

        token_addr  = self._get_contract(source_chain, token)
        decimals    = TOKEN_DECIMALS.get(token.upper(), 6)
        amount_base = _to_base_units(amount, decimals)

        result = await self.wdk.wdk_bridge(
            plaintext_seed = plaintext_seed,
            account_index  = account_index,
            token          = token_addr,
            amount         = amount_base,
            target_chain   = target_chain,
            recipient      = recipient,
            source_chain   = source_chain
        )

        await self._log_transaction(user_id, 'bridge', {
            'source_chain': source_chain,
            'target_chain': target_chain,
            'token':        token,
            'amount':       float(amount),
            'recipient':    recipient,
            'tx_hash':      result.get('tx_hash'),
            'fee':          result.get('fee', '0'),
            'status':       'completed'
        })

        logger.info(f"✅ Bridge complete: {result.get('tx_hash')}")
        return result

    # ─────────────────────────────────────────────────────────────
    # LENDING (Aave EVM)
    # ─────────────────────────────────────────────────────────────

    async def lend(
        self,
        user_id:  str,
        action:   str,      # 'supply' | 'withdraw' | 'borrow' | 'repay'
        token:    str,
        amount:   Decimal,
        chain:    str = 'ethereum',
        account_index: int = 0
    ) -> Dict[str, Any]:
        """Interact with Aave lending protocol for user."""
        logger.info(f"🏦 WDK Aave {action}: {amount} {token} on {chain}")

        plaintext_seed, _ = await self._get_user_seed(user_id, chain)

        token_addr  = self._get_contract(chain, token)
        decimals    = TOKEN_DECIMALS.get(token.upper(), 6)
        amount_base = _to_base_units(amount, decimals)

        result = await self.wdk.wdk_lend(
            plaintext_seed = plaintext_seed,
            account_index  = account_index,
            action         = action,
            token          = token_addr,
            amount         = amount_base,
            chain          = chain
        )

        await self._log_transaction(user_id, f'aave_{action}', {
            'chain':   chain,
            'token':   token,
            'amount':  float(amount),
            'tx_hash': result.get('tx_hash'),
            'fee':     result.get('fee', '0'),
            'status':  'completed'
        })

        logger.info(f"✅ Aave {action} complete: {result.get('tx_hash')}")
        return result

    # ─────────────────────────────────────────────────────────────
    # FIAT (MoonPay)
    # ─────────────────────────────────────────────────────────────

    async def fiat_quote(
        self,
        user_id:              str,
        currency_code:        str,      # e.g. 'NGN', 'USD'
        crypto_currency:      str,      # e.g. 'USDT'
        base_currency_amount: float,
        chain:                str = 'ethereum',
        account_index:        int = 0
    ) -> Dict[str, Any]:
        """Get MoonPay on-ramp quote."""
        plaintext_seed, _ = await self._get_user_seed(user_id, chain)

        result = await self.wdk.wdk_fiat_quote(
            plaintext_seed       = plaintext_seed,
            account_index        = account_index,
            currency_code        = currency_code,
            crypto_currency      = crypto_currency,
            base_currency_amount = base_currency_amount,
            chain                = chain
        )
        return result

    async def fiat_buy(
        self,
        user_id:              str,
        currency_code:        str,
        crypto_currency:      str,
        base_currency_amount: float,
        chain:                str = 'ethereum',
        account_index:        int = 0
    ) -> Dict[str, Any]:
        """Initiate MoonPay on-ramp purchase. Returns redirect URL."""
        plaintext_seed, _ = await self._get_user_seed(user_id, chain)

        result = await self.wdk.wdk_fiat_buy(
            plaintext_seed       = plaintext_seed,
            account_index        = account_index,
            currency_code        = currency_code,
            crypto_currency      = crypto_currency,
            base_currency_amount = base_currency_amount,
            chain                = chain
        )
        return result

    # ─────────────────────────────────────────────────────────────
    # PRICE RATES (Tether Oracle)
    # ─────────────────────────────────────────────────────────────

    async def get_price_rates(
        self,
        tokens: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch live price rates from Tether WDK price oracle.
        Use as primary price source, fallback to existing oracle.
        """
        try:
            result = await self.wdk.wdk_price_rates(tokens=tokens)
            return result.get('rates', {})
        except Exception as e:
            logger.warning(f"⚠️ WDK price rates failed, caller should fallback: {e}")
            raise