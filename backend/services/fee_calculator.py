# File: backend/services/fee_calculator.py
"""
FIXED: Removed execute_query dependency, fixed BusinessModelConfig calls
"""

import logging
from decimal import Decimal, ROUND_UP
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum

from backend.config import settings, MultiChainBusinessModel, LicenseTier
from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class TransactionType(str, Enum):
    CROSS_BORDER = "cross_border"
    ON_RAMP = "on_ramp" 
    P2P_LOCAL = "p2p"
    ASSET_SWAP = "swap"
    WITHDRAWAL = "withdrawal"

class FeeCalculatorService:
    """Production-ready fee calculator for all Seamount transactions"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.business_model = MultiChainBusinessModel()
        
        # Cache exchange rates for 60 seconds
        self.rate_cache = {}
        self.cache_ttl = 60
        
        logger.info("FeeCalculatorService initialized with optimized 2.9% cross-border model")
    
    async def calculate_transaction_fee(
        self,
        transaction_type: TransactionType,
        amount: Decimal,
        user_id: str,
        from_asset: Optional[str] = None,
        to_asset: Optional[str] = None,
        destination_country: Optional[str] = None,
        payment_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate comprehensive fee breakdown for any transaction"""
        try:
            # Get user tier for discounts
            user_tier = await self._get_user_tier(user_id)
            
            # ✅ FIX: Use calculate_total_fee() instead of non-existent method
            fee_calculation = self.business_model.calculate_total_fee(
                transaction_type=transaction_type.value,
                amount=amount,
                user_tier=user_tier,
                from_asset=from_asset,
                to_asset=to_asset
            )
            
            # Add transaction-specific enhancements
            if transaction_type == TransactionType.CROSS_BORDER:
                enhanced_calc = await self._enhance_cross_border_calculation(
                    fee_calculation, amount, destination_country
                )
                fee_calculation.update(enhanced_calc)
            
            elif transaction_type == TransactionType.ON_RAMP:
                enhanced_calc = await self._enhance_onramp_calculation(
                    fee_calculation, amount, payment_method
                )
                fee_calculation.update(enhanced_calc)
            
            # Store calculation for audit trail
            await self._store_fee_calculation(user_id, fee_calculation)
            
            # Add timestamp and metadata
            fee_calculation.update({
                "calculated_at": datetime.utcnow().isoformat(),
                "calculator_version": "2.9_optimized",
                "expires_at": (datetime.utcnow().timestamp() + 300),
                "user_tier": user_tier.value
            })
            
            logger.info(f"Fee calculated: {transaction_type.value} ${float(amount)} = ${fee_calculation['total_fee']:.4f}")
            return fee_calculation
            
        except Exception as e:
            logger.error(f"Fee calculation failed for {transaction_type.value}: {e}")
            raise ValueError(f"Could not calculate fees: {str(e)}")
    
    async def _enhance_cross_border_calculation(
        self, 
        base_calc: Dict, 
        amount: Decimal, 
        destination_country: Optional[str]
    ) -> Dict:
        """Add cross-border specific enhancements"""
        enhanced = {
            "cross_border_details": {
                "settlement_time": "< 5 seconds",
                "corridor": f"Algorand → {destination_country or 'Global'}",
                "supported_assets": ["USDT", "USDCa"],
                "provider": "Cashramp P2P Network"
            }
        }
        
        # Add competitive comparison
        competitive_analysis = self.business_model.calculate_cross_border_economics(amount)
        enhanced["competitive_comparison"] = competitive_analysis.get("competitive_analysis", {})
        enhanced["value_proposition"] = competitive_analysis.get("value_proposition", "Fast & low-cost")
        
        return enhanced
    
    async def _enhance_onramp_calculation(
        self,
        base_calc: Dict,
        amount: Decimal, 
        payment_method: Optional[str]
    ) -> Dict:
        """Add on-ramp specific details"""
        enhanced = {
            "onramp_details": {
                "payment_method": payment_method or "paystack",
                "processing_time": "Instant",
                "supported_currencies": ["NGN", "KES", "GHS", "ZAR"],
                "provider": "Paystack → Algorand"
            }
        }
        
        return enhanced
    
    async def _get_user_tier(self, user_id: str) -> LicenseTier:
        """Get user's license tier for discount calculation"""
        try:
            # ✅ FIX: Use Supabase directly instead of execute_query
            result = await self.db_service.supabase.table('user_profiles')\
                .select('license_tier')\
                .eq('id', user_id)\
                .maybe_single()\
                .execute()
            
            if result.data and result.data.get('license_tier'):
                return LicenseTier(result.data['license_tier'])
            
            return LicenseTier.BUILDER  # Default tier
            
        except Exception as e:
            logger.warning(f"Could not determine user tier: {e}")
            return LicenseTier.BUILDER
    
    async def _store_fee_calculation(self, user_id: str, fee_calculation: Dict):
        """Store fee calculation for audit"""
        try:
            quote_id = f"quote_{user_id}_{int(datetime.utcnow().timestamp())}"
            
            storage_data = {
                "quote_id": quote_id,
                "user_id": user_id,
                "fee_data": fee_calculation,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": fee_calculation.get("expires_at", datetime.utcnow().timestamp() + 300)
            }
            
            # Store via Supabase
            await self.db_service.supabase.table('fee_calculations').insert(storage_data).execute()
            
            fee_calculation["quote_id"] = quote_id
            
        except Exception as e:
            logger.error(f"Failed to store fee calculation: {e}")
