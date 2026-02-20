# File: backend/services/xrp_monitor_service.py
"""
XRP Deposit Monitor — Real-time WebSocket listener for Seamount hot wallet.
Detects RLUSD/USDC/XRP deposits, credits user via destination tag lookup.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from xrpl.asyncio.clients import AsyncWebsocketClient
from xrpl.models.requests import Subscribe

logger = logging.getLogger(__name__)

MAINNET_WS = "wss://xrplcluster.com"
TESTNET_WS = "wss://s.altnet.rippletest.net:51233"
DROPS_PER_XRP = 1_000_000

ISSUER_TO_SYMBOL_MAINNET = {
    "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De": "RLUSD",
    "rGm7WCVp9gb4jZHWTEtGUr4dd74z2XuWhE": "USDC",
}
ISSUER_TO_SYMBOL_TESTNET = {
    "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh": "RLUSD",
    "rHuGNhqTG32mfmAvWA8hUyWRLV3tCSwKQt": "USDC",
}


class XRPMonitorService:
    def __init__(self, hot_wallet_address: str, settings=None, on_deposit: Optional[Callable] = None):
        from backend.config import get_settings
        self.settings = settings or get_settings()
        self.network = getattr(self.settings, 'XRP_NETWORK', 'mainnet')
        self.ws_url = TESTNET_WS if self.network == 'testnet' else MAINNET_WS
        self.hot_wallet_address = hot_wallet_address
        self.on_deposit = on_deposit
        self._running = False
        self.issuer_map = ISSUER_TO_SYMBOL_TESTNET if self.network == 'testnet' else ISSUER_TO_SYMBOL_MAINNET
        logger.info(f"✅ XRPMonitorService | Watching: {hot_wallet_address[:10]}... [{self.network}]")

    async def start(self):
        self._running = True
        delay = 2
        while self._running:
            try:
                await self._listen()
                delay = 2
            except Exception as e:
                logger.error(f"❌ WS disconnected: {e}. Reconnecting in {delay}s...")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)

    async def stop(self):
        self._running = False

    async def _listen(self):
        async with AsyncWebsocketClient(self.ws_url) as client:
            logger.info(f"🔌 WS connected: {self.ws_url}")
            await client.send(Subscribe(accounts=[self.hot_wallet_address]))
            async for msg in client:
                if not self._running:
                    break
                if msg.get('type') == 'transaction':
                    await self._process(msg)

    async def _process(self, tx_data: Dict[str, Any]):
        try:
            tx = tx_data.get('transaction', {})
            meta = tx_data.get('meta', {})

            if not tx_data.get('validated'):
                return
            if meta.get('TransactionResult') != 'tesSUCCESS':
                return
            if tx.get('TransactionType') != 'Payment':
                return
            if tx.get('Destination') != self.hot_wallet_address:
                return

            destination_tag = tx.get('DestinationTag')
            # ⚠️ CRITICAL: Always use delivered_amount, never Amount field
            delivered = meta.get('delivered_amount', tx.get('Amount'))

            event = None
            if isinstance(delivered, str):
                # XRP payment
                xrp_amount = Decimal(delivered) / DROPS_PER_XRP
                event = {
                    'type': 'XRP', 'symbol': 'XRP', 'amount': str(xrp_amount),
                    'destination_tag': destination_tag, 'from_address': tx.get('Account'),
                    'tx_hash': tx.get('hash'), 'ledger_index': tx_data.get('ledger_index'),
                    'timestamp': datetime.utcnow().isoformat(),
                }
            elif isinstance(delivered, dict):
                issuer = delivered.get('issuer')
                symbol = self.issuer_map.get(issuer)
                if symbol:
                    event = {
                        'type': 'IOU', 'symbol': symbol,
                        'amount': str(Decimal(delivered.get('value', '0'))),
                        'issuer': issuer, 'destination_tag': destination_tag,
                        'from_address': tx.get('Account'), 'tx_hash': tx.get('hash'),
                        'ledger_index': tx_data.get('ledger_index'),
                        'timestamp': datetime.utcnow().isoformat(),
                    }
                else:
                    logger.warning(f"⚠️ Unknown IOU issuer: {issuer}. Not credited.")
                    return

            if event:
                logger.info(f"💰 Deposit: {event['amount']} {event['symbol']} tag={destination_tag}")
                if self.on_deposit:
                    await self.on_deposit(event)

        except Exception as e:
            logger.error(f"❌ _process error: {e}")