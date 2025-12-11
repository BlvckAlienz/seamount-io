# File: backend/services/wallet_connect_service.py
"""
WalletConnect Integration Service for Base + Celo
Enables users to connect existing wallets without key management
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from eth_account.messages import encode_defunct
from web3 import Web3

from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class WalletConnectService:
    """
    Manage WalletConnect sessions for Base and Celo chains
    Users connect existing wallets (MetaMask, Coinbase Wallet, MiniPay, Valora)
    """
    
    # Supported chains via WalletConnect
    WALLET_CONNECT_CHAINS = {
        'base': {
            'chain_id': 8453,
            'rpc_url': 'https://mainnet.base.org',
            'name': 'Base',
            'native_currency': 'ETH',
            'explorer': 'https://basescan.org'
        },
        'celo': {
            'chain_id': 42220,
            'rpc_url': 'https://forno.celo.org',
            'name': 'Celo',
            'native_currency': 'CELO',
            'explorer': 'https://celoscan.io'
        }
    }
    
    # Popular wallet providers
    WALLET_PROVIDERS = [
        'metamask',
        'coinbase_wallet',
        'walletconnect',
        'minipay',
        'valora',
        'rabby',
        'rainbow',
        'trust_wallet'
    ]
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        logger.info("✅ WalletConnectService initialized (Base + Celo)")
    
    async def connect_wallet(
        self,
        user_id: str,
        blockchain: str,
        address: str,
        wallet_provider: str,
        signature: Optional[str] = None,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect external wallet via WalletConnect
        
        Args:
            user_id: User ID
            blockchain: 'base' or 'celo'
            address: Wallet address (EVM format: 0x...)
            wallet_provider: 'metamask', 'coinbase_wallet', etc.
            signature: Optional signature for verification
            message: Optional message that was signed
        
        Returns:
            Connection result with wallet info
        """
        
        try:
            # Validate chain
            if blockchain not in self.WALLET_CONNECT_CHAINS:
                raise ValueError(f"Unsupported chain: {blockchain}. Supported: {list(self.WALLET_CONNECT_CHAINS.keys())}")
            
            # Validate address format
            if not Web3.is_address(address):
                raise ValueError(f"Invalid EVM address: {address}")
            
            # Checksum address (0xABC... format)
            address = Web3.to_checksum_address(address)
            
            logger.info(f"🔗 Connecting {blockchain} wallet: {address[:10]}... via {wallet_provider}")
            
            # Optional: Verify signature (proves user owns the wallet)
            if signature and message:
                is_valid = self._verify_signature(address, message, signature)
                if not is_valid:
                    raise ValueError("Invalid signature - user doesn't own this wallet")
                logger.info(f"✅ Signature verified for {address[:10]}...")
            
            # Check if wallet already connected
            existing = await self._get_connected_wallet(user_id, blockchain)
            if existing and existing['address'].lower() == address.lower():
                logger.info(f"ℹ️ Wallet already connected: {address[:10]}...")
                return {
                    'success': True,
                    'message': 'Wallet already connected',
                    'wallet': existing,
                    'is_new': False
                }
            
            # Store in multi_chain_addresses table
            wallet_data = {
                'user_id': user_id,
                'blockchain': blockchain,
                'address': address,
                'connection_type': 'wallet_connect',
                'wallet_provider': wallet_provider,
                'wallet_type': 'wallet_connect',
                'encrypted_seed': None,  # No seed for connected wallets
                'is_primary': True,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Upsert (update if exists, insert if new)
            result = self.db.supabase.table('multi_chain_addresses').upsert(
                wallet_data,
                on_conflict='user_id,blockchain'
            ).execute()
            
            if not result.data:
                raise Exception("Failed to store wallet connection")
            
            # Log connection history
            connection_log = {
                'user_id': user_id,
                'blockchain': blockchain,
                'address': address,
                'wallet_provider': wallet_provider,
                'connection_type': 'wallet_connect',
                'is_active': True,
                'metadata': {
                    'chain_id': self.WALLET_CONNECT_CHAINS[blockchain]['chain_id'],
                    'verified_signature': bool(signature)
                }
            }
            
            self.db.supabase.table('wallet_connections').insert(connection_log).execute()
            
            logger.info(f"✅ {blockchain} wallet connected successfully: {address[:10]}...")
            
            return {
                'success': True,
                'message': f'{blockchain.capitalize()} wallet connected successfully',
                'wallet': {
                    'blockchain': blockchain,
                    'address': address,
                    'wallet_provider': wallet_provider,
                    'chain_id': self.WALLET_CONNECT_CHAINS[blockchain]['chain_id'],
                    'chain_name': self.WALLET_CONNECT_CHAINS[blockchain]['name'],
                    'explorer': f"{self.WALLET_CONNECT_CHAINS[blockchain]['explorer']}/address/{address}"
                },
                'is_new': True
            }
            
        except Exception as e:
            logger.error(f"❌ Wallet connection failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to connect {blockchain} wallet'
            }
    
    async def disconnect_wallet(
        self,
        user_id: str,
        blockchain: str
    ) -> Dict[str, Any]:
        """Disconnect wallet for specific chain"""
        
        try:
            # Mark as inactive in multi_chain_addresses
            result = self.db.supabase.table('multi_chain_addresses').update({
                'is_primary': False,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('user_id', user_id).eq('blockchain', blockchain).execute()
            
            # Mark as inactive in wallet_connections
            self.db.supabase.table('wallet_connections').update({
                'is_active': False,
                'disconnected_at': datetime.utcnow().isoformat()
            }).eq('user_id', user_id).eq('blockchain', blockchain).eq('is_active', True).execute()
            
            logger.info(f"✅ {blockchain} wallet disconnected for user {user_id[:8]}...")
            
            return {
                'success': True,
                'message': f'{blockchain.capitalize()} wallet disconnected successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ Wallet disconnection failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_connected_wallets(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get all connected wallets for user"""
        
        try:
            # Get all active wallets
            result = self.db.supabase.table('multi_chain_addresses')\
                .select('blockchain, address, wallet_provider, connection_type, created_at')\
                .eq('user_id', user_id)\
                .eq('is_primary', True)\
                .execute()
            
            wallets = {}
            for wallet in result.data:
                blockchain = wallet['blockchain']
                
                # Add chain metadata for WalletConnect chains
                if blockchain in self.WALLET_CONNECT_CHAINS:
                    chain_info = self.WALLET_CONNECT_CHAINS[blockchain]
                    wallets[blockchain] = {
                        **wallet,
                        'chain_id': chain_info['chain_id'],
                        'chain_name': chain_info['name'],
                        'native_currency': chain_info['native_currency'],
                        'explorer': f"{chain_info['explorer']}/address/{wallet['address']}"
                    }
                else:
                    wallets[blockchain] = wallet
            
            return {
                'success': True,
                'wallets': wallets,
                'total_chains': len(wallets),
                'wallet_connect_chains': [k for k in wallets.keys() if k in self.WALLET_CONNECT_CHAINS]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get connected wallets: {e}")
            return {
                'success': False,
                'error': str(e),
                'wallets': {}
            }
    
    async def _get_connected_wallet(
        self,
        user_id: str,
        blockchain: str
    ) -> Optional[Dict[str, Any]]:
        """Get connected wallet for specific chain"""
        
        try:
            result = self.db.supabase.table('multi_chain_addresses')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('blockchain', blockchain)\
                .eq('is_primary', True)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get connected wallet: {e}")
            return None
    
    def _verify_signature(
        self,
        address: str,
        message: str,
        signature: str
    ) -> bool:
        """
        Verify that signature was created by address owner
        Uses EIP-191 standard for message signing
        """
        
        try:
            # Encode message (EIP-191 format)
            encoded_message = encode_defunct(text=message)
            
            # Recover address from signature
            recovered_address = Web3().eth.account.recover_message(
                encoded_message,
                signature=signature
            )
            
            # Compare addresses (case-insensitive)
            is_valid = recovered_address.lower() == address.lower()
            
            if is_valid:
                logger.info(f"✅ Signature verified: {address[:10]}...")
            else:
                logger.warning(f"❌ Signature mismatch: expected {address[:10]}..., got {recovered_address[:10]}...")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ Signature verification failed: {e}")
            return False
    
    def get_wallet_connect_config(self, blockchain: str) -> Dict[str, Any]:
        """Get WalletConnect configuration for chain"""
        
        if blockchain not in self.WALLET_CONNECT_CHAINS:
            raise ValueError(f"Unsupported chain: {blockchain}")
        
        return self.WALLET_CONNECT_CHAINS[blockchain]
    
    def is_wallet_connect_chain(self, blockchain: str) -> bool:
        """Check if chain uses WalletConnect"""
        return blockchain in self.WALLET_CONNECT_CHAINS