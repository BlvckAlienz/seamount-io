# File: backend/services/revenue_tracking_service.py
"""
Revenue Tracking Service - Track all platform revenue streams
Captures fees at every transaction point for business analytics
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta, UTC

from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class RevenueTrackingService:
    """
    Tracks all revenue streams across the platform:
    - Transaction fees (on-ramp, off-ramp, P2P, swaps)
    - Gas fee markups (hidden revenue)
    - FX spreads
    - Yield management fees
    """
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        logger.info("RevenueTrackingService initialized")
    
    async def track_transaction_fee(
        self,
        user_id: str,
        transaction_type: str,
        amount: Decimal,
        fee_rate: Decimal,
        platform_fee: Decimal,
        network_fee: Decimal,
        blockchain: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track transaction fee revenue
        
        Args:
            user_id: User who paid the fee
            transaction_type: Type of transaction (cross_border, on_ramp, etc.)
            amount: Transaction amount in USD
            fee_rate: Fee percentage (e.g., 0.018 for 1.8%)
            platform_fee: Platform fee in USD
            network_fee: Network/blockchain fee in USD
            blockchain: Blockchain used
            metadata: Additional transaction data
        """
        try:
            revenue_event = {
                'user_id': user_id,
                'revenue_type': 'transaction_fee',
                'transaction_type': transaction_type,
                'amount': float(amount),
                'fee_rate': float(fee_rate),
                'platform_fee': float(platform_fee),
                'network_fee': float(network_fee),
                'blockchain': blockchain,
                'metadata': metadata or {},
                'created_at': datetime.now(UTC).isoformat()
            }
            
            result = self.db.supabase.table('revenue_events').insert(revenue_event).execute()
            
            logger.info(
                f"✅ Tracked transaction fee: {transaction_type} - "
                f"${platform_fee} from user {user_id[:8]}..."
            )
            
        except Exception as e:
            logger.error(f"Failed to track transaction fee: {e}")
            # Don't raise - revenue tracking shouldn't block transactions
    
    async def track_gas_markup(
        self,
        user_id: str,
        blockchain: str,
        gas_charged: Decimal,
        gas_actual: Decimal,
        markup: Decimal,
        transaction_id: Optional[str] = None
    ) -> None:
        """
        Track hidden gas fee markup revenue
        
        Args:
            user_id: User who paid the gas
            blockchain: Blockchain network
            gas_charged: Amount charged to user
            gas_actual: Actual network cost
            markup: Profit margin (gas_charged - gas_actual)
            transaction_id: Associated transaction ID
        """
        try:
            revenue_event = {
                'user_id': user_id,
                'revenue_type': 'gas_markup',
                'blockchain': blockchain,
                'amount': float(gas_charged),
                'platform_fee': float(markup),
                'network_fee': float(gas_actual),
                'metadata': {'transaction_id': transaction_id} if transaction_id else {},
                'created_at': datetime.now(UTC).isoformat()
            }
            
            result = self.db.supabase.table('revenue_events').insert(revenue_event).execute()
            
            logger.info(
                f"✅ Tracked gas markup: {blockchain} - "
                f"${markup} profit from user {user_id[:8]}..."
            )
            
        except Exception as e:
            logger.error(f"Failed to track gas markup: {e}")
    
    async def track_fx_spread(
        self,
        user_id: str,
        from_currency: str,
        to_currency: str,
        amount: Decimal,
        spread_rate: Decimal,
        spread_amount: Decimal
    ) -> None:
        """
        Track FX spread revenue
        
        Args:
            user_id: User who made the conversion
            from_currency: Source currency
            to_currency: Destination currency
            amount: Transaction amount
            spread_rate: Spread percentage
            spread_amount: Spread profit in USD
        """
        try:
            revenue_event = {
                'user_id': user_id,
                'revenue_type': 'fx_spread',
                'amount': float(amount),
                'fee_rate': float(spread_rate),
                'platform_fee': float(spread_amount),
                'metadata': {
                    'from_currency': from_currency,
                    'to_currency': to_currency
                },
                'created_at': datetime.now(UTC).isoformat()
            }
            
            result = self.db.supabase.table('revenue_events').insert(revenue_event).execute()
            
            logger.info(
                f"✅ Tracked FX spread: {from_currency}/{to_currency} - "
                f"${spread_amount} from user {user_id[:8]}..."
            )
            
        except Exception as e:
            logger.error(f"Failed to track FX spread: {e}")
    
    async def track_yield_share(
        self,
        user_id: str,
        amount: Decimal,
        platform_share: Decimal,
        protocol: str
    ) -> None:
        """
        Track yield management revenue share
        
        Args:
            user_id: User with staked funds
            amount: Total yield generated
            platform_share: Platform's share (e.g., 0.25 for 25%)
            protocol: DeFi protocol (e.g., folks_finance)
        """
        try:
            platform_fee = amount * platform_share
            
            revenue_event = {
                'user_id': user_id,
                'revenue_type': 'yield_share',
                'amount': float(amount),
                'fee_rate': float(platform_share),
                'platform_fee': float(platform_fee),
                'metadata': {'protocol': protocol},
                'created_at': datetime.now(UTC).isoformat()
            }
            
            result = self.db.supabase.table('revenue_events').insert(revenue_event).execute()
            
            logger.info(
                f"✅ Tracked yield share: {protocol} - "
                f"${platform_fee} from user {user_id[:8]}..."
            )
            
        except Exception as e:
            logger.error(f"Failed to track yield share: {e}")
    
    async def get_revenue_summary(
        self,
        days: int = 30,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get revenue summary for analytics
        
        Args:
            days: Number of days to look back
            user_id: Optional user filter
        
        Returns:
            Summary with total revenue and breakdown by type
        """
        try:
            cutoff = datetime.now(UTC) - timedelta(days=days)
            
            # Build query
            query = self.db.supabase.table('revenue_events')\
                .select('*')\
                .gte('created_at', cutoff.isoformat())
            
            if user_id:
                query = query.eq('user_id', user_id)
            
            result = query.execute()
            
            # Calculate totals
            total_revenue = sum(
                float(event.get('platform_fee', 0)) 
                for event in result.data
            )
            
            # Group by type
            by_type = {}
            for event in result.data:
                rev_type = event['revenue_type']
                if rev_type not in by_type:
                    by_type[rev_type] = 0
                by_type[rev_type] += float(event.get('platform_fee', 0))
            
            return {
                'total_revenue': total_revenue,
                'by_type': by_type,
                'event_count': len(result.data),
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to get revenue summary: {e}")
            return {
                'total_revenue': 0.0,
                'by_type': {},
                'event_count': 0,
                'period_days': days
            }