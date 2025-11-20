# File: backend/services/oracle_service.py - ENHANCED 3-TIER ORACLE SYSTEM

import asyncio
import aiohttp
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import deque
import json

from backend.config import settings
from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

@dataclass
class PriceData:
    currency_pair: str
    rate: Decimal
    source: str
    timestamp: datetime
    confidence: float
    volume_24h: Optional[Decimal] = None
    
    def to_dict(self):
        data = asdict(self)
        data['rate'] = str(self.rate)
        data['timestamp'] = self.timestamp.isoformat()
        if self.volume_24h:
            data['volume_24h'] = str(self.volume_24h)
        return data

class EnhancedOracleService:
    """
    3-Tier Oracle System for Real-Time Price Data
    Tier 1: Binance API (highest volume, free)
    Tier 2: CoinGecko Pro (professional grade)
    Tier 3: DIA Oracle (Algorand-native)
    """
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.rate_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 30  # 30 seconds cache
        self.request_timeout = 5  # 5 second timeout per request
        
        # Asset mapping for different APIs
        self.asset_mapping = {
            'binance': {
                'bitcoin': 'BTCUSDT',
                'ethereum': 'ETHUSDT', 
                'algorand': 'ALGOUSDT',
                'tether': 'USDCUSDT',  # Proxy for USDT rate
                'matic': 'MATICUSDT',
                'tron': 'TRXUSDT',
                'solana': 'SOLUSDT',
                'ton': 'TONUSDT'
            },
            'coingecko': {
                'bitcoin': 'bitcoin',
                'ethereum': 'ethereum',
                'algorand': 'algorand',
                'tether': 'tether',
                'matic': 'matic-network',
                'tron': 'tron',
                'solana': 'solana',
                'ton': 'the-open-network'
            },
            'dia': {
                'bitcoin': 'BTC',
                'ethereum': 'ETH', 
                'algorand': 'ALGO',
                'tether': 'USDT',
                'matic': 'MATIC',
                'tron': 'TRX',
                'solana': 'SOL',
                'ton': 'TON'
            }
        }
        
        logger.info("Enhanced 3-Tier Oracle Service initialized")
    
    async def get_asset_price(self, asset_name: str) -> Tuple[Decimal, Dict]:
        """
        Main method to get asset price with 3-tier fallback
        Returns: (price, metadata)
        """
        currency_pair = f"{asset_name.upper()}/USD"
        
        # Check cache first
        cached = self.rate_cache.get(currency_pair)
        if cached and (datetime.now() - cached['timestamp']) < timedelta(seconds=self.cache_ttl):
            logger.debug(f"Returning cached price for {currency_pair}")
            return cached['price'], cached['metadata']
        
        # Try 3-tier fallback system
        price_data = await self._fetch_with_fallback(asset_name)
        
        if not price_data:
            # Use stale cache if available
            if cached:
                logger.warning(f"All oracles failed, using stale cache for {currency_pair}")
                return cached['price'], {**cached['metadata'], 'stale': True}
            
            # Final fallback to hardcoded rates
            fallback_price = self._get_emergency_fallback(asset_name)
            if fallback_price:
                return fallback_price, {
                    'source': 'emergency_fallback',
                    'timestamp': datetime.now().isoformat(),
                    'confidence': 0.5,
                    'warning': 'All oracles failed, using emergency fallback'
                }
            
            raise ValueError(f"Could not fetch price for {currency_pair} - all sources failed")
        
        # Store in cache
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'source': price_data.source,
            'confidence': price_data.confidence,
            'volume_24h': str(price_data.volume_24h) if price_data.volume_24h else None
        }
        
        self.rate_cache[currency_pair] = {
            'price': price_data.rate,
            'metadata': metadata,
            'timestamp': datetime.now()
        }
        
        # Store in database asynchronously - FIXED: use asyncio.create_task with proper error handling
        asyncio.create_task(self._store_price_data_safe([price_data]))
        
        return price_data.rate, metadata
    
    # ✅ FIXED: Add missing get_algorand_price method
    async def get_algorand_price(self) -> Decimal:
        """
        Get Algorand price specifically - for backward compatibility
        """
        price, _ = await self.get_asset_price('algorand')
        return price
    
    # ✅ FIXED: Add method for getting price without metadata
    async def get_price_simple(self, asset_name: str) -> Decimal:
        """
        Simple method to get price without metadata
        """
        price, _ = await self.get_asset_price(asset_name)
        return price
    
    async def _store_price_data_safe(self, price_data: List[PriceData]):
        """Wrapper for safe async price data storage with error handling"""
        try:
            await self.store_price_data(price_data)
        except Exception as e:
            logger.error(f"Background task: Failed to store price data: {str(e)}", exc_info=True)
    
    async def _fetch_with_fallback(self, asset_name: str) -> Optional[PriceData]:
        """Execute 3-tier fallback strategy"""
        
        # Tier 1: Binance (Highest volume, most reliable)
        logger.debug(f"Trying Tier 1: Binance for {asset_name}")
        binance_data = await self._fetch_from_binance(asset_name)
        if binance_data:
            binance_data.confidence = 0.95  # Highest confidence
            return binance_data
        
        # Tier 2: CoinGecko Pro (Professional API)
        logger.debug(f"Tier 1 failed, trying Tier 2: CoinGecko for {asset_name}")
        coingecko_data = await self._fetch_from_coingecko(asset_name)
        if coingecko_data:
            coingecko_data.confidence = 0.90
            return coingecko_data
        
        # Tier 3: DIA Oracle (Algorand-native, great for ecosystem integration)
        logger.debug(f"Tier 2 failed, trying Tier 3: DIA for {asset_name}")
        dia_data = await self._fetch_from_dia(asset_name)
        if dia_data:
            dia_data.confidence = 0.85
            return dia_data
        
        logger.error(f"All 3 oracle tiers failed for {asset_name}")
        return None
    
    async def _fetch_from_binance(self, asset_name: str) -> Optional[PriceData]:
        """Tier 1: Binance API (Free, 1200 requests/min)"""
        try:
            symbol = self.asset_mapping['binance'].get(asset_name.lower())
            if not symbol:
                return None
            
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.request_timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = Decimal(str(data['lastPrice']))
                        volume = Decimal(str(data['volume']))
                        
                        return PriceData(
                            currency_pair=f"{asset_name.upper()}/USD",
                            rate=price,
                            source='binance',
                            timestamp=datetime.now(),
                            confidence=0.95,
                            volume_24h=volume
                        )
                        
        except Exception as e:
            logger.warning(f"Binance API failed for {asset_name}: {e}")
        
        return None
    
    async def _fetch_from_coingecko(self, asset_name: str) -> Optional[PriceData]:
        """Tier 2: CoinGecko Pro API"""
        try:
            asset_id = self.asset_mapping['coingecko'].get(asset_name.lower())
            if not asset_id:
                return None
            
            # Use Pro API if key available, otherwise free API
            if hasattr(settings, 'COINGECKO_API_KEY') and settings.COINGECKO_API_KEY:
                api_key = settings.COINGECKO_API_KEY.get_secret_value()
                url = f"https://pro-api.coingecko.com/api/v3/simple/price?ids={asset_id}&vs_currencies=usd&include_24hr_vol=true"
                headers = {"X-Cg-Pro-Api-Key": api_key}
            else:
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={asset_id}&vs_currencies=usd&include_24hr_vol=true"
                headers = {}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=self.request_timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        asset_data = data[asset_id]
                        price = Decimal(str(asset_data['usd']))
                        volume = Decimal(str(asset_data.get('usd_24h_vol', 0)))
                        
                        return PriceData(
                            currency_pair=f"{asset_name.upper()}/USD",
                            rate=price,
                            source='coingecko',
                            timestamp=datetime.now(),
                            confidence=0.90,
                            volume_24h=volume
                        )
                        
        except Exception as e:
            logger.warning(f"CoinGecko API failed for {asset_name}: {e}")
        
        return None
    
    async def _fetch_from_dia(self, asset_name: str) -> Optional[PriceData]:
        """Tier 3: DIA Oracle (Algorand ecosystem integration)"""
        try:
            symbol = self.asset_mapping['dia'].get(asset_name.lower())
            if not symbol:
                return None
            
            # DIA API endpoint for asset prices
            url = f"https://api.diadata.org/v1/quotation/{symbol}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.request_timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = Decimal(str(data['Price']))
                        
                        return PriceData(
                            currency_pair=f"{asset_name.upper()}/USD", 
                            rate=price,
                            source='dia_oracle',
                            timestamp=datetime.now(),
                            confidence=0.85,
                            volume_24h=None
                        )
                        
        except Exception as e:
            logger.warning(f"DIA Oracle failed for {asset_name}: {e}")
        
        return None
    
    def _get_emergency_fallback(self, asset_name: str) -> Optional[Decimal]:
        """Emergency fallback rates when all oracles fail"""
        emergency_rates = {
            'bitcoin': Decimal("63500.00"),
            'ethereum': Decimal("2650.00"),
            'algorand': Decimal("0.18"),
            'tether': Decimal("1.00"),
            'matic': Decimal("0.75"),
            'tron': Decimal("0.12"),
            'solana': Decimal("150.00"),
            'ton': Decimal("2.50")
        }
        
        rate = emergency_rates.get(asset_name.lower())
        if rate:
            logger.critical(f"Using emergency fallback rate for {asset_name}: ${rate}")
        
        return rate
    
    async def get_ngn_usd_rate(self) -> Tuple[Decimal, Dict]:
        """Get NGN/USD exchange rate for fiat conversions"""
        try:
            # Use multiple sources for NGN/USD rate
            sources = [
                "https://api.exchangerate-api.com/v4/latest/USD",  # Free API
                "https://api.fixer.io/latest?base=USD&symbols=NGN"  # Backup
            ]
            
            for url in sources:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=5) as response:
                            if response.status == 200:
                                data = await response.json()
                                if 'rates' in data and 'NGN' in data['rates']:
                                    ngn_rate = Decimal(str(data['rates']['NGN']))
                                    return ngn_rate, {
                                        'source': 'exchange_rate_api',
                                        'timestamp': datetime.now().isoformat(),
                                        'confidence': 0.90
                                    }
                except Exception as e:
                    logger.warning(f"NGN rate source failed: {e}")
                    continue
            
            # Fallback to recent average
            fallback_rate = Decimal("1450.00")  # Recent NGN/USD rate
            return fallback_rate, {
                'source': 'fallback',
                'timestamp': datetime.now().isoformat(),
                'confidence': 0.70,
                'warning': 'Using fallback NGN/USD rate'
            }
            
        except Exception as e:
            logger.error(f"Failed to get NGN/USD rate: {e}")
            raise ValueError("Could not determine NGN/USD exchange rate")
    
    async def store_price_data(self, price_data: List[PriceData]):
        """Store price data in database for analytics - FIXED: proper async/await handling"""
        try:
            if not price_data:
                logger.warning("[Oracle] No price data to store")
                return
            
            records = []
            for pd in price_data:
                records.append({
                    "currency_pair": pd.currency_pair,
                    "rate": float(pd.rate),
                    "source": pd.source,
                    "confidence": pd.confidence,
                    "volume_24h": float(pd.volume_24h) if pd.volume_24h else None,
                    "timestamp": pd.timestamp.isoformat()
                })
            
            for record in records:
                result = await self.db_service.log_event("price_history", record)
                if result:
                    logger.debug(f"[Oracle] Stored price point: {record['currency_pair']} @ {record['source']}")
                else:
                    logger.warning(f"[Oracle] Failed to store: {record['currency_pair']}")
                
        except AttributeError as e:
            logger.error(f"[Oracle] DatabaseService method error: {str(e)}", exc_info=True)
        except Exception as e:
            logger.error(f"[Oracle] Failed to store price data: {str(e)}", exc_info=True)
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Check health of all oracle sources"""
        health_status = {
            'binance': {'status': 'unknown', 'response_time': None},
            'coingecko': {'status': 'unknown', 'response_time': None}, 
            'dia': {'status': 'unknown', 'response_time': None}
        }
        
        # Test each source with a simple query
        test_asset = 'bitcoin'
        
        # Test Binance
        start_time = datetime.now()
        binance_result = await self._fetch_from_binance(test_asset)
        health_status['binance'] = {
            'status': 'healthy' if binance_result else 'unhealthy',
            'response_time': (datetime.now() - start_time).total_seconds()
        }
        
        # Test CoinGecko
        start_time = datetime.now()
        coingecko_result = await self._fetch_from_coingecko(test_asset)
        health_status['coingecko'] = {
            'status': 'healthy' if coingecko_result else 'unhealthy',
            'response_time': (datetime.now() - start_time).total_seconds()
        }
        
        # Test DIA
        start_time = datetime.now()
        dia_result = await self._fetch_from_dia(test_asset)
        health_status['dia'] = {
            'status': 'healthy' if dia_result else 'unhealthy',
            'response_time': (datetime.now() - start_time).total_seconds()
        }
        
        # Overall health
        healthy_sources = sum(1 for source in health_status.values() if source['status'] == 'healthy')
        overall_status = 'healthy' if healthy_sources >= 2 else 'degraded' if healthy_sources == 1 else 'critical'
        
        return {
            'overall_status': overall_status,
            'healthy_sources': healthy_sources,
            'total_sources': 3,
            'sources': health_status,
            'last_check': datetime.now().isoformat()
        }
        
# Backward compatibility alias
OracleService = EnhancedOracleService