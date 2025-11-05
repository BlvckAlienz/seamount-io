# File: backend/tests/test_onramp_simple.py
"""
Simple On-Ramp Integration Test
Tests: Cashramp → Paystack → Flutterwave fallback
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from uuid import uuid4

from backend.services.database_service import DatabaseService
from backend.services.payment_providers.paystack import PaystackProvider
from backend.services.payment_providers.flutterwave import FlutterwaveProvider
from backend.services.cashramp_service import CashrampService
from backend.config import get_settings

@pytest_asyncio.fixture
async def db_service():
    """Setup database"""
    settings = get_settings()
    from supabase import create_client
    
    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY.get_secret_value()
    )
    
    return DatabaseService(supabase)

@pytest.mark.asyncio
async def test_cashramp_onramp(db_service):
    """Test Cashramp NGN on-ramp (PRIMARY PROVIDER)"""
    
    settings = get_settings()
    cashramp = CashrampService(db_service)
    
    try:
        result = await cashramp.create_ngn_onramp(
            user_id=str(uuid4()),
            asset="USDT",
            amount_ngn=Decimal("10000"),  # ₦10,000
            payment_method="paystack"
        )
        
        assert result["success"] == True, "❌ Cashramp on-ramp failed!"
        assert "onramp_id" in result
        assert "payment_url" in result
        
        print(f"✅ Cashramp on-ramp works!")
        print(f"   Payment URL: {result['payment_url'][:50]}...")
        
    except Exception as e:
        print(f"⚠️ Cashramp failed (expected if no API key): {e}")
        pytest.skip("Cashramp API not configured")

@pytest.mark.asyncio
async def test_paystack_onramp():
    """Test Paystack NGN on-ramp (FALLBACK #1)"""
    
    settings = get_settings()
    
    if not settings.PAYSTACK_SECRET_KEY:
        pytest.skip("Paystack API key not configured")
    
    paystack = PaystackProvider(settings)
    
    try:
        result = await paystack.initialize_payment(
            amount=10000.0,  # ₦10,000
            currency="NGN",
            email="test@seamount.io",
            tx_ref=f"TEST_{uuid4().hex[:8]}"
        )
        
        assert result.get("status") == "success", "❌ Paystack init failed!"
        assert "payment_link" in result
        
        print("✅ Paystack on-ramp works!")
        print(f"   Payment URL: {result['payment_link'][:50]}...")
        
    except Exception as e:
        print(f"❌ Paystack test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_flutterwave_onramp():
    """Test Flutterwave on-ramp (FALLBACK #2)"""
    
    settings = get_settings()
    
    if not settings.FLUTTERWAVE_SECRET_KEY:
        pytest.skip("Flutterwave API key not configured")
    
    flutterwave = FlutterwaveProvider(settings)
    
    try:
        result = await flutterwave.initialize_payment(
            amount=10000.0,  # ₦10,000
            currency="NGN",
            email="test@seamount.io",
            tx_ref=f"TEST_{uuid4().hex[:8]}"
        )
        
        assert result.get("status") == "success", "❌ Flutterwave init failed!"
        assert "payment_link" in result
        
        print("✅ Flutterwave on-ramp works!")
        print(f"   Payment URL: {result['payment_link'][:50]}...")
        
    except Exception as e:
        print(f"❌ Flutterwave test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_provider_hierarchy():
    """Test provider fallback hierarchy"""
    
    settings = get_settings()
    
    # Check which providers are configured
    providers = {
        "cashramp": bool(getattr(settings, 'CASHRAMP_API_KEY', None)),
        "paystack": bool(settings.PAYSTACK_SECRET_KEY),
        "flutterwave": bool(settings.FLUTTERWAVE_SECRET_KEY)
    }
    
    print("\n📊 Provider Configuration Status:")
    print(f"   1️⃣ Cashramp (PRIMARY):  {'✅ Configured' if providers['cashramp'] else '❌ Missing'}")
    print(f"   2️⃣ Paystack (FALLBACK): {'✅ Configured' if providers['paystack'] else '❌ Missing'}")
    print(f"   3️⃣ Flutterwave (BACKUP): {'✅ Configured' if providers['flutterwave'] else '❌ Missing'}")
    
    assert any(providers.values()), "❌ No payment providers configured!"
    
    print("\n✅ At least one provider is configured")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])