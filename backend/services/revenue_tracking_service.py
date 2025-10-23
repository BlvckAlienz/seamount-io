# File: backend/services/revenue_tracking_service.py
"""
Revenue Tracking & Instrumentation Service
Track ALL revenue streams for business intelligence
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from backend.services.database_service import DatabaseService
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class RevenueTrackingService:
    """Track and analyze revenue across all streams"""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        
    async def track_transaction_fee(
        self,
        user_id: str,
        transaction_type: str,
        amount: Decimal,
        fee_rate: Decimal,
        platform_fee: Decimal,
        network_fee: Decimal,
        blockchain: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Track transaction fee revenue"""
        
        try:
            await self.db.supabase.table('revenue_events').insert({
                'user_id': user_id,
                'revenue_type': 'transaction_fee',
                'transaction_type': transaction_type,
                'amount': float(amount),
                'fee_rate': float(fee_rate),
                'platform_fee': float(platform_fee),
                'network_fee': float(network_fee),
                'blockchain': blockchain,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(
                f"📊 Revenue tracked: ${float(platform_fee):.4f} "
                f"({float(fee_rate * 100):.2f}% of ${float(amount)}) - {transaction_type}"
            )
            
        except Exception as e:
            logger.error(f"Failed to track transaction fee: {e}")
            # Don't block transaction on logging failure
    
    async def track_gas_markup(
        self,
        user_id: str,
        blockchain: str,
        gas_charged: Decimal,
        gas_actual: Decimal,
        markup: Decimal,
        transaction_id: Optional[str] = None
    ) -> None:
        """Track hidden gas fee markup revenue"""
        
        try:
            markup_percent = (markup / gas_actual * 100) if gas_actual > 0 else 0
            
            await self.db.supabase.table('revenue_events').insert({
                'user_id': user_id,
                'revenue_type': 'gas_markup',
                'blockchain': blockchain,
                'amount': float(gas_charged),
                'platform_fee': float(markup),
                'metadata': {
                    'gas_actual': float(gas_actual),
                    'gas_charged': float(gas_charged),
                    'markup_percent': float(markup_percent),
                    'transaction_id': transaction_id
                },
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(
                f"💰 Gas markup tracked: ${float(markup):.6f} "
                f"({float(markup_percent):.1f}% markup on {blockchain})"
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
        """Track FX conversion spread revenue"""
        
        try:
            await self.db.supabase.table('revenue_events').insert({
                'user_id': user_id,
                'revenue_type': 'fx_spread',
                'amount': float(amount),
                'platform_fee': float(spread_amount),
                'metadata': {
                    'from_currency': from_currency,
                    'to_currency': to_currency,
                    'spread_rate': float(spread_rate),
                    'spread_bps': float(spread_rate * 10000)  # Basis points
                },
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(
                f"💱 FX spread tracked: ${float(spread_amount):.4f} "
                f"({from_currency}→{to_currency})"
            )
            
        except Exception as e:
            logger.error(f"Failed to track FX spread: {e}")
    
    async def get_revenue_summary(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get revenue summary for period"""
        
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            events = self.db.supabase.table('revenue_events')\
                .select('*')\
                .gte('created_at', cutoff.isoformat())\
                .execute()
            
            if not events.data:
                return {
                    'total_revenue': 0.0,
                    'by_type': {},
                    'days': days
                }
            
            # Aggregate by type
            by_type = {}
            total = Decimal('0')
            
            for event in events.data:
                rev_type = event['revenue_type']
                fee = Decimal(str(event.get('platform_fee', 0)))
                
                if rev_type not in by_type:
                    by_type[rev_type] = Decimal('0')
                
                by_type[rev_type] += fee
                total += fee
            
            return {
                'total_revenue': float(total),
                'by_type': {k: float(v) for k, v in by_type.items()},
                'days': days,
                'event_count': len(events.data)
            }
            
        except Exception as e:
            logger.error(f"Revenue summary failed: {e}")
            return {'error': str(e)}