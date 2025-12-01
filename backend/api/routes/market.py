# File: backend/api/routes/market.py
# Bloomberg-Style Live Market Terminal API

from fastapi import APIRouter, HTTPException, Depends
from backend.services.oracle_service import EnhancedOracleService
from backend.services.database_service import DatabaseService
from backend.dependencies import get_db_service, get_oracle_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/market/snapshot")
async def get_market_snapshot():
    """
    ðŸ"Š GET COMPLETE MARKET SNAPSHOT
    
    Returns Bloomberg-style terminal data:
    - Crypto prices (BTC, ETH, ALGO, TRX)
    - Forex rates (NGN, KES, ZAR, GHS, ETB, EGP vs USD)
    - Commodities (Gold, Silver, Copper, Nickel, Lithium, Cobalt)
    - Cross-rates (BTC/NGN, ETH/ZAR, etc.)
    
    Response:
    {
        "success": true,
        "data": {
            "crypto": {"bitcoin": 63500, ...},
            "forex": {"NGN/USD": 0.00067, ...},
            "commodities": {"XAU": 2650, ...},
            "cross_rates": {"BTC/NGN": 95250000, ...}
        },
        "timestamp": "2024-11-30T12:00:00Z"
    }
    """
    try:
        oracle_service = get_oracle_service()
        snapshot = await oracle_service.get_market_snapshot()
        
        return {
            "success": True,
            "data": snapshot,
            "timestamp": snapshot['timestamp']
        }
    except Exception as e:
        logger.error(f"Market snapshot fetch failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not fetch market data: {str(e)}"
        )

@router.get("/market/forex/{from_currency}/{to_currency}")
async def get_forex_rate(from_currency: str, to_currency: str):
    """
    💱 GET FOREX EXCHANGE RATE
    
    Example: GET /market/forex/NGN/USD
    
    Response:
    {
        "success": true,
        "rate": 0.00067,
        "pair": "NGN/USD",
        "metadata": {...}
    }
    """
    try:
        oracle_service = get_oracle_service()
        rate, metadata = await oracle_service.get_forex_rate(from_currency.upper(), to_currency.upper())
        
        return {
            "success": True,
            "rate": float(rate),
            "pair": f"{from_currency.upper()}/{to_currency.upper()}",
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"Forex rate fetch failed for {from_currency}/{to_currency}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not fetch forex rate: {str(e)}"
        )

@router.get("/market/commodity/{symbol}")
async def get_commodity_price(symbol: str):
    """
    🏆 GET COMMODITY PRICE
    
    Supported: XAU (Gold), XAG (Silver), COPP (Copper), NICK (Nickel), 
               LITH (Lithium), COBT (Cobalt), MANG (Manganese), GRPH (Graphite)
    
    Example: GET /market/commodity/XAU
    
    Response:
    {
        "success": true,
        "price": 2650.00,
        "symbol": "XAU",
        "unit": "USD per troy ounce",
        "metadata": {...}
    }
    """
    try:
        oracle_service = get_oracle_service()
        price, metadata = await oracle_service.get_commodity_price(symbol.upper())
        
        return {
            "success": True,
            "price": float(price),
            "symbol": symbol.upper(),
            "unit": metadata.get('unit', 'USD'),
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"Commodity price fetch failed for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not fetch commodity price: {str(e)}"
        )

@router.get("/market/cross-rate/{asset}/{currency}")
async def get_cross_rate(asset: str, currency: str):
    """
    🌍 GET CROSS-RATE (Asset in Local Currency)
    
    Example: GET /market/cross-rate/bitcoin/NGN
    
    Response:
    {
        "success": true,
        "rate": 95250000,
        "pair": "BTC/NGN",
        "metadata": {...}
    }
    """
    try:
        oracle_service = get_oracle_service()
        rate, metadata = await oracle_service.get_cross_rate(asset.lower(), currency.upper())
        
        return {
            "success": True,
            "rate": float(rate),
            "pair": f"{asset.upper()}/{currency.upper()}",
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"Cross-rate fetch failed for {asset}/{currency}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not fetch cross-rate: {str(e)}"
        )

@router.get("/commodity/{symbol}/history")
async def get_commodity_history(
    symbol: str,
    hours: int = 24,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Get historical prices for commodity (last 24 hours)
    Returns price change % and hourly data for sparkline
    """
    try:
        # Query price_history table
        query = f"""
            SELECT 
                rate as price,
                timestamp
            FROM price_history
            WHERE currency_pair LIKE '%{symbol}%'
                AND timestamp >= NOW() - INTERVAL '{hours} hours'
            ORDER BY timestamp ASC
        """
        
        result = await db_service.execute_query(query)
        
        if not result or len(result) == 0:
            # 🚨 FALLBACK: Generate mock data if no history exists yet
            logger.warning(f"No historical data for {symbol}, generating mock trend")
            
            # Create realistic price trend (slight variation around current price)
            from backend.services.oracle_service import EnhancedOracleService
            oracle = get_oracle_service()
            current_price, _ = await oracle.get_commodity_price(symbol)
            
            # Generate 24 hourly points with ±2% variation
            import random
            base_price = float(current_price)
            mock_prices = []
            
            for i in range(24):
                variation = random.uniform(-0.02, 0.02)  # ±2%
                mock_prices.append(base_price * (1 + variation))
            
            return {
                "success": True,
                "symbol": symbol,
                "prices": mock_prices,
                "timestamps": [],
                "current_price": base_price,
                "change_24h": mock_prices[-1] - mock_prices[0],
                "change_percent": ((mock_prices[-1] - mock_prices[0]) / mock_prices[0]) * 100,
                "mock_data": True
            }
        
        prices = [float(row['price']) for row in result]
        timestamps = [row['timestamp'] for row in result]
        
        # Calculate 24h change
        first_price = prices[0]
        last_price = prices[-1]
        change_24h = last_price - first_price
        change_percent = (change_24h / first_price) * 100 if first_price > 0 else 0
        
        return {
            "success": True,
            "symbol": symbol,
            "prices": prices,
            "timestamps": timestamps,
            "current_price": last_price,
            "change_24h": round(change_24h, 2),
            "change_percent": round(change_percent, 2),
            "mock_data": False
        }
        
    except Exception as e:
        logger.error(f"History fetch failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/quota/health")
async def get_quota_health():
    """
    📊 GET API QUOTA HEALTH STATUS
    
    Returns real-time quota usage for all external APIs
    Useful for monitoring and alerts
    """
    try:
        from backend.dependencies import get_db_service
        from backend.services.quota_service import QuotaService
        
        db_service = get_db_service()
        quota_service = QuotaService(db_service)
        
        all_quotas = await quota_service.get_all_quotas()
        
        # Calculate overall health
        critical_services = []
        warning_services = []
        healthy_services = []
        
        for service, status in all_quotas.items():
            usage = status.get('usage_percent', 0)
            
            if usage >= 90:
                critical_services.append(service)
            elif usage >= 75:
                warning_services.append(service)
            else:
                healthy_services.append(service)
        
        overall_status = 'healthy'
        if critical_services:
            overall_status = 'critical'
        elif warning_services:
            overall_status = 'warning'
        
        return {
            "success": True,
            "overall_status": overall_status,
            "summary": {
                "critical": len(critical_services),
                "warning": len(warning_services),
                "healthy": len(healthy_services)
            },
            "services": all_quotas,
            "critical_services": critical_services,
            "warning_services": warning_services,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Quota health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))