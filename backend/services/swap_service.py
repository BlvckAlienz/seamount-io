import logging
from typing import Dict, Any
from decimal import Decimal
from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException

# --- Core Dependencies ---
from config import Settings, get_settings
from .algorand_service import AlgorandService
from .database_service import DatabaseService
from .multi_chain_wallet_service import MultiChainWalletService as WalletService

logger = logging.getLogger(__name__)

class SwapService:
    """
    Handles all on-chain asset swaps with premium tiered fees.
    Updated for Phase 1: Multi-Asset Support (USDT, USDCa, goBTC, goETH)
    """

    def __init__(
        self, 
        settings: Settings, 
        algorand_service: AlgorandService, 
        db_service: DatabaseService,
        wallet_service: WalletService
    ):
        self.settings = settings
        self.algorand_service = algorand_service
        self.db_service = db_service
        self.wallet_service = wallet_service
        logger.info("SwapService initialized with multi-asset support and premium tiered fees.")

    def _determine_fee_tier(self, from_asset: str, to_asset: str) -> Decimal:
        """
        Determine the appropriate fee tier based on asset types.
        Uses premium fee structure from BusinessModelConfig.
        """
        # Get asset configurations
        supported_assets = self.settings.SUPPORTED_ASSETS
        
        # Check if assets are stable or volatile
        from_stable = supported_assets.get(from_asset, {}).get("is_stable", False)
        to_stable = supported_assets.get(to_asset, {}).get("is_stable", False)
        
        # Apply premium fee structure
        if from_stable and to_stable:
            # Stable to stable: 1.0%
            return Decimal("0.010")
        elif from_stable or to_stable:
            # Stable to volatile or volatile to stable: 1.5%
            return Decimal("0.015")
        else:
            # Volatile to volatile: 2.0%
            return Decimal("0.020")

    async def get_swap_quote(self, from_asset: str, to_asset: str, amount: Decimal) -> Dict[str, Any]:
        """
        Get a real-time swap quote with premium fees.
        """
        try:
            # Get current market prices (simulated for now)
            # In production, this would use the oracle service
            price_ratio = Decimal("1.0")  # 1:1 for simulation
            
            # Calculate amount out before fees
            amount_out_before_fees = amount * price_ratio
            
            # Determine fee tier
            fee_rate = self._determine_fee_tier(from_asset, to_asset)
            
            # Calculate fee amount
            fee_amount = amount_out_before_fees * fee_rate
            
            # Apply minimum fee if needed
            min_fee = Decimal("1.00")  # $1 minimum fee
            if fee_amount < min_fee:
                fee_amount = min_fee
                
            # Calculate final amount out
            amount_out = amount_out_before_fees - fee_amount
            
            logger.info(f"Swap quote: {amount} {from_asset} → {amount_out} {to_asset} with {fee_rate*100}% fee")
            
            return {
                "from_asset": from_asset,
                "to_asset": to_asset,
                "amount_in": float(amount),
                "amount_out": float(amount_out),
                "fee_amount": float(fee_amount),
                "fee_rate": float(fee_rate),
                "price_impact": 0.005,  # Simulated 0.5% price impact
                "min_amount_out": float(amount_out * Decimal("0.995"))  # 0.5% slippage tolerance
            }
            
        except Exception as e:
            logger.error(f"Failed to generate swap quote: {e}")
            raise HTTPException(status_code=500, detail="Could not generate swap quote")

    async def execute_swap(self, user_id: str, from_asset: str, to_asset: str, amount: Decimal) -> Dict[str, Any]:
        """
        Execute an asset swap with premium tiered fees.
        """
        try:
            # Get current wallet balances
            balances = await self.wallet_service.get_wallet_balances(user_id)
            
            # Check if user has sufficient balance
            if balances.get(from_asset, Decimal("0")) < amount:
                raise HTTPException(status_code=400, detail=f"Insufficient {from_asset} balance")
            
            # Get swap quote
            quote = await self.get_swap_quote(from_asset, to_asset, amount)
            
            # SIMULATE swap execution (will be replaced with real DEX integration)
            simulated_tx_id = f"swap_tx_{uuid4().hex[:16]}"
            
            # Update balances in database
            from_balance_new = balances[from_asset] - amount
            to_balance_new = balances[to_asset] + Decimal(str(quote["amount_out"]))
            
            # Update from asset balance
            success = await self.wallet_service.update_asset_balance(user_id, from_asset, from_balance_new)
            if not success:
                raise HTTPException(status_code=500, detail=f"Failed to update {from_asset} balance")
                
            # Update to asset balance
            success = await self.wallet_service.update_asset_balance(user_id, to_asset, to_balance_new)
            if not success:
                # Attempt to revert from asset balance
                await self.wallet_service.update_asset_balance(user_id, from_asset, balances[from_asset])
                raise HTTPException(status_code=500, detail=f"Failed to update {to_asset} balance")
            
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
                "tx_hash": simulated_tx_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.db_service.log_event("swap_transactions", swap_log)
            
            # Log revenue from swap fee
            revenue_log = {
                "user_id": user_id,
                "type": "swap_fee",
                "amount": quote["fee_amount"],
                "asset": to_asset,  # Fee is taken in the output asset
                "transaction_id": simulated_tx_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.db_service.log_event("revenue", revenue_log)

            logger.info(f"Swap executed for user {user_id}: {amount} {from_asset} → {quote['amount_out']} {to_asset}")
            
            return {
                "success": True,
                "tx_id": simulated_tx_id,
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