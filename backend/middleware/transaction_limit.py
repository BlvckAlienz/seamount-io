# File: backend/middleware/transaction_limit.py
"""
KYC Transaction Limit Enforcement Middleware
Blocks transactions exceeding $5K cumulative volume for unverified users
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import HTTPException, status

from backend.config import get_settings, KYCConfig
from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)
settings = get_settings()

class TransactionLimitMiddleware:
    """Enforce KYC thresholds on transactions"""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        
    async def check_transaction_limit(
        self,
        user_id: str,
        amount: Decimal,
        transaction_type: str = "send"
    ) -> Dict[str, Any]:
        """
        Check if transaction exceeds KYC threshold
        
        Returns:
        - allowed: bool
        - remaining_limit: Decimal
        - kyc_required: bool
        - urgency_level: str
        """
        
        try:
            # 1. Get user KYC status
            user = self.db.supabase.table('user_profiles')\
                .select('kyc_status, cumulative_volume_30d')\
                .eq('user_id', user_id)\
                .execute()
            
            if not user.data or len(user.data) == 0:
                # New user - allow transaction
                return {
                    'allowed': True,
                    'remaining_limit': float(KYCConfig.THRESHOLD_USD),
                    'kyc_required': False,
                    'urgency_level': 'none'
                }
            
            user_data = user.data[0]
            kyc_status = user_data.get('kyc_status', 'pending')
            
            # 2. Skip limit for verified users
            if kyc_status == 'verified':
                return {
                    'allowed': True,
                    'remaining_limit': None,  # Unlimited
                    'kyc_required': False,
                    'urgency_level': 'none',
                    'kyc_status': 'verified'
                }
            
            # 3. Calculate cumulative volume (30-day rolling window)
            cumulative = await self._get_cumulative_volume(user_id)
            
            # 4. Check if new transaction would exceed limit
            new_total = cumulative + amount
            remaining = KYCConfig.calculate_remaining_limit(cumulative)
            urgency = KYCConfig.get_urgency_level(cumulative)
            
            # 5. Enforcement logic
            if new_total > KYCConfig.HARD_BLOCK_THRESHOLD:
                logger.warning(
                    f"Transaction blocked for {user_id}: "
                    f"${float(new_total)} exceeds ${float(KYCConfig.HARD_BLOCK_THRESHOLD)}"
                )
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "KYC_REQUIRED",
                        "message": "Complete KYC verification to continue transacting",
                        "current_volume": float(cumulative),
                        "requested_amount": float(amount),
                        "limit": float(KYCConfig.THRESHOLD_USD),
                        "remaining": float(remaining),
                        "urgency": "critical"
                    }
                )
            
            # 6. Warning (soft block - require acknowledgment)
            kyc_required = new_total > KYCConfig.SOFT_BLOCK_THRESHOLD
            
            return {
                'allowed': True,
                'remaining_limit': float(remaining),
                'kyc_required': kyc_required,
                'urgency_level': urgency,
                'current_volume': float(cumulative),
                'threshold': float(KYCConfig.THRESHOLD_USD),
                'warning_message': self._get_warning_message(cumulative, amount) if kyc_required else None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Transaction limit check failed: {e}")
            # Fail open (allow transaction) - don't block users due to system errors
            return {
                'allowed': True,
                'remaining_limit': None,
                'kyc_required': False,
                'urgency_level': 'none',
                'error': str(e)
            }
    
    async def _get_cumulative_volume(self, user_id: str) -> Decimal:
        """Calculate 30-day rolling cumulative transaction volume"""
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=KYCConfig.TRACKING_WINDOW_DAYS)
            
            # Query transactions from last 30 days
            transactions = self.db.supabase.table('transactions')\
                .select('amount, created_at')\
                .eq('user_id', user_id)\
                .gte('created_at', cutoff_date.isoformat())\
                .in_('status', ['completed', 'pending'])\
                .execute()
            
            if not transactions.data:
                return Decimal("0")
            
            # Sum amounts
            total = sum(Decimal(str(tx['amount'])) for tx in transactions.data)
            
            # Update cached value in user_profiles
            self.db.supabase.table('user_profiles')\
                .update({'cumulative_volume_30d': float(total)})\
                .eq('user_id', user_id)\
                .execute()
            
            return total
            
        except Exception as e:
            logger.error(f"Cumulative volume calculation failed: {e}")
            return Decimal("0")  # Fail open
    
    def _get_warning_message(self, cumulative: Decimal, amount: Decimal) -> str:
        """Generate context-aware warning message"""
        
        remaining = KYCConfig.calculate_remaining_limit(cumulative)
        
        if remaining < Decimal("500"):
            return (
                f"⚠️ You're close to your $5,000 transaction limit. "
                f"Only ${float(remaining):.2f} remaining. "
                f"Complete KYC verification now to continue transacting."
            )
        elif remaining < Decimal("1000"):
            return (
                f"📊 You've used ${float(cumulative):.2f} of your $5,000 limit. "
                f"Consider completing KYC verification to unlock unlimited transactions."
            )
        else:
            return (
                f"💡 Tip: Complete KYC verification for unlimited transactions. "
                f"Current limit: ${float(remaining):.2f} remaining."
            )

# Dependency injection
def get_transaction_limit_middleware(
    db_service: DatabaseService
) -> TransactionLimitMiddleware:
    return TransactionLimitMiddleware(db_service)