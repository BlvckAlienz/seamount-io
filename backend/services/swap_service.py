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
from backend.services.algorand_service import AlgorandService
from backend.services.database_service import DatabaseService
from backend.services.multi_chain_wallet_service import MultiChainWalletService as WalletService
from backend.services.revenue_tracking_service import RevenueTrackingService

logger = logging.getLogger(__name__)

class SwapService:
    """
    Handles all on-chain asset swaps with premium tiered fees.
    NOW WITH REAL ALGORAND DEX INTEGRATION!
    """

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
        
        # Algorand DEX Integration
        self.PACT_DEX_URL = "https://api.pact.fi"  # Pact Finance API
        self.FOLKS_FINANCE_URL = "https://api.folks.finance"
        
        # Supported swap pairs on Algorand
        self.SUPPORTED_PAIRS = {
            "USDT": ["ALGO", "USDCa", "goBTC", "goETH"],
            "USDCa": ["ALGO", "USDT", "goBTC", "goETH"],
            "ALGO": ["USDT", "USDCa", "goBTC", "goETH"],
            "goBTC": ["USDT", "USDCa", "ALGO"],
            "goETH": ["USDT", "USDCa", "ALGO"],
        }
        
        logger.info("SwapService initialized with Algorand DEX integration")

    def _determine_fee_tier(self, from_asset: str, to_asset: str) -> Decimal:
        """
        Determine the appropriate fee tier based on asset types.
        Uses premium fee structure from BusinessModelConfig.
        """
        supported_assets = self.settings.SUPPORTED_ASSETS
        
        # Check if assets are stable or volatile
        from_stable = supported_assets.get(from_asset, {}).get("is_stable", False)
        to_stable = supported_assets.get(to_asset, {}).get("is_stable", False)
        
        # Apply premium fee structure
        if from_stable and to_stable:
            return Decimal("0.010")  # Stable to stable: 1.0%
        elif from_stable or to_stable:
            return Decimal("0.015")  # Stable to volatile: 1.5%
        else:
            return Decimal("0.020")  # Volatile to volatile: 2.0%

    async def get_swap_quote(
        self, 
        from_asset: str, 
        to_asset: str, 
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Get a real-time swap quote from Algorand DEX with premium fees.
        """
        try:
            # Validate swap pair
            if to_asset not in self.SUPPORTED_PAIRS.get(from_asset, []):
                raise HTTPException(
                    status_code=400,
                    detail=f"Swap pair {from_asset}/{to_asset} not supported"
                )
            
            # Get ASA IDs
            from_asa_id = self.settings.SUPPORTED_ASSETS[from_asset]["asa_id"]
            to_asa_id = self.settings.SUPPORTED_ASSETS[to_asset]["asa_id"]
            
            # 🚀 REAL DEX QUOTE (Using Pact Finance)
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.PACT_DEX_URL}/api/quote",
                    json={
                        "from_asset": from_asa_id,
                        "to_asset": to_asa_id,
                        "amount": str(amount),
                    }
                ) as response:
                    if response.status == 200:
                        dex_quote = await response.json()
                        amount_out_before_fees = Decimal(str(dex_quote["output_amount"]))
                        price_impact = Decimal(str(dex_quote.get("price_impact", 0.005)))
                    else:
                        # Fallback to oracle-based pricing
                        price_ratio = await self._get_price_ratio(from_asset, to_asset)
                        amount_out_before_fees = amount * price_ratio
                        price_impact = Decimal("0.005")
            
            # Determine fee tier
            fee_rate = self._determine_fee_tier(from_asset, to_asset)
            
            # Calculate fee amount
            fee_amount = amount_out_before_fees * fee_rate
            min_fee = Decimal("1.00")  # $1 minimum fee
            if fee_amount < min_fee:
                fee_amount = min_fee
                
            # Calculate final amount out
            amount_out = amount_out_before_fees - fee_amount
            
            logger.info(
                f"Swap quote: {amount} {from_asset} → {amount_out} {to_asset} "
                f"with {fee_rate*100}% fee (${fee_amount})"
            )
            
            return {
                "from_asset": from_asset,
                "to_asset": to_asset,
                "amount_in": float(amount),
                "amount_out": float(amount_out),
                "fee_amount": float(fee_amount),
                "fee_rate": float(fee_rate),
                "price_impact": float(price_impact),
                "min_amount_out": float(amount_out * Decimal("0.995")),  # 0.5% slippage
                "dex": "pact_finance",
            }
            
        except Exception as e:
            logger.error(f"Failed to generate swap quote: {e}")
            raise HTTPException(status_code=500, detail="Could not generate swap quote")

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
        Execute swap on Algorand DEX (Pact Finance)
        """
        # Get user's Algorand wallet
        user_wallet = await self.wallet_service.get_user_wallet(user_id, "algorand")
        
        # Get ASA IDs
        from_asa_id = self.settings.SUPPORTED_ASSETS[from_asset]["asa_id"]
        to_asa_id = self.settings.SUPPORTED_ASSETS[to_asset]["asa_id"]
        
        # Execute swap via Algorand service
        tx_id = await self.algorand_service.swap_assets(
            sender_address=user_wallet["address"],
            sender_key=user_wallet["private_key"],
            from_asa_id=from_asa_id,
            to_asa_id=to_asa_id,
            amount_in=int(amount_in * 1_000_000),  # Convert to micro-units
            min_amount_out=int(min_amount_out * 1_000_000),
            dex="pact"
        )
        
        return tx_id
    
    async def _get_price_ratio(self, from_asset: str, to_asset: str) -> Decimal:
        """
        Fallback: Get price ratio from oracle service
        """
        # Use oracle service for pricing
        from_price = await self.algorand_service.get_asset_price(from_asset)
        to_price = await self.algorand_service.get_asset_price(to_asset)
        
        return from_price / to_price