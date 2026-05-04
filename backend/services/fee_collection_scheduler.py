# File: backend/services/fee_collection_scheduler.py
"""
Production‑ready fee collection scheduler.
Runs every 45 minutes (configurable) to collect pending fees from all supported chains.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

from backend.config import settings
from backend.services.database_service import DatabaseService
from backend.services.algorand_service import AlgorandService
from backend.services.seed_encryption_service import SeedEncryptionService
from backend.services.wdk_client import WDKClient

logger = logging.getLogger(__name__)

# Chain → decimals for native asset (used to convert main unit to smallest unit)
NATIVE_DECIMALS: Dict[str, int] = {
    'algorand': 6,
    'bitcoin': 8,
    'ethereum': 18,
    'polygon': 18,
    'tron': 6,
    'solana': 9,
}

class FeeCollectionScheduler:
    """
    Background task that collects pending fees from fees_owed.
    Runs at a fixed interval (default 45 minutes).
    """

    def __init__(self, interval_minutes: int = 45):
        self.interval = interval_minutes * 60
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the scheduler loop."""
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        logger.info(f"✅ Fee collection scheduler started (interval={self.interval//60} min)")

    async def stop(self):
        """Stop the scheduler gracefully."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("✅ Fee collection scheduler stopped")

    async def _run_loop(self):
        """Main loop: collect fees, then sleep."""
        while self.running:
            try:
                await self._collect_all_fees()
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}", exc_info=True)
            await asyncio.sleep(self.interval)

    async def _collect_all_fees(self):
        """Collect pending fees for all chains."""
        # Create fresh service instances each cycle (no shared state)
        db = DatabaseService()
        algorand = AlgorandService(settings)
        wdk = WDKClient()
        seed_enc = SeedEncryptionService()

        # Fetch all pending fees
        result = db.supabase.table('fees_owed')\
            .select('*')\
            .eq('status', 'pending')\
            .execute()
        pending = result.data or []
        logger.info(f"Found {len(pending)} pending fees to collect")

        for fee in pending:
            await self._collect_one_fee(fee, db, algorand, wdk, seed_enc)

    async def _collect_one_fee(self, fee: dict, db, algorand, wdk, seed_enc):
        """Process a single pending fee record – actually transfers the native asset."""
        fee_id = fee['id']
        user_id = fee['user_id']
        chain = fee['chain']
        asset = fee['asset']
        amount_main = Decimal(str(fee['fee_amount']))
        treasury = fee['treasury_address']

        logger.info(f"[DEBUG] Processing fee {fee_id}: chain={chain}, asset={asset}, amount={amount_main}, treasury={treasury}")

        if amount_main <= 0:
            logger.error(f"Fee {fee_id} has non‑positive amount {amount_main} – marking as failed")
            db.supabase.table('fees_owed').update({'status': 'failed'}).eq('id', fee_id).execute()
            return

        from_address, encrypted_seed = await self._get_user_wallet(user_id, chain, db)
        logger.info(f"[DEBUG] User wallet: from_address={from_address}, encrypted_seed present={bool(encrypted_seed)}")
        if not from_address or not encrypted_seed:
            logger.error(f"Cannot retrieve wallet for user {user_id} chain {chain} – skipping fee {fee_id}")
            return

        logger.info(f"Collecting {amount_main} {asset} from {from_address[:8]}... to treasury {treasury[:8]}...")

        try:
            decimals = NATIVE_DECIMALS.get(chain, 6)
            amount_smallest = int(amount_main * (10 ** decimals))
            logger.info(f"[DEBUG] Converted amount to smallest unit: {amount_smallest}")

            if chain == 'algorand':
                private_key = seed_enc.decrypt_seed(encrypted_seed)
                logger.info("[DEBUG] Private key decrypted for Algorand")
                tx_id = await self._transfer_algorand(user_id, from_address, private_key, amount_main, treasury, algorand)
            else:
                logger.info(f"[DEBUG] Calling wdk.send_transaction with asset={asset}, chain={chain}, amount={amount_main}")
                tx_id = await self._transfer_wdk(user_id, from_address, encrypted_seed, amount_main, asset, chain, treasury, wdk, seed_enc)

            logger.info(f"[DEBUG] Transfer successful, tx_id={tx_id}")
            db.supabase.table('fees_owed')\
                .update({
                    'status': 'collected',
                    'collected_tx_id': tx_id,
                    'collected_at': datetime.utcnow().isoformat()
                })\
                .eq('id', fee_id)\
                .execute()
            logger.info(f"✅ Collected fee {fee_id}, tx: {tx_id}")

        except Exception as e:
            logger.error(f"❌ Failed to collect fee {fee_id}: {e}", exc_info=True)

    async def _get_user_wallet(self, user_id: str, chain: str, db):
        """Retrieve user's wallet address and encrypted seed for the given chain."""
        if chain == 'algorand':
            # Algorand wallets are stored in user_wallets table
            result = db.supabase.table('user_wallets')\
                .select('algorand_address, algorand_private_key')\
                .eq('user_id', user_id)\
                .execute()
            if result.data and len(result.data) > 0:
                row = result.data[0]
                return row.get('algorand_address'), row.get('algorand_private_key')
            return None, None
        else:
            # Other chains are in multi_chain_addresses
            result = db.supabase.table('multi_chain_addresses')\
                .select('address, encrypted_seed')\
                .eq('user_id', user_id)\
                .eq('blockchain', chain)\
                .execute()
            if result.data and len(result.data) > 0:
                row = result.data[0]
                return row.get('address'), row.get('encrypted_seed')
            return None, None

    async def _transfer_algorand(self, user_id, from_address, private_key, amount_main, treasury, algorand):
        """Transfer native ALGO using AlgorandService."""
        # algorand.transfer_asset expects amount in main unit (ALGO)
        tx_id = await algorand.transfer_asset(
            sender_private_key=private_key,
            receiver_address=treasury,
            asset_id=0,  # 0 = native ALGO
            amount=amount_main,
            memo="Seamount fee collection"
        )
        return tx_id

    async def _transfer_wdk(self, user_id, from_address, encrypted_seed, amount_main,
                            asset_symbol, chain, treasury, wdk, seed_enc):
        """Transfer native asset using WDKClient's send_transaction."""
        # WDK's send_transaction expects the amount in main unit (e.g., TRX, not sun)
        # and the encrypted seed (it will decrypt internally)
        result = await wdk.send_transaction(
            from_address=from_address,
            to_address=treasury,
            amount=amount_main,
            asset=asset_symbol,        # native asset, e.g., 'TRX', 'BTC'
            chain=chain,
            encrypted_seed=encrypted_seed,
            enable_gasless=False       # fee collection should not use gasless
        )

        if not result.get('success'):
            raise Exception(result.get('error', 'WDK transfer failed'))
        return result['tx_id']