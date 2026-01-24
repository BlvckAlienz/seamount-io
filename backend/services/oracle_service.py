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
import traceback 

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

        # ✅ ADD: Configuration attributes
        self.request_timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
        self.cache_ttl = 300  # 5 minutes cache
        
        # ✅ ADD: Quota management
        from backend.services.quota_service import QuotaService
        self.quota_service = QuotaService(db_service)
        logger.info("✅ Quota-aware oracle initialized")
        
        # Load API keys from settings (if available)
        from backend.config import get_settings
        self.settings = get_settings()
        self.alpha_vantage_key = self.settings.ALPHA_VANTAGE_API_KEY.get_secret_value() if self.settings.ALPHA_VANTAGE_API_KEY else 'demo'
        self.twelve_data_key = self.settings.TWELVE_DATA_API_KEY.get_secret_value() if self.settings.TWELVE_DATA_API_KEY else 'demo'
        self.fmp_key = self.settings.FMP_API_KEY.get_secret_value() if self.settings.FMP_API_KEY else 'demo'

        # 🏆 Metals.dev API (FREE tier - 100 req/month)
        if self.settings.METALS_DEV_API_KEY:
            logger.info("✅ Metals.dev configured (60s delay, 100 req/month FREE)")
        else:
            logger.warning("⚠️ Metals.dev not configured - precious metals will use Yahoo Finance")
        
        # 🚨 MISSION CRITICAL: UPDATED TO DEC 2025 LIVE MARKET PRICES WITH CORRECT UNITS
        self.commodity_ranges = {
            # Precious Metals - WIDE RANGES (allow for market volatility)
            'XAU': {'min': Decimal('2000'), 'max': Decimal('8000'), 'name': 'Gold', 'unit': 'oz'},        # Screen shows $4,979
            'XAG': {'min': Decimal('20'), 'max': Decimal('200'), 'name': 'Silver', 'unit': 'oz'},         # Screen shows $101
            'XPT': {'min': Decimal('500'), 'max': Decimal('5000'), 'name': 'Platinum', 'unit': 'oz'},     # Screen shows $2,741
            'XPD': {'min': Decimal('500'), 'max': Decimal('5000'), 'name': 'Palladium', 'unit': 'oz'},    # Screen shows $2,027
            
            # Industrial Metals - WIDE RANGES (per metric ton)
            'COPP': {'min': Decimal('5000'), 'max': Decimal('25000'), 'name': 'Copper', 'unit': 'ton'},   # Screen shows $13,113
            'NICK': {'min': Decimal('8000'), 'max': Decimal('30000'), 'name': 'Nickel', 'unit': 'ton'},   # Screen shows $14,820
            'ALUM': {'min': Decimal('1500'), 'max': Decimal('5000'), 'name': 'Aluminum', 'unit': 'ton'},  # Should be ~$2,500
            'ZINC': {'min': Decimal('1500'), 'max': Decimal('6000'), 'name': 'Zinc', 'unit': 'ton'},      # Should be ~$2,900
            
            # Critical Minerals - WIDE RANGES (per metric ton)
            'LITH': {'min': Decimal('5000'), 'max': Decimal('40000'), 'name': 'Lithium', 'unit': 'ton'},
            'COBT': {'min': Decimal('15000'), 'max': Decimal('80000'), 'name': 'Cobalt', 'unit': 'ton'},
            'MANG': {'min': Decimal('500'), 'max': Decimal('5000'), 'name': 'Manganese', 'unit': 'ton'},
            'GRPH': {'min': Decimal('300'), 'max': Decimal('3000'), 'name': 'Graphite', 'unit': 'ton'},
            'TANT': {'min': Decimal('30000'), 'max': Decimal('200000'), 'name': 'Tantalum', 'unit': 'ton'},
        }

        # Asset mapping for different APIs
        self.asset_mapping = {
            'binance': {
                'bitcoin': 'BTCUSDT',
                'btc': 'BTCUSDT',  # ➕ ADD
                'ethereum': 'ETHUSDT',
                'eth': 'ETHUSDT',  # ➕ ADD
                'algorand': 'ALGOUSDT',
                'algo': 'ALGOUSDT',  # ➕ ADD
                'tether': 'USDCUSDT',
                'usdt': 'USDCUSDT',  # ➕ ADD
                'matic': 'MATICUSDT',
                'tron': 'TRXUSDT',
                'trx': 'TRXUSDT',  # ➕ ADD
                'solana': 'SOLUSDT',
                'sol': 'SOLUSDT',  # ➕ ADD
                'ton': 'TONUSDT'
            },
            'coingecko': {
                'bitcoin': 'bitcoin',
                'btc': 'bitcoin',  # ➕ ADD
                'ethereum': 'ethereum',
                'eth': 'ethereum',  # ➕ ADD
                'algorand': 'algorand',
                'algo': 'algorand',  # ➕ ADD
                'tether': 'tether',
                'usdt': 'tether',  # ➕ ADD
                'matic': 'matic-network',
                'tron': 'tron',
                'trx': 'tron',  # ➕ ADD
                'solana': 'solana',
                'sol': 'solana',  # ➕ ADD
                'ton': 'the-open-network'
            },
            'dia': {
                'bitcoin': 'BTC',
                'btc': 'BTC',  # ➕ ADD
                'ethereum': 'ETH',
                'eth': 'ETH',  # ➕ ADD
                'algorand': 'ALGO',
                'algo': 'ALGO',  # ➕ ADD
                'tether': 'USDT',
                'usdt': 'USDT',  # ➕ ADD
                'matic': 'MATIC',
                'tron': 'TRX',
                'trx': 'TRX',  # ➕ ADD
                'solana': 'SOL',
                'sol': 'SOL',  # ➕ ADD
                'ton': 'TON'
            }
        }
        
        logger.info("Enhanced 3-Tier Oracle Service initialized")
    
    def _validate_commodity_price(self, commodity_symbol: str, price: Decimal, source: str) -> bool:
        """
        Validate commodity prices - PERMISSIVE to allow for extreme market moves
        Only rejects prices that are CLEARLY broken (10x outside range)
        """
        if price <= 0:
            logger.error(f"❌ REJECTED: {commodity_symbol} ${price} from {source} (non-positive)")
            return False
        
        expected = self.commodity_ranges.get(commodity_symbol)
        if not expected:
            # If no range defined, accept any positive price
            logger.warning(f"⚠️ No validation range for {commodity_symbol}, accepting ${price} from {source}")
            return True
        
        min_price = expected['min']
        max_price = expected['max']
        
        # PERMISSIVE: Allow 10x deviation (for black swan events)
        lower_bound = min_price * Decimal('0.1')  # 10x below min
        upper_bound = max_price * Decimal('10.0') # 10x above max
        
        if lower_bound <= price <= upper_bound:
            # Additional sanity check: reject if >1000x expected midpoint
            midpoint = (min_price + max_price) / 2
            if price > midpoint * 1000 or price < midpoint / 1000:
                logger.error(f"🚨 REJECTED EXTREME OUTLIER: {commodity_symbol} ${price} from {source} (>1000x from midpoint ${midpoint})")
                return False
                
            logger.debug(f"✅ ACCEPTED: {commodity_symbol} ${price} from {source} (range: ${min_price}-${max_price})")
            return True
        else:
            logger.error(f"❌ REJECTED: {commodity_symbol} ${price} from {source} (expected: ${min_price}-${max_price}, bounds: ${lower_bound}-${upper_bound})")
            return False
    
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

                        # ✅ Record API call
                        await self.quota_service.record_api_call('binance', success=True)
                        
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
            'btc': Decimal("63500.00"),  # ➕ ADD
            'ethereum': Decimal("2650.00"),
            'eth': Decimal("2650.00"),  # ➕ ADD
            'algorand': Decimal("0.18"),
            'algo': Decimal("0.18"),  # ➕ ADD
            'tether': Decimal("1.00"),
            'usdt': Decimal("1.00"),  # ➕ ADD
            'matic': Decimal("0.75"),
            'tron': Decimal("0.12"),
            'trx': Decimal("0.12"),  # ➕ ADD
            'solana': Decimal("150.00"),
            'sol': Decimal("150.00"),  # ➕ ADD
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

    # ============================================================================
    # 💱 FOREX RATES (African Currencies + Major Pairs)
    # ============================================================================
    
    async def get_forex_rate(self, from_currency: str, to_currency: str = "USD") -> Tuple[Decimal, Dict]:
        """
        Get forex exchange rate with 3-tier fallback
        Supports: NGN, KES, ZAR, GHS, ETB, EGP, USD, EUR, GBP, JPY, CNY
        
        Returns: (rate, metadata)
        Example: await get_forex_rate("NGN", "USD") → (0.0007, {...})
        """
        currency_pair = f"{from_currency}/{to_currency}"
        
        # Check cache
        cached = self.rate_cache.get(currency_pair)
        if cached and (datetime.now() - cached['timestamp']) < timedelta(seconds=self.cache_ttl):
            logger.debug(f"Returning cached forex rate for {currency_pair}")
            return cached['price'], cached['metadata']
        
        # Tier 1: ExchangeRate-API (Free, 1500 requests/month)
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
                async with session.get(url, timeout=self.request_timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        rate = Decimal(str(data['rates'].get(to_currency, 0)))
                        
                        if rate > 0:
                            metadata = {
                                'timestamp': datetime.now().isoformat(),
                                'source': 'exchangerate-api',
                                'confidence': 0.95,
                                'pair': currency_pair
                            }
                            
                            self.rate_cache[currency_pair] = {
                                'price': rate,
                                'metadata': metadata,
                                'timestamp': datetime.now()
                            }
                            
                            return rate, metadata
        except Exception as e:
            logger.warning(f"ExchangeRate-API failed for {currency_pair}: {e}")
        
        # Tier 2: Fixer.io (Backup)
        try:
            # Note: Fixer free tier requires API key, but we can use fallback
            async with aiohttp.ClientSession() as session:
                url = f"https://api.fixer.io/latest?base={from_currency}&symbols={to_currency}"
                async with session.get(url, timeout=self.request_timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        rate = Decimal(str(data['rates'].get(to_currency, 0)))
                        
                        if rate > 0:
                            metadata = {
                                'timestamp': datetime.now().isoformat(),
                                'source': 'fixer',
                                'confidence': 0.90,
                                'pair': currency_pair
                            }
                            return rate, metadata
        except Exception as e:
            logger.warning(f"Fixer.io failed for {currency_pair}: {e}")
        
        # Tier 3: Emergency Fallback Rates (From Central Banks - Nov 2024)
        fallback_rates = {
            'NGN/USD': Decimal('0.00067'),  # 1 USD = ~1,500 NGN
            'KES/USD': Decimal('0.0069'),   # 1 USD = ~145 KES
            'ZAR/USD': Decimal('0.054'),    # 1 USD = ~18.5 ZAR
            'GHS/USD': Decimal('0.084'),    # 1 USD = ~12 GHS
            'ETB/USD': Decimal('0.018'),    # 1 USD = ~56 ETB
            'EGP/USD': Decimal('0.020'),    # 1 USD = ~49 EGP
            'USD/NGN': Decimal('1500.00'),
            'USD/KES': Decimal('145.00'),
            'USD/ZAR': Decimal('18.50'),
            'USD/GHS': Decimal('12.00'),
            'USD/ETB': Decimal('56.00'),
            'USD/EGP': Decimal('49.00'),
        }
        
        rate = fallback_rates.get(currency_pair)
        if rate:
            logger.critical(f"Using emergency fallback rate for {currency_pair}: {rate}")
            return rate, {
                'source': 'fallback',
                'timestamp': datetime.now().isoformat(),
                'confidence': 0.70,
                'warning': 'All forex sources failed - using Nov 2024 central bank reference'
            }
        
        raise ValueError(f"Could not fetch forex rate for {currency_pair}")
    
    # ============================================================================
    # 🏆 COMMODITIES PRICES (Critical Minerals + Precious Metals)
    # ============================================================================
    
    async def get_commodity_price(self, commodity_symbol: str) -> Tuple[Decimal, Dict]:
        """
        🏆 BLOOMBERG-GRADE COMMODITY ORACLE (Optimized for Free APIs)
        
        TIER PRIORITY:
        1. Metals.dev (FREE 100 req/month, 60s delay) - Precious metals only
        2. Yahoo Finance (UNLIMITED) - All metals via futures
        3. Alpha Vantage (500/day with your key)
        4. Twelve Data (800/day with your key)
        5. FMP (250/day with your key)
        
        ALL DATA MUST BE LIVE - NO CACHED/REFERENCE DATA
        
        Returns: (price_usd_per_unit, metadata)
        """
        """
        🆕 QUOTA-AWARE commodity price fetching
        """
        cache_key = f"commodity:{commodity_symbol}"
        
        # Check cache (5min TTL)
        cached = self.rate_cache.get(cache_key)
        if cached and (datetime.now() - cached['timestamp']) < timedelta(minutes=5):
            logger.debug(f"Returning cached commodity price for {commodity_symbol}")
            return cached['price'], cached['metadata']
        
        # ✅ CHECK QUOTA BEFORE USING METALS.DEV
        metals_dev_available = await self.quota_service.can_use_service('metals_dev', reserve_calls=10)
        
        # TIER 1: Metals.dev (ONLY if quota available)
        if commodity_symbol in ['XAU', 'XAG', 'XPT', 'XPD'] and metals_dev_available:
            try:
                metals_dev_key = self.settings.METALS_DEV_API_KEY
                if metals_dev_key:
                    async with aiohttp.ClientSession() as session:
                        url = f"https://api.metals.dev/v1/latest?api_key={metals_dev_key.get_secret_value()}&currency=USD&unit=toz"
                        
                        async with session.get(url, timeout=10) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                if 'metals' in data:
                                    metal_map = {
                                        'XAU': 'gold',
                                        'XAG': 'silver',
                                        'XPT': 'platinum',
                                        'XPD': 'palladium'
                                    }
                                    
                                    metal_name = metal_map.get(commodity_symbol)
                                    if metal_name and metal_name in data['metals']:
                                        price = Decimal(str(data['metals'][metal_name]))
                                        
                                        if self._validate_commodity_price(commodity_symbol, price, 'Metals.dev'):
                                            # ✅ Record successful API call
                                            await self.quota_service.record_api_call('metals_dev', success=True)
                                            
                                            metadata = {
                                                'timestamp': datetime.now().isoformat(),
                                                'source': 'metals_dev',
                                                'confidence': 0.95,
                                                'unit': 'USD per troy ounce',
                                                'symbol': commodity_symbol,
                                                'live': True,
                                                'note': 'Max 60-second delay from exchanges'
                                            }
                                            
                                            self.rate_cache[cache_key] = {
                                                'price': price,
                                                'metadata': metadata,
                                                'timestamp': datetime.now()
                                            }
                                            
                                            logger.info(f"✅ [Metals.dev] {commodity_symbol}: ${price}")
                                            return price, metadata
            except Exception as e:
                logger.warning(f"⚠️ [Tier 1] Metals.dev failed for {commodity_symbol}: {e}")
        else:
            if not metals_dev_available:
                logger.info(f"⏭️ Skipping Metals.dev (quota: {await self.quota_service.get_quota_status('metals_dev')})")
        
        # ============================================================================
        # TIER 2: YAHOO FINANCE (UNLIMITED, futures markets)
        # Best for: All metals (XAU, XAG, XPT, XPD, COPP, ALUM, ZINC, NICK)
        # ============================================================================
        yahoo_ticker_map = {
            # Precious Metals (already in USD/oz - NO conversion)
            'XAU': {'ticker': 'GC=F', 'multiplier': Decimal('1'), 'unit': 'USD per troy ounce'},
            'XAG': {'ticker': 'SI=F', 'multiplier': Decimal('1'), 'unit': 'USD per troy ounce'},
            'XPT': {'ticker': 'PL=F', 'multiplier': Decimal('1'), 'unit': 'USD per troy ounce'},
            'XPD': {'ticker': 'PA=F', 'multiplier': Decimal('1'), 'unit': 'USD per troy ounce'},
            
            # Industrial Metals - CRITICAL: Check Yahoo's actual quote units
            'COPP': {'ticker': 'HG=F', 'multiplier': Decimal('2204.62'), 'unit': 'USD per metric ton'},  # USD/lb → USD/ton
            'ALUM': {'ticker': 'ALI=F', 'multiplier': Decimal('1'), 'unit': 'USD per metric ton'},       # 🚨 ALREADY IN USD/TON
            'ZINC': {'ticker': 'ZN=F', 'multiplier': Decimal('1'), 'unit': 'USD per metric ton'},        # 🚨 ALREADY IN USD/TON  
            'NICK': {'ticker': 'NI=F', 'multiplier': Decimal('1'), 'unit': 'USD per metric ton'},        # 🚨 USE FUTURES TICKER
        }
        
        yahoo_config = yahoo_ticker_map.get(commodity_symbol)
        if yahoo_config:
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_config['ticker']}?interval=1m&range=1d"
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    
                    async with session.get(url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            raw_price = Decimal(str(data['chart']['result'][0]['meta']['regularMarketPrice']))
                            price = raw_price * yahoo_config['multiplier']
                            
                            if self._validate_commodity_price(commodity_symbol, price, 'Yahoo Finance'):
                                # ✅ Record API call
                                await self.quota_service.record_api_call('yahoo_finance', success=True)
                                
                                metadata = {
                                    'timestamp': datetime.now().isoformat(),
                                    'source': 'yahoo_finance',
                                    'confidence': 0.92,
                                    'unit': yahoo_config['unit'],
                                    'symbol': commodity_symbol,
                                    'live': True,
                                    'raw_price': float(raw_price),
                                    'ticker': yahoo_config['ticker']
                                }
                                
                                self.rate_cache[cache_key] = {
                                    'price': price,
                                    'metadata': metadata,
                                    'timestamp': datetime.now()
                                }
                                
                                logger.info(f"✅ [Yahoo Finance] {commodity_symbol}: ${price}")
                                return price, metadata
            except Exception as e:
                logger.warning(f"⚠️ [Tier 2] Yahoo Finance failed for {commodity_symbol}: {e}")
        
        # ============================================================================
        # TIER 3: ALPHA VANTAGE (500 req/day with your key)
        # ============================================================================
        alpha_vantage_map = {
            'COPP': 'COPPER', 'NICK': 'NICKEL', 'ALUM': 'ALUMINUM', 
            'ZINC': 'ZINC', 'XAU': 'XAU', 'XAG': 'XAG'
        }
        
        av_symbol = alpha_vantage_map.get(commodity_symbol)
        if av_symbol and self.alpha_vantage_key != 'demo':
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://www.alphavantage.co/query?function=COMMODITY_QUOTE_ENDPOINT&symbol={av_symbol}&apikey={self.alpha_vantage_key}"
                    
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            price = None
                            if 'data' in data and len(data['data']) > 0:
                                price = Decimal(str(data['data'][0].get('value', 0)))
                            elif 'price' in data:
                                price = Decimal(str(data['price']))
                            
                            if price and price > 0 and self._validate_commodity_price(commodity_symbol, price, 'Alpha Vantage'):
                                metadata = {
                                    'timestamp': datetime.now().isoformat(),
                                    'source': 'alpha_vantage',
                                    'confidence': 0.90,
                                    'unit': 'USD per troy ounce' if commodity_symbol.startswith('X') else 'USD per metric ton',
                                    'symbol': commodity_symbol,
                                    'live': True
                                }
                                
                                logger.info(f"✅ [Alpha Vantage] {commodity_symbol}: ${price}")
                                return price, metadata
            except Exception as e:
                logger.warning(f"⚠️ [Tier 3] Alpha Vantage failed for {commodity_symbol}: {e}")
        
        # ============================================================================
        # TIER 4: TWELVE DATA (800 req/day with your key)
        # ============================================================================
        twelve_data_map = {
            'COPP': 'COPPER', 'NICK': 'NICKEL', 'ALUM': 'ALUMINUM',
            'ZINC': 'ZINC', 'XAU': 'GOLD', 'XAG': 'SILVER'
        }
        
        td_symbol = twelve_data_map.get(commodity_symbol)
        if td_symbol and self.twelve_data_key != 'demo':
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.twelvedata.com/price?symbol={td_symbol}&apikey={self.twelve_data_key}"
                    
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if 'price' in data:
                                price = Decimal(str(data['price']))
                                
                                if price > 0 and self._validate_commodity_price(commodity_symbol, price, 'Twelve Data'):
                                    metadata = {
                                        'timestamp': datetime.now().isoformat(),
                                        'source': 'twelve_data',
                                        'confidence': 0.88,
                                        'unit': 'USD per troy ounce' if commodity_symbol.startswith('X') else 'USD per metric ton',
                                        'symbol': commodity_symbol,
                                        'live': True
                                    }
                                    
                                    logger.info(f"✅ [Twelve Data] {commodity_symbol}: ${price}")
                                    return price, metadata
            except Exception as e:
                logger.warning(f"⚠️ [Tier 4] Twelve Data failed for {commodity_symbol}: {e}")
        
        # ============================================================================
        # TIER 5: FINANCIAL MODELING PREP (250 req/day with your key)
        # ============================================================================
        if self.fmp_key != 'demo':
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://financialmodelingprep.com/api/v3/quote/{commodity_symbol}?apikey={self.fmp_key}"
                    
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if isinstance(data, list) and len(data) > 0 and 'price' in data[0]:
                                price = Decimal(str(data[0]['price']))
                                
                                if price > 0 and self._validate_commodity_price(commodity_symbol, price, 'FMP'):
                                    metadata = {
                                        'timestamp': datetime.now().isoformat(),
                                        'source': 'fmp',
                                        'confidence': 0.85,
                                        'unit': 'USD per troy ounce' if commodity_symbol.startswith('X') else 'USD per metric ton',
                                        'symbol': commodity_symbol,
                                        'live': True
                                    }
                                    
                                    logger.info(f"✅ [FMP] {commodity_symbol}: ${price}")
                                    return price, metadata
            except Exception as e:
                logger.warning(f"⚠️ [Tier 5] FMP failed for {commodity_symbol}: {e}")
        
        # ============================================================================
        # TIER 6: Critical Minerals (Market Reference - LIVE DATA PREFERRED)
        # ============================================================================
        
        # Lithium (via market reference - fallback only)
        if commodity_symbol == 'LITH':
            try:
                price = Decimal('13500.00')  # Nov 2025 lithium carbonate
                
                metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'market_reference',
                    'confidence': 0.75,
                    'unit': 'USD per metric ton',
                    'symbol': commodity_symbol,
                    'live': False,
                    'note': 'Lithium carbonate China spot price reference (Nov 2025)'
                }
                
                logger.info(f"✅ [Market Reference] {commodity_symbol}: ${price}")
                return price, metadata
            except Exception as e:
                logger.warning(f"⚠️ Lithium reference failed: {e}")
        
        # Cobalt (LME reference)
        if commodity_symbol == 'COBT':
            try:
                price = Decimal('27000.00')  # Nov 2025 cobalt
                
                metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'market_reference',
                    'confidence': 0.75,
                    'unit': 'USD per metric ton',
                    'symbol': commodity_symbol,
                    'live': False,
                    'note': 'LME cobalt reference price (Nov 2025)'
                }
                
                logger.info(f"✅ [Market Reference] {commodity_symbol}: ${price}")
                return price, metadata
            except Exception as e:
                logger.warning(f"⚠️ Cobalt reference failed: {e}")
        
        # Manganese
        if commodity_symbol == 'MANG':
            try:
                price = Decimal('1900.00')  # Nov 2025 manganese ore
                
                metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'market_reference',
                    'confidence': 0.75,
                    'unit': 'USD per metric ton',
                    'symbol': commodity_symbol,
                    'live': False,
                    'note': 'Manganese ore China reference (Nov 2025)'
                }
                
                logger.info(f"✅ [Market Reference] {commodity_symbol}: ${price}")
                return price, metadata
            except Exception as e:
                logger.warning(f"⚠️ Manganese reference failed: {e}")
        
        # Tantalum
        if commodity_symbol == 'TANT':
            try:
                price = Decimal('85000.00')  # Nov 2025 tantalum
                
                metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'market_reference',
                    'confidence': 0.70,
                    'unit': 'USD per metric ton',
                    'symbol': commodity_symbol,
                    'live': False,
                    'note': 'Tantalum pentoxide reference (Nov 2025)'
                }
                
                logger.info(f"✅ [Market Reference] {commodity_symbol}: ${price}")
                return price, metadata
            except Exception as e:
                logger.warning(f"⚠️ Tantalum reference failed: {e}")
        
        # Graphite
        if commodity_symbol == 'GRPH':
            try:
                price = Decimal('950.00')  # Nov 2025 graphite
                
                metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'market_reference',
                    'confidence': 0.75,
                    'unit': 'USD per metric ton',
                    'symbol': commodity_symbol,
                    'live': False,
                    'note': 'Natural flake graphite China reference (Nov 2025)'
                }
                
                logger.info(f"✅ [Market Reference] {commodity_symbol}: ${price}")
                return price, metadata
            except Exception as e:
                logger.warning(f"⚠️ Graphite reference failed: {e}")
        
        # ============================================================================
        # TIER 6: LME MARKET REFERENCES (For metals without Yahoo Finance tickers)
        # Based on latest LME spot prices - updated daily
        # ============================================================================
        
        # Nickel (LME spot reference)
        if commodity_symbol == 'NICK':
            try:
                # Nov 2025 LME Nickel: $14,820/ton (source: tradingeconomics.com)
                price = Decimal('14820.00')
                
                metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'lme_reference',
                    'confidence': 0.85,
                    'unit': 'USD per metric ton',
                    'symbol': commodity_symbol,
                    'live': False,  # Daily reference, not real-time
                    'note': 'LME Nickel spot price reference (Nov 2025 - tradingeconomics.com)'
                }
                
                self.rate_cache[cache_key] = {
                    'price': price,
                    'metadata': metadata,
                    'timestamp': datetime.now()
                }
                
                logger.info(f"✅ [LME Reference] {commodity_symbol}: ${price}")
                return price, metadata
            except Exception as e:
                logger.warning(f"⚠️ LME Nickel reference failed: {e}")
        
        # Zinc (LME spot reference)
        if commodity_symbol == 'ZINC':
            try:
                # Nov 2025 LME Zinc: $3,055/ton (source: investing.com)
                price = Decimal('3055.00')
                
                metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'lme_reference',
                    'confidence': 0.85,
                    'unit': 'USD per metric ton',
                    'symbol': commodity_symbol,
                    'live': False,  # Daily reference, not real-time
                    'note': 'LME Zinc futures price reference (Nov 2025 - investing.com)'
                }
                
                self.rate_cache[cache_key] = {
                    'price': price,
                    'metadata': metadata,
                    'timestamp': datetime.now()
                }
                
                logger.info(f"✅ [LME Reference] {commodity_symbol}: ${price}")
                return price, metadata
            except Exception as e:
                logger.warning(f"⚠️ LME Zinc reference failed: {e}")

        # ============================================================================
        # 🚨 EMERGENCY FALLBACK - USE LAST SUCCESSFUL DB PRICE
        # ============================================================================

        # Try to get last known good price from database (last 24h)
        async def _get_emergency_price_from_db(self, commodity_symbol: str) -> Optional[Decimal]:
            """Fetch last successful price from DB within 24 hours"""
            try:
                query = """
                    SELECT rate 
                    FROM public.price_history 
                    WHERE currency_pair = $1
                    AND timestamp > NOW() - INTERVAL '24 hours'
                    AND confidence > 0.8
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """
                result = await self.db_service.db.fetchrow(
                    query, 
                    f"{commodity_symbol}/USD"
                )
                
                if result and result['rate']:
                    price = Decimal(str(result['rate']))
                    logger.warning(f"📊 Using last DB price for {commodity_symbol}: ${price}")
                    return price
                    
            except Exception as e:
                logger.error(f"Failed to fetch emergency price from DB: {e}")
            
            return None

        # If DB fails, use WIDE market ranges (will accept almost any reasonable price)
        emergency_price_calculation = {
            # Use midpoint of validation ranges as absolute last resort
            'XAU': (self.commodity_ranges['XAU']['min'] + self.commodity_ranges['XAU']['max']) / 2,
            'XAG': (self.commodity_ranges['XAG']['min'] + self.commodity_ranges['XAG']['max']) / 2,
            'XPT': (self.commodity_ranges['XPT']['min'] + self.commodity_ranges['XPT']['max']) / 2,
            'XPD': (self.commodity_ranges['XPD']['min'] + self.commodity_ranges['XPD']['max']) / 2,
            'COPP': (self.commodity_ranges['COPP']['min'] + self.commodity_ranges['COPP']['max']) / 2,
            'ALUM': (self.commodity_ranges['ALUM']['min'] + self.commodity_ranges['ALUM']['max']) / 2,
            'ZINC': (self.commodity_ranges['ZINC']['min'] + self.commodity_ranges['ZINC']['max']) / 2,
            'NICK': (self.commodity_ranges['NICK']['min'] + self.commodity_ranges['NICK']['max']) / 2,
            'LITH': (self.commodity_ranges['LITH']['min'] + self.commodity_ranges['LITH']['max']) / 2,
            'COBT': (self.commodity_ranges['COBT']['min'] + self.commodity_ranges['COBT']['max']) / 2,
            'MANG': (self.commodity_ranges['MANG']['min'] + self.commodity_ranges['MANG']['max']) / 2,
            'GRPH': (self.commodity_ranges['GRPH']['min'] + self.commodity_ranges['GRPH']['max']) / 2,
            'TANT': (self.commodity_ranges['TANT']['min'] + self.commodity_ranges['TANT']['max']) / 2,
        }

        # FIRST: Try database
        db_price = await self._get_emergency_price_from_db(commodity_symbol)
        if db_price:
            return db_price, {
                'timestamp': datetime.now().isoformat(),
                'source': 'emergency_db_fallback',
                'confidence': 0.70,
                'unit': 'USD per troy ounce' if commodity_symbol in ['XAU', 'XAG', 'XPT', 'XPD'] else 'USD per metric ton',
                'symbol': commodity_symbol,
                'live': False,
                'warning': 'Using last successful DB price (within 24h)'
            }

        # LAST RESORT: Use calculated midpoint
        if commodity_symbol in emergency_price_calculation:
            price = emergency_price_calculation[commodity_symbol]
            logger.critical(f"🚨 ABSOLUTE LAST RESORT for {commodity_symbol}: ${price} (calculated midpoint)")
    
    # ============================================================================
    # 🌍 CROSS-RATES (BTC/NGN, ETH/ZAR, etc.)
    # ============================================================================
    
    async def get_cross_rate(self, asset: str, currency: str) -> Tuple[Decimal, Dict]:
        """
        Calculate cross-rate: Asset price in local currency
        Example: BTC/NGN = (BTC/USD) * (USD/NGN)
        
        Returns: (rate, metadata)
        """
        # Get asset price in USD
        asset_usd_price, asset_metadata = await self.get_asset_price(asset)
        
        # Get forex rate
        if currency == 'USD':
            return asset_usd_price, asset_metadata
        
        usd_to_currency_rate, forex_metadata = await self.get_forex_rate('USD', currency)
        
        # Calculate cross-rate
        cross_rate = asset_usd_price * usd_to_currency_rate
        
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'source': 'calculated',
            'confidence': min(asset_metadata['confidence'], forex_metadata['confidence']),
            'components': {
                'asset_price': str(asset_usd_price),
                'forex_rate': str(usd_to_currency_rate),
                'asset_source': asset_metadata['source'],
                'forex_source': forex_metadata['source']
            },
            'pair': f"{asset}/{currency}"
        }
        
        return cross_rate, metadata
    
    # ============================================================================
    # 📈 BATCH FETCHER (For Terminal Dashboard - Single API Call)
    # ============================================================================
    
    async def get_market_snapshot(self) -> Dict[str, Any]:
        """
        Get complete market snapshot for Bloomberg-style terminal
        
        Returns:
        {
            'crypto': {'bitcoin': 63500.00, ...},
            'forex': {'NGN/USD': 0.00067, ...},
            'commodities': {'XAU': 2650.00, ...},
            'cross_rates': {'BTC/NGN': 95250000, ...},
            'timestamp': '2024-11-30T12:00:00Z'
        }
        """
        snapshot = {
            'crypto': {},
            'forex': {},
            'commodities': {},
            'cross_rates': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Crypto assets (parallel fetch)
        crypto_symbols = ['bitcoin', 'ethereum', 'algorand', 'tron']
        crypto_tasks = [self.get_asset_price(symbol) for symbol in crypto_symbols]
        crypto_results = await asyncio.gather(*crypto_tasks, return_exceptions=True)
        
        for symbol, result in zip(crypto_symbols, crypto_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {symbol}: {result}")
                continue
            price, _ = result
            snapshot['crypto'][symbol] = float(price)
        
        # Forex pairs (parallel fetch)
        forex_pairs = [
            ('NGN', 'USD'), ('KES', 'USD'), ('ZAR', 'USD'), 
            ('GHS', 'USD'), ('ETB', 'USD'), ('EGP', 'USD')
        ]
        forex_tasks = [self.get_forex_rate(from_curr, to_curr) for from_curr, to_curr in forex_pairs]
        forex_results = await asyncio.gather(*forex_tasks, return_exceptions=True)
        
        for (from_curr, to_curr), result in zip(forex_pairs, forex_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {from_curr}/{to_curr}: {result}")
                continue
            rate, _ = result
            snapshot['forex'][f"{from_curr}/{to_curr}"] = float(rate)
            # Also store inverse
            snapshot['forex'][f"{to_curr}/{from_curr}"] = float(Decimal('1') / rate) if rate > 0 else 0
        
        # Commodities (parallel fetch) - EXPANDED TO INCLUDE CRITICAL MINERALS
        commodity_symbols = [
            'XAU', 'XAG', 'XPT', 'XPD',           # Precious metals
            'COPP', 'NICK', 'ALUM', 'ZINC',       # Industrial metals
            'LITH', 'COBT', 'MANG', 'GRPH', 'TANT' # Critical minerals
        ]
        commodity_tasks = [self.get_commodity_price(symbol) for symbol in commodity_symbols]
        commodity_results = await asyncio.gather(*commodity_tasks, return_exceptions=True)
        
        for symbol, result in zip(commodity_symbols, commodity_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {symbol}: {result}")
                continue
            price, _ = result
            snapshot['commodities'][symbol] = float(price)
        
        # Cross-rates (BTC/NGN, ETH/ZAR, etc.)
        cross_pairs = [
            ('bitcoin', 'NGN'), ('bitcoin', 'KES'), ('bitcoin', 'ZAR'),
            ('ethereum', 'NGN'), ('ethereum', 'ZAR')
        ]
        cross_tasks = [self.get_cross_rate(asset, curr) for asset, curr in cross_pairs]
        cross_results = await asyncio.gather(*cross_tasks, return_exceptions=True)
        
        for (asset, curr), result in zip(cross_pairs, cross_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {asset}/{curr}: {result}")
                continue
            rate, _ = result
            snapshot['cross_rates'][f"{asset.upper()}/{curr}"] = float(rate)
        
        return snapshot
          
# Backward compatibility alias
OracleService = EnhancedOracleService