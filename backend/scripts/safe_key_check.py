# backend/scripts/safe_key_check.py
import os
import sys

# Add the project root to Python path safely
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

def safe_check():
    print("🔍 SAFE KEY CHECK - READ ONLY")
    print("=" * 50)
    
    # 1. Check environment variables (without revealing full values)
    print("\n1. ENVIRONMENT VARIABLES:")
    env_keys = ['ENCRYPTION_KEY', 'SEED_ENCRYPTION_KEY']
    for key in env_keys:
        value = os.getenv(key)
        if value:
            print(f"   ✅ {key}: EXISTS (length: {len(value)})")
            print(f"      Preview: {value[:10]}...{value[-10:]}")
        else:
            print(f"   ❌ {key}: NOT SET")
    
    # 2. Try to import config safely
    print("\n2. CONFIG CHECK:")
    try:
        from backend.config import get_settings
        settings = get_settings()
        
        config_keys = ['SEED_ENCRYPTION_KEY', 'ENCRYPTION_KEY']
        for key_name in config_keys:
            if hasattr(settings, key_name):
                key_value = getattr(settings, key_name)
                if hasattr(key_value, 'get_secret_value'):
                    secret = key_value.get_secret_value()
                    print(f"   ✅ {key_name}: EXISTS in config (length: {len(secret)})")
                    print(f"      Preview: {secret[:10]}...{secret[-10:]}")
                else:
                    print(f"   ⚠️  {key_name}: EXISTS but no get_secret_value method")
            else:
                print(f"   ❌ {key_name}: NOT in config")
                
    except Exception as e:
        print(f"   ❌ Config import failed: {e}")
    
    # 3. Check database encryption status
    print("\n3. DATABASE ENCRYPTION STATUS:")
    try:
        from supabase import create_client
        from backend.config import get_settings
        
        settings = get_settings()
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY.get_secret_value()
        )
        
        # Check if we have encrypted data
        result = supabase.table("multi_chain_addresses")\
            .select("blockchain, encrypted_seed")\
            .limit(3)\
            .execute()
            
        if result.data:
            print(f"   ✅ Found {len(result.data)} encrypted records")
            for row in result.data:
                blockchain = row.get('blockchain', 'unknown')
                encrypted = row.get('encrypted_seed', '')
                print(f"      {blockchain}: encrypted length = {len(encrypted)}")
        else:
            print("   ⚠️  No encrypted data found in multi_chain_addresses")
            
    except Exception as e:
        print(f"   ❌ Database check failed: {e}")
    
    print("\n" + "=" * 50)
    print("✅ SAFE CHECK COMPLETE - NO CHANGES MADE")

if __name__ == "__main__":
    safe_check()