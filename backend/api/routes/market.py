# File: backend/api/routes/market.py
# Bloomberg-Style Live Market Terminal API - PRODUCTION READY (FIXED)

from fastapi import APIRouter, HTTPException, Depends
from backend.services.oracle_service import EnhancedOracleService
from backend.services.database_service import DatabaseService
from backend.dependencies import get_db_service, get_oracle_service
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

# ✅ Router with /market prefix - all routes will be /api/v1/market/...
router = APIRouter(prefix="/market", tags=["Market Terminal"])


@router.get("/snapshot")
async def get_market_snapshot(
    oracle_service: EnhancedOracleService = Depends(get_oracle_service)
):
    """
    📊 GET COMPLETE MARKET SNAPSHOT
    
    Returns Bloomberg-style terminal data:
    - Crypto prices (BTC, ETH, ALGO, TRX)
    - Forex rates (NGN, KES, ZAR, GHS, ETB, EGP vs USD)
    - Commodities (Gold, Silver, Platinum, Palladium, Copper, Nickel, Lithium, Cobalt)
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


@router.get("/forex/{from_currency}/{to_currency}")
async def get_forex_rate(
    from_currency: str,
    to_currency: str,
    oracle_service: EnhancedOracleService = Depends(get_oracle_service)
):
    """
    💱 GET FOREX EXCHANGE RATE
    
    Example: GET /api/v1/market/forex/NGN/USD
    
    Response:
    {
        "success": true,
        "rate": 0.00067,
        "pair": "NGN/USD",
        "metadata": {...}
    }
    """
    try:
        rate, metadata = await oracle_service.get_forex_rate(
            from_currency.upper(),
            to_currency.upper()
        )
        
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


@router.get("/commodity/{symbol}")
async def get_commodity_price(
    symbol: str,
    oracle_service: EnhancedOracleService = Depends(get_oracle_service)
):
    """
    🏆 GET COMMODITY PRICE
    
    Supported: XAU (Gold), XAG (Silver), XPT (Platinum), XPD (Palladium),
               COPP (Copper), NICK (Nickel), ALUM (Aluminum), ZINC (Zinc),
               LITH (Lithium), COBT (Cobalt), MANG (Manganese), GRPH (Graphite),
               TANT (Tantalum)
    
    Example: GET /api/v1/market/commodity/XAU
    
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


# 🚨 FIXED: Removed double /market prefix
@router.get("/commodity/{symbol}/history")  # ✅ WAS: /market/commodity/{symbol}/history
async def get_commodity_history(
    symbol: str,
    hours: int = 24,
    db_service: DatabaseService = Depends(get_db_service),
    oracle_service: EnhancedOracleService = Depends(get_oracle_service)
):
    """
    📈 GET COMMODITY PRICE HISTORY
    
    Returns historical prices for the last 24 hours (default)
    Includes price change % and hourly data for sparkline charts
    
    🚨 FIX: Corrected route path from /market/commodity to /commodity
    """
    try:
        # 🚨 FIX: Construct proper currency pair
        currency_pair = f"{symbol.upper()}/USD"
        
        # ✅ FIX: Make cutoff_time timezone-aware
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # 🚨 FIX: Use db_service.query() instead of execute_query()
        result = await db_service.query(
            table="price_history",
            filters={"currency_pair": currency_pair},
            order_by={"timestamp": "asc"}
        )
        
        # Filter by time (since query() doesn't support WHERE timestamp >)
        result = [
            row for row in result 
            if datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')) > cutoff_time
        ]
        
        if not result or len(result) == 0:
            # 🚨 FALLBACK: Generate mock data if no history exists yet
            logger.warning(f"No historical data for {symbol}, generating mock trend")
            
            current_price, _ = await oracle_service.get_commodity_price(symbol)
            
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
        
        prices = [float(row['rate']) for row in result]
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
        logger.error(f"History fetch failed for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Could not fetch price history: {str(e)}"
        )


@router.get("/cross-rate/{asset}/{currency}")
async def get_cross_rate(
    asset: str,
    currency: str,
    oracle_service: EnhancedOracleService = Depends(get_oracle_service)
):
    """
    🌍 GET CROSS-RATE (Asset in Local Currency)
    
    Example: GET /api/v1/market/cross-rate/bitcoin/NGN
    
    Response:
    {
        "success": true,
        "rate": 95250000,
        "pair": "BTC/NGN",
        "metadata": {...}
    }
    """
    try:
        rate, metadata = await oracle_service.get_cross_rate(
            asset.lower(),
            currency.upper()
        )
        
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


# ✅ SEPARATE ROUTER FOR QUOTA (not under /market)
quota_router = APIRouter(prefix="/quota", tags=["API Quota"])


@quota_router.get("/health")
async def get_quota_health(
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    📊 GET API QUOTA HEALTH STATUS
    
    Returns real-time quota usage for all external APIs
    Useful for monitoring and alerts
    
    Example: GET /api/v1/quota/health
    
    Response:
    {
        "success": true,
        "overall_status": "healthy",
        "summary": {
            "critical": 0,
            "warning": 1,
            "healthy": 5
        },
        "services": {...},
        "timestamp": "2024-12-01T12:00:00Z"
    }
    """
    try:
        from backend.services.quota_service import QuotaService
        
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
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Quota health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not fetch quota status: {str(e)}"
        )