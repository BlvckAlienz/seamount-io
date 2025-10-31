# File: backend/scripts/nuke_seed_issue.py
# 🔥 NUCLEAR DIAGNOSTIC + FIX SCRIPT

import os
import sys
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def get_supabase_client():
    """Get Supabase client with SERVICE ROLE KEY (bypasses RLS)"""
    from supabase import create_client
    
    url = os.getenv('SUPABASE_URL')
    # 🚨 MUST use SERVICE_ROLE_KEY to bypass RLS
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not service_key:
        print("❌ CRITICAL: SUPABASE_SERVICE_ROLE_KEY not found in .env")
        print("   This key is REQUIRED to bypass Row Level Security")
        sys.exit(1)
    
    print(f"✅ Using service role key (length: {len(service_key)})")
    return create_client(url, service_key)

def check_table(supabase, table_name, columns):
    """Check if table exists and return row count"""
    try:
        result = supabase.table(table_name).select(columns).execute()
        return len(result.data), result.data
    except Exception as e:
        return 0, f"ERROR: {str(e)}"

def diagnose_and_fix():
    print("=" * 70)
    print("🔥 NUCLEAR SEED DIAGNOSTIC + FIX")
    print("=" * 70)
    
    # Initialize
    supabase = get_supabase_client()
    encryption_key = os.getenv('ENCRYPTION_KEY')
    
    if not encryption_key:
        print("❌ ENCRYPTION_KEY not found in .env")
        sys.exit(1)
    
    cipher = Fernet(encryption_key.encode())
    print(f"✅ Encryption key loaded (length: {len(encryption_key)})\n")
    
    # 📍 STEP 1: Check user_wallets (Algorand)
    print("=" * 70)
    print("📊 CHECKING user_wallets TABLE (Algorand)")
    print("=" * 70)
    
    algo_count, algo_data = check_table(
        supabase, 
        'user_wallets', 
        'user_id, algorand_address, algorand_mnemonic'
    )
    
    if isinstance(algo_data, str):  # Error
        print(f"❌ {algo_data}\n")
        algo_wallets = []
    else:
        print(f"✅ Found {algo_count} Algorand wallets\n")
        algo_wallets = [w for w in algo_data if w.get('algorand_mnemonic')]
        print(f"   {len(algo_wallets)} have encrypted seeds\n")
    
    # 📍 STEP 2: Check multi_chain_addresses (WDK)
    print("=" * 70)
    print("📊 CHECKING multi_chain_addresses TABLE (WDK Chains)")
    print("=" * 70)
    
    wdk_count, wdk_data = check_table(
        supabase,
        'multi_chain_addresses',
        'user_id, blockchain, address, encrypted_seed'
    )
    
    if isinstance(wdk_data, str):  # Error
        print(f"❌ {wdk_data}\n")
        wdk_wallets = []
    else:
        print(f"✅ Found {wdk_count} WDK wallets\n")
        wdk_wallets = [w for w in wdk_data if w.get('encrypted_seed')]
        print(f"   {len(wdk_wallets)} have encrypted seeds\n")
    
    if not algo_wallets and not wdk_wallets:
        print("❌ NO ENCRYPTED SEEDS FOUND IN ANY TABLE!")
        print("\n🔍 POSSIBLE CAUSES:")
        print("   1. RLS is blocking queries (check Supabase RLS policies)")
        print("   2. Seeds are stored in different columns")
        print("   3. Database is actually empty")
        return
    
    # 📍 STEP 3: Test decryption
    print("=" * 70)
    print("🔓 TESTING DECRYPTION")
    print("=" * 70)
    
    issues = []
    fixed = []
    
    # Test Algorand seeds
    for wallet in algo_wallets:
        user_id = wallet['user_id']
        encrypted = wallet['algorand_mnemonic']
        
        print(f"\n👤 User: {user_id}")
        print(f"   Chain: Algorand")
        print(f"   Address: {wallet.get('algorand_address', 'N/A')}")
        print(f"   Encrypted length: {len(encrypted)}")
        
        try:
            # Try decryption
            decrypted = decrypt_seed(cipher, encrypted)
            word_count = len(decrypted.split())
            print(f"   ✅ DECRYPTION SUCCESS ({word_count} words)")
            
            if word_count != 25:
                print(f"   ⚠️  WARNING: Expected 25 words, got {word_count}")
                issues.append({
                    'user_id': user_id,
                    'chain': 'algorand',
                    'issue': f'Wrong word count: {word_count}'
                })
            
        except Exception as e:
            print(f"   ❌ DECRYPTION FAILED: {e}")
            issues.append({
                'user_id': user_id,
                'chain': 'algorand',
                'issue': str(e),
                'encrypted': encrypted
            })
    
    # Test WDK seeds
    for wallet in wdk_wallets:
        user_id = wallet['user_id']
        blockchain = wallet['blockchain']
        encrypted = wallet['encrypted_seed']
        
        print(f"\n👤 User: {user_id}")
        print(f"   Chain: {blockchain}")
        print(f"   Address: {wallet.get('address', 'N/A')}")
        print(f"   Encrypted length: {len(encrypted)}")
        
        try:
            decrypted = decrypt_seed(cipher, encrypted)
            word_count = len(decrypted.split())
            print(f"   ✅ DECRYPTION SUCCESS ({word_count} words)")
            
            if word_count != 12:
                print(f"   ⚠️  WARNING: Expected 12 words, got {word_count}")
                issues.append({
                    'user_id': user_id,
                    'chain': blockchain,
                    'issue': f'Wrong word count: {word_count}'
                })
                
        except Exception as e:
            print(f"   ❌ DECRYPTION FAILED: {e}")
            issues.append({
                'user_id': user_id,
                'chain': blockchain,
                'issue': str(e),
                'encrypted': encrypted
            })
    
    # 📍 STEP 4: Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    total_wallets = len(algo_wallets) + len(wdk_wallets)
    failed_wallets = len(issues)
    
    print(f"Total wallets checked: {total_wallets}")
    print(f"Failed decryption: {failed_wallets}")
    print(f"Success rate: {((total_wallets - failed_wallets) / total_wallets * 100):.1f}%")
    
    if issues:
        print("\n❌ ISSUES FOUND:")
        for issue in issues:
            print(f"   • User {issue['user_id']} ({issue['chain']}): {issue['issue']}")
        
        print("\n🔧 WANT TO AUTO-FIX? (y/n): ", end='')
        response = input().strip().lower()
        
        if response == 'y':
            fix_broken_seeds(supabase, cipher, issues)
    else:
        print("\n✅ ALL SEEDS DECRYPT SUCCESSFULLY!")
        print("   The issue is NOT with seed encryption.")
        print("   Check your seed_retrieval_service.py logic.")

