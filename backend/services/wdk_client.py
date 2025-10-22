# File: backend/services/wdk_client.py
"""
ROCK SOLID WDK Client - Follows Tether's Official Patterns
Based on: https://docs.wallet.tether.io/start-building/react-native-quickstart
"""

import logging
import aiohttp
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime

from backend.config import get_settings

logger = logging.getLogger(__name__)

class WDKClient:
    """
    Production-ready Tether WDK client
    Implements patterns from official React Native starter
    """
    
    # Supported chains (from Tether docs)
    SUPPORTED_CHAINS = [
        'bitcoin',      # SegWit native transfers
        'ethereum',     # Gasless with sponsored gas
        'polygon',      # Gasless with sponsored gas
        'arbitrum',     # Gasless with sponsored gas
        'ton',          # Native transfers
        'tron',         # USDT native
        'solana'        # High-speed
    ]
    
    # Gasless-enabled chains (Account Abstraction)
    GASLESS_CHAINS = ['ethereum', 'polygon', 'arbitrum']
    
    def __init__(self):
        self.settings = get_settings()
        
        # Your WDK microservice (handles wallet ops)
        self.base_url = self.settings.WDK_SERVICE_URL or "http://localhost:3001"
        
        # ✅ CRITICAL: Get API key from environment (no fallback)
        if not self.settings.WDK_API_KEY:
            logger.error("❌ FATAL: WDK_API_KEY not configured in environment!")
            logger.error("   Add WDK_API_KEY to backend/.env or Render environment")
            raise ValueError("WDK_API_KEY environment variable required")
        
        self.api_key = self.settings.WDK_API_KEY.get_secret_value()
        
        # WDK Indexer API (balance queries, tx history)
        self.indexer_url = "https://indexer-api.tether.io" if self.api_key else None
        
        if self.indexer_url:
            logger.info(f"✅ WDK Client initialized: {len(self.SUPPORTED_CHAINS)} chains, Indexer: ON")
            logger.info(f"   Using API Key: {self.api_key[:10]}...")
        else:
            logger.warning(f"⚠️ WDK Client initialized WITHOUT Indexer API key")
            logger.warning(f"   Get key from: https://wdk-api.tether.io")
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        use_indexer: bool = False
    ) -> Dict[str, Any]:
        """Make authenticated HTTP request"""
        
        # Choose base URL
        if use_indexer:
            if not self.indexer_url:
                raise Exception("WDK Indexer API key not configured")
            base = self.indexer_url
        else:
            base = self.base_url
        
        url = f"{base}{endpoint}"
        
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key if use_indexer else '5a2de129c82deb82d71667613c3a76a7d69f9f4536b779f36f03deb572061ed7'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == 'GET':
                    async with session.get(url, headers=headers) as response:
                        response.raise_for_status()
                        return await response.json()
                else:  # POST
                    async with session.post(url, json=data, headers=headers) as response:
                        response.raise_for_status()
                        return await response.json()
                        
        except aiohttp.ClientError as e:
            logger.error(f"❌ WDK request failed ({method} {endpoint}): {e}")
            raise Exception(f"WDK service unavailable: {str(e)}")
    
    # ========== WALLET CREATION (Tether Pattern) ==========
    
    async def generate_seed(self) -> Dict[str, Any]:
        """Generate encrypted mnemonic seed phrase"""
        result = await self._make_request('POST', '/wallet/generate-seed')
        
        if not result.get('success'):
            raise Exception("Seed generation failed")
        
        return {
            'encrypted_seed': result['encrypted_seed'],
            'created_at': datetime.utcnow().isoformat()
        }
    
    async def create_wallet(
        self, 
        encrypted_seed: str, 
        chains: Optional[List[str]] = None,
        enable_gasless: bool = True
    ) -> Dict[str, Any]:
        """
        Create wallets on specified chains
        Follows Tether's multi-chain wallet pattern
        """
        
        if chains is None:
            # Default: Essential chains from Tether docs
            chains = ['bitcoin', 'ethereum', 'polygon', 'ton']
        
        # Validate chains
        invalid_chains = [c for c in chains if c not in self.SUPPORTED_CHAINS]
        if invalid_chains:
            raise ValueError(f"Unsupported chains: {invalid_chains}")
        
        payload = {
            'encrypted_seed': encrypted_seed,
            'chains': chains,
            'enable_gasless': enable_gasless and any(c in self.GASLESS_CHAINS for c in chains)
        }
        
        result = await self._make_request('POST', '/wallet/create', data=payload)
        
        if not result.get('success'):
            raise Exception(f"Wallet creation failed: {result.get('error', 'Unknown error')}")
        
        logger.info(f"✅ Wallets created on {len(result['wallets'])} chains")
        return result
    
    # ========== BALANCE QUERIES (Using Indexer API) ==========
    
    async def get_balance(
    self, 
    address: str, 
    chain: str,
    use_indexer: bool = True
) -> Decimal:
    """Get balance for address on specific chain"""
    
    if chain not in self.SUPPORTED_CHAINS:
        raise ValueError(f"Unsupported chain: {chain}")
    
    # Try Indexer first (if available)
    if use_indexer and self.indexer_url:
        try:
            result = await self._make_request(
                'GET', 
                f'/v1/balance/{chain}/{address}',
                use_indexer=True
            )
            return Decimal(str(result.get('balance', '0')))
        except Exception as e:
            logger.warning(f"⚠️ Indexer failed, using direct query: {e}")
    
    # ✅ FIX: Use GET request with query params (not POST with body)
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': self.api_key
            }
            
            # Use GET with query parameters
            url = f"{self.base_url}/wallet/balance"
            params = {
                'chain': chain,
                'address': address
            }
            
            async with session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                result = await response.json()
                
                if not result.get('success'):
                    logger.error(f"Balance query failed: {result.get('error')}")
                    return Decimal('0')
                
                return Decimal(str(result.get('balance', '0')))
                
    except Exception as e:
        logger.error(f"❌ Balance query failed for {chain}: {e}")
        return Decimal('0')
    
    async def get_balances_multi_chain(
        self, 
        addresses: Dict[str, str]
    ) -> Dict[str, Dict[str, Any]]:
        """Get balances across multiple chains efficiently"""
        
        balances = {}
        
        # Try batch query via Indexer
        if self.indexer_url:
            try:
                result = await self._make_request(
                    'POST',
                    '/v1/balances/batch',
                    data={'addresses': addresses},
                    use_indexer=True
                )
                return result.get('balances', {})
            except Exception as e:
                logger.warning(f"⚠️ Batch indexer query failed: {e}")
        
        # Fallback: Query each chain individually
        for chain, address in addresses.items():
            try:
                balance = await self.get_balance(address, chain, use_indexer=False)
                balances[chain] = {
                    'balance': float(balance),
                    'address': address,
                    'chain': chain
                }
            except Exception as e:
                logger.error(f"❌ Balance query failed for {chain}: {e}")
                balances[chain] = {'balance': 0.0, 'error': str(e)}
        
        return balances
    
    # ========== TRANSACTIONS ==========
    
    async def send_transaction(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
        asset: str,
        chain: str,
        encrypted_seed: str,
        enable_gasless: bool = True
    ) -> Dict[str, Any]:
        """Send transaction on specified chain"""
        
        if chain not in self.SUPPORTED_CHAINS:
            raise ValueError(f"Unsupported chain: {chain}")
        
        # Check if gasless is available
        use_gasless = enable_gasless and chain in self.GASLESS_CHAINS
        
        payload = {
            'from_address': from_address,
            'to_address': to_address,
            'amount': str(amount),
            'asset': asset,
            'chain': chain,
            'encrypted_seed': encrypted_seed,
            'gasless': use_gasless
        }
        
        result = await self._make_request('POST', '/wallet/send', data=payload)
        
        if not result.get('success'):
            raise Exception(f"Transaction failed: {result.get('error', 'Unknown error')}")
        
        result['gasless_used'] = use_gasless
        result['chain_used'] = chain
        
        logger.info(f"✅ Transaction sent on {chain} ({'gasless' if use_gasless else 'standard'})")
        return result
    
    # ========== UTILITY METHODS ==========
    
    def is_chain_supported(self, chain: str) -> bool:
        """Check if chain is supported"""
        return chain.lower() in self.SUPPORTED_CHAINS
    
    def is_gasless_available(self, chain: str) -> bool:
        """Check if gasless transactions available"""
        return chain.lower() in self.GASLESS_CHAINS
    
    async def health_check(self) -> Dict[str, Any]:
        """Check WDK service health"""
        try:
            result = await self._make_request('GET', '/health')
            return {
                'status': 'healthy',
                'wdk_service': result,
                'indexer_enabled': self.indexer_url is not None,
                'supported_chains': self.SUPPORTED_CHAINS
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'supported_chains': self.SUPPORTED_CHAINS
            }