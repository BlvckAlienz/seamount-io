# File: backend/services/fee_calculator.py
"""
FIXED: Removed all B2C user tier logic
✅ B2C users pay standard transaction fees - NO SUBSCRIPTION TIERS
✅ B2B API customers have license tiers (Builder/Scale/Enterprise)
✅ Revenue = transaction fees (B2C) + API subscriptions (B2B)
"""

import logging
from decimal import Decimal, ROUND_UP
from typing import Dict, Any, Optional
from datetime import datetime

from backend.config import settings, MultiChainBusinessModel, TransactionType
from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class FeeCalculatorService:
    """Production-ready fee calculator - B2C users have NO tiers"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.business_model = MultiChainBusinessModel()
        
        # Cache exchange rates for 60 seconds
        self.rate_cache = {}
        self.cache_ttl = 60
        
        logger.info("FeeCalculatorService initialized - B2C standard pricing, B2B API licensing")
    
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
        """
        Calculate comprehensive fee breakdown for any transaction
        
        ✅ FIX: B2C users = standard pricing (no tiers)
        ✅ FIX: B2B API users = check license tier (separate system)
        """
        try:
            # ✅ Check if user is B2B API customer (optional)
            is_api_customer = await self._is_api_customer(user_id)
            
            if is_api_customer:
                # B2B API customer - check license tier
                api_tier = await self._get_api_license_tier(user_id)
                fee_calculation = self.business_model.calculate_api_customer_fee(
                    transaction_type=transaction_type.value,
                    amount=amount,
                    license_tier=api_tier,
                    from_asset=from_asset,
                    to_asset=to_asset
                )
            else:
                # ✅ B2C user - standard pricing (NO TIERS)
                fee_calculation = self.business_model.calculate_total_fee(
                    transaction_type=transaction_type.value,
                    amount=amount,
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
                "calculator_version": "2.0_b2c_standard",
                "expires_at": (datetime.utcnow().timestamp() + 300),
                "user_type": "api_customer" if is_api_customer else "standard"
            })
            
            logger.info(f"Fee calculated: {transaction_type.value} ${float(amount)} = ${fee_calculation['total_fee']:.4f}")
            return fee_calculation
            
        except Exception as e:
            logger.error(f"Fee calculation failed for {transaction_type.value}: {e}")
            raise ValueError(f"Could not calculate fees: {str(e)}")
    
    async def _is_api_customer(self, user_id: str) -> bool:
        """Check if user is a B2B API customer (has active license)"""
        try:
            result = await self.db_service.supabase.table('api_licenses')\
                .select('id')\
                .eq('user_id', user_id)\
                .eq('status', 'active')\
                .maybe_single()\
                .execute()
            
            return result.data is not None
            
        except Exception as e:
            logger.warning(f"Could not check API customer status: {e}")
            return False
    
    async def _get_api_license_tier(self, user_id: str):
        """Get API license tier for B2B customers"""
        try:
            from backend.config import LicenseTier
            
            result = await self.db_service.supabase.table('api_licenses')\
                .select('tier')\
                .eq('user_id', user_id)\
                .eq('status', 'active')\
                .maybe_single()\
                .execute()
            
            if result.data and result.data.get('tier'):
                return LicenseTier(result.data['tier'])
            
            return LicenseTier.BUILDER  # Default for API customers
            
        except Exception as e:
            logger.warning(f"Could not determine API license tier: {e}")
            from backend.config import LicenseTier
            return LicenseTier.BUILDER
    
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
                "provider": "Multi-chain P2P Network"
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
                "provider": "Paystack → Multi-chain"
            }
        }
        
        return enhanced
    
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