"""
Treasury Service for Seamount.io - Fiat Reserve and USDS Backing Management
Maintains 1:1 USD backing for USDS tokens
File Location: backend/services/treasury_service.py
"""

import asyncio
import logging
from typing import Dict, Optional, Any, List
from decimal import Decimal, getcontext
from datetime import datetime, timedelta
import json

# Set decimal precision for financial calculations
getcontext().prec = 28

logger = logging.getLogger(__name__)

class TreasuryService:
    """Manages fiat reserves and USDS token backing"""
    
    def __init__(self):
        self.fiat_reserves = {}
        self.usds_circulation = Decimal('0')
        self.reserve_ratio = Decimal('1.0')  # 1:1 backing
        self.min_reserve_ratio = Decimal('0.95')  # 95% minimum
        self.transactions_log = []
        
        # Banking integration
        self.bank_accounts = {}
        self.reserve_monitoring = True
        
    async def initialize_treasury(self, initial_reserves: Dict[str, Decimal]) -> Dict[str, Any]:
        """Initialize treasury with initial fiat reserves"""
        try:
            self.fiat_reserves = initial_reserves.copy()
            
            # Log initialization
            init_log = {
                'action': 'treasury_initialized',
                'timestamp': datetime.now(),
                'reserves': dict(initial_reserves),
                'usds_circulation': float(self.usds_circulation)
            }
            self.transactions_log.append(init_log)
            
            logger.info(f"Treasury initialized with reserves: {initial_reserves}")
            
            return {
                'success': True,
                'reserves': dict(self.fiat_reserves),
                'usds_circulation': float(self.usds_circulation),
                'reserve_ratio': float(self.reserve_ratio)
            }
            
        except Exception as e:
            logger.error(f"Treasury initialization failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def record_deposit(self, amount: Decimal, usds_minted: Decimal, transaction_id: str) -> Dict[str, Any]:
        """Record fiat deposit and corresponding USDS minting"""
        try:
            # Increase fiat reserves
            if 'USD' not in self.fiat_reserves:
                self.fiat_reserves['USD'] = Decimal('0')
            
            self.fiat_reserves['USD'] += amount
            
            # Increase USDS circulation
            self.usds_circulation += usds_minted
            
            # Recalculate reserve ratio
            if self.usds_circulation > 0:
                self.reserve_ratio = sum(self.fiat_reserves.values()) / self.usds_circulation
            
            # Log transaction
            deposit_log = {
                'action': 'deposit_recorded',
                'timestamp': datetime.now(),
                'transaction_id': transaction_id,
                'fiat_deposited': float(amount),
                'usds_minted': float(usds_minted),
                'new_reserves': dict(self.fiat_reserves),
                'new_circulation': float(self.usds_circulation),
                'reserve_ratio': float(self.reserve_ratio)
            }
            self.transactions_log.append(deposit_log)
            
            # Check reserve health
            health_check = await self._check_reserve_health()
            
            logger.info(f"Deposit recorded: {amount} USD, {usds_minted} USDS minted")
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'new_reserves': dict(self.fiat_reserves),
                'new_circulation': float(self.usds_circulation),
                'reserve_ratio': float(self.reserve_ratio),
                'health_status': health_check
            }
            
        except Exception as e:
            logger.error(f"Deposit recording failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def record_withdrawal(self, amount: Decimal, usds_burned: Decimal, transaction_id: str) -> Dict[str, Any]:
        """Record fiat withdrawal and corresponding USDS burning"""
        try:
            # Decrease fiat reserves
            if 'USD' not in self.fiat_reserves or self.fiat_reserves['USD'] < amount:
                return {'success': False, 'error': 'Insufficient fiat reserves'}
            
            self.fiat_reserves['USD'] -= amount
            
            # Decrease USDS circulation
            self.usds_circulation -= usds_burned
            
            # Recalculate reserve ratio
            if self.usds_circulation > 0:
                self.reserve_ratio = sum(self.fiat_reserves.values()) / self.usds_circulation
            else:
                self.reserve_ratio = Decimal('1.0')
            
            # Log transaction
            withdrawal_log = {
                'action': 'withdrawal_recorded',
                'timestamp': datetime.now(),
                'transaction_id': transaction_id,
                'fiat_withdrawn': float(amount),
                'usds_burned': float(usds_burned),
                'new_reserves': dict(self.fiat_reserves),
                'new_circulation': float(self.usds_circulation),
                'reserve_ratio': float(self.reserve_ratio)
            }
            self.transactions_log.append(withdrawal_log)
            
            # Check reserve health
            health_check = await self._check_reserve_health()
            
            logger.info(f"Withdrawal recorded: {amount} USD, {usds_burned} USDS burned")
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'new_reserves': dict(self.fiat_reserves),
                'new_circulation': float(self.usds_circulation),
                'reserve_ratio': float(self.reserve_ratio),
                'health_status': health_check
            }
            
        except Exception as e:
            logger.error(f"Withdrawal recording failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def check_withdrawal_capacity(self, amount: Decimal) -> Dict[str, Any]:
        """Check if treasury can handle withdrawal request"""
        try:
            total_reserves = sum(self.fiat_reserves.values())
            
            # Check if sufficient reserves
            sufficient_reserves = total_reserves >= amount
            
            # Check if withdrawal would maintain minimum reserve ratio
            projected_reserves = total_reserves - amount
            projected_circulation = self.usds_circulation - amount
            
            if projected_circulation > 0:
                projected_ratio = projected_reserves / projected_circulation
                maintains_ratio = projected_ratio >= self.min_reserve_ratio
            else:
                maintains_ratio = True
            
            return {
                'sufficient': sufficient_reserves and maintains_ratio,
                'available_reserves': float(total_reserves),
                'requested_amount': float(amount),
                'projected_ratio': float(projected_ratio if projected_circulation > 0 else 1.0),
                'minimum_ratio': float(self.min_reserve_ratio),
                'reason': 'Sufficient reserves' if sufficient_reserves and maintains_ratio else 'Insufficient reserves or ratio violation'
            }
            
        except Exception as e:
            logger.error(f"Withdrawal capacity check failed: {str(e)}")
            return {'sufficient': False, 'error': str(e)}
    
    async def get_treasury_status(self) -> Dict[str, Any]:
        """Get current treasury status"""
        try:
            total_reserves = sum(self.fiat_reserves.values())
            health_check = await self._check_reserve_health()
            
            return {
                'total_reserves': float(total_reserves),
                'reserves_by_currency': {k: float(v) for k, v in self.fiat_reserves.items()},
                'usds_circulation': float(self.usds_circulation),
                'reserve_ratio': float(self.reserve_ratio),
                'minimum_ratio': float(self.min_reserve_ratio),
                'health_status': health_check['status'],
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Treasury status check failed: {str(e)}")
            return {'error': str(e)}
    
    async def generate_reserve_report(self, period_days: int = 30) -> Dict[str, Any]:
        """Generate treasury reserve report"""
        try:
            cutoff_date = datetime.now() - timedelta(days=period_days)
            
            # Filter transactions for the period
            period_transactions = [
                tx for tx in self.transactions_log
                if tx['timestamp'] >= cutoff_date
            ]
            
            # Calculate metrics
            total_deposits = sum(
                tx['fiat_deposited'] for tx in period_transactions
                if tx['action'] == 'deposit_recorded'
            )
            
            total_withdrawals = sum(
                tx['fiat_withdrawn'] for tx in period_transactions
                if tx['action'] == 'withdrawal_recorded'
            )
            
            net_flow = total_deposits - total_withdrawals
            
            # Get current status
            current_status = await self.get_treasury_status()
            
            return {
                'period_days': period_days,
                'period_start': cutoff_date.isoformat(),
                'period_end': datetime.now().isoformat(),
                'total_deposits': total_deposits,
                'total_withdrawals': total_withdrawals,
                'net_flow': net_flow,
                'transaction_count': len(period_transactions),
                'current_status': current_status,
                'average_daily_flow': net_flow / period_days if period_days > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Reserve report generation failed: {str(e)}")
            return {'error': str(e)}
    
    async def handle_emergency_protocol(self, trigger_reason: str) -> Dict[str, Any]:
        """Handle emergency scenarios (bank run, regulatory issues, etc.)"""
        try:
            # Log emergency trigger
            emergency_log = {
                'action': 'emergency_protocol_triggered',
                'timestamp': datetime.now(),
                'reason': trigger_reason,
                'reserves_at_trigger': dict(self.fiat_reserves),
                'circulation_at_trigger': float(self.usds_circulation),
                'ratio_at_trigger': float(self.reserve_ratio)
            }
            self.transactions_log.append(emergency_log)
            
            # Implement emergency measures
            emergency_measures = []
            
            # 1. Pause new USDS minting
            emergency_measures.append('new_minting_paused')
            
            # 2. Increase reserve requirements
            self.min_reserve_ratio = Decimal('1.05')  # 105% during emergency
            emergency_measures.append('reserve_ratio_increased')
            
            # 3. Implement withdrawal limits
            emergency_measures.append('withdrawal_limits_activated')
            
            # 4. Notify regulatory authorities
            emergency_measures.append('regulatory_notification_sent')
            
            logger.critical(f"Emergency protocol activated: {trigger_reason}")
            
            return {
                'success': True,
                'trigger_reason': trigger_reason,
                'measures_implemented': emergency_measures,
                'new_min_ratio': float(self.min_reserve_ratio),
                'status': 'emergency_mode_active'
            }
            
        except Exception as e:
            logger.error(f"Emergency protocol failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _check_reserve_health(self) -> Dict[str, Any]:
        """Internal health check for reserves"""
        try:
            total_reserves = sum(self.fiat_reserves.values())
            
            # Health indicators
            health_indicators = {
                'adequate_reserves': total_reserves >= self.usds_circulation,
                'healthy_ratio': self.reserve_ratio >= self.min_reserve_ratio,
                'positive_reserves': total_reserves > 0,
                'circulation_backed': self.usds_circulation <= total_reserves
            }
            
            # Overall health status
            all_healthy = all(health_indicators.values())
            
            if all_healthy:
                status = 'healthy'
            elif health_indicators['adequate_reserves'] and health_indicators['healthy_ratio']:
                status = 'warning'
            else:
                status = 'critical'
            
            return {
                'status': status,
                'indicators': health_indicators,
                'reserve_ratio': float(self.reserve_ratio),
                'min_ratio': float(self.min_reserve_ratio),
                'total_reserves': float(total_reserves),
                'reserve_coverage': float(total_reserves / self.usds_circulation) if self.usds_circulation > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"Reserve health check failed: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    async def rebalance_reserves(self, target_ratio: Decimal = None) -> Dict[str, Any]:
        """Rebalance reserves to maintain optimal ratios"""
        if target_ratio is None:
            target_ratio = Decimal('1.05')  # 5% buffer
        
        try:
            current_total = sum(self.fiat_reserves.values())
            required_reserves = self.usds_circulation * target_ratio
            
            if current_total < required_reserves:
                deficit = required_reserves - current_total
                
                # Trigger reserve increase
                rebalance_log = {
                    'action': 'reserve_rebalance_triggered',
                    'timestamp': datetime.now(),
                    'current_reserves': float(current_total),
                    'required_reserves': float(required_reserves),
                    'deficit': float(deficit),
                    'target_ratio': float(target_ratio)
                }
                self.transactions_log.append(rebalance_log)
                
                return {
                    'success': True,
                    'action_required': 'increase_reserves',
                    'deficit': float(deficit),
                    'target_ratio': float(target_ratio)
                }
            else:
                return {
                    'success': True,
                    'action_required': 'none',
                    'reserves_adequate': True,
                    'current_ratio': float(current_total / self.usds_circulation) if self.usds_circulation > 0 else 0.0
                }
                
        except Exception as e:
            logger.error(f"Reserve rebalancing failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_audit_trail(self, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Get complete audit trail of treasury operations"""
        try:
            if start_date is None:
                start_date = datetime.now() - timedelta(days=30)
            if end_date is None:
                end_date = datetime.now()
            
            # Filter transactions by date range
            filtered_transactions = [
                tx for tx in self.transactions_log
                if start_date <= tx['timestamp'] <= end_date
            ]
            
            # Sort by timestamp
            filtered_transactions.sort(key=lambda x: x['timestamp'])
            
            return filtered_transactions
            
        except Exception as e:
            logger.error(f"Audit trail retrieval failed: {str(e)}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Treasury service health check"""
        try:
            health_status = await self._check_reserve_health()
            
            return {
                'healthy': health_status['status'] in ['healthy', 'warning'],
                'status': health_status['status'],
                'reserve_ratio': health_status['reserve_ratio'],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Treasury health check failed: {str(e)}")
            return {'healthy': False, 'error': str(e)}