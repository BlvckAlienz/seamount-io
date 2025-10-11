# File: backend/services/wallet_service.py - PRODUCTION FIXES
"""
Fixed Wallet Service with correct schema mapping and key encoding
"""

import logging
from typing import Dict, Optional, List, Any
from decimal import Decimal
from algosdk import account, mnemonic
from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime
from fastapi import HTTPException

from backend.config import settings
from backend.services.database_service import DatabaseService
from backend.services.algorand_service import AlgorandService

logger = logging.getLogger(__name__)

class WalletService:
    """Production-ready wallet service with correct Supabase schema mapping"""
    
    def __init__(self, db_service: DatabaseService, algorand_service: AlgorandService):
        self.db_service = db_service
        self.algorand_service = algorand_service
        
        # Initialize encryption
        if not settings.ENCRYPTION_KEY:
            raise ValueError("ENCRYPTION_KEY must be set for wallet operations")
        
        encryption_key_bytes = settings.ENCRYPTION_KEY.get_secret_value().encode()
        self.cipher = Fernet(encryption_key_bytes)
        
        # Multi-asset configuration
        self.supported_assets = settings.SUPPORTED_ASSETS
        
        logger.info("WalletService initialized with multi-asset support")
    
    def _encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except InvalidToken:
            logger.error("Wallet data decryption failed - invalid token")
            raise HTTPException(status_code=500, detail="Wallet data decryption failed")
    
    async def create_algorand_wallet(self, user_id: str) -> Dict[str, Any]:
        """
        FIXED: Create Algorand wallet with correct schema mapping
        """
        try:
            logger.info(f"Creating Algorand wallet for user: {user_id}")
            
            # Generate new Algorand account
            private_key, address = account.generate_account()
            mnemonic_phrase = mnemonic.from_private_key(private_key)
            
            # FIX: private_key is already a STRING from algosdk, don't call .hex()
            encrypted_pk = self._encrypt(private_key)
            
            # FIX: Use correct Supabase column names
            wallet_data = {
                "user_id": user_id,
                "algorand_address": address,
                "wallet_address": address,
                "algorand_private_key": encrypted_pk,  # NOT encrypted_private_key
                "wallet_type": "managed",  # NOT blockchain
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Use Supabase upsert directly
            response = self.db_service.supabase.table("user_wallets").upsert(
                wallet_data, 
                on_conflict="user_id"
            ).execute()
            
            if not response.data:
                raise Exception("Failed to create wallet in database")
            
            # Initialize wallet balances
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
            
            # Use Supabase directly
            self.db_service.supabase.table("wallet_balances").insert(balance_data).execute()
            logger.info(f"Initialized balance records for user: {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize wallet balances: {e}")
            # Don't fail wallet creation if balance init fails
    
    async def get_user_balances(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive wallet balances for user"""
        try:
            # Get user's wallet - FIX: use correct column name
            response = self.db_service.supabase.table("user_wallets").select("algorand_address").eq("user_id", user_id).eq("is_active", True).maybe_single().execute()
            
            if not response.data:
                return {"balances": {}, "total_usd": 0.0, "wallet_exists": False}
            
            wallet_address = response.data['algorand_address']
            
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
                    continue
                
                asset_id = config['asset_id']
                decimals = config['decimals']
                raw_balance = asset_lookup.get(asset_id, 0)
                
                # Convert from raw units to human readable
                balances[symbol] = raw_balance / (10 ** decimals)
            
            return balances
            
        except Exception as e:
            logger.error(f"Failed to fetch live balances for {wallet_address}: {e}")
            return await self._get_cached_balances(wallet_address)
    
    async def _get_cached_balances(self, wallet_address: str) -> Dict[str, float]:
        """Get cached balances from database"""
        try:
            response = self.db_service.supabase.table("wallet_balances").select("*").eq("wallet_address", wallet_address).maybe_single().execute()
            
            if response.data:
                balance_row = response.data
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
            update_data = {
                "algo_balance": balances.get("ALGO", 0),
                "usdt_balance": balances.get("USDT", 0),
                "usdc_balance": balances.get("USDCa", 0),
                "gobtc_balance": balances.get("goBTC", 0),
                "goeth_balance": balances.get("goETH", 0),
                "last_updated": datetime.utcnow().isoformat()
            }
            
            self.db_service.supabase.table("wallet_balances").update(update_data).eq("user_id", user_id).execute()
            
        except Exception as e:
            logger.error(f"Failed to update cached balances: {e}")
    
    async def _calculate_portfolio_value(self, balances: Dict[str, float]) -> float:
        """Calculate total USD value of portfolio"""
        try:
            total_usd = 0.0
            
            # Current market prices (TODO: replace with oracle service)
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
    
    async def get_wallet_info(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive wallet information"""
        try:
            # Get wallet details - FIX: use correct column name
            response = self.db_service.supabase.table("user_wallets").select("*").eq("user_id", user_id).eq("is_active", True).maybe_single().execute()
            
            if not response.data:
                return {"wallet_exists": False}
            
            wallet_data = response.data
            
            # Get balances
            balances = await self.get_user_balances(user_id)
            
            return {
                "wallet_exists": True,
                "wallet_address": wallet_data["algorand_address"],
                "blockchain": "algorand",
                "wallet_type": wallet_data.get("wallet_type", "managed"),
                "created_at": wallet_data.get("created_at"),
                "balances": balances["balances"],
                "total_usd": balances["total_usd"],
                "supported_assets": list(self.supported_assets.keys())
            }
            
        except Exception as e:
            logger.error(f"Failed to get wallet info: {e}")
            return {"wallet_exists": False, "error": str(e)}