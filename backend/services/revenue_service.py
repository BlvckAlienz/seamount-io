import logging
from typing import Dict, Any
from decimal import Decimal, getcontext
from datetime import datetime, timedelta

# --- Core Dependencies ---
from config import Settings
from .database_service import DatabaseService

# Set decimal precision for financial calculations
getcontext().prec = 28
logger = logging.getLogger(__name__)

class RevenueService:
    """
    Handles all revenue collection and tracking logic, using the definitive
    business rules from the application's central configuration.
    """
    def __init__(self, settings: Settings, db_service: DatabaseService):
        """
        Initializes the service with pre-configured dependencies.
        """
        self.settings = settings
        self.db_service = db_service
        logger.info("RevenueService initialized successfully.")

    async def _log_revenue(self, amount: Decimal, fee_type: str, transaction_id: str, status: str = 'collected') -> None:
        """Logs a revenue event to the database via the DatabaseService."""
        try:
            revenue_log = {
                "amount": float(amount),
                "fee_type": fee_type,
                "transaction_id": transaction_id,
                "status": status
            }
            # This call assumes a 'log_event' or similar method in your DatabaseService
            # that can write to a 'revenue_log' table.
            await self.db_service.log_event("revenue_log", revenue_log)
        except Exception as e:
            logger.error(f"Revenue logging failed for tx_id {transaction_id}: {e}", exc_info=True)
            # In a production system, this would go to a dead-letter queue for retry.

    def _get_user_tier_info(self, country_code: str) -> str:
        """Helper to determine a user's geographic tier from the central config."""
        for tier, countries in self.settings.GEOGRAPHIC_TIERS.items():
            if country_code.upper() in countries:
                return tier
        return 'tier_3' # Default to the most restrictive tier

    async def collect_and_log_fee(self, amount: Decimal, sender_country: str, recipient_country: str, transaction_id: str) -> Decimal:
        """
        Calculates and logs the definitive transaction fee based on the business logic
        defined in the central FEE_STRUCTURE.
        """
        try:
            sender_tier = self._get_user_tier_info(sender_country)
            fee_structure = self.settings.FEE_STRUCTURE
            fee_type = "cross_border"
            
            if sender_country == recipient_country:
                fee_type = "p2p_local"
                fee_key = sender_tier if sender_tier in fee_structure['processing'] else 'tier_2_standard'
                fee_rate = fee_structure['processing'][fee_key]
                fee_amount = amount * Decimal(str(fee_rate))
            else:
                fee_key = sender_tier if sender_tier in fee_structure['bridge'] else 'tier_2_standard'
                fee_rate = fee_structure['bridge'][fee_key]
                fee_amount = amount * Decimal(str(fee_rate))
                min_fee = Decimal(str(fee_structure['bridge']['min_fee']))
                max_fee = Decimal(str(fee_structure['bridge']['max_fee']))
                fee_amount = max(min_fee, min(fee_amount, max_fee))

            final_fee = fee_amount.quantize(Decimal('0.01'))

            await self._log_revenue(final_fee, fee_type, transaction_id)
            
            logger.info(f"Fee collected for tx {transaction_id}: {final_fee} ({fee_type})")
            return final_fee
            
        except Exception as e:
            logger.error(f"Fee collection failed for tx {transaction_id}: {e}", exc_info=True)
            return Decimal('0')

    async def collect_trading_fee(self, profit_amount: Decimal, transaction_id: str) -> Decimal:
        """Calculates and logs a performance fee from trading profits."""
        try:
            # Assuming a simple 20% performance fee, can be moved to config
            performance_fee_rate = Decimal('0.20')
            fee_amount = profit_amount * performance_fee_rate
            
            await self._log_revenue(fee_amount, 'trading_performance', transaction_id)
            
            logger.info(f"Trading fee collected: {fee_amount} from {profit_amount} profit")
            return fee_amount
            
        except Exception as e:
            logger.error(f"Trading fee collection failed: {e}", exc_info=True)
            return Decimal('0')

    async def get_revenue_summary(self) -> Dict[str, Any]:
        """Gets a real revenue summary for a dashboard by querying the database."""
        try:
            # These complex queries should be handled by dedicated methods in the DatabaseService
            # to keep this service clean and focused on business logic.
            today_summary = await self.db_service.get_revenue_summary_for_period(days=1)
            total_summary = await self.db_service.get_revenue_summary_for_period()
            
            total_revenue = Decimal(str(total_summary.get('total_revenue', '0')))
            total_count = total_summary.get('transaction_count', 0)
            
            return {
                'today_revenue': float(today_summary.get('total_revenue', 0)),
                'today_transactions': today_summary.get('transaction_count', 0),
                'total_revenue': float(total_revenue),
                'total_transactions': total_count,
                'avg_fee': float(total_revenue / total_count) if total_count > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"Revenue summary generation failed: {e}", exc_info=True)
            return {
                'today_revenue': 0.0,
                'today_transactions': 0,
                'total_revenue': 0.0,
                'total_transactions': 0,
                'avg_fee': 0.0,
                'error': 'Could not generate revenue summary.'
            }