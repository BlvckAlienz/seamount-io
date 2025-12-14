# File: scripts/simple_auth.py
"""
Seamount Auth Helper - Zero dependencies
Works with Python 3.6+ standard library only
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

# Load .env manually
def load_env():
    env_file = Path('.env')
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

load_env()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Missing credentials in .env")
    print("   Required: SUPABASE_URL and SUPABASE_ANON_KEY")
    exit(1)

def login(email, password):
    """Login and get JWT token"""
    
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    
    data = json.dumps({
        "email": email,
        "password": password
    }).encode('utf-8')
    
    headers = {
        'apikey': SUPABASE_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"🔐 Authenticating {email}...")
        
        req = urllib.request.Request(url, data=data, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            token = result.get('access_token')
            user = result.get('user', {})
            
            if token:
                print("✅ Authentication successful!\n")
                print(f"👤 User ID: {user.get('id', 'N/A')}")
                print(f"📧 Email: {user.get('email', 'N/A')}")
                print(f"\n🎟️ ACCESS TOKEN (first 50 chars):")
                print(f"   {token[:50]}...")
                
                # Save to file
                Path('test_token.txt').write_text(token)
                print(f"\n💾 Token saved to: test_token.txt")
                
                # Generate test commands
                print("\n" + "="*80)
                print("📋 READY-TO-USE TEST COMMANDS:")
                print("="*80)
                print("\n# Load token")
                print("export TOKEN=$(cat test_token.txt)\n")
                print("# Test authentication")
                print('curl http://localhost:8000/api/v1/user/profile \\')
                print('  -H "Authorization: Bearer $TOKEN"\n')
                print("# Tokenize asset")
                print('curl -X POST http://localhost:8000/api/v1/tokenization/convert-asset \\')
                print('  -H "Authorization: Bearer $TOKEN" \\')
                print('  -H "Content-Type: application/json" \\')
                print("  -d '{")
                print('    "custodian_id": "mock-custodian-001",')
                print('    "symbol": "DANGCEM",')
                print('    "name": "Dangote Cement Plc",')
                print('    "quantity": 1000,')
                print('    "price_per_unit": 450.00')
                print("  }'\n")
                
                return token
            else:
                print("❌ No token in response")
                print(f"Response: {result}")
                return None
    
    except urllib.error.HTTPError as e:
        print(f"\n❌ Authentication failed: {e.code} {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            error_data = json.loads(error_body)
            print(f"Error: {error_data.get('error_description', error_data)}")
        except:
            print(f"Error details: {e.read().decode('utf-8')}")
        return None
    except urllib.error.URLError as e:
        print(f"\n❌ Connection error: {e.reason}")
        print("   Check your SUPABASE_URL in .env")
        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return None

def create_user(email, password):
    """Create new user (signup)"""
    
    url = f"{SUPABASE_URL}/auth/v1/signup"
    
    data = json.dumps({
        "email": email,
        "password": password,
        "data": {
            "firstName": "Test",
            "lastName": "User"
        }
    }).encode('utf-8')
    
    headers = {
        'apikey': SUPABASE_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"👤 Creating user {email}...")
        
        req = urllib.request.Request(url, data=data, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            user = result.get('user', {})
            token = result.get('access_token')
            
            if user:
                print(f"✅ User created: {user.get('id')}")
                
                if token:
                    print("✅ Auto-logged in!")
                    Path('test_token.txt').write_text(token)
                    print(f"💾 Token saved to: test_token.txt")
                    return token
                else:
                    print("⚠️ Email confirmation may be required")
                    print("   Check your email, then use login option")
                    return None
            else:
                print("❌ User creation failed")
                print(f"Response: {result}")
                return None
    
    except urllib.error.HTTPError as e:
        print(f"\n❌ Signup failed: {e.code} {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            error_data = json.loads(error_body)
            print(f"Error: {error_data.get('msg', error_data)}")
        except:
            print(f"Error details: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║         SEAMOUNT AUTH HELPER - ZERO DEPENDENCIES VERSION                ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝\n")
    
    print("Choose an option:\n")
    print("1️⃣ Login with existing user")
    print("2️⃣ Create new user (signup)")
    print("3️⃣ Exit\n")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        email = input("\n📧 Email: ").strip()
        password = input("🔒 Password: ").strip()
        token = login(email, password)
        
        if token:
            print("\n✅ READY TO TEST TOKENIZATION API!")
    
    elif choice == "2":
        email = input("\n📧 Email: ").strip()
        password = input("🔒 Password (min 6 chars): ").strip()
        
        if len(password) < 6:
            print("❌ Password must be at least 6 characters")
            exit(1)
        
        token = create_user(email, password)
        
        if token:
            print("\n✅ READY TO TEST TOKENIZATION API!")
    
    elif choice == "3":
        print("👋 Goodbye!")
    
    else:
        print("❌ Invalid choice")