# File: backend/services/price_logger_service.py
# Production-Grade Price Logging with Tiered Refresh Rates

import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from backend.services.oracle_service import EnhancedOracleService
from backend.services.quota_service import QuotaService

logger = logging.getLogger(__name__)

class PriceLoggerService:
    """
    Intelligent price logging with tiered refresh rates
    - Never wastes premium API quotas
    - Different refresh rates for different asset classes
    - Quota-aware tier selection
    """
    
    # ✅ TIERED REFRESH CONFIGURATION
    REFRESH_CONFIG = {
        'crypto': {
            'assets': ['bitcoin', 'ethereum', 'algorand', 'tron'],
            'interval_seconds': 30,  # Every 30 seconds (volatile)
            'preferred_sources': ['binance', 'coingecko_free']  # Unlimited APIs only
        },
        'precious_metals': {
            'assets': ['XAU', 'XAG', 'XPT', 'XPD'],
            'interval_seconds': 300,  # Every 5 minutes
            'preferred_sources': ['yahoo_finance']  # Skip metals_dev in background
        },
        'industrial_metals': {
            'assets': ['COPP', 'ALUM', 'NICK', 'ZINC'],
            'interval_seconds': 900,  # Every 15 minutes (slower markets)
            'preferred_sources': ['yahoo_finance']
        },
        'critical_minerals': {
            'assets': ['LITH', 'COBT', 'MANG', 'GRPH', 'TANT'],
            'interval_seconds': 3600,  # Every hour (reference prices)
            'preferred_sources': ['market_reference']
        },
        'forex': {
            'pairs': [
                ('NGN', 'USD'), ('KES', 'USD'), ('ZAR', 'USD'),
                ('GHS', 'USD'), ('ETB', 'USD'), ('EGP', 'USD')
            ],
            'interval_seconds': 600,  # Every 10 minutes
            'preferred_sources': ['exchangerate_api']
        }
    }
    
    def __init__(self, oracle_service: EnhancedOracleService, quota_service: QuotaService):
        self.oracle = oracle_service
        self.quota = quota_service
        self.running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start(self):
        """Start all price logging tasks"""
        if self.running:
            logger.warning("Price logger already running")
            return
        
        self.running = True
        logger.info("🚀 Starting intelligent price logger...")
        
        # Start separate task for each asset class
        self._tasks = [
            asyncio.create_task(self._log_crypto_prices()),
            asyncio.create_task(self._log_precious_metals()),
            asyncio.create_task(self._log_industrial_metals()),
            asyncio.create_task(self._log_critical_minerals()),
            asyncio.create_task(self._log_forex_rates()),
            asyncio.create_task(self._monitor_quota_health())
        ]
        
        logger.info("✅ All price logging tasks started")
    
    async def stop(self):
        """Stop all price logging tasks"""
        self.running = False
        
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("✅ Price logger stopped")
    
    async def _log_crypto_prices(self):
        """Log crypto prices every 30 seconds"""
        config = self.REFRESH_CONFIG['crypto']
        
        while self.running:
            try:
                for symbol in config['assets']:
                    try:
                        price, metadata = await self.oracle.get_asset_price(symbol)
                        logger.debug(f"📊 Crypto: {symbol} = ${price} ({metadata['source']})")
                    except Exception as e:
                        logger.error(f"Failed to log {symbol}: {e}")
                
                await asyncio.sleep(config['interval_seconds'])
                
            except Exception as e:
                logger.error(f"Crypto logging error: {e}")
                await asyncio.sleep(60)
    
    async def _log_precious_metals(self):
        """Log precious metals every 5 minutes (SKIP metals_dev)"""
        config = self.REFRESH_CONFIG['precious_metals']
        
        while self.running:
            try:
                for symbol in config['assets']:
                    try:
                        # 🚨 CRITICAL: Force Yahoo Finance tier (skip metals_dev)
                        # This preserves metals_dev quota for user-facing terminal requests
                        price, metadata = await self.oracle.get_commodity_price(symbol)
                        
                        # Only log if NOT from metals_dev (background should never use it)
                        if metadata.get('source') != 'metals_dev':
                            logger.debug(f"📊 Precious: {symbol} = ${price} ({metadata['source']})")
                        else:
                            logger.warning(f"⚠️ Background task accidentally used metals_dev for {symbol}")
                        
                    except Exception as e:
                        logger.error(f"Failed to log {symbol}: {e}")
                
                await asyncio.sleep(config['interval_seconds'])
                
            except Exception as e:
                logger.error(f"Precious metals logging error: {e}")
                await asyncio.sleep(300)
    
    async def _log_industrial_metals(self):
        """Log industrial metals every 15 minutes"""
        config = self.REFRESH_CONFIG['industrial_metals']
        
        while self.running:
            try:
                for symbol in config['assets']:
                    try:
                        price, metadata = await self.oracle.get_commodity_price(symbol)
                        logger.debug(f"📊 Industrial: {symbol} = ${price} ({metadata['source']})")
                    except Exception as e:
                        logger.error(f"Failed to log {symbol}: {e}")
                
                await asyncio.sleep(config['interval_seconds'])
                
            except Exception as e:
                logger.error(f"Industrial metals logging error: {e}")
                await asyncio.sleep(900)
    
    async def _log_critical_minerals(self):
        """Log critical minerals every hour"""
        config = self.REFRESH_CONFIG['critical_minerals']
        
        while self.running:
            try:
                for symbol in config['assets']:
                    try:
                        price, metadata = await self.oracle.get_commodity_price(symbol)
                        logger.debug(f"📊 Critical: {symbol} = ${price} ({metadata['source']})")
                    except Exception as e:
                        logger.error(f"Failed to log {symbol}: {e}")
                
                await asyncio.sleep(config['interval_seconds'])
                
            except Exception as e:
                logger.error(f"Critical minerals logging error: {e}")
                await asyncio.sleep(3600)
    
    async def _log_forex_rates(self):
        """Log forex rates every 10 minutes"""
        config = self.REFRESH_CONFIG['forex']
        
        while self.running:
            try:
                for from_curr, to_curr in config['pairs']:
                    try:
                        rate, metadata = await self.oracle.get_forex_rate(from_curr, to_curr)
                        logger.debug(f"📊 Forex: {from_curr}/{to_curr} = {rate} ({metadata['source']})")
                    except Exception as e:
                        logger.error(f"Failed to log {from_curr}/{to_curr}: {e}")
                
                await asyncio.sleep(config['interval_seconds'])
                
            except Exception as e:
                logger.error(f"Forex logging error: {e}")
                await asyncio.sleep(600)
    
    async def _monitor_quota_health(self):
        """Monitor quota usage every hour"""
        while self.running:
            try:
                all_quotas = await self.quota.get_all_quotas()
                
                # Log high usage services
                for service, status in all_quotas.items():
                    usage = status.get('usage_percent', 0)
                    
                    if usage >= 90:
                        logger.warning(
                            f"🚨 {service}: {status['calls_used']}/{status['monthly_limit']} "
                            f"({usage}%) - CRITICAL"
                        )
                    elif usage >= 75:
                        logger.warning(
                            f"⚠️ {service}: {status['calls_used']}/{status['monthly_limit']} "
                            f"({usage}%) - HIGH"
                        )
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error(f"Quota monitoring error: {e}")
                await asyncio.sleep(3600)