# File: backend/scripts/collect_fees.py
"""
Fee Collection Script
Collects pending fees from users and sends to treasury

USAGE:
  python backend/scripts/collect_fees.py --chain algorand --dry-run
  python backend/scripts/collect_fees.py --chain all
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.config import get_settings, CENTRAL_TREASURY_ADDRESSES
from backend.services.database_service import DatabaseService
from backend.services.algorand_service import AlgorandService
from backend.services.multi_chain_wallet_service import MultiChainWalletService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def collect_fees_for_chain(chain: str, dry_run: bool = False):
    """
    Collect pending fees for a specific chain
    
    Args:
        chain: 'algorand', 'bitcoin', 'ethereum', 'polygon', or 'tron'
        dry_run: If True, only simulate (don't actually collect)
    """
    
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Collecting fees for {chain}...")
    
    # Initialize services
    settings = get_settings()
    db = DatabaseService()
    
    # Get pending fees for this chain
    result = db.supabase.table('fees_owed')\
        .select('*')\
        .eq('chain', chain)\
        .eq('status', 'pending')\
        .order('created_at')\
        .execute()
    
    if not result.data or len(result.data) == 0:
        logger.info(f"✅ No pending fees for {chain}")
        return
    
    pending_fees = result.data
    logger.info(f"📊 Found {len(pending_fees)} pending fees totaling ${sum(Decimal(str(f['fee_amount'])) for f in pending_fees):.2f}")
    
    # Group by user and asset
    from collections import defaultdict
    fees_by_user = defaultdict(lambda: defaultdict(Decimal))
    
    for fee in pending_fees:
        fees_by_user[fee['user_id']][fee['asset']] += Decimal(str(fee['fee_amount']))
    
    # Collect from each user
    collected_count = 0
    failed_count = 0
    
    for user_id, assets in fees_by_user.items():
        for asset, total_fee in assets.items():
            try:
                logger.info(f"💸 Collecting ${total_fee} {asset} from user {user_id[:8]}...")
                
                if not dry_run:
                    # Get user's wallet credentials
                    wallet = db.supabase.table('user_wallets')\
                        .select('algorand_address, algorand_private_key')\
                        .eq('user_id', user_id)\
                        .execute()
                    
                    if not wallet.data or len(wallet.data) == 0:
                        logger.error(f"❌ No wallet found for user {user_id}")
                        failed_count += 1
                        continue
                    
                    # Decrypt private key
                    from backend.services.seed_encryption_service import SeedEncryptionService
                    encryption_service = SeedEncryptionService()
                    
                    encrypted_key = wallet.data[0]['algorand_private_key']
                    decrypted_key = encryption_service.decrypt_seed(encrypted_key)
                    
                    # Send fee to treasury
                    algorand_service = AlgorandService(settings)
                    treasury_address = CENTRAL_TREASURY_ADDRESSES[chain]
                    
                    # Determine asset ID
                    asset_id = 0 if asset == 'ALGO' else settings.SUPPORTED_ASSETS.get(asset, {}).get('asset_id')
                    
                    tx_id = await algorand_service.transfer_asset(
                        sender_private_key=decrypted_key,
                        receiver_address=treasury_address,
                        asset_id=asset_id,
                        amount=total_fee,
                        memo=f"Fee collection from {user_id[:8]}"
                    )
                    
                    logger.info(f"✅ Collected: {tx_id}")
                    
                    # Update fee records
                    fee_ids = [f['id'] for f in pending_fees if f['user_id'] == user_id and f['asset'] == asset]
                    
                    db.supabase.table('fees_owed')\
                        .update({
                            'status': 'collected',
                            'collected_tx_id': tx_id,
                            'collected_at': datetime.utcnow().isoformat(),
                            'updated_at': datetime.utcnow().isoformat()
                        })\
                        .in_('id', fee_ids)\
                        .execute()
                    
                    collected_count += 1
                else:
                    logger.info(f"[DRY RUN] Would collect ${total_fee} {asset}")
                    collected_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Failed to collect from user {user_id}: {e}")
                failed_count += 1
    
    logger.info(f"📊 Summary: {collected_count} collected, {failed_count} failed")

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect pending platform fees')
    parser.add_argument('--chain', default='all', help='Chain to collect from (all, algorand, bitcoin, etc.)')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without actually collecting')
    
    args = parser.parse_args()
    
    chains = ['algorand', 'bitcoin', 'ethereum', 'polygon', 'tron'] if args.chain == 'all' else [args.chain]
    
    for chain in chains:
        await collect_fees_for_chain(chain, dry_run=args.dry_run)

if __name__ == '__main__':
    asyncio.run(main())