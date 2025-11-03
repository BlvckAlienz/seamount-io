# TEST THIS - Verify oracle returns real prices
# File: backend/tests/test_oracle.py

async def test_oracle_accuracy():
    from backend.services.oracle_service import EnhancedOracleService
    
    oracle = EnhancedOracleService(db_service)
    
    # Test Bitcoin price
    btc_price, metadata = await oracle.get_asset_price('bitcoin')
    
    assert btc_price > 20000, f"❌ BTC price too low: ${btc_price}"
    assert metadata['confidence'] > 0.8, "❌ Low confidence oracle data"
    
    print(f"✅ BTC Price: ${btc_price} from {metadata['source']}")