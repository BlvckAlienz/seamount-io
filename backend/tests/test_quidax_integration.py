# File: backend/tests/test_quidax_integration.py
"""
Quidax Integration Tests
Tests all Quidax functionality end-to-end
"""

import sys
from pathlib import Path

# Add project root to path (go up 2 levels from tests/ to seamount-io/)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import asyncio
import os
from decimal import Decimal
from unittest.mock import Mock, patch
from backend.services.quidax_service import QuidaxService

# ============================================================================
# TEST DATA
# ============================================================================

MOCK_TICKER_RESPONSE = {
    "ticker": {
        "bid": "1650.50",
        "ask": "1652.00",
        "last": "1651.25",
        "volume": "125000.50"
    }
}

MOCK_ORDER_RESPONSE = {
    "data": {
        "id": "order_12345",
        "payment_url": "https://quidax.com/pay/abc123",
        "status": "pending"
    }
}

# ============================================================================
# TEST CASES
# ============================================================================

class TestQuidaxService:
    """Test Quidax Service functionality"""
    
    def __init__(self):
        self.mock_supabase = Mock()
        self.service = QuidaxService(self.mock_supabase)
        self.results = []
    
    async def test_get_ticker(self):
        """Test getting market ticker"""
        print("🔍 Test: Get Ticker")
        try:
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = MOCK_TICKER_RESPONSE
                mock_get.return_value = mock_response
                
                result = await self.service.get_ticker("usdtngn")
                
                assert result["success"] == True
                assert "bid" in result
                assert "ask" in result
                
                print(f"✅ PASSED - Bid: {result['bid']}, Ask: {result['ask']}")
                self.results.append(("Get Ticker", True))
        except Exception as e:
            print(f"❌ FAILED - {e}")
            self.results.append(("Get Ticker", False))
    
    async def test_get_quote(self):
        """Test getting price quote"""
        print("🔍 Test: Get Quote")
        try:
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = MOCK_TICKER_RESPONSE
                mock_get.return_value = mock_response
                
                # Mock database insert
                self.mock_supabase.table.return_value.insert.return_value.execute.return_value = None
                
                result = await self.service.get_quote(
                    user_id="test_user_123",
                    market="usdtngn",
                    quote_type="buy",
                    amount=10000.0,
                    amount_type="fiat"
                )
                
                assert result["success"] == True
                assert "quote_reference" in result
                assert result["crypto_amount"] > 0
                
                print(f"✅ PASSED - Quote: NGN 10,000 = {result['crypto_amount']:.2f} USDT")
                self.results.append(("Get Quote", True))
        except Exception as e:
            print(f"❌ FAILED - {e}")
            self.results.append(("Get Quote", False))
    
    async def test_create_instant_order(self):
        """Test creating instant order"""
        print("🔍 Test: Create Instant Order")
        try:
            # Mock quote retrieval
            mock_quote_data = {
                "user_id": "test_user_123",
                "market": "usdtngn",
                "quote_type": "buy",
                "crypto_amount": 6.06,
                "fiat_amount": 10000.0,
                "unit_price": 1650.50,
                "quidax_fee": 100.0,
                "total_amount": 10100.0,
                "expires_at": "2025-12-25T12:00:00Z",
                "quote_reference": "quote_abc123",
                "is_used": False
            }
            
            self.mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_quote_data
            
            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = MOCK_ORDER_RESPONSE
                mock_response.raise_for_status = Mock()
                mock_post.return_value = mock_response
                
                # Mock database operations
                self.mock_supabase.table.return_value.insert.return_value.execute.return_value = None
                self.mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = None
                
                result = await self.service.create_instant_order(
                    user_id="test_user_123",
                    quote_reference="quote_abc123"
                )
                
                assert result["success"] == True
                assert "order_id" in result
                assert "payment_url" in result
                
                print(f"✅ PASSED - Order ID: {result['order_id']}")
                self.results.append(("Create Instant Order", True))
        except Exception as e:
            print(f"❌ FAILED - {e}")
            import traceback
            traceback.print_exc()
            self.results.append(("Create Instant Order", False))
    
    async def test_verify_webhook_signature(self):
        """Test webhook signature verification"""
        print("🔍 Test: Webhook Signature Verification")
        try:
            # Mock webhook secret
            self.service.webhook_secret = "test_webhook_secret"
            
            payload = '{"event":"instant_order.done","data":{"id":"order_123"}}'
            timestamp = "1640000000"
            
            # Generate signature
            import hashlib
            import hmac
            signed_payload = f"{timestamp}.{payload}"
            signature = hmac.new(
                self.service.webhook_secret.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            signature_header = f"t={timestamp},v1={signature}"
            
            result = self.service.verify_webhook_signature(payload, signature_header)
            
            assert result == True
            
            print("✅ PASSED - Webhook signature verified")
            self.results.append(("Webhook Signature", True))
        except Exception as e:
            print(f"❌ FAILED - {e}")
            self.results.append(("Webhook Signature", False))
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🧪 Running Quidax Integration Tests\n")
        print("="*60)
        
        await self.test_get_ticker()
        print()
        
        await self.test_get_quote()
        print()
        
        await self.test_create_instant_order()
        print()
        
        await self.test_verify_webhook_signature()
        print()
        
        print("="*60)
        print("📊 SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, result in self.results if result)
        total = len(self.results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print("\n⚠️ SOME TESTS FAILED!")
            print("\nFailed tests:")
            for name, result in self.results:
                if not result:
                    print(f"  ❌ {name}")

# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    tester = TestQuidaxService()
    asyncio.run(tester.run_all_tests())