# File: backend/services/wallet_service.py - OPTIMIZED MULTI-ASSET VERSION
"""
Optimized Wallet Service with Multi-Asset Support
Merges best features from both versions for production readiness
"""

import logging
from typing import Dict, Optional, List, Any, Tuple
from decimal import Decimal
from algosdk import account, mnemonic
from supabase import Client
from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime
from fastapi import HTTPException
import asyncio
import aiohttp

from backend.config import settings
from backend.services.database_service import DatabaseService
from backend.services.algorand_service import AlgorandService

logger = logging.getLogger(__name__)

class WalletService:
    """
    Production-ready wallet service with multi-asset support
    Handles secure wallet creation, encryption, and Algorand integration
    """
    
    def __init__(self, db_service: DatabaseService, algorand_service: AlgorandService):
        self.db_service = db_service
        self.algorand_service = algorand_service
        
        # Initialize encryption
        if not settings.ENCRYPTION_KEY:
            raise ValueError("ENCRYPTION_KEY must be set for wallet operations")
        
        encryption_key_bytes = settings.ENCRYPTION_KEY.get_secret_value().encode()
        self.cipher = Fernet(encryption_key_bytes)
        
        # Multi-asset configuration from settings
        self.supported_assets = settings.SUPPORTED_ASSETS
        
        logger.info("WalletService initialized with multi-asset support")
    
    def _encrypt(self, data: str) -> str:
        """Encrypt sensitive data using configured key"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data using configured key"""
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except InvalidToken:
            logger.error("Wallet data decryption failed - invalid token")
            raise HTTPException(status_code=500, detail="Wallet data decryption failed")
    
    async def create_algorand_wallet(self, user_id: str) -> Dict[str, Any]:
        """Create new Algorand wallet with multi-asset support"""
        try:
            logger.info(f"Creating Algorand wallet for user: {user_id}")
            
            # Generate new Algorand account
            private_key, address = account.generate_account()
            mnemonic_phrase = mnemonic.from_private_key(private_key)
            
            # Store wallet with encrypted private key
            wallet_data = {
                "user_id": user_id,
                "wallet_address": address,
                "encrypted_private_key": self._encrypt(private_key.hex()),
                "blockchain": "algorand",
                "is_active": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Insert into user_wallets table
            insert_query = """
                INSERT INTO user_wallets (
                    user_id, wallet_address, encrypted_private_key, 
                    blockchain, is_active, created_at
                ) VALUES (%(user_id)s, %(wallet_address)s, %(encrypted_private_key)s,
                          %(blockchain)s, %(is_active)s, %(created_at)s)
                ON CONFLICT (user_id, blockchain) 
                DO UPDATE SET 
                    wallet_address = EXCLUDED.wallet_address,
                    encrypted_private_key = EXCLUDED.encrypted_private_key,
                    is_active = EXCLUDED.is_active,
                    created_at = EXCLUDED.created_at
                RETURNING wallet_address;
            """
            
            result = await self.db_service.execute_query(insert_query, wallet_data)
            
            if not result:
                raise Exception("Failed to create wallet in database")
            
            # Initialize wallet balances for all supported assets
            await self._initialize_wallet_balances(user_id, address)
            
            logger.info(f"Algorand wallet created successfully: {address}")
            
            return {
                "success": True,
                "wallet_address": address,
                "blockchain": "algorand",
                "mnemonic": mnemonic_phrase,
                "supported_assets": list(self.supported_assets.keys()),
                "message": "Algorand wallet created successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create Algorand wallet for user {user_id}: {e}")
            raise Exception(f"Wallet creation failed: {str(e)}")
    
    async def _initialize_wallet_balances(self, user_id: str, wallet_address: str):
        """Initialize balance records for all supported assets"""
        try:
            balance_data = {
                "user_id": user_id,
                "wallet_address": wallet_address,
                "algo_balance": 0.0,
                "usdt_balance": 0.0,
                "usdc_balance": 0.0,
                "gobtc_balance": 0.0,
                "goeth_balance": 0.0,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Insert balance record
            insert_query = """
                INSERT INTO wallet_balances (
                    user_id, wallet_address, algo_balance, usdt_balance, 
                    usdc_balance, gobtc_balance, goeth_balance, last_updated
                ) VALUES (%(user_id)s, %(wallet_address)s, %(algo_balance)s, %(usdt_balance)s,
                          %(usdc_balance)s, %(gobtc_balance)s, %(goeth_balance)s, %(last_updated)s)
                ON CONFLICT (user_id) DO NOTHING;
            """
            
            await self.db_service.execute_query(insert_query, balance_data)
            logger.info(f"Initialized balance records for user: {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize wallet balances: {e}")
            # Don't fail wallet creation if balance init fails
    
    async def get_user_balances(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive wallet balances for user"""
        try:
            # Get user's wallet address
            wallet_query = """
                SELECT wallet_address FROM user_wallets 
                WHERE user_id = %s AND blockchain = 'algorand' AND is_active = true
            """
            wallet_result = await self.db_service.execute_query(wallet_query, (user_id,))
            
            if not wallet_result:
                return {"balances": {}, "total_usd": 0.0, "wallet_exists": False}
            
            wallet_address = wallet_result[0]['wallet_address']
            
            # Get live balances from Algorand network
            live_balances = await self._fetch_live_balances(wallet_address)
            
            # Update database with live balances
            await self._update_cached_balances(user_id, live_balances)
            
            # Calculate total portfolio value
            total_usd = await self._calculate_portfolio_value(live_balances)
            
            return {
                "wallet_address": wallet_address,
                "balances": live_balances,
                "total_usd": total_usd,
                "wallet_exists": True,
                "supported_assets": list(self.supported_assets.keys()),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get balances for user {user_id}: {e}")
            return {"balances": {}, "total_usd": 0.0, "wallet_exists": False}
    
    async def _fetch_live_balances(self, wallet_address: str) -> Dict[str, float]:
        """Fetch actual balances from Algorand blockchain"""
        try:
            balances = {}
            
            # Use AlgorandService to get account info
            account_info = await self.algorand_service.get_account_info(wallet_address)
            
            if not account_info:
                # Return zero balances if account doesn't exist
                return {asset: 0.0 for asset in self.supported_assets.keys()}
            
            # ALGO balance (native currency)
            algo_balance = account_info.get('amount', 0) / 1_000_000
            balances['ALGO'] = algo_balance
            
            # Get ASA (Algorand Standard Asset) balances
            assets = account_info.get('assets', [])
            asset_lookup = {asset['asset-id']: asset['amount'] for asset in assets}
            
            # Map configured assets to their balances
            for symbol, config in self.supported_assets.items():
                if symbol == 'ALGO':
                    continue  # Already handled above
                
                asset_id = config['asset_id']
                decimals = config['decimals']
                raw_balance = asset_lookup.get(asset_id, 0)
                
                # Convert from raw units to human readable
                balances[symbol] = raw_balance / (10 ** decimals)
            
            return balances
            
        except Exception as e:
            logger.error(f"Failed to fetch live balances for {wallet_address}: {e}")
            # Return cached balances as fallback
            return await self._get_cached_balances(wallet_address)
    
    async def _get_cached_balances(self, wallet_address: str) -> Dict[str, float]:
        """Get cached balances from database"""
        try:
            query = """
                SELECT algo_balance, usdt_balance, usdc_balance, 
                       gobtc_balance, goeth_balance
                FROM wallet_balances 
                WHERE wallet_address = %s
            """
            result = await self.db_service.execute_query(query, (wallet_address,))
            
            if result:
                balance_row = result[0]
                return {
                    "ALGO": float(balance_row.get("algo_balance", 0)),
                    "USDT": float(balance_row.get("usdt_balance", 0)),
                    "USDCa": float(balance_row.get("usdc_balance", 0)),
                    "goBTC": float(balance_row.get("gobtc_balance", 0)),
                    "goETH": float(balance_row.get("goeth_balance", 0))
                }
            
            return {asset: 0.0 for asset in self.supported_assets.keys()}
            
        except Exception as e:
            logger.error(f"Failed to get cached balances: {e}")
            return {asset: 0.0 for asset in self.supported_assets.keys()}
    
    async def _update_cached_balances(self, user_id: str, balances: Dict[str, float]):
        """Update cached balances in database"""
        try:
            update_query = """
                UPDATE wallet_balances SET
                    algo_balance = %s,
                    usdt_balance = %s,
                    usdc_balance = %s, 
                    gobtc_balance = %s,
                    goeth_balance = %s,
                    last_updated = NOW()
                WHERE user_id = %s
            """
            
            await self.db_service.execute_query(update_query, (
                balances.get("ALGO", 0),
                balances.get("USDT", 0),
                balances.get("USDCa", 0),
                balances.get("goBTC", 0),
                balances.get("goETH", 0),
                user_id
            ))
            
        except Exception as e:
            logger.error(f"Failed to update cached balances: {e}")
    
    async def _calculate_portfolio_value(self, balances: Dict[str, float]) -> float:
        """Calculate total USD value of portfolio"""
        try:
            total_usd = 0.0
            
            # Current market prices (replace with oracle service)
            asset_prices = {
                "ALGO": 0.18,
                "USDT": 1.0,
                "USDCa": 1.0,
                "goBTC": 63500.0,
                "goETH": 2650.0
            }
            
            for asset, balance in balances.items():
                if balance > 0:
                    price = asset_prices.get(asset, 0.0)
                    total_usd += balance * price
            
            return round(total_usd, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate portfolio value: {e}")
            return 0.0
    
    async def prepare_asset_transfer(
        self, 
        user_id: str, 
        asset: str, 
        recipient: str, 
        amount: Decimal
    ) -> Dict[str, Any]:
        """Prepare asset transfer transaction for user signing"""
        try:
            # Validate asset
            if asset not in self.supported_assets:
                raise ValueError(f"Unsupported asset: {asset}")
            
            # Get user wallet
            wallet_query = """
                SELECT wallet_address, encrypted_private_key FROM user_wallets 
                WHERE user_id = %s AND blockchain = 'algorand' AND is_active = true
            """
            wallet_result = await self.db_service.execute_query(wallet_query, (user_id,))
            
            if not wallet_result:
                raise ValueError("User wallet not found")
            
            wallet_address = wallet_result[0]['wallet_address']
            
            # Check balance
            balances = await self._fetch_live_balances(wallet_address)
            available_balance = Decimal(str(balances.get(asset, 0)))
            
            if available_balance < amount:
                raise ValueError(f"Insufficient balance. Available: {available_balance}, Required: {amount}")
            
            # Get asset configuration
            asset_config = self.supported_assets[asset]
            
            # Use AlgorandService to prepare transaction
            if asset == "ALGO":
                # Native ALGO transfer
                prepared_tx = await self.algorand_service.prepare_payment_txn(
                    sender=wallet_address,
                    receiver=recipient,
                    amount=amount
                )
            else:
                # Asset transfer
                prepared_tx = await self.algorand_service.prepare_asset_transfer_txn(
                    sender=wallet_address,
                    receiver=recipient,
                    asset_id=asset_config['asset_id'],
                    amount=amount
                )
            
            return {
                "success": True,
                "transaction_data": prepared_tx,
                "asset": asset,
                "amount": float(amount),
                "recipient": recipient,
                "estimated_fee": 0.001  # Algorand transaction fee
            }
            
        except Exception as e:
            logger.error(f"Failed to prepare asset transfer: {e}")
            raise Exception(f"Transfer preparation failed: {str(e)}")
    
    async def execute_signed_transaction(self, user_id: str, signed_txn: str) -> Dict[str, Any]:
        """Execute a user-signed transaction"""
        try:
            # Submit transaction via AlgorandService
            tx_id = await self.algorand_service.submit_transaction(signed_txn)
            
            # Store transaction record
            tx_record = {
                "user_id": user_id,
                "tx_id": tx_id,
                "type": "asset_transfer",
                "status": "submitted",
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.db_service.log_event("wallet_transaction", tx_record)
            
            return {
                "success": True,
                "tx_id": tx_id,
                "status": "submitted",
                "explorer_url": f"https://explorer.algonode.cloud/tx/{tx_id}"
            }
            
        except Exception as e:
            logger.error(f"Transaction execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_transaction_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's transaction history"""
        try:
            # Get user wallet
            wallet_query = """
                SELECT wallet_address FROM user_wallets 
                WHERE user_id = %s AND blockchain = 'algorand' AND is_active = true
            """
            wallet_result = await self.db_service.execute_query(wallet_query, (user_id,))
            
            if not wallet_result:
                return []
            
            wallet_address = wallet_result[0]['wallet_address']
            
            # Get transactions from database
            history_query = """
                SELECT tx_id, type, amount, asset, status, created_at, completed_at
                FROM wallet_transactions 
                WHERE user_id = %s OR sender = %s OR receiver = %s
                ORDER BY created_at DESC 
                LIMIT %s
            """
            
            results = await self.db_service.execute_query(
                history_query, 
                (user_id, wallet_address, wallet_address, limit)
            )
            
            transactions = []
            for tx in results or []:
                transactions.append({
                    "tx_id": tx["tx_id"],
                    "type": tx["type"],
                    "amount": float(tx["amount"]) if tx["amount"] else 0,
                    "asset": tx["asset"],
                    "status": tx["status"],
                    "created_at": tx["created_at"],
                    "completed_at": tx["completed_at"],
                    "explorer_url": f"https://explorer.algonode.cloud/tx/{tx['tx_id']}"
                })
            
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to get transaction history: {e}")
            return []
    
    async def refresh_all_balances(self, user_id: str) -> Dict[str, Any]:
        """Force refresh of all user balances"""
        try:
            balances = await self.get_user_balances(user_id)
            
            return {
                "success": True,
                "balances": balances["balances"],
                "total_usd": balances["total_usd"],
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Balance refresh failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def check_asset_opt_in_status(self, user_id: str, asset: str) -> Dict[str, Any]:
        """Check if user is opted into specific asset"""
        try:
            if asset not in self.supported_assets:
                raise ValueError(f"Unsupported asset: {asset}")
            
            # Get user wallet
            wallet_query = """
                SELECT wallet_address FROM user_wallets 
                WHERE user_id = %s AND blockchain = 'algorand' AND is_active = true
            """
            wallet_result = await self.db_service.execute_query(wallet_query, (user_id,))
            
            if not wallet_result:
                return {"opted_in": False, "wallet_exists": False}
            
            wallet_address = wallet_result[0]['wallet_address']
            asset_id = self.supported_assets[asset]['asset_id']
            
            # Check opt-in status via AlgorandService
            is_opted_in = await self.algorand_service.check_asset_opt_in(wallet_address, asset_id)
            
            return {
                "opted_in": is_opted_in,
                "asset": asset,
                "asset_id": asset_id,
                "wallet_exists": True
            }
            
        except Exception as e:
            logger.error(f"Opt-in status check failed: {e}")
            return {"opted_in": False, "error": str(e)}
    
    async def get_wallet_info(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive wallet information"""
        try:
            # Get wallet details
            wallet_query = """
                SELECT wallet_address, blockchain, created_at FROM user_wallets 
                WHERE user_id = %s AND is_active = true
            """
            wallet_result = await self.db_service.execute_query(wallet_query, (user_id,))
            
            if not wallet_result:
                return {"wallet_exists": False}
            
            wallet_data = wallet_result[0]
            
            # Get balances
            balances = await self.get_user_balances(user_id)
            
            # Get recent transactions
            recent_txs = await self.get_transaction_history(user_id, limit=10)
            
            return {
                "wallet_exists": True,
                "wallet_address": wallet_data["wallet_address"],
                "blockchain": wallet_data["blockchain"],
                "created_at": wallet_data["created_at"],
                "balances": balances["balances"],
                "total_usd": balances["total_usd"],
                "supported_assets": list(self.supported_assets.keys()),
                "recent_transactions": recent_txs[:5],  # Last 5 transactions
                "transaction_count": len(recent_txs)
            }
            
        except Exception as e:
            logger.error(f"Failed to get wallet info: {e}")
            return {"wallet_exists": False, "error": str(e)} 
                