def decrypt_seed(cipher, encrypted_seed):
    """Decrypt with aggressive error handling"""
    # Strip whitespace
    encrypted_seed = encrypted_seed.strip()
    
    # Fix padding
    missing = len(encrypted_seed) % 4
    if missing:
        encrypted_seed += '=' * (4 - missing)
    
    # Decode and decrypt
    encrypted_bytes = base64.b64decode(encrypted_seed)
    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    return decrypted_bytes.decode('utf-8')

def fix_broken_seeds(supabase, cipher, issues):
    """Attempt to re-encrypt broken seeds"""
    print("\n" + "=" * 70)
    print("🔧 ATTEMPTING AUTO-FIX")
    print("=" * 70)
    
    for issue in issues:
        if 'encrypted' not in issue:
            print(f"❌ Cannot fix {issue['user_id']}: No encrypted data")
            continue
        
        try:
            # Try to decrypt with aggressive padding
            old_encrypted = issue['encrypted']
            plaintext = decrypt_seed(cipher, old_encrypted)
            
            # Re-encrypt properly
            encrypted_bytes = cipher.encrypt(plaintext.encode())
            new_encrypted = base64.b64encode(encrypted_bytes).decode('utf-8')
            
            # Update database
            if issue['chain'] == 'algorand':
                supabase.table('user_wallets')\
                    .update({'algorand_mnemonic': new_encrypted})\
                    .eq('user_id', issue['user_id'])\
                    .execute()
            else:
                supabase.table('multi_chain_addresses')\
                    .update({'encrypted_seed': new_encrypted})\
                    .eq('user_id', issue['user_id'])\
                    .eq('blockchain', issue['chain'])\
                    .execute()
            
            print(f"✅ Fixed {issue['user_id']} ({issue['chain']})")
            
        except Exception as e:
            print(f"❌ Failed to fix {issue['user_id']}: {e}")

if __name__ == "__main__":
    diagnose_and_fix()