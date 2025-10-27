# File: backend/services/wdk_client.py
"""
ROCK SOLID WDK Client - Follows Tether's Official Patterns
With comprehensive retry logic and circuit breaker pattern
"""

import logging
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta

from backend.config import get_settings

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit breaker pattern for WDK service resilience"""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self):
        if self.state == "OPEN":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = "HALF_OPEN"
                return True
            return False
        return True
    
    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"🚨 Circuit breaker OPENED after {self.failure_count} failures")

class WDKClient:
    """
    Production-ready Tether WDK client with comprehensive resilience
    Implements patterns from official React Native starter
    """
    
    # Supported chains (from Tether docs)
    SUPPORTED_CHAINS = [
        'bitcoin',      # ✅ Available via @tetherto/wdk-wallet-btc
        'ethereum',     # ✅ Available via @tetherto/wdk-wallet-evm  
        'polygon',      # ✅ Available via @tetherto/wdk-wallet-evm
        'tron',         # ✅ Available via @tetherto/wdk-wallet-tron
        # 'arbitrum',   # ❌ Commented out - no package yet
        # 'ton',        # ❌ Commented out - no package yet  
        # 'solana'      # ❌ Commented out - no package yet
    ]
    
    # EVM gasless chains that use the same wallet manager
    GASLESS_CHAINS = ['ethereum', 'polygon']  # Add arbitrum later when available
    
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
        
        # Circuit breaker for service resilience
        self.circuit_breaker = CircuitBreaker()
        
        # Service health tracking
        self.service_healthy = True
        self.last_health_check = None
        
        if self.indexer_url:
            logger.info(f"✅ WDK Client initialized: {len(self.SUPPORTED_CHAINS)} chains, Indexer: ON")
            logger.info(f"   Using API Key: {self.api_key[:10]}...")
        else:
            logger.warning(f"⚠️ WDK Client initialized WITHOUT Indexer API key")
            logger.warning(f"   Get key from: https://wdk-api.tether.io")
    
    async def _make_request_with_retry(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        use_indexer: bool = False,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> Dict[str, Any]:
        """Make authenticated HTTP request with exponential backoff retry"""
        
        # Check circuit breaker first
        if not self.circuit_breaker.can_execute():
            raise Exception("WDK service temporarily unavailable (circuit breaker open)")
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
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
                
                async with aiohttp.ClientSession() as session:
                    if method == 'GET':
                        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                            if response.status in [502, 503, 504]:
                                raise aiohttp.ClientResponseError(
                                    request_info=response.request_info,
                                    history=response.history,
                                    status=response.status,
                                    message=f"Service unavailable: {response.status}"
                                )
                            response.raise_for_status()
                            result = await response.json()
                            
                            # Success - record it in circuit breaker
                            self.circuit_breaker.record_success()
                            self.service_healthy = True
                            return result
                    else:  # POST, PUT, etc.
                        async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                            if response.status in [502, 503, 504]:
                                raise aiohttp.ClientResponseError(
                                    request_info=response.request_info,
                                    history=response.history,
                                    status=response.status,
                                    message=f"Service unavailable: {response.status}"
                                )
                            response.raise_for_status()
                            result = await response.json()
                            
                            # Success - record it in circuit breaker
                            self.circuit_breaker.record_success()
                            self.service_healthy = True
                            return result
                            
            except aiohttp.ClientError as e:
                last_exception = e
                logger.warning(f"⚠️ WDK request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                # Record failure in circuit breaker
                self.circuit_breaker.record_failure()
                self.service_healthy = False
                
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) * (0.5 + 0.5 * asyncio.get_event_loop().time() % 1)
                    logger.info(f"Retrying WDK request in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ All {max_retries} attempts failed for {method} {endpoint}")
        
        # All retries failed
        raise Exception(f"WDK service unavailable after {max_retries} attempts: {str(last_exception)}")
    
    # Alias for backward compatibility
    _make_request = _make_request_with_retry
    
    # ========== WALLET CREATION (Tether Pattern) ==========
    
    async def generate_seed(self) -> Dict[str, Any]:
        """Generate encrypted mnemonic seed phrase"""
        try:
            result = await self._make_request('POST', '/wallet/generate-seed')
            
            if not result.get('success'):
                raise Exception("Seed generation failed")
            
            return {
                'encrypted_seed': result['encrypted_seed'],
                'created_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Seed generation failed: {e}")
            # Fallback: generate locally (for development)
            if self.settings.ENVIRONMENT == "development":
                return self._generate_seed_fallback()
            raise
    
    def _generate_seed_fallback(self) -> Dict[str, Any]:
        """Fallback seed generation for development"""
        logger.warning("Using fallback seed generation for development")
        return {
            'encrypted_seed': 'dev_fallback_encrypted_seed_' + datetime.utcnow().isoformat(),
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
    ) -> Dict[str, Any]:
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
                return result
            except Exception as e:
                logger.warning(f"⚠️ Indexer failed, using direct query: {e}")
        
        # ✅ FIXED: Use GET request with query params (not POST with body)
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
                
                async with session.get(url, headers=headers, params=params, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"Balance query returned {response.status}")
                        return {'balance': '0', 'success': False}
                    
                    result = await response.json()
                    
                    if not result.get('success'):
                        logger.error(f"Balance query failed: {result.get('error')}")
                        return {'balance': '0', 'success': False}
                    
                    return result
                    
        except Exception as e:
            logger.error(f"❌ Balance query failed for {chain}: {e}")
            return {'balance': '0', 'success': False}
    
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
                balance_data = await self.get_balance(address, chain, use_indexer=False)
                balance = Decimal(str(balance_data.get('balance', '0')))
                balances[chain] = {
                    'balance': float(balance),
                    'address': address,
                    'chain': chain,
                    'success': balance_data.get('success', False)
                }
            except Exception as e:
                logger.error(f"❌ Balance query failed for {chain}: {e}")
                balances[chain] = {'balance': 0.0, 'error': str(e), 'success': False}
        
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
                'supported_chains': self.SUPPORTED_CHAINS,
                'circuit_breaker': self.circuit_breaker.state
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'supported_chains': self.SUPPORTED_CHAINS,
                'circuit_breaker': self.circuit_breaker.state
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get current service status"""
        return {
            'healthy': self.service_healthy,
            'circuit_breaker_state': self.circuit_breaker.state,
            'failure_count': self.circuit_breaker.failure_count,
            'last_failure': self.circuit_breaker.last_failure_time.isoformat() if self.circuit_breaker.last_failure_time else None
        }