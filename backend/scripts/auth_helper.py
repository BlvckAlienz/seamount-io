# File: scripts/auth_helper.py
"""
Seamount Auth Helper - Generate JWT tokens for API testing
Usage: python scripts/auth_helper.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from supabase import create_client, Client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')  # Use anon key for client-side auth

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================================
# OPTION 1: LOGIN WITH EXISTING USER
# ============================================================================

def login_user(email: str, password: str) -> dict:
    """Login and get JWT token"""
    try:
        print(f"🔐 Authenticating {email}...")
        
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.session:
            print("✅ Authentication successful!")
            print(f"\n📋 USER INFO:")
            print(f"   Email: {response.user.email}")
            print(f"   User ID: {response.user.id}")
            print(f"\n🎟️ ACCESS TOKEN (copy this):")
            print(f"   {response.session.access_token}")
            print(f"\n⏰ Token expires: {response.session.expires_at}")
            
            # Save to file for easy access
            with open('test_token.txt', 'w') as f:
                f.write(response.session.access_token)
            print(f"\n💾 Token saved to: test_token.txt")
            
            return {
                'success': True,
                'access_token': response.session.access_token,
                'refresh_token': response.session.refresh_token,
                'user_id': response.user.id,
                'email': response.user.email
            }
        else:
            print("❌ Authentication failed: No session returned")
            return {'success': False, 'error': 'No session returned'}
            
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return {'success': False, 'error': str(e)}

# ============================================================================
# OPTION 2: CREATE TEST USER
# ============================================================================

def create_test_user(email: str, password: str) -> dict:
    """Create a new test user"""
    try:
        print(f"👤 Creating test user: {email}...")
        
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "firstName": "Test",
                    "lastName": "User",
                    "countryCode": "NG"
                }
            }
        })
        
        if response.user:
            print("✅ User created successfully!")
            print(f"   User ID: {response.user.id}")
            
            if response.session:
                print(f"\n🎟️ ACCESS TOKEN:")
                print(f"   {response.session.access_token}")
                
                with open('test_token.txt', 'w') as f:
                    f.write(response.session.access_token)
                print(f"\n💾 Token saved to: test_token.txt")
                
                return {
                    'success': True,
                    'access_token': response.session.access_token,
                    'user_id': response.user.id
                }
            else:
                print("⚠️ User created but email confirmation may be required")
                print("   Check your email and use login_user() after confirming")
                return {'success': True, 'requires_confirmation': True}
        else:
            print("❌ User creation failed")
            return {'success': False}
            
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return {'success': False, 'error': str(e)}

# ============================================================================
# OPTION 3: QUICK TEST MODE (No Email Confirmation)
# ============================================================================

def create_instant_test_user() -> dict:
    """
    Create test user with auto-confirm (requires Supabase email confirmation disabled)
    Use this for local testing only
    """
    import random
    import string
    
    # Generate random email
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    email = f"test_{random_suffix}@seamount-test.local"
    password = "TestPassword123!"
    
    print(f"🚀 Creating instant test user...")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    
    result = create_test_user(email, password)
    
    if result.get('success'):
        print("\n✅ READY TO TEST!")
        print(f"\nℹ️ Credentials saved for this session:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        
        # Save credentials
        with open('test_credentials.json', 'w') as f:
            json.dump({
                'email': email,
                'password': password,
                'user_id': result.get('user_id')
            }, f, indent=2)
        print(f"   Saved to: test_credentials.json")
    
    return result

# ============================================================================
# CURL COMMAND GENERATOR
# ============================================================================

def generate_curl_commands(token: str, base_url: str = "http://localhost:8000"):
    """Generate ready-to-use curl commands"""
    
    commands = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    SEAMOUNT API TEST COMMANDS                            ║
╚══════════════════════════════════════════════════════════════════════════╝

🎟️ YOUR TOKEN: {token[:30]}...

📋 COPY-PASTE THESE COMMANDS:

1️⃣ TEST AUTHENTICATION
curl {base_url}/api/v1/user/profile \\
  -H "Authorization: Bearer {token}"

2️⃣ TOKENIZE ASSET
curl -X POST {base_url}/api/v1/tokenization/convert-asset \\
  -H "Authorization: Bearer {token}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "custodian_id": "mock-custodian-001",
    "symbol": "DANGCEM",
    "name": "Dangote Cement Plc",
    "quantity": 1000,
    "isin": "NGDANGCEM001",
    "price_per_unit": 450.00
  }}'

3️⃣ LIST MY ASSETS
curl {base_url}/api/v1/tokenization/my-assets \\
  -H "Authorization: Bearer {token}"

4️⃣ VIEW MARKET OFFERS
curl {base_url}/api/v1/tokenization/offers \\
  -H "Authorization: Bearer {token}"

5️⃣ PROTOCOL METRICS
curl {base_url}/api/v1/tokenization/metrics \\
  -H "Authorization: Bearer {token}"

💾 TOKEN SAVED TO: test_token.txt
📝 Use: export TOKEN=$(cat test_token.txt)
   Then: curl -H "Authorization: Bearer $TOKEN" ...
"""
    
    print(commands)
    
    # Save to file
    with open('curl_commands.sh', 'w') as f:
        f.write(f"""#!/bin/bash
# Seamount API Test Commands
# Generated: {os.popen('date').read().strip()}

export TOKEN="{token}"
export BASE_URL="{base_url}"

echo "✅ Token loaded. Use: curl -H \\"Authorization: Bearer $TOKEN\\" ..."
""")
    
    os.chmod('curl_commands.sh', 0o755)
    print("💾 Commands saved to: curl_commands.sh")
    print("   Run: source curl_commands.sh")

# ============================================================================
# INTERACTIVE MENU
# ============================================================================

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║              SEAMOUNT AUTH HELPER - JWT TOKEN GENERATOR                  ║
╚══════════════════════════════════════════════════════════════════════════╝

Choose an option:

1️⃣ Login with existing user
2️⃣ Create new test user (requires email confirmation)
3️⃣ Create instant test user (no email confirmation needed) ⚡ FASTEST
4️⃣ Exit

""")
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == "1":
        email = input("📧 Email: ").strip()
        password = input("🔒 Password: ").strip()
        result = login_user(email, password)
        
        if result.get('success'):
            token = result['access_token']
            print("\n" + "="*80)
            generate_curl_commands(token)
    
    elif choice == "2":
        email = input("📧 Email: ").strip()
        password = input("🔒 Password: ").strip()
        result = create_test_user(email, password)
        
        if result.get('success') and not result.get('requires_confirmation'):
            token = result['access_token']
            print("\n" + "="*80)
            generate_curl_commands(token)
    
    elif choice == "3":
        result = create_instant_test_user()
        
        if result.get('success') and result.get('access_token'):
            token = result['access_token']
            print("\n" + "="*80)
            generate_curl_commands(token)
    
    elif choice == "4":
        print("👋 Goodbye!")
        sys.exit(0)
    
    else:
        print("❌ Invalid choice")
        sys.exit(1)

if __name__ == "__main__":
    main()