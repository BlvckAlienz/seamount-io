# File: backend/tests/test_revenue_tracking.py
"""
Revenue Tracking Service Tests - FIXED VERSION
Validates fee capture at every transaction point
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

# Import services
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
    # ✅ FIX: Await the fixture
    db = await db_service if hasattr(db_service, '__await__') else db_service
    return RevenueTrackingService(db)

@pytest.mark.asyncio
async def test_track_transaction_fee(revenue_service):
    """Test transaction fee tracking"""
    
    # Get the actual service (not coroutine)
    service = await revenue_service if hasattr(revenue_service, '__await__') else revenue_service
    
    # Track a cross-border fee
    await service.track_transaction_fee(
        user_id="test_user_123",
        transaction_type="cross_border",
        amount=Decimal("1000"),
        fee_rate=Decimal("0.012"),
        platform_fee=Decimal("12"),
        network_fee=Decimal("0.01"),
        blockchain="algorand",
        metadata={"test": True, "timestamp": datetime.utcnow().isoformat()}
    )
    
    # Verify it was logged
    result = await service.db.supabase.table('revenue_events')\
        .select('*')\
        .eq('user_id', 'test_user_123')\
        .order('created_at', desc=True)\
        .limit(1)\
        .execute()
    
    assert len(result.data) > 0, "❌ Revenue event not logged!"
    
    event = result.data[0]
    assert event['revenue_type'] == 'transaction_fee'
    assert float(event['platform_fee']) == 12.0
    assert event['blockchain'] == 'algorand'
    
    print("✅ Transaction fee tracking works!")

@pytest.mark.asyncio
async def test_track_gas_markup(revenue_service):
    """Test hidden gas fee markup tracking"""
    
    service = await revenue_service if hasattr(revenue_service, '__await__') else revenue_service
    
    await service.track_gas_markup(
        user_id="test_user_123",
        blockchain="ethereum",
        gas_charged=Decimal("0.50"),
        gas_actual=Decimal("0.35"),
        markup=Decimal("0.15"),
        transaction_id="TX_TEST_001"
    )
    
    # Verify markup was recorded
    result = await service.db.supabase.table('revenue_events')\
        .select('*')\
        .eq('user_id', 'test_user_123')\
        .eq('revenue_type', 'gas_markup')\
        .order('created_at', desc=True)\
        .limit(1)\
        .execute()
    
    assert len(result.data) > 0, "❌ Gas markup not logged!"
    
    event = result.data[0]
    assert float(event['platform_fee']) == 0.15
    
    print("✅ Gas markup tracking works!")

@pytest.mark.asyncio
async def test_track_fx_spread(revenue_service):
    """Test FX spread revenue tracking"""
    
    service = await revenue_service if hasattr(revenue_service, '__await__') else revenue_service
    
    await service.track_fx_spread(
        user_id="test_user_123",
        from_currency="NGN",
        to_currency="USD",
        amount=Decimal("1000"),
        spread_rate=Decimal("0.004"),
        spread_amount=Decimal("4")
    )
    
    # Verify spread was recorded
    result = await service.db.supabase.table('revenue_events')\
        .select('*')\
        .eq('user_id', 'test_user_123')\
        .eq('revenue_type', 'fx_spread')\
        .order('created_at', desc=True)\
        .limit(1)\
        .execute()
    
    assert len(result.data) > 0, "❌ FX spread not logged!"
    
    event = result.data[0]
    assert float(event['platform_fee']) == 4.0
    
    print("✅ FX spread tracking works!")

@pytest.mark.asyncio
async def test_get_revenue_summary(revenue_service):
    """Test revenue summary aggregation"""
    
    service = await revenue_service if hasattr(revenue_service, '__await__') else revenue_service
    
    # Track multiple fees
    for i in range(5):
        await service.track_transaction_fee(
            user_id=f"test_user_{i}",
            transaction_type="cross_border",
            amount=Decimal("100"),
            fee_rate=Decimal("0.012"),
            platform_fee=Decimal("1.2"),
            network_fee=Decimal("0.01"),
            blockchain="algorand",
            metadata={"batch_test": True}
        )
    
    # Get summary
    summary = await service.get_revenue_summary(days=1)
    
    assert summary['total_revenue'] > 0, "❌ No revenue in summary!"
    assert 'by_type' in summary
    
    print(f"✅ Revenue summary works! Total: ${summary['total_revenue']}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])