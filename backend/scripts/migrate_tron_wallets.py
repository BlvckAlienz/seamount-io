#!/usr/bin/env python3
"""
🚨 EMERGENCY: Fix all truncated Tron addresses
Regenerates wallets using corrected WDK client
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from supabase import create_client
from backend.config import get_settings
from backend.services.wdk_client import WDKClient
from backend.services.seed_encryption_service import SeedEncryptionService
from mnemonic import Mnemonic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def migrate_tron_wallets():
    """Regenerate all invalid Tron wallets"""
    
    settings = get_settings()
    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY.get_secret_value()
    )
    
    wdk = WDKClient()
    encryption = SeedEncryptionService()
    mnemo = Mnemonic("english")
    
    # Step 1: Backup
    logger.info("💾 Creating backup table...")
    
    backup_sql = """
    CREATE TABLE IF NOT EXISTS tron_migration_backup_20250119 AS 
    SELECT * FROM multi_chain_addresses WHERE blockchain = 'tron';
    """
    
    try:
        result = supabase.rpc('exec_sql', {'sql': backup_sql}).execute()
        logger.info("✅ Backup created: tron_migration_backup_20250119")
    except Exception as e:
        logger.warning(f"Backup table may exist: {e}")
    
    # Step 2: Get invalid wallets
    logger.info("🔍 Querying invalid Tron wallets...")
    
    result = supabase.table("multi_chain_addresses")\
        .select("*")\
        .eq("blockchain", "tron")\
        .execute()
    
    if not result.data:
        logger.error("❌ No Tron wallets found")
        return
    
    invalid_wallets = [w for w in result.data if len(w.get("address", "")) != 34]
    
    logger.info(f"📊 Total Tron wallets: {len(result.data)}")
    logger.info(f"🚨 Invalid wallets: {len(invalid_wallets)}")
    
    if not invalid_wallets:
        logger.info("✅ All wallets are valid!")
        return
    
    # Step 3: Confirm
    print(f"\n{'='*70}")
    print(f"⚠️  {len(invalid_wallets)} wallets will be regenerated")
    print(f"⚠️  Users will get NEW Tron addresses")
    print(f"⚠️  Old addresses will be saved in backup table")
    print(f"{'='*70}\n")
    
    confirm = input("Type 'MIGRATE' to proceed: ")
    if confirm != "MIGRATE":
        logger.info("❌ Cancelled")
        return
    
    # Step 4: Migrate
    success = 0
    failed = 0
    
    for i, wallet in enumerate(invalid_wallets, 1):
        user_id = wallet["user_id"]
        old_address = wallet["address"]
        
        logger.info(f"🔄 [{i}/{len(invalid_wallets)}] Migrating user {user_id}...")
        
        try:
            # Generate new seed
            new_seed = mnemo.generate(strength=128)
            encrypted_seed = encryption.encrypt_seed(new_seed)
            
            # Create wallet via WDK (with new validation)
            wdk_result = await wdk.create_wallet(
                plaintext_seed=new_seed,
                chains=["tron"],
                enable_gasless=True
            )
            
            new_address = wdk_result["wallets"]["tron"]["address"]
            
            # Double-check (should never fail now)
            if len(new_address) != 34:
                raise Exception(f"Still got bad address: {new_address}")
            
            # Update database
            supabase.table("multi_chain_addresses")\
                .update({
                    "address": new_address,
                    "encrypted_seed": encrypted_seed,
                    "updated_at": "now()"
                })\
                .eq("user_id", user_id)\
                .eq("blockchain", "tron")\
                .execute()
            
            logger.info(f"   ✅ {old_address[:6]}...{old_address[-3:]} → {new_address[:6]}...{new_address[-4:]}")
            success += 1
            
            await asyncio.sleep(0.5)  # Rate limit
            
        except Exception as e:
            logger.error(f"   ❌ Failed: {e}")
            failed += 1
    
    # Summary
    print(f"\n{'='*70}")
    print(f"✅ MIGRATION COMPLETE")
    print(f"{'='*70}")
    print(f"✅ Success: {success}")
    print(f"❌ Failed: {failed}")
    print(f"💾 Backup: tron_migration_backup_20250119")
    print(f"\n📧 NEXT: Email users about address changes")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    asyncio.run(migrate_tron_wallets())