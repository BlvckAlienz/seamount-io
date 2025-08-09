import asyncio
import aiohttp
import logging
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import json
import hashlib
from dataclasses import dataclass, asdict
from statistics import median, mean
import time
import sqlite3
from contextlib import asynccontextmanager
import numpy as np
from collections import defaultdict, deque
import hmac
import os

# Assuming config is in the parent directory
from config import get_settings

settings = get_settings()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
        if self.volume_24h: data['volume_24h'] = str(self.volume_24h)
        return data

class OracleService:
    def __init__(self, db_path: str = "oracle.db"):
        self.db_path = db_path
        self.rate_cache: Dict[str, Dict[str, Any]] = {}
        self.source_weights = {
            'coinbase': 0.3, 'coingecko': 0.3, 'chainlink': 0.4
        }
        self.audit_trail = deque(maxlen=1000)
        asyncio.create_task(self._init_database())

    async def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY, currency_pair TEXT, rate REAL, source TEXT,
                    confidence REAL, volume REAL, timestamp TEXT
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    async def fetch_from_source(self, session: aiohttp.ClientSession, source: str, currency_pair: str) -> Optional[PriceData]:
        # Placeholder for actual API calls
        base, quote = currency_pair.split('/')
        try:
            # Add logic for each source
            if source == 'coinbase':
                # response = await session.get(f"https://api.coinbase.com/v2/prices/{base}-{quote}/spot")
                # data = await response.json()
                # rate = Decimal(data['data']['amount'])
                rate = Decimal('1.0') # Mock
                return PriceData(currency_pair, rate, source, datetime.now(), 0.95)
            elif source == 'coingecko':
                # response = await session.get(f"https://api.coingecko.com/api/v3/simple/price?ids={base.lower()}&vs_currencies={quote.lower()}")
                # data = await response.json()
                # rate = Decimal(str(data[base.lower()][quote.lower()]))
                rate = Decimal('1.01') # Mock
                return PriceData(currency_pair, rate, source, datetime.now(), 0.90)
        except Exception as e:
            logger.error(f"Error fetching from {source}: {e}")
            return None

    async def fetch_all_sources(self, currency_pair: str) -> List[PriceData]:
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_from_source(session, source, currency_pair) for source in self.source_weights.keys()]
            results = await asyncio.gather(*tasks)
            return [res for res in results if res is not None]

    def calculate_weighted_price(self, price_data: List[PriceData]) -> Tuple[Decimal, float]:
        if not price_data: return Decimal('0'), 0.0
        
        weighted_sum = Decimal('0')
        total_weight = Decimal('0')
        for pd in price_data:
            weight = Decimal(str(self.source_weights.get(pd.source, 0))) * Decimal(str(pd.confidence))
            weighted_sum += pd.rate * weight
            total_weight += weight
            
        if total_weight == 0: return Decimal('0'), 0.0
        
        consensus_price = weighted_sum / total_weight
        # Simplified confidence calculation
        confidence = float(min(1.0, total_weight / sum(Decimal(str(w)) for w in self.source_weights.values())))
        return consensus_price, confidence

    async def get_price(self, base_currency: str, quote_currency: str) -> Tuple[Decimal, Dict]:
        currency_pair = f"{base_currency.upper()}/{quote_currency.upper()}"
        
        cached = self.rate_cache.get(currency_pair)
        if cached and (datetime.now() - cached['timestamp']) < timedelta(minutes=1):
            return cached['price'], cached['metadata']

        price_data = await self.fetch_all_sources(currency_pair)
        if not price_data:
            raise ValueError(f"Could not fetch any price data for {currency_pair}")

        consensus_price, confidence = self.calculate_weighted_price(price_data)
        
        metadata = {
            'timestamp': datetime.now(),
            'sources_used': [pd.source for pd in price_data],
            'confidence': confidence
        }
        
        self.rate_cache[currency_pair] = {'price': consensus_price, 'metadata': metadata, 'timestamp': datetime.now()}
        asyncio.create_task(self.store_price_data(price_data))
        
        self.audit_trail.append({'action': 'get_price', 'pair': currency_pair, 'price': str(consensus_price), 'time': datetime.now().isoformat()})
        
        return consensus_price, metadata

    async def store_price_data(self, price_data: List[PriceData]):
        conn = sqlite3.connect(self.db_path)
        try:
            for pd in price_data:
                conn.execute(
                    "INSERT INTO price_history (currency_pair, rate, source, confidence, volume, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (pd.currency_pair, float(pd.rate), pd.source, pd.confidence, float(pd.volume_24h or 0), pd.timestamp.isoformat())
                )
            conn.commit()
        finally:
            conn.close()