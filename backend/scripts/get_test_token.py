#!/usr/bin/env python3
"""
Generate test JWT token for API testing
Usage: python backend/scripts/get_test_token.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from supabase import create_client
from backend.config import get_settings
import uuid

def get_test_token():
    """Register test user and get JWT token"""
    
    settings = get_settings()
    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY.get_secret_value()
    )
    
    # Generate unique test email to avoid conflicts
    test_email = f"test_{uuid.uuid4().hex[:8]}@seamount.io"
    test_password = "TestPassword123!"
    
    print(f"🆕 Creating test user: {test_email}")
    
    try:
        # Use admin API to create user with auto-confirmed email
        create_response = supabase.auth.admin.create_user({
            "email": test_email,
            "password": test_password,
            "email_confirm": True,  # Auto-confirm
            "user_metadata": {
                "first_name": "Test",
                "last_name": "User"
            }
        })
        
        user_id = create_response.user.id
        print(f"✅ Test user created with ID: {user_id}")
        
        # Sign in to get session token
        print(f"🔐 Signing in...")
        auth_response = supabase.auth.sign_in_with_password({
            "email": test_email,
            "password": test_password
        })
        
        if not auth_response.session:
            raise Exception("No session returned - check Supabase auth settings")
        
        token = auth_response.session.access_token
        
        print(f"\n✅ SUCCESS!")
        print(f"📧 Email: {test_email}")
        print(f"🔑 Password: {test_password}")
        print(f"👤 User ID: {user_id}")
        print(f"\n" + "="*60)
        print(f"JWT TOKEN:")
        print(f"="*60)
        print(token)
        print("="*60)
        print(f"\n💡 EXPORT FOR TESTING:")
        print(f'export TOKEN="{token}"')
        print(f"\n📋 TEST COMMANDS:")
        print(f'curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/health')
        print(f'curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" http://localhost:8000/api/v1/wallet/create -d \'{{}}\'')
        
        return token
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"\n🔧 TROUBLESHOOTING:")
        print(f"1. Verify Supabase credentials in .env")
        print(f"2. Check Supabase Dashboard → Authentication → Settings")
        print(f"3. Ensure 'Enable email confirmations' is OFF for testing")
        sys.exit(1)

if __name__ == "__main__":
    get_test_token()