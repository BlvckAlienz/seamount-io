"""
Trial Balance Generation Service - DEBUG VERSION
"""
import logging
import traceback
from datetime import date
from typing import Dict, Any, List
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

class TrialBalanceGenerator:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        logger.info("✅ TrialBalanceGenerator initialized")
    
    async def generate(self, user_id: str, period_start: date, period_end: date, save_to_db: bool = True) -> Dict:
        """Generate trial balance for a period"""
        try:
            logger.info(f"🔵 Starting trial balance generation for user {user_id}")
            logger.info(f"🔵 Period: {period_start} to {period_end}")
            
            # Fetch categorized transactions for the user in the period
            logger.info("🔵 Fetching transactions from database...")
            
            try:
                trans_result = self.supabase.table('transactions')\
                    .select('*')\
                    .eq('user_id', user_id)\
                    .gte('transaction_date', period_start.isoformat())\
                    .lte('transaction_date', period_end.isoformat())\
                    .not_.is_('account_code', 'null')\
                    .execute()
                
                logger.info(f"🔵 Query executed, got {len(trans_result.data) if trans_result.data else 0} transactions")
                
            except Exception as query_error:
                logger.error(f"❌ Database query failed: {str(query_error)}")
                logger.error(f"❌ Query error details: {traceback.format_exc()}")
                return {
                    'success': False,
                    'error': f'Database query failed: {str(query_error)}'
                }
            
            if not trans_result.data:
                logger.warning("⚠️ No categorized transactions found for the period")
                return {
                    'success': False,
                    'error': 'No categorized transactions found for the period'
                }
            
            transactions = trans_result.data
            logger.info(f"✅ Found {len(transactions)} transactions")
            
            # Log a sample transaction for debugging
            if transactions:
                logger.info(f"🔵 Sample transaction: {transactions[0]}")
            
            # Group by account code
            accounts = {}
            for trans in transactions:
                try:
                    account_code = trans.get('account_code', '0000')
                    if not account_code or account_code == 'null':
                        account_code = '0000'  # Default code for uncategorized
                    
                    account_name = trans.get('category', 'Unknown')
                    
                    if account_code not in accounts:
                        accounts[account_code] = {
                            'account_code': account_code,
                            'account_name': account_name,
                            'debits': Decimal('0.00'),
                            'credits': Decimal('0.00'),
                            'balance': Decimal('0.00')
                        }
                    
                    # Convert amounts safely
                    try:
                        debit_str = str(trans.get('debit_amount', 0))
                        if debit_str is None or debit_str == 'null':
                            debit = Decimal('0.00')
                        else:
                            debit = Decimal(debit_str)
                    except (InvalidOperation, TypeError, ValueError) as e:
                        logger.warning(f"⚠️ Invalid debit amount: {trans.get('debit_amount')}, error: {e}")
                        debit = Decimal('0.00')
                    
                    try:
                        credit_str = str(trans.get('credit_amount', 0))
                        if credit_str is None or credit_str == 'null':
                            credit = Decimal('0.00')
                        else:
                            credit = Decimal(credit_str)
                    except (InvalidOperation, TypeError, ValueError) as e:
                        logger.warning(f"⚠️ Invalid credit amount: {trans.get('credit_amount')}, error: {e}")
                        credit = Decimal('0.00')
                    
                    accounts[account_code]['debits'] += debit
                    accounts[account_code]['credits'] += credit
                    
                except Exception as trans_error:
                    logger.error(f"❌ Error processing transaction {trans.get('id')}: {str(trans_error)}")
                    continue
            
            if not accounts:
                logger.error("❌ No accounts could be processed")
                return {
                    'success': False,
                    'error': 'No valid account data could be processed'
                }
            
            logger.info(f"✅ Processed {len(accounts)} accounts")
            
            # Calculate balances and totals
            total_debits = Decimal('0.00')
            total_credits = Decimal('0.00')
            
            for account_code, account_data in accounts.items():
                # Simple balance calculation (debits - credits)
                account_data['balance'] = account_data['debits'] - account_data['credits']
                total_debits += account_data['debits']
                total_credits += account_data['credits']
            
            # Format accounts for response
            accounts_list = []
            for account_code, account_data in accounts.items():
                accounts_list.append({
                    'account_code': account_data['account_code'],
                    'account_name': account_data['account_name'],
                    'account_type': self._get_account_type(account_code),
                    'debits': float(account_data['debits']),
                    'credits': float(account_data['credits']),
                    'balance': float(account_data['balance'])
                })
            
            trial_balance = {
                'accounts': accounts_list,
                'total_debits': float(total_debits),
                'total_credits': float(total_credits),
                'is_balanced': abs(total_debits - total_credits) < Decimal('0.01'),
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat()
            }
            
            # 🚨 SANITY CHECK: Validate aggregated totals
            if total_debits > 1_000_000_000:  # ₦1 Billion
                logger.error(
                    f"🚨 TRIAL BALANCE SANITY CHECK FAILED: "
                    f"Total debits = ₦{total_debits:,.2f} (exceeds ₦1B)"
                )
                return {
                    'success': False,
                    'error': 'Trial balance contains suspicious amounts. Please verify source data.'
                }

            if total_credits > 1_000_000_000:
                logger.error(
                    f"🚨 TRIAL BALANCE SANITY CHECK FAILED: "
                    f"Total credits = ₦{total_credits:,.2f} (exceeds ₦1B)"
                )
                return {
                    'success': False,
                    'error': 'Trial balance contains suspicious amounts. Please verify source data.'
                }

            logger.info(f"✅ Trial balance calculated: {len(accounts_list)} accounts")
            logger.info(f"✅ Total debits: {total_debits}, Total credits: {total_credits}")
            logger.info(f"✅ Is balanced: {trial_balance['is_balanced']}")
            
            # Save to database if requested
            report_id = None
            if save_to_db:
                try:
                    report_data = {
                        'user_id': user_id,
                        'period_start': period_start,
                        'period_end': period_end,
                        'report_data': trial_balance,  # This matches your JSONB column
                        'total_debits': float(total_debits),
                        'total_credits': float(total_credits),
                        'is_balanced': trial_balance['is_balanced'],
                        'generated_at': datetime.now().isoformat()
                        # Note: Don't include excel_url unless you're generating it
                    }
                    
                    logger.info("🔵 Saving trial balance to database...")
                    result = self.supabase.table('trial_balances').insert(report_data).execute()
                    if result.data:
                        report_id = result.data[0]['id']
                        logger.info(f"✅ Saved to database with ID: {report_id}")
                except Exception as save_error:
                    logger.error(f"❌ Failed to save trial balance to database: {str(save_error)}")
            
            return {
                'success': True,
                'trial_balance': trial_balance,
                'report_id': report_id
            }
            
        except Exception as e:
            logger.error(f"❌ Trial balance generation failed: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def _get_account_type(self, account_code: str) -> str:
        """Map account code to account type"""
        if not account_code or len(account_code) == 0:
            return 'Other'
        
        first_digit = account_code[0]
        
        account_types = {
            '1': 'Asset',
            '2': 'Liability',
            '3': 'Equity',
            '4': 'Revenue',
            '5': 'Expense',
            '6': 'Expense',
            '7': 'Revenue',
            '8': 'Expense',
            '9': 'Expense'
        }
        
        return account_types.get(first_digit, 'Other')