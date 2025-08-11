import asyncio
import aiohttp
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import deque

from config import Settings
from .database_service import DatabaseService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PriceData:
    currency_pair: str; rate: Decimal; source: str
    timestamp: datetime; confidence: float; volume_24h: Optional[Decimal] = None
    def to_dict(self):
        data = asdict(self); data['rate'] = str(self.rate)
        data['timestamp'] = self.timestamp.isoformat()
        if self.volume_24h: data['volume_24h'] = str(self.volume_24h)
        return data

class OracleService:
    def __init__(self, settings: Settings, db_service: DatabaseService):
        self.settings = settings
        self.db_service = db_service
        self.rate_cache: Dict[str, Dict[str, Any]] = {}
        self.source_weights = {'coinbase': 0.3, 'coingecko': 0.3, 'chainlink': 0.4}
        self.audit_trail = deque(maxlen=1000)
        logger.info("OracleService initialized successfully.")

    async def fetch_from_source(self, session: aiohttp.ClientSession, source: str, currency_pair: str) -> Optional[PriceData]:
        base, quote = currency_pair.split('/')
        try:
            if source == 'coinbase':
                rate = Decimal('1.0') # Mock
                return PriceData(currency_pair, rate, source, datetime.now(), 0.95)
            elif source == 'coingecko':
                rate = Decimal('1.01') # Mock
                return PriceData(currency_pair, rate, source, datetime.now(), 0.90)
        except Exception as e:
            logger.error(f"Error fetching from {source} for {currency_pair}: {e}")
        return None

    async def fetch_all_sources(self, currency_pair: str) -> List[PriceData]:
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_from_source(session, source, currency_pair) for source in self.source_weights.keys()]
            results = await asyncio.gather(*tasks)
            return [res for res in results if res is not None]

    def calculate_weighted_price(self, price_data: List[PriceData]) -> Tuple[Decimal, float]:
        if not price_data: return Decimal('0'), 0.0
        weighted_sum = Decimal('0'); total_weight = Decimal('0')
        for pd in price_data:
            weight = Decimal(str(self.source_weights.get(pd.source, 0))) * Decimal(str(pd.confidence))
            weighted_sum += pd.rate * weight
            total_weight += weight
        if total_weight == 0: return Decimal('0'), 0.0
        consensus_price = weighted_sum / total_weight
        confidence = float(min(1.0, total_weight / sum(Decimal(str(w)) for w in self.source_weights.values())))
        return consensus_price, confidence

    async def get_price(self, base_currency: str, quote_currency: str) -> Tuple[Decimal, Dict]:
        currency_pair = f"{base_currency.upper()}/{quote_currency.upper()}"
        cached = self.rate_cache.get(currency_pair)
        if cached and (datetime.now() - cached['timestamp']) < timedelta(minutes=1):
            return cached['price'], cached['metadata']

        price_data = await self.fetch_all_sources(currency_pair)
        if not price_data:
            raise ValueError(f"Could not fetch price data for {currency_pair}")

        consensus_price, confidence = self.calculate_weighted_price(price_data)
        metadata = {'timestamp': datetime.now().isoformat(), 'sources_used': [pd.source for pd in price_data], 'confidence': confidence}
        self.rate_cache[currency_pair] = {'price': consensus_price, 'metadata': metadata, 'timestamp': datetime.now()}
        
        asyncio.create_task(self.store_price_data(price_data))
        self.audit_trail.append({'action': 'get_price', 'pair': currency_pair, 'price': str(consensus_price), 'time': datetime.now().isoformat()})
        
        return consensus_price, metadata

    async def store_price_data(self, price_data: List[PriceData]):
        """
        Persists price data to the Supabase database via the DatabaseService.
        """
        try:
            records_to_insert = []
            for pd in price_data:
                records_to_insert.append({
                    "currency_pair": pd.currency_pair,
                    "rate": float(pd.rate),
                    "source": pd.source,
                    "confidence": pd.confidence,
                    "volume": float(pd.volume_24h or 0),
                    "timestamp": pd.timestamp.isoformat()
                })
            
            if records_to_insert:
                await self.db_service.log_batch_event("price_history", records_to_insert)
                logger.info(f"Successfully stored {len(records_to_insert)} price points.")
        except Exception as e:
            logger.error(f"Failed to store price data: {e}", exc_info=True)