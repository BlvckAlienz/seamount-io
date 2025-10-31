# File: backend/scripts/diagnose_seed_issue.py
# FIXED: Works when run from backend/ directory

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography.fernet import Fernet
import base64
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_multi_chain_seeds(supabase, cipher, data):
    """Check seeds in multi_chain_addresses table"""
    print(f"\n🔍 Checking {len(data)} multi-chain wallets...\n")
    
    for wallet in data:
        user_id = wallet['user_id']
        encrypted = wallet.get('encrypted_seed')
        
        if not encrypted:
            print(f"⚠️  User {user_id}: No seed stored")
            continue
        
        print(f"User {user_id}:")
        print(f"  Encrypted length: {len(encrypted)}")
        print(f"  First 20 chars: {encrypted[:20]}...")
        
        # Test base64 and decryption (same logic as before)
        try:
            base64.b64decode(encrypted)
            print(f"  ✅ Valid base64 encoding")
        except Exception as e:
            print(f"  ❌ Invalid base64: {e}")
        
        try:
            decrypted_bytes = cipher.decrypt(base64.b64decode(encrypted))
            plaintext = decrypted_bytes.decode('utf-8')
            word_count = len(plaintext.split())
            print(f"  ✅ Decryption works! ({word_count} words)")
        except Exception as e:
            print(f"  ❌ Decryption failed: {type(e).__name__}: {str(e)[:50]}")
        
        print()

def diagnose_seeds():
    """Check seed encryption status"""
    
    # Initialize Supabase directly (no dependencies.py)
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    encryption_key = os.getenv('ENCRYPTION_KEY')
    
    if not all([supabase_url, supabase_key, encryption_key]):
        print("❌ Missing environment variables!")
        print(f"   SUPABASE_URL: {'✓' if supabase_url else '✗'}")
        print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✓' if supabase_key else '✗'}")
        print(f"   ENCRYPTION_KEY: {'✓' if encryption_key else '✗'}")
        return
    
    supabase = create_client(supabase_url, supabase_key)
    cipher = Fernet(encryption_key.encode())
    
    # Check BOTH tables
    print("🔍 Checking database tables...\n")
    
    all_seeds = []
    
    # 1. Check user_wallets (Algorand)
    try:
        result = supabase.table('user_wallets')\
            .select('user_id, algorand_address, algorand_mnemonic')\
            .execute()
        
        print(f"✓ user_wallets: {len(result.data)} rows")
        
        if result.data:
            for wallet in result.data:
                if wallet.get('algorand_mnemonic'):
                    all_seeds.append({
                        'user_id': wallet['user_id'],
                        'address': wallet.get('algorand_address', 'N/A'),
                        'encrypted_seed': wallet['algorand_mnemonic'],
                        'source': 'user_wallets',
                        'chain': 'algorand'
                    })
    except Exception as e:
        print(f"✗ user_wallets error: {e}")
    
    # 2. Check multi_chain_addresses (WDK chains)
    try:
        result = supabase.table('multi_chain_addresses')\
            .select('user_id, blockchain, address, encrypted_seed')\
            .execute()
        
        print(f"✓ multi_chain_addresses: {len(result.data)} rows\n")
        
        if result.data:
            for wallet in result.data:
                if wallet.get('encrypted_seed'):
                    all_seeds.append({
                        'user_id': wallet['user_id'],
                        'address': wallet.get('address', 'N/A'),
                        'encrypted_seed': wallet['encrypted_seed'],
                        'source': 'multi_chain_addresses',
                        'chain': wallet.get('blockchain', 'unknown')
                    })
    except Exception as e:
        print(f"✗ multi_chain_addresses error: {e}\n")
    
    if not all_seeds:
        print("❌ No encrypted seeds found in any table!")
        return
    
    print(f"📊 Total seeds to check: {len(all_seeds)}\n")
    print("="*60 + "\n")
    
    check_all_seeds(cipher, all_seeds)
    
    print(f"\n🔍 Checking {len(result.data)} wallets...\n")
    
    for user in result.data:
        user_id = user['user_id']
        encrypted = user.get('algorand_mnemonic')
        
        if not encrypted:
            print(f"⚠️  User {user_id}: No seed stored")
            continue
        
        print(f"User {user_id}:")
        print(f"  Encrypted length: {len(encrypted)}")
        print(f"  First 20 chars: {encrypted[:20]}...")
        
        # Test 1: Is it valid base64?
        try:
            base64.b64decode(encrypted)
            print(f"  ✅ Valid base64 encoding")
        except Exception as e:
            print(f"  ❌ Invalid base64: {e}")
            
            # Try adding padding
            missing = len(encrypted) % 4
            if missing:
                padded = encrypted + '=' * (4 - missing)
                try:
                    base64.b64decode(padded)
                    print(f"  ⚠️  Needs {4-missing} padding characters")
                except:
                    print(f"  ❌ Still invalid after padding")
        
        # Test 2: Can it be decrypted?
        try:
            decrypted_bytes = cipher.decrypt(base64.b64decode(encrypted))
            plaintext = decrypted_bytes.decode('utf-8')
            word_count = len(plaintext.split())
            print(f"  ✅ Decryption works! ({word_count} words)")
            
            if word_count == 25:
                print(f"  ✅ Valid 25-word Algorand mnemonic")
            else:
                print(f"  ⚠️  Unexpected word count: {word_count}")
                
        except Exception as e:
            print(f"  ❌ Decryption failed: {type(e).__name__}: {str(e)[:50]}")
        
        print()

if __name__ == "__main__":
    diagnose_seeds()