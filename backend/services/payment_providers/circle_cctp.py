# File Location: backend/services/payment_providers/circle_cctp.py
import logging
import asyncio
import aiohttp
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional
from config import Settings

logger = logging.getLogger(__name__)

class CircleCCTPProvider:
    """
    Circle Cross-Chain Transfer Protocol (CCTP) for international USDC transfers.
    Supports Ethereum, Polygon, Avalanche, Arbitrum, and Optimism.
    Near-zero fees for cross-border transfers.
    """
    
    # Supported networks and their chain IDs
    SUPPORTED_NETWORKS = {
        'ethereum': {'chain_id': 0, 'rpc_url': 'https://eth-mainnet.alchemyapi.io/v2/'},
        'polygon': {'chain_id': 7, 'rpc_url': 'https://polygon-rpc.com/'},
        'avalanche': {'chain_id': 1, 'rpc_url': 'https://api.avax.network/ext/bc/C/rpc'},
        'arbitrum': {'chain_id': 3, 'rpc_url': 'https://arb1.arbitrum.io/rpc'},
        'optimism': {'chain_id': 2, 'rpc_url': 'https://mainnet.optimism.io'}
    }
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = settings.CIRCLE_API_KEY.get_secret_value()
        self.base_url = "https://api.circle.com/v1"
        
        # Default to Ethereum mainnet
        self.default_source_chain = 'ethereum'
        
        self._validate_config()
    
    def _validate_config(self):
        if not self.api_key:
            raise ValueError("Circle API key is required")
        
        logger.info("✅ Circle CCTP Processor initialized")
    
    async def _request_with_retry(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """HTTP request with retry logic"""
        headers = kwargs.get('headers', {})
        headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        kwargs['headers'] = headers
        
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(method, url, **kwargs) as response:
                        data = await response.json()
                        
                        if response.status in [200, 201]:
                            return data
                        
                        # Rate limiting
                        if response.status == 429:
                            wait_time = retry_delay * (2 ** attempt)
                            logger.warning(f"Circle API rate limited. Retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                        
                        logger.error(f"Circle API error: {response.status} - {data}")
                        if attempt == max_retries - 1:
                            return {'error': data, 'status_code': response.status}
                        
            except aiohttp.ClientError as e:
                logger.error(f"HTTP error attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay * (2 ** attempt))
        
        raise Exception("Circle API max retries exceeded")
    
    async def get_supported_chains(self) -> Dict[str, Any]:
        """Get list of supported chains for CCTP"""
        try:
            url = f"{self.base_url}/config"
            data = await self._request_with_retry('GET', url)
            
            if 'error' in data:
                return {'success': False, 'message': 'Failed to fetch supported chains'}
            
            return {'success': True, 'chains': self.SUPPORTED_NETWORKS}
            
        except Exception as e:
            logger.error(f"💥 Error fetching chains: {e}")
            return {'success': False, 'message': str(e)}
    
    async def initiate_cross_chain_transfer(self, 
                                          amount: Decimal, 
                                          recipient_address: str,
                                          destination_chain: str,
                                          tx_ref: str,
                                          source_chain: str = None) -> Dict[str, Any]:
        """
        Initiate a cross-chain USDC transfer using Circle CCTP
        
        Args:
            amount: Amount in USDC
            recipient_address: Destination wallet address
            destination_chain: Target blockchain network
            tx_ref: Transaction reference
            source_chain: Source blockchain (defaults to ethereum)
        """
        
        source_chain = source_chain or self.default_source_chain
        
        if destination_chain not in self.SUPPORTED_NETWORKS:
            return {
                'success': False, 
                'message': f'Unsupported destination chain: {destination_chain}'
            }
        
        if source_chain not in self.SUPPORTED_NETWORKS:
            return {
                'success': False, 
                'message': f'Unsupported source chain: {source_chain}'
            }
        
        # Convert amount to USDC base units (6 decimals)
        usdc_amount = int(float(amount) * 1_000_000)
        
        payload = {
            "amount": {
                "amount": str(usdc_amount),
                "currency": "USD"
            },
            "source": {
                "type": "blockchain",
                "chain": self.SUPPORTED_NETWORKS[source_chain]['chain_id']
            },
            "destination": {
                "type": "blockchain", 
                "chain": self.SUPPORTED_NETWORKS[destination_chain]['chain_id'],
                "address": recipient_address
            },
            "idempotencyKey": tx_ref,
            "metadata": {
                "beneficiaryEmail": "",
                "reference": tx_ref,
                "platform": "Seamount.io"
            }
        }
        
        try:
            url = f"{self.base_url}/transfers"
            data = await self._request_with_retry('POST', url, json=payload)
            
            if 'error' in data:
                return {
                    'success': False,
                    'message': data.get('error', {}).get('message', 'Transfer initiation failed')
                }
            
            transfer_data = data.get('data', {})
            
            logger.info(f"✅ Circle CCTP transfer initiated: {tx_ref}")
            return {
                'success': True,
                'transfer_id': transfer_data.get('id'),
                'status': transfer_data.get('status'),
                'source_wallet_id': transfer_data.get('source', {}).get('id'),
                'destination_wallet_id': transfer_data.get('destination', {}).get('id'),
                'tx_ref': tx_ref
            }
            
        except Exception as e:
            logger.error(f"💥 Circle CCTP transfer exception: {e}")
            return {'success': False, 'message': str(e)}
    
    async def verify_transfer(self, transfer_id: str) -> Dict[str, Any]:
        """Check the status of a CCTP transfer"""
        
        try:
            url = f"{self.base_url}/transfers/{transfer_id}"
            data = await self._request_with_retry('GET', url)
            
            if 'error' in data:
                return {
                    'verified': False,
                    'message': data.get('error', {}).get('message', 'Transfer verification failed')
                }
            
            transfer_data = data.get('data', {})
            status = transfer_data.get('status', 'pending')
            
            return {
                'verified': status == 'complete',
                'status': status,
                'amount': transfer_data.get('amount', {}).get('amount', '0'),
                'currency': 'USDC',
                'transfer_id': transfer_id,
                'transaction_hash': transfer_data.get('transactionHash'),
                'fees': transfer_data.get('fees', []),
                'created_at': transfer_data.get('createDate'),
                'updated_at': transfer_data.get('updateDate')
            }
            
        except Exception as e:
            logger.error(f"💥 Circle verify transfer exception: {e}")
            return {'verified': False, 'message': str(e)}
    
    async def get_wallet_balance(self, wallet_id: Optional[str] = None) -> Dict[str, Any]:
        """Get USDC wallet balance"""
        
        try:
            if wallet_id:
                url = f"{self.base_url}/wallets/{wallet_id}"
            else:
                # Get master wallet or first available wallet
                url = f"{self.base_url}/wallets"
            
            data = await self._request_with_retry('GET', url)
            
            if 'error' in data:
                return {
                    'success': False,
                    'message': 'Failed to fetch wallet balance'
                }
            
            if wallet_id:
                wallet_data = data.get('data', {})
                balances = wallet_data.get('balances', [])
            else:
                wallets = data.get('data', [])
                if not wallets:
                    return {'success': False, 'message': 'No wallets found'}
                balances = wallets[0].get('balances', [])
            
            usdc_balance = next((b for b in balances if b['currency'] == 'USD'), {'amount': '0'})
            
            return {
                'success': True,
                'balance': float(usdc_balance['amount']),
                'currency': 'USDC'
            }
            
        except Exception as e:
            logger.error(f"💥 Circle balance check exception: {e}")
            return {'success': False, 'message': str(e)}
    
    async def estimate_transfer_fee(self, 
                                  amount: Decimal,
                                  source_chain: str,
                                  destination_chain: str) -> Dict[str, Any]:
        """
        Estimate cross-chain transfer fees
        Note: CCTP typically has very low fees (gas only)
        """
        
        # Basic validation
        if source_chain not in self.SUPPORTED_NETWORKS:
            return {'success': False, 'message': f'Unsupported source chain: {source_chain}'}
        
        if destination_chain not in self.SUPPORTED_NETWORKS:
            return {'success': False, 'message': f'Unsupported destination chain: {destination_chain}'}
        
        # CCTP fee estimation (approximate values)
        base_fees = {
            'ethereum': Decimal('25.0'),    # ~$25 ETH gas
            'polygon': Decimal('0.5'),      # ~$0.50 MATIC gas
            'avalanche': Decimal('2.0'),    # ~$2 AVAX gas
            'arbitrum': Decimal('3.0'),     # ~$3 ARB gas
            'optimism': Decimal('2.0')      # ~$2 OP gas
        }
        
        source_fee = base_fees.get(source_chain, Decimal('10.0'))
        destination_fee = base_fees.get(destination_chain, Decimal('10.0'))
        
        # Same chain = no transfer needed
        if source_chain == destination_chain:
            total_fee = Decimal('0.0')
        else:
            total_fee = source_fee + destination_fee
        
        return {
            'success': True,
            'estimated_fee': float(total_fee),
            'fee_currency': 'USD',
            'source_chain_fee': float(source_fee),
            'destination_chain_fee': float(destination_fee),
            'breakdown': {
                'cctp_protocol_fee': 0.0,  # CCTP itself is free
                'source_gas_fee': float(source_fee),
                'destination_gas_fee': float(destination_fee)
            }
        }