# File: backend/scripts/fix_seed_encryption.py
# ⚠️ ONE-TIME FIX: Re-encrypt seeds with proper base64 encoding

import asyncio
from cryptography.fernet import Fernet
import base64
import os

from backend.services.database_service import DatabaseService
from backend.dependencies import get_supabase_client

async def fix_all_seeds():
    """Re-encrypt all seeds with proper formatting"""
    
    supabase = get_supabase_client()
    db = DatabaseService(supabase)
    
    # Get encryption key
    encryption_key = os.getenv('ENCRYPTION_KEY')
    cipher = Fernet(encryption_key.encode())
    
    # Get all users with wallets
    users = supabase.table('user_wallets')\
        .select('user_id, algorand_mnemonic')\
        .execute()
    
    for user in users.data:
        try:
            user_id = user['user_id']
            old_encrypted = user['algorand_mnemonic']
            
            if not old_encrypted:
                continue
            
            # Try to decrypt with old format
            try:
                # Add padding if needed
                missing = len(old_encrypted) % 4
                if missing:
                    old_encrypted += '=' * (4 - missing)
                
                decrypted_bytes = cipher.decrypt(base64.b64decode(old_encrypted))
                plaintext = decrypted_bytes.decode('utf-8')
                
                # Re-encrypt properly
                encrypted_bytes = cipher.encrypt(plaintext.encode())
                new_encrypted = base64.b64encode(encrypted_bytes).decode('utf-8')
                
                # Update database
                supabase.table('user_wallets')\
                    .update({'algorand_mnemonic': new_encrypted})\
                    .eq('user_id', user_id)\
                    .execute()
                
                print(f"✅ Fixed seed for user {user_id}")
                
            except Exception as e:
                print(f"❌ Failed to fix seed for user {user_id}: {e}")
                
        except Exception as e:
            print(f"❌ Error processing user: {e}")

if __name__ == "__main__":
    asyncio.run(fix_all_seeds())