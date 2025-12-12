# File: backend/services/wallet_connect_service.py
"""
WalletConnect Integration Service for Base + Celo
Enables users to connect existing wallets without key management
"""

import logging
import os
import secrets
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from eth_account.messages import encode_defunct
from web3 import Web3
import jwt

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
            'chain_id_hex': '0x2105',
            'rpc_url': 'https://mainnet.base.org',
            'name': 'Base',
            'native_currency': 'ETH',
            'explorer': 'https://basescan.org'
        },
        'celo': {
            'chain_id': 42220,
            'chain_id_hex': '0xA4EC',
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
        # Secret for nonce signing (should be in environment variables)
        self.nonce_secret = os.getenv('NONCE_SECRET', secrets.token_hex(32))
        logger.info("✅ WalletConnectService initialized (Base + Celo) with nonce auth")
    
    # Add this method to WalletConnectService class (after __init__)
    async def get_connected_wallets(self, user_id: str) -> Dict[str, Any]:
        """Get all connected wallets for a user (WalletConnect chains only)"""
        try:
            result = self.db.supabase.table('multi_chain_addresses') \
                .select('blockchain, address, wallet_provider, created_at') \
                .eq('user_id', user_id) \
                .eq('connection_type', 'wallet_connect') \
                .execute()
            
            wallets = []
            for wallet in result.data:
                wallets.append({
                    'blockchain': wallet['blockchain'],
                    'address': wallet['address'],
                    'wallet_provider': wallet['wallet_provider'],
                    'created_at': wallet['created_at']
                })
            
            connected_chains = [w['blockchain'] for w in wallets]
            
            logger.info(f"✅ Found {len(connected_chains)} WalletConnect wallets for user {user_id[:8]}...")
            
            return {
                'success': True,
                'wallet_connect_chains': connected_chains,
                'wallets': wallets
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get connected wallets: {e}")
            return {
                'success': False,
                'error': str(e),
                'wallet_connect_chains': [],
                'wallets': []
            }
    
    async def generate_nonce(self, address: str, blockchain: str) -> Dict[str, Any]:
        """
        Generate a nonce for wallet authentication
        
        Args:
            address: Wallet address
            blockchain: 'base' or 'celo'
            
        Returns:
            Nonce payload with expiration
        """
        try:
            # Generate unique nonce
            nonce = secrets.token_hex(32)
            expires_at = datetime.utcnow() + timedelta(minutes=5)
            
            # Store nonce in database for validation
            nonce_data = {
                'address': Web3.to_checksum_address(address),
                'blockchain': blockchain,
                'nonce': nonce,
                'expires_at': expires_at.isoformat(),
                'used': False,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Store in nonces table
            result = self.db.supabase.table('wallet_nonces').insert(nonce_data).execute()
            
            if not result.data:
                raise Exception("Failed to store nonce")
            
            # Create signed message for frontend to sign
            message = f"Sign this message to connect your {self.WALLET_CONNECT_CHAINS[blockchain]['name']} wallet.\n\nNonce: {nonce}\nAddress: {address}\nChain: {blockchain}"
            
            logger.info(f"✅ Nonce generated for {address[:10]}... on {blockchain}")
            
            return {
                'success': True,
                'nonce': nonce,
                'message': message,
                'expires_at': expires_at.isoformat(),
                'blockchain': blockchain
            }
            
        except Exception as e:
            logger.error(f"❌ Nonce generation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def connect_wallet(
        self,
        user_id: str,
        blockchain: str,
        address: str,
        wallet_provider: str,
        signature: str,
        nonce: str
    ) -> Dict[str, Any]:
        """
        Connect external wallet via nonce-based authentication
        
        Args:
            user_id: User ID
            blockchain: 'base' or 'celo'
            address: Wallet address (EVM format: 0x...)
            wallet_provider: 'metamask', 'coinbase_wallet', etc.
            signature: Signature of the nonce message
            nonce: Nonce from generate_nonce endpoint
            
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
            
            # Checksum address
            address = Web3.to_checksum_address(address)
            
            logger.info(f"🔗 Connecting {blockchain} wallet: {address[:10]}... via {wallet_provider}")
            
            # Step 1: Verify nonce is valid and not expired
            nonce_valid = await self._verify_nonce(address, blockchain, nonce)
            if not nonce_valid:
                raise ValueError("Invalid or expired nonce")
            
            # Step 2: Reconstruct the signed message
            message = f"Sign this message to connect your {self.WALLET_CONNECT_CHAINS[blockchain]['name']} wallet.\n\nNonce: {nonce}\nAddress: {address}\nChain: {blockchain}"
            
            # Step 3: Verify signature
            is_valid = self._verify_signature(address, message, signature)
            if not is_valid:
                raise ValueError("Invalid signature - authentication failed")
            
            logger.info(f"✅ Signature verified for {address[:10]}...")
            
            # Step 4: Mark nonce as used
            await self._mark_nonce_used(address, blockchain, nonce)
            
            # Step 5: Check if wallet already connected
            existing = await self._get_connected_wallet(user_id, blockchain)
            if existing and existing['address'].lower() == address.lower():
                logger.info(f"ℹ️ Wallet already connected: {address[:10]}...")
                return {
                    'success': True,
                    'message': 'Wallet already connected',
                    'wallet': existing,
                    'is_new': False
                }
            
            # Step 6: Store in multi_chain_addresses table
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
                    'verified_signature': True,
                    'auth_method': 'nonce'
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
    
    async def _verify_nonce(self, address: str, blockchain: str, nonce: str) -> bool:
        """Verify that nonce exists, is valid, and not expired"""
        try:
            result = self.db.supabase.table('wallet_nonces')\
                .select('*')\
                .eq('address', address)\
                .eq('blockchain', blockchain)\
                .eq('nonce', nonce)\
                .eq('used', False)\
                .execute()
            
            if not result.data or len(result.data) == 0:
                logger.warning(f"❌ Nonce not found or already used: {nonce[:16]}...")
                return False
            
            nonce_record = result.data[0]
            expires_at = datetime.fromisoformat(nonce_record['expires_at'].replace('Z', '+00:00'))
            
            if datetime.utcnow() > expires_at:
                logger.warning(f"❌ Nonce expired: {nonce[:16]}...")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Nonce verification failed: {e}")
            return False
    
    async def _mark_nonce_used(self, address: str, blockchain: str, nonce: str):
        """Mark nonce as used to prevent replay attacks"""
        try:
            self.db.supabase.table('wallet_nonces')\
                .update({'used': True, 'used_at': datetime.utcnow().isoformat()})\
                .eq('address', address)\
                .eq('blockchain', blockchain)\
                .eq('nonce', nonce)\
                .execute()
            
            logger.info(f"✅ Nonce marked as used: {nonce[:16]}...")
            
        except Exception as e:
            logger.error(f"❌ Failed to mark nonce as used: {e}")
    
    # ... REST OF THE CLASS METHODS REMAIN THE SAME (disconnect_wallet, get_connected_wallets, etc.) ...
    # Only changing the _verify_signature method to be more robust:
    
    def _verify_signature(
        self,
        address: str,
        message: str,
        signature: str
    ) -> bool:
        """
        Verify that signature was created by address owner
        Uses EIP-191 standard for message signing with better error handling
        """
        
        try:
            # Clean signature (remove 0x prefix if present in message signature)
            if signature.startswith('0x'):
                signature = signature[2:]
            
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
                logger.info(f"✅ Signature verified for {address[:10]}...")
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
        
        config = self.WALLET_CONNECT_CHAINS[blockchain]
        return {
            **config,
            'chain_id_hex': config.get('chain_id_hex', hex(config['chain_id'])),
            'chain_id_decimal': config['chain_id']
        }