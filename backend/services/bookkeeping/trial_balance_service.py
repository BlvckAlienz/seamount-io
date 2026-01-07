# backend/services/bookkeeping/trial_balance_service.py
"""
Trial Balance Generator - Produces accounting reports
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal

logger = logging.getLogger(__name__)

class TrialBalanceGenerator:
    """
    Generate trial balance reports from categorized transactions
    """
    
    def __init__(self, supabase_client):
        """
        Initialize with Supabase client for database operations
        """
        self.supabase = supabase_client
    
    async def generate(
        self,
        user_id: str,
        period_start: date,
        period_end: date,
        save_to_db: bool = True
    ) -> Dict:
        """
        Generate trial balance for a given period
        
        Args:
            user_id: User's UUID
            period_start: Start date of reporting period
            period_end: End date of reporting period
            save_to_db: Whether to save the report to database
        
        Returns:
            {
                'success': bool,
                'trial_balance': Dict,
                'total_debits': Decimal,
                'total_credits': Decimal,
                'is_balanced': bool,
                'report_id': Optional[str]
            }
        """
        try:
            # Call database function to generate trial balance
            result = self.supabase.rpc(
                'generate_trial_balance',
                {
                    'p_user_id': user_id,
                    'p_period_start': period_start.isoformat(),
                    'p_period_end': period_end.isoformat()
                }
            ).execute()
            
            if not result.data:
                return {
                    'success': False,
                    'error': 'No data returned from database'
                }
            
            trial_balance_data = result.data
            
            # Parse response
            accounts = trial_balance_data.get('accounts', [])
            total_debits = Decimal(str(trial_balance_data.get('total_debits', 0)))
            total_credits = Decimal(str(trial_balance_data.get('total_credits', 0)))
            is_balanced = trial_balance_data.get('is_balanced', False)
            
            # Save to database if requested
            report_id = None
            if save_to_db:
                report_id = await self._save_report(
                    user_id=user_id,
                    period_start=period_start,
                    period_end=period_end,
                    report_data=trial_balance_data,
                    total_debits=float(total_debits),
                    total_credits=float(total_credits),
                    is_balanced=is_balanced
                )
            
            logger.info(f"✅ Trial balance generated: {len(accounts)} accounts, Balanced: {is_balanced}")
            
            return {
                'success': True,
                'trial_balance': trial_balance_data,
                'total_debits': total_debits,
                'total_credits': total_credits,
                'is_balanced': is_balanced,
                'report_id': report_id
            }
            
        except Exception as e:
            logger.error(f"❌ Trial balance generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _save_report(
        self,
        user_id: str,
        period_start: date,
        period_end: date,
        report_data: Dict,
        total_debits: float,
        total_credits: float,
        is_balanced: bool
    ) -> Optional[str]:
        """
        Save trial balance report to database
        """
        try:
            result = self.supabase.table('trial_balances').insert({
                'user_id': user_id,
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'report_data': report_data,
                'total_debits': total_debits,
                'total_credits': total_credits,
                'is_balanced': is_balanced,
                'generated_at': datetime.utcnow().isoformat()
            }).execute()
            
            if result.data:
                report_id = result.data[0]['id']
                logger.info(f"✅ Report saved: {report_id}")
                return report_id
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to save report: {str(e)}")
            return None
    
    async def get_saved_reports(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Retrieve user's saved trial balance reports
        """
        try:
            result = self.supabase.table('trial_balances')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('generated_at', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve reports: {str(e)}")
            return []
    
    def validate_trial_balance(self, trial_balance: Dict) -> Dict:
        """
        Validate trial balance and identify issues
        
        Returns:
            {
                'is_valid': bool,
                'issues': List[str],
                'warnings': List[str]
            }
        """
        issues = []
        warnings = []
        
        total_debits = Decimal(str(trial_balance.get('total_debits', 0)))
        total_credits = Decimal(str(trial_balance.get('total_credits', 0)))
        
        # Check if balanced
        if total_debits != total_credits:
            difference = abs(total_debits - total_credits)
            issues.append(
                f"Trial balance not balanced. Difference: ₦{difference:,.2f}"
            )
        
        # Check for empty accounts
        accounts = trial_balance.get('accounts', [])
        if len(accounts) == 0:
            warnings.append("No transactions found for this period")
        
        # Check for accounts with zero balances
        zero_balance_accounts = [
            acc for acc in accounts 
            if Decimal(str(acc.get('balance', 0))) == 0
        ]
        if zero_balance_accounts:
            warnings.append(
                f"{len(zero_balance_accounts)} accounts have zero balances"
            )
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }