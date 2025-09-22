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

class OracleService:
    def __init__(self, settings: Settings, db_service: DatabaseService):
        self.settings = settings
        self.db_service = db_service
        self.rate_cache: Dict[str, Dict[str, Any]] = {}
        self.source_weights = {'coinbase': 0.3, 'coingecko': 0.3, 'chainlink': 0.4}
        self.audit_trail = deque(maxlen=1000)
        logger.info("OracleService initialized successfully.")

    async def fetch_from_source(self, session: aiohttp.ClientSession, source: str, asset_id: str) -> Optional[PriceData]:
        """
        Fetches price for a specific asset (e.g., 'bitcoin', 'ethereum') from a source.
        """
        try:
            if source == 'coingecko':
                # Use the free API endpoint for simple price data
                api_url = f"https://api.coingecko.com/api/v3/simple/price?ids={asset_id}&vs_currencies=usd&include_24hr_vol=true"
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = Decimal(str(data[asset_id]['usd']))
                        volume = Decimal(str(data[asset_id].get('usd_24h_vol', 0)))
                        return PriceData(
                            currency_pair=f"{asset_id.upper()}/USD",
                            rate=price,
                            source=source,
                            timestamp=datetime.now(),
                            confidence=0.98, # High confidence for CoinGecko
                            volume_24h=volume
                        )
                    else:
                        logger.warning(f"CoinGecko API error: {response.status}")
            # Add more sources (e.g., Binance, Kraken) here later for redundancy
        except Exception as e:
            logger.error(f"Error fetching from {source} for {asset_id}: {e}")
        return None

    async def get_asset_price(self, asset_name: str) -> Tuple[Decimal, Dict]:
        """
        Gets the current USD price of a specific asset (e.g., 'bitcoin', 'ethereum').
        This is the primary method for other services to use.
        """
        currency_pair = f"{asset_name.upper()}/USD"
        cached = self.rate_cache.get(currency_pair)
        if cached and (datetime.now() - cached['timestamp']) < timedelta(seconds=30): # Cache for 30 sec
            return cached['price'], cached['metadata']

        # For now, we primarily use CoinGecko. We can add more sources later.
        async with aiohttp.ClientSession() as session:
            price_data = await self.fetch_from_source(session, 'coingecko', asset_name)

        if not price_data:
            # Fallback to cache even if stale, then error
            if cached:
                logger.warning(f"Using stale cached price for {currency_pair} after fetch failure.")
                return cached['price'], cached['metadata']
            raise ValueError(f"Could not fetch price data for {currency_pair}")

        # For a single source, consensus is easy.
        consensus_price = price_data.rate
        confidence = price_data.confidence

        metadata = {
            'timestamp': datetime.now().isoformat(),
            'sources_used': [price_data.source],
            'confidence': confidence,
            'source_data': price_data.to_dict()
        }
        self.rate_cache[currency_pair] = {'price': consensus_price, 'metadata': metadata, 'timestamp': datetime.now()}
        
        asyncio.create_task(self.store_price_data([price_data]))
        self.audit_trail.append({'action': 'get_asset_price', 'asset': asset_name, 'price': str(consensus_price), 'time': datetime.now().isoformat()})
        
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