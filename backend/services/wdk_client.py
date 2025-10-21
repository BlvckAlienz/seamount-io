# File: backend/services/wdk_client.py
"""
Enhanced WDK Client - Full Tether WDK Integration
Supports: Bitcoin, Lightning, Ethereum, Polygon, Arbitrum, TON, TRON, Solana
Features: Gasless transactions, WDK Indexer, Account Abstraction
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
    Production-ready Tether WDK client with full multi-chain support
    """
    
    # All supported chains (production ready)
    SUPPORTED_CHAINS = [
        'bitcoin',      # SegWit native transfers
        'lightning',    # Instant BTC micropayments (Spark)
        'ethereum',     # EVM + Account Abstraction
        'polygon',      # Gasless transactions
        'arbitrum',     # Gasless L2
        'ton',          # High-performance
        'tron',         # USDT native chain
        'solana'        # High-speed transactions
    ]
    
    # Gasless-enabled chains (Account Abstraction)
    GASLESS_CHAINS = ['ethereum', 'polygon', 'arbitrum']
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.WDK_SERVICE_URL or "http://localhost:3001"
        self.api_key = self.settings.WDK_API_KEY.get_secret_value() if self.settings.WDK_API_KEY else None
        
        # Optional: WDK Indexer API for faster balance queries
        self.indexer_api_key = getattr(self.settings, 'WDK_INDEXER_API_KEY', None)
        self.indexer_url = "https://indexer-api.tether.io" if self.indexer_api_key else None
        
        logger.info(f"✅ WDK Client initialized: {len(self.SUPPORTED_CHAINS)} chains, Indexer: {'ON' if self.indexer_url else 'OFF'}")
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        use_indexer: bool = False
    ) -> Dict[str, Any]:
        """Make authenticated HTTP request to WDK service or Indexer"""
        
        base = self.indexer_url if use_indexer else self.base_url
        url = f"{base}{endpoint}"
        
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.indexer_api_key if use_indexer else self.api_key
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
        except Exception as e:
            logger.error(f"❌ Unexpected error in WDK request: {e}")
            raise
    
    # ========== WALLET CREATION ==========
    
    async def generate_seed(self) -> Dict[str, Any]:
        """Generate new mnemonic seed phrase (encrypted)"""
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
        
        Args:
            encrypted_seed: Encrypted mnemonic from generate_seed()
            chains: List of chains to create wallets on (default: all)
            enable_gasless: Enable Account Abstraction on supported chains
        """
        
        if chains is None:
            chains = self.SUPPORTED_CHAINS
        
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
    
    # ========== BALANCE QUERIES ==========
    
    async def get_balance(
        self, 
        address: str, 
        chain: str,
        use_indexer: bool = True
    ) -> Decimal:
        """
        Get balance for address on specific chain
        
        Args:
            address: Wallet address
            chain: Blockchain identifier
            use_indexer: Use WDK Indexer API for faster queries (if available)
        """
        
        if chain not in self.SUPPORTED_CHAINS:
            raise ValueError(f"Unsupported chain: {chain}")
        
        # Try WDK Indexer first (faster)
        if use_indexer and self.indexer_url:
            try:
                result = await self._make_request(
                    'GET', 
                    f'/balance/{chain}/{address}',
                    use_indexer=True
                )
                return Decimal(str(result.get('balance', '0')))
            except Exception as e:
                logger.warning(f"⚠️ Indexer failed, falling back to direct query: {e}")
        
        # Fallback: Direct WDK service query
        result = await self._make_request(
            'GET', 
            f'/wallet/balance?address={address}&chain={chain}'
        )
        
        return Decimal(str(result.get('balance', '0')))
    
    async def get_balances_multi_chain(
        self, 
        addresses: Dict[str, str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get balances across multiple chains efficiently
        
        Args:
            addresses: Dict of {chain: address}
        
        Returns:
            {chain: {balance: Decimal, usd_value: Decimal}}
        """
        
        balances = {}
        
        # Use WDK Indexer for batch query if available
        if self.indexer_url:
            try:
                result = await self._make_request(
                    'POST',
                    '/balances/batch',
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
    
    # ========== TRANSACTION HISTORY ==========
    
    async def get_transaction_history(
        self,
        address: str,
        chain: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get transaction history for address (requires WDK Indexer)"""
        
        if not self.indexer_url:
            logger.warning("⚠️ Transaction history requires WDK Indexer API key")
            return []
        
        try:
            result = await self._make_request(
                'GET',
                f'/transactions/{chain}/{address}?limit={limit}',
                use_indexer=True
            )
            return result.get('transactions', [])
        except Exception as e:
            logger.error(f"❌ Transaction history query failed: {e}")
            return []
    
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
        """
        Send transaction on specified chain
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            amount: Amount to send
            asset: Asset identifier (e.g., 'USDT', 'BTC', 'ETH')
            chain: Blockchain to use
            encrypted_seed: Encrypted wallet seed for signing
            enable_gasless: Use Account Abstraction if available
        """
        
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
        
        # Add metadata for revenue tracking
        result['gasless_used'] = use_gasless
        result['chain_used'] = chain
        
        logger.info(f"✅ Transaction sent on {chain} ({'gasless' if use_gasless else 'standard'})")
        return result
    
    # ========== LIGHTNING NETWORK ==========
    
    async def create_lightning_invoice(
        self,
        amount_sats: int,
        description: str = "Seamount payment",
        expiry_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Create Lightning Network invoice for receiving BTC
        
        Args:
            amount_sats: Amount in satoshis
            description: Invoice description
            expiry_seconds: Invoice expiry time
        """
        
        payload = {
            'amount_sats': amount_sats,
            'description': description,
            'expiry': expiry_seconds
        }
        
        result = await self._make_request('POST', '/lightning/invoice', data=payload)
        
        if not result.get('success'):
            raise Exception("Lightning invoice creation failed")
        
        return {
            'invoice': result['invoice'],
            'payment_hash': result['payment_hash'],
            'expires_at': result['expires_at'],
            'amount_sats': amount_sats
        }
    
    async def pay_lightning_invoice(
        self,
        invoice: str,
        encrypted_seed: str
    ) -> Dict[str, Any]:
        """
        Pay Lightning Network invoice
        
        Args:
            invoice: BOLT11 invoice string
            encrypted_seed: Encrypted wallet seed
        """
        
        payload = {
            'invoice': invoice,
            'encrypted_seed': encrypted_seed
        }
        
        result = await self._make_request('POST', '/lightning/pay', data=payload)
        
        if not result.get('success'):
            raise Exception(f"Lightning payment failed: {result.get('error', 'Unknown')}")
        
        logger.info(f"✅ Lightning payment sent: {result.get('amount_sats')} sats")
        return result
    
    # ========== GASLESS TRANSACTIONS ==========
    
    async def estimate_gasless_fee(
        self,
        chain: str,
        asset: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Estimate fee for gasless transaction (paid in USDT)
        
        Returns fee breakdown with markup opportunities
        """
        
        if chain not in self.GASLESS_CHAINS:
            raise ValueError(f"Gasless not supported on {chain}")
        
        payload = {
            'chain': chain,
            'asset': asset,
            'amount': str(amount)
        }
        
        result = await self._make_request('POST', '/gasless/estimate', data=payload)
        
        return {
            'gas_cost_native': Decimal(result.get('gas_cost_native', '0')),  # ETH/MATIC
            'gas_cost_usdt': Decimal(result.get('gas_cost_usdt', '0')),  # USDT equivalent
            'platform_fee': Decimal(result.get('platform_fee', '0')),
            'total_usdt': Decimal(result.get('total_usdt', '0')),
            'savings_percent': result.get('savings_percent', 0)
        }
    
    # ========== UTILITY METHODS ==========
    
    def is_chain_supported(self, chain: str) -> bool:
        """Check if chain is supported"""
        return chain.lower() in self.SUPPORTED_CHAINS
    
    def is_gasless_available(self, chain: str) -> bool:
        """Check if gasless transactions available on chain"""
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