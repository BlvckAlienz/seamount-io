# TEST THIS - Verify Paystack/Flutterwave work
# File: backend/tests/test_payment_providers.py

async def test_payment_providers():
    from backend.services.payment_providers.paystack import PaystackProvider
    from backend.config import get_settings
    from decimal import Decimal
    
    settings = get_settings()
    paystack = PaystackProvider(settings)
    
    # Test payment initialization (use test mode)
    result = await paystack.initialize_payment(
        amount=1000.0,
        currency="NGN",
        email="test@seamount.io",
        tx_ref="TEST_123"
    )
    
    assert result['status'] == 'success', "❌ Paystack initialization failed"
    assert 'payment_link' in result, "❌ No payment link returned"
    
    print(f"✅ Paystack works! Link: {result['payment_link']}")