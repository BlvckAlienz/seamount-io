# /backend/services/swap_service.py

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import aiohttp
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod, indexer
from tinyman.v1.client import TinymanTestnetClient, TinymanMainnetClient
from tinyman.assets import Asset
from tinyman.pools import Pool

logger = logging.getLogger(__name__)

class TinymanClient:
    """
    Tinyman DEX integration for token swapping
    Supports both V1 and V2 pools with enhanced error handling
    """
    
    def __init__(self, network: str = "mainnet"):
        self.network = network
        self.client = None
        self.algod_client = None
        self.pools_cache = {}
        self.assets_cache = {}
        self.last_cache_update = {}
        self.cache_ttl = 300  # 5 minutes
        
    async def initialize(self, algod_client):
        """Initialize Tinyman client"""
        self.algod_client = algod_client
        
        if self.network == "mainnet":
            self.client = TinymanMainnetClient(algod_client=algod_client)
        else:
            self.client = TinymanTestnetClient(algod_client=algod_client)
        
        # Load commonly used assets
        await self._load_common_assets()
        
        logger.info(f"Tinyman client initialized for {self.network}")
    
    async def _load_common_assets(self):
        """Load commonly traded assets"""
        common_assets = {
            'ALGO': 0,
            'USDC': 31566704,
            'USDT': 312769,
            'STBL': 465865291,
            'GOAL': 401593499,
            'USDS': 0  # Placeholder - replace with actual USDS asset ID
        }
        
        for symbol, asset_id in common_assets.items():
            try:
                if asset_id == 0 and symbol == 'ALGO':
                    # ALGO is native
                    asset = self.client.fetch_asset(asset_id)
                elif symbol == 'USDS':
                    # Skip USDS for now - add actual asset ID when available
                    continue
                else:
                    asset = self.client.fetch_asset(asset_id)
                
                self.assets_cache[symbol] = asset
                self.last_cache_update[f"asset_{symbol}"] = datetime.utcnow()
                
            except Exception as e:
                logger.warning(f"Failed to load asset {symbol}: {e}")
    
    async def _get_asset(self, token) -> Optional[Asset]:
        """Get asset from cache or fetch from network"""
        cache_key = f"asset_{token.symbol}"
        
        # Check cache validity
        if (cache_key in self.assets_cache and 
            cache_key in self.last_cache_update and
            datetime.utcnow() - self.last_cache_update[cache_key] < timedelta(seconds=self.cache_ttl)):
            return self.assets_cache[cache_key]
        
        try:
            asset = self.client.fetch_asset(token.asset_id)
            self.assets_cache[token.symbol] = asset
            self.last_cache_update[cache_key] = datetime.utcnow()
            return asset
        except Exception as e:
            logger.error(f"Failed to fetch asset {token.symbol}: {e}")
            return None
    
    async def _get_pool(self, asset_a: Asset, asset_b: Asset) -> Optional[Pool]:
        """Get pool from cache or fetch from network"""
        pool_key = f"{min(asset_a.id, asset_b.id)}_{max(asset_a.id, asset_b.id)}"
        
        # Check cache validity
        if (pool_key in self.pools_cache and 
            pool_key in self.last_cache_update and
            datetime.utcnow() - self.last_cache_update[pool_key] < timedelta(seconds=self.cache_ttl)):
            return self.pools_cache[pool_key]
        
        try:
            pool = self.client.fetch_pool(asset_a, asset_b)
            if pool and pool.exists:
                self.pools_cache[pool_key] = pool
                self.last_cache_update[pool_key] = datetime.utcnow()
                return pool
            return None
        except Exception as e:
            logger.error(f"Failed to fetch pool for {asset_a.id}-{asset_b.id}: {e}")
            return None
    
    async def get_quote(self, from_token, to_token, amount_in: Decimal) -> Optional[Dict]:
        """
        Get swap quote from Tinyman
        """
        try:
            # Get assets
            from_asset = await self._get_asset(from_token)
            to_asset = await self._get_asset(to_token) 
            
            if not from_asset or not to_asset:
                logger.warning(f"Assets not found: {from_token.symbol} or {to_token.symbol}")
                return None
            
            # Get pool
            pool = await self._get_pool(from_asset, to_asset)
            if not pool:
                logger.warning(f"Pool not found for {from_token.symbol}-{to_token.symbol}")
                return None
            
            # Calculate swap quote
            amount_in_base_units = int(amount_in * (10 ** from_token.decimals))
            
            quote = pool.fetch_fixed_input_swap_quote(
                amount_in=amount_in_base_units,
                asset_in=from_asset
            )
            
            if not quote.amount_out or quote.amount_out <= 0:
                logger.warning("Invalid quote received from Tinyman")
                return None
            
            # Convert to decimal
            amount_out = Decimal(quote.amount_out) / (10 ** to_token.decimals)
            
            # Calculate exchange rate and price impact
            exchange_rate = (amount_out / amount_in).quantize(Decimal('0.000001')) if amount_in > 0 else Decimal('0')
            
            # Get pool state for price impact calculation
            pool_info = await self._get_pool_info(pool)
            price_impact = await self._calculate_price_impact(
                pool_info, amount_in, from_token, to_token
            )
            
            # Calculate fees (Tinyman charges 0.3%)
            fees = amount_in * Decimal('0.003')
            
            # Define SwapQuote and SwapProvider locally if not available
            class SwapProvider:
                TINYMAN = "tinyman"
                
            class SwapQuote:
                def __init__(self, **kwargs):
                    self.__dict__.update(kwargs)
            
            return SwapQuote(
                from_token=from_token,
                to_token=to_token,
                amount_in=amount_in,
                amount_out=amount_out,
                price_impact=price_impact,
                exchange_rate=exchange_rate,
                provider=SwapProvider.TINYMAN,
                route=[from_token, to_token],  # Direct swap
                fees=fees,
                expires_at=datetime.utcnow() + timedelta(minutes=2),
                quote_id=f"tinyman_{int(datetime.utcnow().timestamp())}"
            )
            
        except Exception as e:
            logger.error(f"Tinyman quote failed: {e}")
            return None
    
    async def execute_swap(self, quote, user_address: str, private_key: str = None) -> Dict:
        """
        Execute swap on Tinyman
        """
        try:
            # Get assets and pool
            from_asset = await self._get_asset(quote.from_token)
            to_asset = await self._get_asset(quote.to_token)
            pool = await self._get_pool(from_asset, to_asset)
            
            if not pool:
                return {'success': False, 'error': 'Pool not found'}
            
            # Prepare swap transaction
            amount_in_base_units = int(quote.amount_in * (10 ** quote.from_token.decimals))
            min_amount_out = int((quote.amount_out * Decimal('0.99')) * (10 ** quote.to_token.decimals))  # 1% slippage
            
            # Get fresh quote to ensure accuracy
            swap_quote = pool.fetch_fixed_input_swap_quote(
                amount_in=amount_in_base_units,
                asset_in=from_asset
            )
            
            if not swap_quote.amount_out or swap_quote.amount_out < min_amount_out:
                return {
                    'success': False, 
                    'error': 'Price moved unfavorably, please retry'
                }
            
            # Prepare swap transactions
            swap_transactions = pool.prepare_swap_transactions(
                amount_in=amount_in_base_units,
                asset_in=from_asset,
                swapper_address=user_address
            )
            
            if not swap_transactions:
                return {'success': False, 'error': 'Failed to prepare swap transactions'}
            
            # If private key provided, sign and submit
            if private_key:
                # Sign transactions
                signed_group = []
                for txn in swap_transactions:
                    signed_txn = txn.sign(private_key)
                    signed_group.append(signed_txn)
                
                    rate=rate.quantize(Decimal('0.000001')),
                tx_id = self.algod_client.send_transactions(signed_group)
                
                    confidence=0.9,
                    volume_24h=Decimal(str(data.get('volume', 0))).quantize(Decimal('0.01')),
                    bid_ask_spread=Decimal(str(data.get('spread', 0.01))).quantize(Decimal('0.0001'))
                )
                
                return {
                    'success': True,
                    'tx_id': tx_id,
                    'confirmed_round': confirmed_txn['confirmed-round'],
                    'amount_out': Decimal(swap_quote.amount_out) / (10 ** quote.to_token.decimals)
                }
            else:
                # Return unsigned transactions for external signing
                return {
                    'success': True,
                    'unsigned_transactions': [txn.dictify() for txn in swap_transactions],
                    'expected_amount_out': Decimal(swap_quote.amount_out) / (10 ** quote.to_token.decimals)
                }
                
        except Exception as e:
            logger.error(f"Tinyman swap execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _get_pool_info(self, pool: Pool) -> Dict:
        """Get detailed pool information"""
        try:
            pool.refresh()
            return {
                'asset_1_reserves': pool.asset_1_reserves,
                'asset_2_reserves': pool.asset_2_reserves,
                'total_liquidity': pool.total_liquidity,
                'asset_1': pool.asset_1,
                'asset_2': pool.asset_2
            }
        except Exception as e:
            logger.error(f"Failed to get pool info: {e}")
            return {}
    
    async def _calculate_price_impact(self, pool_info: Dict, amount_in: Decimal, 
                                    from_token, to_token) -> Decimal:
        """Calculate price impact of the swap"""
        try:
            if not pool_info:
                return Decimal('0')
            
            # Simplified price impact calculation
            # This is a basic implementation - you might want to use more sophisticated calculation
            from_reserves = Decimal(pool_info.get('asset_1_reserves', 0))
            to_reserves = Decimal(pool_info.get('asset_2_reserves', 0))
            
            if from_reserves == 0 or to_reserves == 0:
                return Decimal('0')
            
            # Calculate price impact as percentage
            amount_in_base = amount_in * (10 ** from_token.decimals)
            impact = (amount_in_base / from_reserves) * 100
            
            return min(impact, Decimal('100'))  # Cap at 100%
            
        except Exception as e:
            logger.error(f"Price impact calculation failed: {e}")
            return Decimal('0')
    
    async def get_supported_tokens(self) -> List[Dict]:
        """Get list of supported tokens for swapping"""
        supported = []
        for symbol, asset in self.assets_cache.items():
            if asset:
                supported.append({
                    'symbol': symbol,
                    'asset_id': asset.id,
                    'name': asset.name,
                    'decimals': asset.decimals,
                    'unit_name': asset.unit_name
                })
        return supported
    
    async def get_pool_liquidity(self, token_a, token_b) -> Optional[Dict]:
        """Get liquidity information for a token pair"""
        try:
            asset_a = await self._get_asset(token_a)
            asset_b = await self._get_asset(token_b)
            
            if not asset_a or not asset_b:
                return None
            
            pool = await self._get_pool(asset_a, asset_b)
            if not pool:
                return None
            
            try:
                pool_info = await self._get_pool_info(pool)
            
                return {
                    'token_a_reserves': Decimal(pool_info.get('asset_1_reserves', 0)) / (10 ** token_a.decimals),
                    'token_b_reserves': Decimal(pool_info.get('asset_2_reserves', 0)) / (10 ** token_b.decimals),
                    'total_liquidity': pool_info.get('total_liquidity', 0),
                    'apy': await self._estimate_pool_apy(pool_info)  # Implement if needed
                }
            except Exception as e:
                logger.error(f"Failed to process pool info: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to get pool liquidity: {e}")
            return None
    
    async def _estimate_pool_apy(self, pool_info: Dict) -> Decimal:
        """Estimate pool APY - placeholder implementation"""
        # This would require historical data to calculate properly
        # For now, return a placeholder
        return Decimal('0')
    
    async def health_check(self) -> bool:
        """Check if Tinyman client is healthy"""
        try:
            # Try to fetch ALGO asset as a simple health check
            if 'ALGO' in self.assets_cache:
                return True
            
            # Try to fetch ALGO if not in cache
            asset = self.client.fetch_asset(0)
            return asset is not None
            
        except Exception as e:
            logger.error(f"Tinyman health check failed: {e}")
            return False
