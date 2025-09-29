# File: backend/services/fee_calculator.py
"""
Core Fee Calculator Service for Seamount.io
Implements optimized 2.9% cross-border model with competitive positioning
Real-time fee calculation with provider cost integration
"""

import logging
from decimal import Decimal, ROUND_UP
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum

from backend.config import settings, BusinessModelConfig, LicenseTier
from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class TransactionType(str, Enum):
    CROSS_BORDER = "cross_border"
    ON_RAMP = "on_ramp" 
    P2P_LOCAL = "p2p"
    ASSET_SWAP = "swap"
    WITHDRAWAL = "withdrawal"

class FeeCalculatorService:
    """
    Production-ready fee calculator for all Seamount transactions
    Integrates with BusinessModelConfig for consistent pricing
    """
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.business_model = BusinessModelConfig()
        
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
        """
        Calculate comprehensive fee breakdown for any transaction
        Returns detailed fee structure with competitive analysis
        """
        try:
            # Get user tier for discounts
            user_tier = await self._get_user_tier(user_id)
            
            # Calculate base fees using BusinessModelConfig
            fee_calculation = BusinessModelConfig.get_fee_for_transaction(
                transaction_type=transaction_type.value,
                amount=amount,
                from_asset=from_asset,
                to_asset=to_asset,
                user_tier=user_tier
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
                "expires_at": (datetime.utcnow().timestamp() + 300),  # 5 min expiry
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
        """
        Add cross-border specific enhancements and competitive analysis
        """
        enhanced = {
            "cross_border_details": {
                "settlement_time": "< 5 seconds",
                "corridor": f"Algorand â†’ {destination_country or 'Global'}",
                "supported_assets": ["USDT", "USDCa"],
                "provider": "Cashramp P2P Network"
            }
        }
        
        # Add competitive comparison
        competitive_analysis = BusinessModelConfig.calculate_cross_border_economics(amount)
        enhanced["competitive_comparison"] = competitive_analysis["competitive_analysis"]
        enhanced["value_proposition"] = competitive_analysis["value_proposition"]
        
        # Estimate provider costs for this transaction
        cashramp_cost = amount * BusinessModelConfig.PROVIDER_COSTS["cashramp_p2p"]
        operational_cost = amount * BusinessModelConfig.PROVIDER_COSTS["operational_buffer"]
        
        enhanced["provider_economics"] = {
            "cashramp_fee": float(cashramp_cost),
            "operational_cost": float(operational_cost),
            "estimated_profit": float(Decimal(str(base_calc["discounted_fee"])) - cashramp_cost - operational_cost),
            "profit_margin_percent": float(
                (Decimal(str(base_calc["discounted_fee"])) - cashramp_cost - operational_cost) / 
                Decimal(str(base_calc["discounted_fee"])) * 100
            )
        }
        
        return enhanced
    
    async def _enhance_onramp_calculation(
        self,
        base_calc: Dict,
        amount: Decimal, 
        payment_method: Optional[str]
    ) -> Dict:
        """
        Add on-ramp specific details and provider integration
        """
        enhanced = {
            "onramp_details": {
                "payment_method": payment_method or "paystack",
                "processing_time": "Instant",
                "supported_currencies": ["NGN", "KES", "GHS", "ZAR"],
                "provider": "Paystack â†’ Algorand"
            }
        }
        
        # Provider cost calculation
        if payment_method == "paystack":
            provider_cost = amount * BusinessModelConfig.PROVIDER_COSTS["paystack_onramp"]
            enhanced["provider_economics"] = {
                "paystack_fee": float(provider_cost),
                "estimated_profit": float(Decimal(str(base_calc["discounted_fee"])) - provider_cost),
                "profit_margin_percent": float(
                    (Decimal(str(base_calc["discounted_fee"])) - provider_cost) / 
                    Decimal(str(base_calc["discounted_fee"])) * 100
                )
            }
        
        return enhanced
    
    async def calculate_batch_fees(
        self,
        transactions: List[Dict[str, Any]],
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Calculate fees for multiple transactions efficiently
        Useful for portfolio rebalancing or batch transfers
        """
        results = []
        
        for tx in transactions:
            try:
                fee_calc = await self.calculate_transaction_fee(
                    transaction_type=TransactionType(tx["type"]),
                    amount=Decimal(str(tx["amount"])),
                    user_id=user_id,
                    from_asset=tx.get("from_asset"),
                    to_asset=tx.get("to_asset"),
                    destination_country=tx.get("destination_country"),
                    payment_method=tx.get("payment_method")
                )
                
                results.append({
                    "transaction_id": tx.get("id", f"batch_{len(results)}"),
                    "success": True,
                    "fee_calculation": fee_calc
                })
                
            except Exception as e:
                logger.error(f"Batch fee calculation failed for transaction: {e}")
                results.append({
                    "transaction_id": tx.get("id", f"batch_{len(results)}"),
                    "success": False,
                    "error": str(e)
                })
        
        # Calculate batch summary
        successful_calculations = [r for r in results if r["success"]]
        total_amount = sum(Decimal(str(r["fee_calculation"]["amount"])) for r in successful_calculations)
        total_fees = sum(Decimal(str(r["fee_calculation"]["total_fee"])) for r in successful_calculations)
        
        batch_summary = {
            "batch_results": results,
            "summary": {
                "total_transactions": len(transactions),
                "successful_calculations": len(successful_calculations),
                "total_amount": float(total_amount),
                "total_fees": float(total_fees),
                "average_fee_rate": float((total_fees / total_amount * 100)) if total_amount > 0 else 0
            }
        }
        
        return batch_summary
    
    async def get_fee_estimate_quick(
        self,
        transaction_type: TransactionType,
        amount: Decimal,
        user_tier: LicenseTier = LicenseTier.STARTER
    ) -> Dict[str, Any]:
        """
        Quick fee estimate without database calls
        Used for UI preview before user confirms transaction
        """
        fee_calc = BusinessModelConfig.get_fee_for_transaction(
            transaction_type=transaction_type.value,
            amount=amount,
            user_tier=user_tier
        )
        
        # Add quick competitive context
        if transaction_type == TransactionType.CROSS_BORDER:
            western_union_cost = amount * Decimal("0.055")  # 5.5% average
            savings = western_union_cost - Decimal(str(fee_calc["total_fee"]))
            
            fee_calc["quick_comparison"] = {
                "western_union_cost": float(western_union_cost),
                "seamount_cost": fee_calc["total_fee"],
                "savings": float(savings),
                "savings_percent": float((savings / western_union_cost * 100)),
                "speed_advantage": "5000x faster"
            }
        
        fee_calc["estimate_disclaimer"] = "Final fees may vary based on market conditions"
        return fee_calc
    
    async def validate_fee_quote(
        self,
        quote_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Validate a previously generated fee quote
        Ensures quote hasn't expired and rates are still valid
        """
        try:
            # Retrieve stored quote
            query = """
                SELECT fee_data, created_at, expires_at 
                FROM fee_calculations 
                WHERE quote_id = %s AND user_id = %s
            """
            result = await self.db_service.execute_query(query, (quote_id, user_id))
            
            if not result:
                return {"valid": False, "error": "Quote not found"}
            
            quote_data = result[0]
            expires_at = quote_data["expires_at"]
            
            # Check expiry
            if datetime.utcnow().timestamp() > expires_at:
                return {"valid": False, "error": "Quote expired", "expired_at": expires_at}
            
            return {
                "valid": True,
                "quote_id": quote_id,
                "fee_data": quote_data["fee_data"],
                "expires_in_seconds": int(expires_at - datetime.utcnow().timestamp())
            }
            
        except Exception as e:
            logger.error(f"Fee quote validation failed: {e}")
            return {"valid": False, "error": str(e)}
    
    async def _get_user_tier(self, user_id: str) -> LicenseTier:
        """Get user's license tier for discount calculation"""
        try:
            query = "SELECT license_tier FROM user_profiles WHERE id = %s"
            result = await self.db_service.execute_query(query, (user_id,))
            
            if result and result[0]["license_tier"]:
                return LicenseTier(result[0]["license_tier"])
            
            return LicenseTier.STARTER  # Default tier
            
        except Exception as e:
            logger.warning(f"Could not determine user tier: {e}")
            return LicenseTier.STARTER
    
    async def _store_fee_calculation(self, user_id: str, fee_calculation: Dict):
        """Store fee calculation for audit and quote validation"""
        try:
            quote_id = f"quote_{user_id}_{int(datetime.utcnow().timestamp())}"
            
            storage_data = {
                "quote_id": quote_id,
                "user_id": user_id,
                "fee_data": fee_calculation,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": fee_calculation.get("expires_at", datetime.utcnow().timestamp() + 300)
            }
            
            # Store in fee_calculations table (create if doesn't exist)
            await self.db_service.log_event("fee_calculation", storage_data)
            
            # Update fee_calculation with quote_id for reference
            fee_calculation["quote_id"] = quote_id
            
        except Exception as e:
            logger.error(f"Failed to store fee calculation: {e}")
            # Don't fail the transaction if storage fails
    
    def get_supported_corridors(self) -> List[Dict[str, Any]]:
        """Get list of supported cross-border corridors"""
        return [
            {
                "from_country": "NG",
                "to_countries": ["KE", "GH", "ZA", "UG", "TZ"],
                "supported_assets": ["USDT", "USDCa"],
                "fee_rate": "2.9%",
                "settlement_time": "< 5 seconds",
                "daily_limit_usd": 10000,
                "monthly_limit_usd": 50000
            },
            {
                "from_country": "KE", 
                "to_countries": ["NG", "UG", "TZ", "GH"],
                "supported_assets": ["USDT", "USDCa"],
                "fee_rate": "2.9%",
                "settlement_time": "< 5 seconds",
                "daily_limit_usd": 10000,
                "monthly_limit_usd": 50000
            }
        ]
    
    async def get_fee_analytics(
        self,
        user_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get fee analytics for user or platform-wide
        Useful for revenue tracking and optimization
        """
        try:
            # Default to last 30 days
            if not date_from:
                date_from = datetime.utcnow().replace(day=1)  # Start of month
            if not date_to:
                date_to = datetime.utcnow()
            
            # Build query based on scope
            if user_id:
                query = """
                    SELECT 
                        transaction_type,
                        COUNT(*) as transaction_count,
                        SUM(amount) as total_volume,
                        SUM(fee_amount) as total_fees,
                        AVG(effective_fee_rate) as avg_fee_rate
                    FROM transactions 
                    WHERE user_id = %s AND created_at BETWEEN %s AND %s
                    GROUP BY transaction_type
                """
                params = (user_id, date_from, date_to)
            else:
                query = """
                    SELECT 
                        transaction_type,
                        COUNT(*) as transaction_count,
                        SUM(amount) as total_volume,
                        SUM(fee_amount) as total_fees,
                        AVG(effective_fee_rate) as avg_fee_rate
                    FROM transactions 
                    WHERE created_at BETWEEN %s AND %s
                    GROUP BY transaction_type
                """
                params = (date_from, date_to)
            
            results = await self.db_service.execute_query(query, params)
            
            analytics = {
                "period": {
                    "from": date_from.isoformat(),
                    "to": date_to.isoformat(),
                    "user_id": user_id
                },
                "breakdown": []
            }
            
            total_volume = Decimal("0")
            total_fees = Decimal("0")
            
            for row in results or []:
                volume = Decimal(str(row["total_volume"] or 0))
                fees = Decimal(str(row["total_fees"] or 0))
                
                total_volume += volume
                total_fees += fees
                
                analytics["breakdown"].append({
                    "transaction_type": row["transaction_type"],
                    "count": row["transaction_count"],
                    "volume": float(volume),
                    "fees": float(fees),
                    "avg_fee_rate": float(row["avg_fee_rate"] or 0)
                })
            
            # Calculate summary
            analytics["summary"] = {
                "total_transactions": sum(b["count"] for b in analytics["breakdown"]),
                "total_volume": float(total_volume),
                "total_fees": float(total_fees),
                "average_fee_rate": float((total_fees / total_volume * 100)) if total_volume > 0 else 0,
                "revenue_per_transaction": float(total_fees / analytics["summary"]["total_transactions"]) if analytics.get("summary", {}).get("total_transactions", 0) > 0 else 0
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Fee analytics query failed: {e}")
            return {
                "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
                "breakdown": [],
                "summary": {"total_transactions": 0, "total_volume": 0, "total_fees": 0}
            }
                