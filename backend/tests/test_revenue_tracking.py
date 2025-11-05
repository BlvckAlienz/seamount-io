# File: backend/tests/test_revenue_tracking.py
"""
Revenue Tracking Service Tests - SCHEMA FIXED
Uses correct Supabase auth.users schema (no username column)
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime, UTC
from uuid import uuid4

from backend.services.revenue_tracking_service import RevenueTrackingService
from backend.services.database_service import DatabaseService
from backend.config import get_settings

@pytest_asyncio.fixture
async def db_service():
    """Create database service for testing"""
    settings = get_settings()
    from supabase import create_client
    
    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY.get_secret_value()
    )
    
    return DatabaseService(supabase)

@pytest_asyncio.fixture
async def revenue_service(db_service):
    """Create revenue tracking service"""
    return RevenueTrackingService(db_service)

@pytest_asyncio.fixture
async def test_user(db_service):
    """Use existing test user from database"""
    # Use the test user you already created
    test_user_id = "6e5f1aff-39b1-4201-87aa-c00ff243460f"
    
    yield test_user_id
    
    # Cleanup: Delete revenue events for this user
    try:
        db_service.supabase.table('revenue_events').delete().eq('user_id', test_user_id).execute()
    except Exception as e:
        print(f"Cleanup warning: {e}")

@pytest.mark.asyncio
async def test_track_transaction_fee(revenue_service, test_user):
    """Test transaction fee tracking"""
    
    # Track a cross-border fee
    await revenue_service.track_transaction_fee(
        user_id=test_user,
        transaction_type="cross_border",
        amount=Decimal("1000"),
        fee_rate=Decimal("0.018"),
        platform_fee=Decimal("18"),
        network_fee=Decimal("0.01"),
        blockchain="algorand",
        metadata={"test": True, "timestamp": datetime.now(UTC).isoformat()}
    )
    
    # Verify it was logged
    result = revenue_service.db.supabase.table('revenue_events')\
        .select('*')\
        .eq('user_id', test_user)\
        .order('created_at', desc=True)\
        .limit(1)\
        .execute()
    
    assert len(result.data) > 0, "❌ Revenue event not logged!"
    
    event = result.data[0]
    assert event['revenue_type'] == 'transaction_fee'
    assert float(event['platform_fee']) == 18.0
    assert event['blockchain'] == 'algorand'
    
    print("✅ Transaction fee tracking works!")

@pytest.mark.asyncio
async def test_track_gas_markup(revenue_service, test_user):
    """Test hidden gas fee markup tracking"""
    
    await revenue_service.track_gas_markup(
        user_id=test_user,
        blockchain="ethereum",
        gas_charged=Decimal("0.50"),
        gas_actual=Decimal("0.35"),
        markup=Decimal("0.15"),
        transaction_id=f"TX_{uuid4().hex[:8].upper()}"
    )
    
    result = revenue_service.db.supabase.table('revenue_events')\
        .select('*')\
        .eq('user_id', test_user)\
        .eq('revenue_type', 'gas_markup')\
        .order('created_at', desc=True)\
        .limit(1)\
        .execute()
    
    assert len(result.data) > 0, "❌ Gas markup not logged!"
    
    event = result.data[0]
    assert float(event['platform_fee']) == 0.15
    
    print("✅ Gas markup tracking works!")

@pytest.mark.asyncio
async def test_track_fx_spread(revenue_service, test_user):
    """Test FX spread revenue tracking"""
    
    await revenue_service.track_fx_spread(
        user_id=test_user,
        from_currency="NGN",
        to_currency="USD",
        amount=Decimal("1000"),
        spread_rate=Decimal("0.004"),
        spread_amount=Decimal("4")
    )
    
    result = revenue_service.db.supabase.table('revenue_events')\
        .select('*')\
        .eq('user_id', test_user)\
        .eq('revenue_type', 'fx_spread')\
        .order('created_at', desc=True)\
        .limit(1)\
        .execute()
    
    assert len(result.data) > 0, "❌ FX spread not logged!"
    
    event = result.data[0]
    assert float(event['platform_fee']) == 4.0
    
    print("✅ FX spread tracking works!")

@pytest.mark.asyncio
async def test_get_revenue_summary(revenue_service, test_user):
    """Test revenue summary aggregation"""
    
    # Track multiple fees using the existing test user
    for i in range(5):
        await revenue_service.track_transaction_fee(
            user_id=test_user,
            transaction_type="cross_border",
            amount=Decimal("100"),
            fee_rate=Decimal("0.018"),
            platform_fee=Decimal("1.8"),
            network_fee=Decimal("0.01"),
            blockchain="algorand",
            metadata={"batch_test": True, "iteration": i}
        )
    
    # Get summary
    summary = await revenue_service.get_revenue_summary(days=1)
    
    assert summary['total_revenue'] > 0, "❌ No revenue in summary!"
    assert 'by_type' in summary
    
    print(f"✅ Revenue summary works! Total: ${summary['total_revenue']}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])