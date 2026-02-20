# File: backend/services/xrp_defi_service.py
"""
XRP DeFi Service — AMM yield farming for Seamount.io
Operates from DeFi wallet. User positions tracked proportionally in Supabase.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from xrpl.asyncio.clients import AsyncJsonRpcClient
from xrpl.asyncio.transaction import submit_and_wait
from xrpl.wallet import Wallet
from xrpl.models.transactions import AMMDeposit, AMMWithdraw
from xrpl.models.requests import AMMInfo
from xrpl.models.amounts import IssuedCurrencyAmount

logger = logging.getLogger(__name__)

MAINNET_RPC = "https://s1.ripple.com:51234"
TESTNET_RPC = "https://s.altnet.rippletest.net:51234"
DROPS_PER_XRP = 1_000_000
MAX_RETRIES = 3
RETRY_DELAY = 2


class XRPDeFiService:
    def __init__(self, xrp_service, settings=None):
        from backend.config import get_settings
        self.settings = settings or get_settings()
        self.xrp_svc = xrp_service
        self.network = getattr(self.settings, 'XRP_NETWORK', 'mainnet')
        self.rpc_url = TESTNET_RPC if self.network == 'testnet' else MAINNET_RPC

        _seed = getattr(self.settings, 'XRP_DEFI_WALLET_SEED', None)
        self._defi_seed = _seed.get_secret_value() if hasattr(_seed, 'get_secret_value') else _seed
        self.defi_address = getattr(self.settings, 'XRP_DEFI_WALLET_ADDRESS', None)
        logger.info(f"✅ XRPDeFiService [{self.network}]")

    def _iou(self, symbol: str, amount: Decimal) -> IssuedCurrencyAmount:
        return IssuedCurrencyAmount(
            currency=self.xrp_svc.get_currency_code(symbol),
            issuer=self.xrp_svc.get_issuer(symbol),
            value=str(amount),
        )

    async def get_pool_info(self, symbol: str = 'RLUSD') -> Optional[Dict]:
        try:
            async with AsyncJsonRpcClient(self.rpc_url) as client:
                response = await client.request(AMMInfo(
                    asset={"currency": "XRP"},
                    asset2={
                        "currency": self.xrp_svc.get_currency_code(symbol),
                        "issuer": self.xrp_svc.get_issuer(symbol),
                    },
                ))
                if response.status.value == 'success':
                    return response.result.get('amm')
                return None
        except Exception as e:
            logger.error(f"❌ get_pool_info({symbol}): {e}")
            return None

    async def deposit_to_pool(self, symbol: str, token_amount: Decimal, xrp_amount: Decimal) -> Dict[str, Any]:
        """Two-asset deposit into AMM pool (RLUSD/XRP or USDC/XRP)."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with AsyncJsonRpcClient(self.rpc_url) as client:
                    defi_wallet = Wallet.from_seed(self._defi_seed)
                    tx = AMMDeposit(
                        account=defi_wallet.classic_address,
                        asset={"currency": "XRP"},
                        asset2={
                            "currency": self.xrp_svc.get_currency_code(symbol),
                            "issuer": self.xrp_svc.get_issuer(symbol),
                        },
                        amount=str(int(xrp_amount * DROPS_PER_XRP)),
                        amount2=self._iou(symbol, token_amount),
                        flags=0x00100000,  # tfTwoAsset
                    )
                    response = await submit_and_wait(tx, client, defi_wallet)
                    tx_result = response.result.get('meta', {}).get('TransactionResult')
                    if tx_result == 'tesSUCCESS':
                        logger.info(f"✅ AMM deposit: {xrp_amount} XRP + {token_amount} {symbol}")
                        return {
                            'success': True, 'tx_hash': response.result['hash'],
                            'symbol': symbol, 'xrp_deposited': str(xrp_amount),
                            'token_deposited': str(token_amount),
                        }
                    raise Exception(f"AMM deposit failed: {tx_result}")
            except Exception as e:
                if attempt == MAX_RETRIES:
                    raise
                await asyncio.sleep(RETRY_DELAY * attempt)

    async def withdraw_from_pool(self, symbol: str, lp_token_amount: str) -> Dict[str, Any]:
        """Withdraw from AMM by redeeming LP tokens."""
        pool = await self.get_pool_info(symbol)
        if not pool:
            raise Exception(f"Pool {symbol}/XRP not found")
        amm_account = pool.get('account')
        lp_currency = pool.get('lp_token', {}).get('currency')

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with AsyncJsonRpcClient(self.rpc_url) as client:
                    defi_wallet = Wallet.from_seed(self._defi_seed)
                    tx = AMMWithdraw(
                        account=defi_wallet.classic_address,
                        asset={"currency": "XRP"},
                        asset2={
                            "currency": self.xrp_svc.get_currency_code(symbol),
                            "issuer": self.xrp_svc.get_issuer(symbol),
                        },
                        lp_token_in=IssuedCurrencyAmount(
                            currency=lp_currency, issuer=amm_account, value=lp_token_amount
                        ),
                        flags=0x00010000,  # tfLPToken
                    )
                    response = await submit_and_wait(tx, client, defi_wallet)
                    tx_result = response.result.get('meta', {}).get('TransactionResult')
                    if tx_result == 'tesSUCCESS':
                        return {'success': True, 'tx_hash': response.result['hash']}
                    raise Exception(f"AMM withdrawal failed: {tx_result}")
            except Exception as e:
                if attempt == MAX_RETRIES:
                    raise
                await asyncio.sleep(RETRY_DELAY * attempt)