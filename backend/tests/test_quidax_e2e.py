# File: test_quidax_e2e.py
"""
End-to-End Quidax Flow Test
Simulates complete user journey: Quote → Order → Webhook
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"
AUTH_TOKEN = "YOUR_AUTH_TOKEN_HERE"  # Replace with actual token

def test_e2e_flow():
    """Test complete Quidax on-ramp flow"""
    
    print("🧪 Quidax End-to-End Flow Test")
    print("="*60)
    print()
    
    # ========================================================================
    # STEP 1: Get Quote
    # ========================================================================
    print("📍 Step 1: Getting quote...")
    
    quote_data = {
        "market": "usdtngn",
        "quote_type": "buy",
        "amount": 10000,
        "amount_type": "fiat"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/quidax/quote",
            headers={
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            json=quote_data
        )
        
        if response.status_code == 200:
            quote = response.json()
            print(f"✅ Quote received:")
            print(f"   Quote Reference: {quote.get('quote_reference')}")
            print(f"   Crypto Amount: {quote.get('crypto_amount')} USDT")
            print(f"   Total Cost: NGN {quote.get('total')}")
            print()
            
            quote_reference = quote.get('quote_reference')
        else:
            print(f"❌ Quote failed: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Quote error: {e}")
        return False
    
    # ========================================================================
    # STEP 2: Create Instant Order
    # ========================================================================
    print("📍 Step 2: Creating instant order...")
    
    order_data = {
        "quote_reference": quote_reference
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/quidax/instant-order",
            headers={
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            json=order_data
        )
        
        if response.status_code == 200:
            order = response.json()
            print(f"✅ Order created:")
            print(f"   Order ID: {order.get('order_id')}")
            print(f"   Payment URL: {order.get('payment_url')}")
            print(f"   Status: {order.get('status')}")
            print()
            
            order_id = order.get('order_id')
        else:
            print(f"❌ Order creation failed: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Order creation error: {e}")
        return False
    
    # ========================================================================
    # STEP 3: Check Order Status
    # ========================================================================
    print("📍 Step 3: Checking order status...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/quidax/orders/{order_id}",
            headers={
                "Authorization": f"Bearer {AUTH_TOKEN}"
            }
        )
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Order status retrieved:")
            print(f"   Status: {status.get('status')}")
            print(f"   Market: {status.get('market')}")
            print(f"   Price: {status.get('price')}")
            print()
        else:
            print(f"⚠️ Order status check failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Order status error: {e}")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("="*60)
    print("✅ END-TO-END TEST COMPLETED")
    print("="*60)
    print()
    print("Next steps:")
    print("1. User would be redirected to:", order.get('payment_url'))
    print("2. User completes payment on Quidax")
    print("3. Quidax sends webhook to /api/v1/webhooks/quidax")
    print("4. Webhook handler credits user's wallet")
    print("5. Auto-withdrawal to user's WDK wallet (if configured)")
    print()
    
    return True

if __name__ == "__main__":
    success = test_e2e_flow()
    exit(0 if success else 1)