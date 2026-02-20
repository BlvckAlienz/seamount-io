# File: backend/services/xrp_service.py
"""
XRP Ledger Core Service — Seamount.io Custodial Engine
Manages: trust lines, deposits detection, withdrawals, stablecoin registry.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from xrpl.asyncio.clients import AsyncJsonRpcClient
from xrpl.asyncio.transaction import submit_and_wait
from xrpl.wallet import Wallet
from xrpl.models.transactions import Payment, TrustSet
from xrpl.models.requests import AccountInfo, AccountLines
from xrpl.models.amounts import IssuedCurrencyAmount

logger = logging.getLogger(__name__)

MAINNET_RPC = "https://s1.ripple.com:51234"
TESTNET_RPC = "https://s.altnet.rippletest.net:51234"
DROPS_PER_XRP = 1_000_000
MAX_RETRIES = 3
RETRY_DELAY = 2

STABLECOIN_REGISTRY = {
    "RLUSD": {
        "mainnet_issuer": "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De",
        "testnet_issuer": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
        "currency_code": "524C555344000000000000000000000000000000",
    },
    "USDC": {
        "mainnet_issuer": "rGm7WCVp9gb4jZHWTEtGUr4dd74z2XuWhE",
        "testnet_issuer": "rHuGNhqTG32mfmAvWA8hUyWRLV3tCSwKQt",
        "currency_code": "5553444300000000000000000000000000000000",
    },
}


class XRPService:
    def __init__(self, settings=None):
        from backend.config import get_settings
        self.settings = settings or get_settings()
        self.network = getattr(self.settings, 'XRP_NETWORK', 'mainnet')
        self.rpc_url = TESTNET_RPC if self.network == 'testnet' else MAINNET_RPC

        _seed = getattr(self.settings, 'XRP_HOT_WALLET_SEED', None)
        self._hot_wallet_seed = _seed.get_secret_value() if hasattr(_seed, 'get_secret_value') else _seed
        self.hot_wallet_address = getattr(self.settings, 'XRP_HOT_WALLET_ADDRESS', None)

        logger.info(f"✅ XRPService [{self.network}] | Hot: {self.hot_wallet_address}")

    def get_issuer(self, symbol: str) -> str:
        cfg = STABLECOIN_REGISTRY.get(symbol.upper())
        if not cfg:
            raise ValueError(f"Unknown stablecoin: {symbol}")
        return cfg['mainnet_issuer'] if self.network == 'mainnet' else cfg['testnet_issuer']

    def get_currency_code(self, symbol: str) -> str:
        return STABLECOIN_REGISTRY[symbol.upper()]['currency_code']

    async def setup_hot_wallet_trust_lines(self) -> Dict[str, Any]:
        """
        🚨 Run ONCE after hot wallet is funded with XRP.
        Sets RLUSD + USDC trust lines. Required before any deposits can be received.
        """
        results = {}
        async with AsyncJsonRpcClient(self.rpc_url) as client:
            hot_wallet = Wallet.from_seed(self._hot_wallet_seed)
            for symbol in ['RLUSD', 'USDC']:
                try:
                    tx = TrustSet(
                        account=hot_wallet.classic_address,
                        limit_amount=IssuedCurrencyAmount(
                            currency=self.get_currency_code(symbol),
                            issuer=self.get_issuer(symbol),
                            value="1000000000",
                        ),
                    )
                    response = await submit_and_wait(tx, client, hot_wallet)
                    tx_result = response.result.get('meta', {}).get('TransactionResult')
                    results[symbol] = {
                        'success': tx_result == 'tesSUCCESS',
                        'tx_hash': response.result.get('hash'),
                    }
                    logger.info(f"✅ Trust line set: {symbol} | {tx_result}")
                except Exception as e:
                    logger.error(f"❌ Trust line failed for {symbol}: {e}")
                    results[symbol] = {'success': False, 'error': str(e)}
        return results

    async def get_hot_wallet_balances(self) -> Dict[str, Decimal]:
        """Get XRP + stablecoin balances of Seamount hot wallet."""
        balances = {'XRP': Decimal('0'), 'RLUSD': Decimal('0'), 'USDC': Decimal('0')}
        try:
            async with AsyncJsonRpcClient(self.rpc_url) as client:
                info_resp = await client.request(AccountInfo(
                    account=self.hot_wallet_address, ledger_index="validated"
                ))
                if info_resp.status.value == 'success':
                    drops = int(info_resp.result['account_data']['Balance'])
                    balances['XRP'] = Decimal(drops) / DROPS_PER_XRP

                lines_resp = await client.request(AccountLines(account=self.hot_wallet_address))
                if lines_resp.status.value == 'success':
                    for line in lines_resp.result.get('lines', []):
                        for symbol in ['RLUSD', 'USDC']:
                            if line.get('account') == self.get_issuer(symbol):
                                balances[symbol] = Decimal(line.get('balance', '0'))
        except Exception as e:
            logger.error(f"❌ get_hot_wallet_balances: {e}")
        return balances

    async def send_stablecoin(
        self,
        symbol: str,
        destination: str,
        amount: Decimal,
        destination_tag: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send RLUSD or USDC from hot wallet (user withdrawal)."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with AsyncJsonRpcClient(self.rpc_url) as client:
                    hot_wallet = Wallet.from_seed(self._hot_wallet_seed)
                    payment = Payment(
                        account=hot_wallet.classic_address,
                        destination=destination,
                        destination_tag=destination_tag,
                        amount=IssuedCurrencyAmount(
                            currency=self.get_currency_code(symbol),
                            issuer=self.get_issuer(symbol),
                            value=str(amount),
                        ),
                    )
                    response = await submit_and_wait(payment, client, hot_wallet)
                    tx_result = response.result.get('meta', {}).get('TransactionResult')

                    if tx_result == 'tesSUCCESS':
                        # ⚠️ Always check delivered_amount — not Amount
                        meta = response.result.get('meta', {})
                        delivered = meta.get('delivered_amount', {})
                        delivered_amount = (
                            Decimal(delivered.get('value', str(amount)))
                            if isinstance(delivered, dict) else Decimal(str(amount))
                        )
                        logger.info(f"✅ Withdrawal: {delivered_amount} {symbol} → {destination[:10]}...")
                        return {
                            'success': True,
                            'tx_hash': response.result['hash'],
                            'symbol': symbol,
                            'amount_requested': str(amount),
                            'amount_delivered': str(delivered_amount),
                            'destination': destination,
                        }
                    raise Exception(f"Payment failed: {tx_result}")

            except Exception as e:
                logger.warning(f"⚠️ send_stablecoin attempt {attempt}/{MAX_RETRIES}: {e}")
                if attempt == MAX_RETRIES:
                    logger.error(f"❌ send_stablecoin permanently failed: {symbol} {amount} → {destination}")
                    raise
                await asyncio.sleep(RETRY_DELAY * attempt)

    async def send_xrp(self, destination: str, amount_xrp: Decimal, destination_tag: Optional[int] = None) -> Dict[str, Any]:
        """Send XRP from hot wallet."""
        drops = str(int(amount_xrp * DROPS_PER_XRP))
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with AsyncJsonRpcClient(self.rpc_url) as client:
                    hot_wallet = Wallet.from_seed(self._hot_wallet_seed)
                    payment = Payment(
                        account=hot_wallet.classic_address,
                        amount=drops,
                        destination=destination,
                        destination_tag=destination_tag,
                    )
                    response = await submit_and_wait(payment, client, hot_wallet)
                    tx_result = response.result.get('meta', {}).get('TransactionResult')
                    if tx_result == 'tesSUCCESS':
                        return {'success': True, 'tx_hash': response.result['hash']}
                    raise Exception(f"XRP payment failed: {tx_result}")
            except Exception as e:
                if attempt == MAX_RETRIES:
                    raise
                await asyncio.sleep(RETRY_DELAY * attempt)