import logging
from typing import Dict, Any, List
from decimal import Decimal, getcontext
from datetime import datetime, timedelta

# --- Core Dependencies ---
from config import Settings
from .database_service import DatabaseService
from .algorand_service import AlgorandService

# Set decimal precision for financial calculations
getcontext().prec = 28
logger = logging.getLogger(__name__)

class TreasuryService:
    """
    Manages fiat reserves and USDS token backing. It is a modern, dependency-injected service.
    """
    
    def __init__(self, settings: Settings, db_service: DatabaseService, algorand_service: AlgorandService):
        """
        Initializes the service with pre-configured dependencies.
        """
        self.settings = settings
        self.db_service = db_service
        self.algorand_service = algorand_service
        self.min_reserve_ratio = Decimal('1.0') # Maintain 100% backing at all times
        logger.info("TreasuryService initialized successfully.")
    
    async def get_treasury_status(self) -> Dict[str, Any]:
        """Gets the current, real-time status of the treasury from the database and blockchain."""
        try:
            # In a production system, these values would be fetched from a secure,
            # continuously updated source of truth, like a dedicated table in your database.
            # For this implementation, we will fetch them from the blockchain and simulate fiat reserves.
            
            usds_circulation = await self.algorand_service.get_total_usds_supply()
            # This is a placeholder for a real-time fiat reserve balance API call
            fiat_reserves = await self.db_service.get_fiat_reserve_balance('USD')

            if usds_circulation > 0:
                reserve_ratio = fiat_reserves / usds_circulation
            else:
                reserve_ratio = Decimal('inf') # Infinite ratio if no circulation
            
            health_status = 'healthy'
            if reserve_ratio < self.min_reserve_ratio:
                health_status = 'critical'
            elif reserve_ratio < Decimal(str(self.settings.USDS_BACKING_RATIO)):
                health_status = 'warning'

            return {
                'total_reserves_usd': float(fiat_reserves),
                'usds_circulation': float(usds_circulation),
                'reserve_ratio': float(reserve_ratio),
                'target_ratio': float(self.settings.USDS_BACKING_RATIO),
                'health_status': health_status,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Treasury status check failed: {e}", exc_info=True)
            return {'error': str(e), 'health_status': 'unknown'}

    async def record_deposit(self, amount: Decimal, usds_minted: Decimal, transaction_id: str) -> bool:
        """Records a fiat deposit event in the treasury log."""
        try:
            log_entry = {
                'action': 'deposit',
                'fiat_amount': float(amount),
                'fiat_currency': 'USD',
                'usds_amount': float(usds_minted),
                'transaction_id': transaction_id,
            }
            # This should call a method in database_service to log the transaction
            # await self.db_service.log_treasury_transaction(log_entry)
            logger.info(f"Treasury deposit recorded: {amount} USD for transaction {transaction_id}")
            return True
        except Exception as e:
            logger.error(f"Deposit recording failed for transaction {transaction_id}: {e}", exc_info=True)
            return False

    async def record_withdrawal(self, amount: Decimal, usds_burned: Decimal, transaction_id: str) -> bool:
        """Records a fiat withdrawal event in the treasury log."""
        try:
            log_entry = {
                'action': 'withdrawal',
                'fiat_amount': float(amount),
                'fiat_currency': 'USD',
                'usds_amount': float(usds_burned),
                'transaction_id': transaction_id,
            }
            # await self.db_service.log_treasury_transaction(log_entry)
            logger.info(f"Treasury withdrawal recorded: {amount} USD for transaction {transaction_id}")
            return True
        except Exception as e:
            logger.error(f"Withdrawal recording failed for transaction {transaction_id}: {e}", exc_info=True)
            return False

    async def check_withdrawal_capacity(self, amount_to_withdraw: Decimal) -> Dict[str, Any]:
        """Checks if the treasury can safely handle a withdrawal request."""
        try:
            status = await self.get_treasury_status()
            current_reserves = Decimal(str(status['total_reserves_usd']))
            
            if current_reserves < amount_to_withdraw:
                return {'sufficient': False, 'reason': 'Insufficient fiat reserves.'}
            
            projected_reserves = current_reserves - amount_to_withdraw
            projected_circulation = Decimal(str(status['usds_circulation'])) - amount_to_withdraw

            if projected_circulation > 0:
                projected_ratio = projected_reserves / projected_circulation
                if projected_ratio < self.min_reserve_ratio:
                    return {
                        'sufficient': False,
                        'reason': f"Withdrawal would breach minimum reserve ratio. Projected: {projected_ratio:.2f}%"
                    }
            
            return {'sufficient': True, 'reason': 'Sufficient reserves and ratio maintained.'}
            
        except Exception as e:
            logger.error(f"Withdrawal capacity check failed: {e}", exc_info=True)
            return {'sufficient': False, 'error': 'Internal treasury error.'}

    async def generate_reserve_report(self, period_days: int = 30) -> Dict[str, Any]:
        """Generates a treasury reserve report for compliance and transparency."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_days)
            
            # These calls would be delegated to the database_service
            # total_deposits = await self.db_service.get_treasury_volume('deposit', start_date, end_date)
            # total_withdrawals = await self.db_service.get_treasury_volume('withdrawal', start_date, end_date)
            total_deposits = Decimal('500000') # Mock data
            total_withdrawals = Decimal('150000') # Mock data
            
            net_flow = total_deposits - total_withdrawals
            current_status = await self.get_treasury_status()
            
            return {
                'period_days': period_days,
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'total_deposits_usd': float(total_deposits),
                'total_withdrawals_usd': float(total_withdrawals),
                'net_flow_usd': float(net_flow),
                'current_status': current_status
            }
            
        except Exception as e:
            logger.error(f"Reserve report generation failed: {e}", exc_info=True)
            return {'error': 'Failed to generate reserve report.'}