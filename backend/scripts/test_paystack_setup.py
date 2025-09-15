# File Location: backend/scripts/test_paystack_setup.py

import os
import asyncio
import httpx
from decimal import Decimal
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from backend/.env (one level up)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

async def verify_paystack_setup():
    """Quick verification that Paystack is configured correctly"""
    
    print("🔍 SEAMOUNT.IO PAYSTACK SETUP VERIFICATION")
    print("=" * 50)
    
    # Check environment variables
    required_vars = [
        'PAYSTACK_PUBLIC_KEY',
        'PAYSTACK_SECRET_KEY', 
        'PAYSTACK_WEBHOOK_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {value[:10]}...")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    # Test Paystack API connectivity
    print("\n🌐 Testing Paystack API connectivity...")
    
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.paystack.co/bank",
                headers=headers,
                timeout=10.0
            )
            
        if response.status_code == 200:
            banks = response.json()
            print(f"✅ Paystack API connected! Found {len(banks['data'])} banks")
            print(f"   Sample banks: {[b['name'] for b in banks['data'][:3]]}")
        else:
            print(f"❌ Paystack API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Paystack connection failed: {e}")
        return False
    
    print("\n🎯 SETUP STATUS: READY FOR TESTING!")
    return True

if __name__ == "__main__":
    success = asyncio.run(verify_paystack_setup())
    if success:
        print("\n🚀 Run the test payment now!")
    else:
        print("\n🔧 Fix the issues above before testing")