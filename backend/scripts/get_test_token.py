#!/usr/bin/env python3
"""
Generate test JWT token for API testing
Usage: python backend/scripts/get_test_token.py

TROUBLESHOOTING:
- If supabase import fails: pip install --upgrade supabase
- If .env missing: Copy .env.example to .env
- If Supabase creds invalid: Check Supabase Dashboard
"""

import os
import sys
from pathlib import Path
import uuid

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

print("🔧 Initializing test token generator...")

# ============================================================================
# STEP 1: Check Dependencies
# ============================================================================

def check_dependencies():
    """Verify all required packages are installed"""
    missing = []
    
    try:
        import supabase
        print("✅ supabase package found")
    except ImportError:
        missing.append("supabase")
        print("❌ supabase package missing")
    
    try:
        from backend.config import get_settings
        print("✅ backend.config accessible")
    except ImportError as e:
        print(f"❌ Cannot import backend.config: {e}")
        missing.append("backend.config")
    
    if missing:
        print(f"\n🚨 MISSING DEPENDENCIES: {', '.join(missing)}")
        print("\n📦 FIX:")
        print("pip install --upgrade supabase python-dotenv pydantic-settings")
        sys.exit(1)
    
    return True

# ============================================================================
# STEP 2: Load Configuration
# ============================================================================

def load_config():
    """Load Supabase credentials from environment"""
    try:
        from backend.config import get_settings
        settings = get_settings()
        
        # Validate required settings
        if not settings.SUPABASE_URL:
            raise ValueError("SUPABASE_URL not set in .env")
        if not settings.SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_SERVICE_KEY not set in .env")
        
        print(f"✅ Config loaded - URL: {settings.SUPABASE_URL[:30]}...")
        return settings
        
    except Exception as e:
        print(f"❌ Config error: {e}")
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Check .env file exists in project root")
        print("2. Verify SUPABASE_URL and SUPABASE_SERVICE_KEY are set")
        print("3. Copy values from Supabase Dashboard > Settings > API")
        sys.exit(1)

# ============================================================================
# STEP 3: Create Supabase Client
# ============================================================================

def create_supabase_client(settings):
    """Initialize Supabase client with error handling"""
    try:
        from supabase import create_client, Client
        
        client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY.get_secret_value()
        )
        
        print("✅ Supabase client created")
        return client
        
    except Exception as e:
        print(f"❌ Supabase client error: {e}")
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Verify Supabase project is not paused")
        print("2. Check API keys are correct")
        print("3. Test connection: curl https://YOUR_PROJECT.supabase.co/rest/v1/")
        sys.exit(1)

# ============================================================================
# STEP 4: Generate Test Token
# ============================================================================

def generate_test_token(supabase):
    """Create test user and return JWT token"""
    
    # Generate unique credentials
    test_id = uuid.uuid4().hex[:8]
    test_email = f"test_{test_id}@seamount.io"
    test_password = "TestPassword123!"
    
    print(f"\n🆕 Creating test user: {test_email}")
    
    try:
        # METHOD 1: Admin API (Auto-confirms email)
        print("📝 Attempting admin user creation...")
        
        create_response = supabase.auth.admin.create_user({
            "email": test_email,
            "password": test_password,
            "email_confirm": True,  # Skip email verification
            "user_metadata": {
                "first_name": "Test",
                "last_name": "User",
                "country_code": "NG"
            }
        })
        
        user_id = create_response.user.id
        print(f"✅ Test user created: {user_id}")
        
    except Exception as create_error:
        print(f"⚠️ Admin creation failed: {create_error}")
        print("🔄 Trying standard signup (may require email confirmation)...")
        
        try:
            # METHOD 2: Standard signup (may need email confirmation disabled)
            signup_response = supabase.auth.sign_up({
                "email": test_email,
                "password": test_password,
                "options": {
                    "data": {
                        "first_name": "Test",
                        "last_name": "User",
                        "country_code": "NG"
                    }
                }
            })
            
            user_id = signup_response.user.id
            print(f"✅ Test user registered: {user_id}")
            
        except Exception as signup_error:
            print(f"❌ All creation methods failed")
            print(f"Admin error: {create_error}")
            print(f"Signup error: {signup_error}")
            print("\n🔧 FIX:")
            print("1. Go to Supabase Dashboard > Authentication > Settings")
            print("2. Disable 'Enable email confirmations' for testing")
            print("3. Re-run this script")
            sys.exit(1)
    
    # Sign in to get JWT token
    print(f"\n🔐 Signing in to get JWT token...")
    
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": test_email,
            "password": test_password
        })
        
        if not auth_response.session:
            raise Exception("No session returned - check Supabase auth settings")
        
        token = auth_response.session.access_token
        
        # Success output
        print(f"\n" + "="*70)
        print(f"✅ SUCCESS - TEST TOKEN GENERATED")
        print("="*70)
        print(f"\n📧 Email:    {test_email}")
        print(f"🔑 Password: {test_password}")
        print(f"👤 User ID:  {user_id}")
        print(f"\n🎟️  JWT TOKEN:")
        print("-"*70)
        print(token)
        print("-"*70)
        
        # Export command
        print(f"\n💡 EXPORT FOR TESTING:")
        print(f'export TOKEN="{token}"')
        
        # Windows alternative
        print(f"\n🪟 WINDOWS USERS:")
        print(f'set TOKEN={token}')
        
        # Test commands
        print(f"\n📋 TEST COMMANDS:")
        print(f"\n1️⃣ Health Check:")
        print(f'curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/health')
        
        print(f"\n2️⃣ Create Wallet:")
        print(f'curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" http://localhost:8000/api/v1/wallet/create -d \'{{}}\'')
        
        print(f"\n3️⃣ Tokenization Health:")
        print(f'curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/tokenization/health')
        
        print(f"\n" + "="*70)
        
        return {
            "token": token,
            "user_id": user_id,
            "email": test_email,
            "password": test_password
        }
        
    except Exception as auth_error:
        print(f"❌ Authentication failed: {auth_error}")
        print("\n🔧 POSSIBLE CAUSES:")
        print("1. Email confirmation required (disable in Supabase settings)")
        print("2. Password policy too strict")
        print("3. Auth service not enabled")
        sys.exit(1)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution flow"""
    try:
        # Step 1: Verify dependencies
        check_dependencies()
        
        # Step 2: Load configuration
        settings = load_config()
        
        # Step 3: Create Supabase client
        supabase = create_supabase_client(settings)
        
        # Step 4: Generate token
        result = generate_test_token(supabase)
        
        # Save to file for convenience
        token_file = project_root / ".test_token"
        with open(token_file, "w") as f:
            f.write(f"TOKEN={result['token']}\n")
            f.write(f"USER_ID={result['user_id']}\n")
            f.write(f"EMAIL={result['email']}\n")
            f.write(f"PASSWORD={result['password']}\n")
        
        print(f"\n💾 Token saved to: {token_file}")
        print(f"📖 Load with: source .test_token (Linux/Mac) or type .test_token (Windows)")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())