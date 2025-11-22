# File: backend/services/swap_service.py
"""
Enhanced Swap Service with Real Algorand DEX Integration
Supports Pact, Folks Finance, and other Algorand DEX protocols
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, UTC
from uuid import uuid4
from fastapi import HTTPException

# Core Dependencies
from backend.config import Settings, get_settings
from backend.services.algorand_defi_service import AlgorandDeFiService
from backend.services.algorand_service import AlgorandService
from backend.services.database_service import DatabaseService
from backend.services.multi_chain_wallet_service import MultiChainWalletService as WalletService
from backend.services.revenue_tracking_service import RevenueTrackingService
from backend.services.seed_encryption_service import SeedEncryptionService

logger = logging.getLogger(__name__)

class SwapService:
    """
    Handles all on-chain asset swaps with premium tiered fees.
    NOW WITH REAL ALGORAND DEX INTEGRATION!
    """

    # ➕ ADD THIS MAPPING
    # 🗺️ Frontend-to-Backend Asset Key Mapping
    ASSET_KEY_MAPPING = {
        # Frontend sends simple names, we map to config keys
        "USDT": "USDT_ALGO",
        "USDT_ETH": "USDT_ETH",
        "USDT_POLYGON": "USDT_POLYGON",
        "USDT_TRON": "USDT_TRON",
        "USDC_ETH": "USDC_ETH",
        "USDC_POLYGON": "USDC_POLYGON",
        # Everything else passes through
        "ALGO": "ALGO",
        "USDCa": "USDCa",
        "goBTC": "goBTC",
        "goETH": "goETH",
        "BTC": "BTC",
        "ETH": "ETH",
        "MATIC": "MATIC",
        "TRX": "TRX",
    }

    # ➕ SUPPORTED SWAP PAIRS (Pact Finance MainNet)
    SUPPORTED_PAIRS = {
        "ALGO": ["USDT", "USDCa", "goBTC", "goETH"],
        "USDT": ["ALGO", "USDCa", "goBTC", "goETH"],
        "USDCa": ["ALGO", "USDT", "goBTC", "goETH"],
        "goBTC": ["ALGO", "USDT", "USDCa", "goETH"],
        "goETH": ["ALGO", "USDT", "USDCa", "goBTC"],
    }

    def __init__(
        self, 
        settings: Settings, 
        algorand_service: AlgorandService, 
        db_service: DatabaseService,
        wallet_service: WalletService,
        revenue_service: RevenueTrackingService
    ):
        self.settings = settings
        self.algorand_service = algorand_service
        self.db_service = db_service
        self.wallet_service = wallet_service
        self.revenue_service = revenue_service
        
        # Initialize encryption service for secure key handling
        self.encryption_service = SeedEncryptionService()
        logger.info("âœ… Encryption service initialized for swap operations")

        # INITIALIZE REAL DEX SERVICE (MainNet)
        self.dex_service = AlgorandDeFiService(
            algod_client=algorand_service.algod_client
        )
        
        logger.info("SwapService initialized with Pact DEX (MainNet)")

    def _determine_fee_tier(self, from_asset: str, to_asset: str) -> Decimal:
        """
        Determine fee tier. Expects mapped keys (e.g., USDT_ALGO not USDT)
        """
        supported_assets = self.settings.SUPPORTED_ASSETS
        
        # Get configs (keys are already mapped)
        from_config = supported_assets.get(from_asset, {})
        to_config = supported_assets.get(to_asset, {})
        
        from_stable = from_config.get("is_stable", False)
        to_stable = to_config.get("is_stable", False)
        
        if from_stable and to_stable:
            return Decimal("0.010")  # 1.0% stable-to-stable
        elif from_stable or to_stable:
            return Decimal("0.015")  # 1.5% stable-to-volatile
        else:
            return Decimal("0.020")  # 2.0% volatile-to-volatile

    async def get_swap_quote(
        self, 
        from_asset: str, 
        to_asset: str, 
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Get a real-time swap quote from Algorand DEX with premium fees.
        ✅ FIXED: Maps frontend keys to backend config keys
        """
        try:
            # ✅ FIX: Map frontend asset names to backend config keys
            from_asset_key = self.ASSET_KEY_MAPPING.get(from_asset, from_asset)
            to_asset_key = self.ASSET_KEY_MAPPING.get(to_asset, to_asset)
            
            logger.info(
                f"📊 Asset mapping: {from_asset} → {from_asset_key}, "
                f"{to_asset} → {to_asset_key}"
            )
            
            # Validate swap pair (use original names for validation)
            if to_asset not in self.SUPPORTED_PAIRS.get(from_asset, []):
                raise HTTPException(
                    status_code=400,
                    detail=f"Swap pair {from_asset}/{to_asset} not supported"
                )
            
            # Get asset configs using mapped keys
            from_asset_config = self.settings.SUPPORTED_ASSETS.get(from_asset_key)
            to_asset_config = self.settings.SUPPORTED_ASSETS.get(to_asset_key)
            
            if not from_asset_config:
                logger.error(f"❌ Config not found for: {from_asset} (mapped to {from_asset_key})")
                logger.error(f"Available keys: {list(self.settings.SUPPORTED_ASSETS.keys())}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Asset configuration not found for {from_asset}"
                )
            
            if not to_asset_config:
                logger.error(f"❌ Config not found for: {to_asset} (mapped to {to_asset_key})")
                raise HTTPException(
                    status_code=400,
                    detail=f"Asset configuration not found for {to_asset}"
                )
            
            from_asset_id = from_asset_config["asset_id"]
            to_asset_id = to_asset_config["asset_id"]
            
            logger.info(
                f"📊 Fetching quote: {amount} {from_asset} (ID: {from_asset_id}) "
                f"→ {to_asset} (ID: {to_asset_id})"
            )
            
            # Use the AlgorandDeFiService for real quotes
            dex_quote = await self.dex_service.get_swap_quote(
                from_asset_id=from_asset_id,
                to_asset_id=to_asset_id,
                amount_in=amount
            )
            
            # Extract DEX quote data
            amount_out_before_fees = Decimal(str(dex_quote["amount_out"]))
            price_impact = Decimal(str(dex_quote["price_impact"]))
            
            # Determine fee tier (use mapped keys)
            fee_rate = self._determine_fee_tier(from_asset_key, to_asset_key)
            
            # Calculate platform fee
            fee_amount = amount_out_before_fees * fee_rate
            min_fee = Decimal("1.00")
            if fee_amount < min_fee:
                fee_amount = min_fee
            
            # Calculate final amount out
            amount_out = amount_out_before_fees - fee_amount
            
            logger.info(
                f"✅ Quote generated: {amount} {from_asset} → {amount_out} {to_asset} "
                f"(Fee: {fee_rate*100}% = ${fee_amount})"
            )
            
            return {
                "from_asset": from_asset,  # Return original names for frontend
                "to_asset": to_asset,
                "amount_in": float(amount),
                "amount_out": float(amount_out),
                "fee_amount": float(fee_amount),
                "fee_rate": float(fee_rate),
                "price_impact": float(price_impact),
                "min_amount_out": float(amount_out * Decimal("0.995")),
                "dex": dex_quote["dex"],
                "pool_id": dex_quote.get("pool_id"),
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to generate swap quote: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Swap quote failed: {str(e)}")

    async def execute_swap(
        self, 
        user_id: str, 
        from_asset: str, 
        to_asset: str, 
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Execute an asset swap with real DEX integration.
        """
        try:
            # Get current wallet balances
            balances = await self.wallet_service.get_wallet_balances(user_id)
            
            # Check if user has sufficient balance
            if balances.get(from_asset, Decimal("0")) < amount:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient {from_asset} balance"
                )
            
            # Get swap quote
            quote = await self.get_swap_quote(from_asset, to_asset, amount)
            
            # 🚀 EXECUTE REAL SWAP ON ALGORAND DEX
            swap_tx_id = await self._execute_dex_swap(
                user_id=user_id,
                from_asset=from_asset,
                to_asset=to_asset,
                amount_in=amount,
                min_amount_out=Decimal(str(quote["min_amount_out"]))
            )
            
            # Update balances in database
            from_balance_new = balances[from_asset] - amount
            to_balance_new = balances[to_asset] + Decimal(str(quote["amount_out"]))
            
            # Update from asset balance
            await self.wallet_service.update_asset_balance(user_id, from_asset, from_balance_new)
            # Update to asset balance
            await self.wallet_service.update_asset_balance(user_id, to_asset, to_balance_new)
            
            # Log the swap transaction
            swap_log = {
                "user_id": user_id,
                "from_asset": from_asset,
                "to_asset": to_asset,
                "amount_in": float(amount),
                "amount_out": quote["amount_out"],
                "fee_amount": quote["fee_amount"],
                "fee_rate": quote["fee_rate"],
                "status": "completed",
                "tx_hash": swap_tx_id,
                "dex": quote["dex"],
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            await self.db_service.log_event("swap_transactions", swap_log)
            
            # 🚨 TRACK REVENUE
            await self.revenue_service.track_transaction_fee(
                user_id=user_id,
                transaction_type="swap",
                amount=amount,
                fee_rate=Decimal(str(quote["fee_rate"])),
                platform_fee=Decimal(str(quote["fee_amount"])),
                network_fee=Decimal("0.001"),  # Algorand network fee
                blockchain="algorand",
                metadata={
                    "swap_pair": f"{from_asset}/{to_asset}",
                    "dex": quote["dex"]
                }
            )

            logger.info(
                f"✅ Swap executed: {amount} {from_asset} → {quote['amount_out']} {to_asset} "
                f"(TX: {swap_tx_id})"
            )
            
            return {
                "success": True,
                "tx_id": swap_tx_id,
                "amount_in": float(amount),
                "amount_out": quote["amount_out"],
                "fee_amount": quote["fee_amount"],
                "from_asset_new_balance": float(from_balance_new),
                "to_asset_new_balance": float(to_balance_new)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Swap execution failed for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Swap execution failed")
    
    async def _execute_dex_swap(
        self,
        user_id: str,
        from_asset: str,
        to_asset: str,
        amount_in: Decimal,
        min_amount_out: Decimal
    ) -> str:
        """
        Execute swap on Algorand DEX using our DeFi service
        âœ… PRODUCTION: Uses same encryption pattern as multi_chain_wallet_service
        """
        try:
            # Get user's wallet credentials from database
            wallet_query = """
                SELECT algorand_address, algorand_private_key 
                FROM user_wallets 
                WHERE user_id = %s
            """
            wallet_result = await self.db_service.execute_query(
                wallet_query, 
                (user_id,)
            )
            
            if not wallet_result or len(wallet_result) == 0:
                raise ValueError(
                    "❌ NO WALLET FOUND\n\n"
                    "You don't have an Algorand wallet yet.\n"
                    "Please create a wallet first in the dashboard."
                )
            
            user_address = wallet_result[0]["algorand_address"]
            encrypted_key = wallet_result[0]["algorand_private_key"]
            
            # âœ… DECRYPT PRIVATE KEY (Same pattern as multi_chain_wallet_service)
            try:
                decrypted_private_key = self.encryption_service.decrypt_seed(encrypted_key)
                logger.info(f"🔓 Successfully decrypted key for swap operation")
            except Exception as decrypt_err:
                logger.error(f"❌ Private key decryption failed: {decrypt_err}")
                raise Exception(f"Failed to decrypt wallet credentials: {decrypt_err}")
            
            # Get ASA IDs from config
            from_asa_id = self.settings.SUPPORTED_ASSETS[from_asset]["asa_id"]
            to_asa_id = self.settings.SUPPORTED_ASSETS[to_asset]["asa_id"]
            
            # âœ… Execute swap via DeFi service with DECRYPTED key
            tx_id = await self.dex_service.execute_swap(
                user_address=user_address,
                user_private_key=decrypted_private_key,  # âœ… NOW DECRYPTED
                from_asset_id=from_asa_id,
                to_asset_id=to_asa_id,
                amount_in=amount_in,
                min_amount_out=min_amount_out
            )
            
            logger.info(f"âœ… Swap executed successfully: {tx_id}")
            return tx_id
            
        except Exception as e:
            logger.error(f"DEX swap execution failed: {e}", exc_info=True)
            raise
        
    async def _get_price_ratio(self, from_asset: str, to_asset: str) -> Decimal:
        """
        Fallback: Get price ratio from oracle service
        """
        # Use oracle service for pricing
        from_price = await self.algorand_service.get_asset_price(from_asset)
        to_price = await self.algorand_service.get_asset_price(to_asset)
        
        return from_price / to_price