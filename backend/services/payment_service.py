# File Location: backend/services/payment_service.py (UNIFIED ENHANCED VERSION)
import logging
from decimal import Decimal, getcontext
from typing import Dict, Any, Optional, Literal
from uuid import uuid4
from datetime import datetime
from fastapi import HTTPException

# Core Dependencies
from supabase import Client
from config import Settings
from .algorand_service import AlgorandService
from .kyc_service import KYCService
from .audit_service import AuditService, AuditEventType
from .treasury_service import TreasuryService
from .notification_service import NotificationService

# Payment Processors (Focus on viable providers: Paystack + Sterling + Flutterwave)
from .payment_providers.flutterwave import FlutterwaveProcessor
from .payment_providers.paystack import PaystackProcessor
# Note: Circle CCTP removed for now - requires business verification

getcontext().prec = 28
logger = logging.getLogger(__name__)

class EnhancedPaymentService:
    """
    PRODUCTION-READY Payment Service with Smart Routing:
    - Nigerian NGN payments â†’ Paystack (1.2% vs 2.15% Flutterwave = 45% savings)
    - International transfers â†’ Sterling Bank API (when approved) 
    - Fallback safety net â†’ Flutterwave (all currencies)
    - Circle CCTP future integration â†’ Post business verification
    """
    
    # OPTIMIZED ROUTING RULES FOR IMMEDIATE DEPLOYMENT
    PROVIDER_RULES = {
        'nigeria_local': {
            'primary': 'paystack',           # 1.2% fees (best for NGN)
            'fallback': 'flutterwave',       # 2.15% fees (safety net)
            'currencies': ['NGN'],
            'max_amount': Decimal('10000000'),  # 10M NGN (~$25K USD)
            'fee_savings': 0.45                 # 45% fee reduction vs Flutterwave
        },
        'international_africa': {
            'primary': 'sterling_bank',      # When API approved
            'fallback': 'flutterwave',       # 3.8% fees (current fallback)
            'currencies': ['KES', 'GHS', 'ZAR', 'UGX', 'TZS'],
            'max_amount': Decimal('50000'),     # $50K USD equiv
            'fee_savings': 0.60                 # 60% savings vs Flutterwave
        },
        'international_global': {
            'primary': 'flutterwave',        # Only option until Sterling approved
            'fallback': None,
            'currencies': ['USD', 'EUR', 'GBP', 'CAD', 'AUD'],
            'max_amount': Decimal('25000'),     # $25K USD
            'fee_savings': 0.0                  # No savings yet
        }
    }
    
    def __init__(
        self, 
        settings: Settings, 
        supabase_client: Client, 
        algorand_service: AlgorandService, 
        kyc_service: KYCService, 
        audit_service: AuditService,
        treasury_service: TreasuryService,
        notification_service: NotificationService
    ):
        self.settings = settings
        self.supabase = supabase_client
        self.algorand_service = algorand_service
        self.kyc_service = kyc_service
        self.audit = audit_service
        self.treasury = treasury_service
        self.notifications = notification_service
        
        # Initialize available payment processors
        self.paystack = PaystackProcessor(settings)
        self.flutterwave = FlutterwaveProcessor(settings)
        # self.sterling_bank = SterlingBankProcessor(settings)  # Add when API approved
        
        self.processors = {
            'paystack': self.paystack,
            'flutterwave': self.flutterwave,
            # 'sterling_bank': self.sterling_bank  # Uncomment when ready
        }
        
        logger.info("ðŸŽ¯ Enhanced Payment Service initialized - Production routing active")
    
    def _determine_optimal_route(self, amount: Decimal, currency: str, user_country: str) -> Dict[str, Any]:
        """PRODUCTION Smart Routing - Live fee optimization"""
        
        country_code = user_country.upper()
        
        # Rule 1: Nigerian NGN â†’ Paystack (45% fee savings)
        if currency == 'NGN' and country_code == 'NG':
            if amount <= self.PROVIDER_RULES['nigeria_local']['max_amount']:
                return {
                    'route_type': 'nigeria_local',
                    'primary_provider': 'paystack',
                    'fallback_provider': 'flutterwave',
                    'expected_fee_pct': 1.2,
                    'fee_savings_pct': 45,
                    'reason': 'Nigerian local - Paystack 45% cheaper than Flutterwave',
                    'estimated_fee': float(amount * Decimal('0.012'))
                }
        
        # Rule 2: African countries â†’ Sterling Bank (when available)
        african_currencies = ['KES', 'GHS', 'ZAR', 'UGX', 'TZS']
        if currency in african_currencies:
            # Check if Sterling Bank API is available
            sterling_available = self.processors.get('sterling_bank') is not None
            
            if sterling_available and amount <= self.PROVIDER_RULES['international_africa']['max_amount']:
                return {
                    'route_type': 'international_africa',
                    'primary_provider': 'sterling_bank',
                    'fallback_provider': 'flutterwave',
                    'expected_fee_pct': 1.5,
                    'fee_savings_pct': 60,
                    'reason': 'African corridor - Sterling Bank 60% cheaper',
                    'estimated_fee': float(amount * Decimal('0.015'))
                }
            else:
                return {
                    'route_type': 'international_africa',
                    'primary_provider': 'flutterwave',
                    'fallback_provider': None,
                    'expected_fee_pct': 3.8,
                    'fee_savings_pct': 0,
                    'reason': 'African corridor - Sterling Bank pending approval',
                    'estimated_fee': float(amount * Decimal('0.038'))
                }
        
        # Rule 3: Global currencies â†’ Flutterwave (until Circle CCTP ready)
        global_currencies = ['USD', 'EUR', 'GBP', 'CAD', 'AUD']
        if currency in global_currencies:
            return {
                'route_type': 'international_global',
                'primary_provider': 'flutterwave',
                'fallback_provider': None,
                'expected_fee_pct': 3.8,
                'fee_savings_pct': 0,
                'reason': 'Global transfer - Circle CCTP integration pending',
                'estimated_fee': float(amount * Decimal('0.038'))
            }
        
        # Rule 4: Fallback for unsupported currencies
        return {
            'route_type': 'fallback',
            'primary_provider': 'flutterwave',
            'fallback_provider': None,
            'expected_fee_pct': 3.8,
            'fee_savings_pct': 0,
            'reason': 'Unsupported currency - Flutterwave universal fallback',
            'estimated_fee': float(amount * Decimal('0.038'))
        }
    
    async def _execute_with_fallback(self, 
                                   operation: str,
                                   primary_provider: str,
                                   fallback_provider: Optional[str],
                                   **kwargs) -> Dict[str, Any]:
        """Execute with automatic fallback + retry mechanism"""
        
        providers_to_try = [primary_provider]
        if fallback_provider:
            providers_to_try.append(fallback_provider)
        
        last_error = None
        
        for attempt, provider_name in enumerate(providers_to_try):
            try:
                processor = self.processors.get(provider_name)
                if not processor:
                    raise ValueError(f"Processor {provider_name} not initialized")
                
                logger.info(f"ðŸ”„ Attempting {operation} with {provider_name} (attempt {attempt + 1})")
                
                if operation == 'initialize_payment':
                    result = await processor.initialize_payment(**kwargs)
                elif operation == 'verify_payment':
                    result = await processor.verify_payment(**kwargs)
                elif operation == 'initiate_payout':
                    result = await processor.initiate_payout(**kwargs)
                else:
                    raise ValueError(f"Unsupported operation: {operation}")
                
                # Success
                logger.info(f"âœ… {operation} successful with {provider_name}")
                result['provider_used'] = provider_name
                result['attempt_number'] = attempt + 1
                return result
                
            except Exception as e:
                logger.error(f"âŒ {operation} failed with {provider_name}: {e}")
                last_error = e
                
                # If primary failed and fallback exists, continue to next provider
                if provider_name == primary_provider and fallback_provider:
                    logger.warning(f"ðŸ”„ Falling back from {primary_provider} to {fallback_provider}")
                    continue
        
        # All providers failed
        logger.error(f"ðŸ’¥ All providers failed for {operation}. Last error: {str(last_error)}")
        raise HTTPException(
            status_code=503, 
            detail=f"Payment processing temporarily unavailable. Please try again in a few minutes."
        )
    
    # =============================================================================
    # ENHANCED FIAT DEPOSIT (ON-RAMP) WITH PRODUCTION ROUTING
    # =============================================================================
    
    async def initialize_fiat_deposit(self, 
                                    user_id: str, 
                                    user_email: str, 
                                    amount: Decimal, 
                                    currency: str,
                                    user_country: str = 'NG') -> Dict[str, Any]:
        """Production-ready deposit with smart routing"""
        
        transaction_id = f"DEP_{uuid4().hex[:8]}"
        logger.info(f"ðŸ’³ Initializing deposit {transaction_id}: {amount} {currency} for user {user_id}")
        
        try:
            # Validate inputs
            if amount <= Decimal("0.0"):
                raise ValueError("Deposit amount must be positive")
            
            if amount > Decimal("100000"):  # $100K limit
                raise ValueError("Deposit amount exceeds maximum limit")
            
            # Get optimal routing
            route_info = self._determine_optimal_route(amount, currency, user_country)
            
            # Log routing decision for analytics
            await self.audit.log_event(
                AuditEventType.MINT_INITIATED, 
                user_id=user_id, 
                resource_id=transaction_id,
                details={
                    "amount": float(amount),
                    "currency": currency,
                    "route_type": route_info['route_type'],
                    "primary_provider": route_info['primary_provider'],
                    "expected_fee": route_info['estimated_fee'],
                    "fee_savings_pct": route_info['fee_savings_pct']
                }
            )
            
            # Create transaction record
            tx_data = {
                "id": transaction_id,
                "user_id": user_id,
                "transaction_type": "deposit",
                "status": "pending",
                "amount": float(amount),
                "currency": currency,
                "provider": route_info['primary_provider'],
                "routing_metadata": route_info,
                "created_at": datetime.utcnow().isoformat(),
                "reference": transaction_id
            }
            
            await self.supabase.table("payment_transactions").insert(tx_data).execute()
            
            # Execute payment initialization with smart routing
            result = await self._execute_with_fallback(
                operation='initialize_payment',
                primary_provider=route_info['primary_provider'],
                fallback_provider=route_info.get('fallback_provider'),
                amount=amount,
                currency=currency,
                email=user_email,
                tx_ref=transaction_id,
                callback_url=f"{self.settings.api_base_url}/webhooks/{route_info['primary_provider']}",
                return_url=f"{self.settings.frontend_url}/deposit/success"
            )
            
            # Update with provider response
            update_data = {
                "provider_tx_id": result.get('tx_id') or result.get('reference'),
                "payment_url": result.get('payment_url') or result.get('authorization_url'),
                "provider_response": result,
                "provider": result['provider_used'],  # Actual provider used (after fallback)
                "updated_at": datetime.utcnow().isoformat()
            }
            
            await self.supabase.table("payment_transactions").update(update_data).eq("id", transaction_id).execute()
            
            logger.info(f"âœ… Deposit initialized: {transaction_id} via {result['provider_used']}")
            
            return {
                "transaction_id": transaction_id,
                "payment_url": result.get('payment_url') or result.get('authorization_url'),
                "amount": float(amount),
                "currency": currency,
                "provider": result['provider_used'],
                "estimated_fee": route_info['estimated_fee'],
                "fee_savings": f"{route_info['fee_savings_pct']}%",
                "expires_at": result.get('expires_at'),
                "routing_reason": route_info['reason']
            }
            
        except Exception as e:
            logger.error(f"ðŸ’¥ Deposit initialization failed: {e}")
            
            # Update transaction status
            try:
                await self.supabase.table("payment_transactions").update({
                    "status": "failed",
                    "error_message": str(e),
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", transaction_id).execute()
            except:
                pass  # Don't fail on DB update error
                
            raise HTTPException(status_code=400, detail=f"Failed to initialize deposit: {e}")
    
    # =============================================================================
    # ENHANCED FIAT WITHDRAWAL (OFF-RAMP) WITH PRODUCTION ROUTING
    # =============================================================================
    
    async def initialize_fiat_withdrawal(self,
                                       user_id: str,
                                       amount: Decimal,
                                       currency: str,
                                       bank_details: Dict[str, str],
                                       user_country: str = 'NG') -> Dict[str, Any]:
        """Production-ready withdrawal with smart routing"""
        
        transaction_id = f"WTH_{uuid4().hex[:8]}"
        logger.info(f"ðŸ’° Initializing withdrawal {transaction_id}: {amount} {currency}")
        
        try:
            # Validate USDS balance
            usds_balance = await self.algorand_service.get_usds_balance(user_id)
            if usds_balance < amount:
                raise HTTPException(status_code=400, detail="Insufficient USDS balance")
            
            # Get optimal routing
            route_info = self._determine_optimal_route(amount, currency, user_country)
            
            # Create withdrawal transaction
            tx_data = {
                "id": transaction_id,
                "user_id": user_id,
                "transaction_type": "withdrawal",
                "status": "pending",
                "amount": float(amount),
                "currency": currency,
                "provider": route_info['primary_provider'],
                "bank_details": bank_details,
                "routing_metadata": route_info,
                "created_at": datetime.utcnow().isoformat(),
                "reference": transaction_id
            }
            
            await self.supabase.table("payment_transactions").insert(tx_data).execute()
            
            # Execute payout with smart routing
            result = await self._execute_with_fallback(
                operation='initiate_payout',
                primary_provider=route_info['primary_provider'],
                fallback_provider=route_info.get('fallback_provider'),
                amount=amount,
                currency=currency,
                bank_details=bank_details,
                reference=transaction_id
            )
            
            # Update with payout details
            await self.supabase.table("payment_transactions").update({
                "provider_tx_id": result.get('id') or result.get('reference'),
                "provider_response": result,
                "provider": result['provider_used'],
                "status": "processing",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", transaction_id).execute()
            
            logger.info(f"âœ… Withdrawal initiated: {transaction_id} via {result['provider_used']}")
            
            return {
                "transaction_id": transaction_id,
                "status": "processing",
                "provider": result['provider_used'],
                "estimated_fee": route_info['estimated_fee'],
                "fee_savings": f"{route_info['fee_savings_pct']}%",
                "estimated_completion": "5-30 minutes depending on provider"
            }
            
        except Exception as e:
            logger.error(f"ðŸ’¥ Withdrawal failed: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to process withdrawal: {e}")
    
    # =============================================================================
    # WEBHOOK EVENT HANDLERS (UNIFIED FOR ALL PROVIDERS)
    # =============================================================================
    
    async def _handle_successful_payment(self, 
                                       transaction_id: str, 
                                       provider_tx_id: str, 
                                       amount: Decimal, currency: str, metadata: Dict[str, Any]):
        """Process successful payment confirmation with USDS minting"""
        
        try:
            # Get transaction details
            tx_result = await self.supabase.table("payment_transactions")\
                .select("*")\
                .eq("id", transaction_id)\
                .single()
            
            if not tx_result.data:
                raise ValueError(f"Transaction not found: {transaction_id}")
            
            tx = tx_result.data
            
            if tx['transaction_type'] == 'deposit':
                # Mint USDS tokens equivalent to fiat received
                mint_result = await self.algorand_service.mint_usds(
                    user_id=tx['user_id'],
                    amount=amount,
                    reference=transaction_id
                )
                
                # Update transaction with completion details
                await self.supabase.table("payment_transactions").update({
                    "status": "completed",
                    "algorand_tx_id": mint_result['txn_id'],
                    "provider_tx_id": provider_tx_id,
                    "actual_amount": float(amount),
                    "completed_at": datetime.utcnow().isoformat(),
                    "metadata": metadata
                }).eq("id", transaction_id).execute()
                
                # Update treasury reserves
                await self.treasury.record_mint(amount, tx['currency'], transaction_id)
                
                # Log successful mint
                await self.audit.log_event(
                    AuditEventType.MINT_COMPLETED,
                    user_id=tx['user_id'],
                    resource_id=transaction_id,
                    details={
                        "amount_fiat": float(amount),
                        "currency": tx['currency'],
                        "usds_minted": float(amount),
                        "algorand_tx": mint_result['txn_id'],
                        "provider": tx['provider']
                    }
                )
                
                # Send success notification
                await self.notifications.send_deposit_success(
                    tx['user_id'], 
                    amount, 
                    tx['currency'],
                    transaction_id
                )
                
            elif tx['transaction_type'] == 'withdrawal':
                # Burn USDS tokens
                burn_result = await self.algorand_service.burn_usds(
                    user_id=tx['user_id'],
                    amount=amount,
                    reference=transaction_id
                )
                
                # Update transaction
                await self.supabase.table("payment_transactions").update({
                    "status": "completed",
                    "algorand_tx_id": burn_result['txn_id'],
                    "provider_tx_id": provider_tx_id,
                    "actual_amount": float(amount),
                    "completed_at": datetime.utcnow().isoformat(),
                    "metadata": metadata
                }).eq("id", transaction_id).execute()
                
                # Update treasury reserves
                await self.treasury.record_burn(amount, tx['currency'], transaction_id)
                
                # Log successful burn
                await self.audit.log_event(
                    AuditEventType.BURN_COMPLETED,
                    user_id=tx['user_id'],
                    resource_id=transaction_id,
                    details={
                        "amount_fiat": float(amount),
                        "currency": tx['currency'],
                        "usds_burned": float(amount),
                        "algorand_tx": burn_result['txn_id'],
                        "provider": tx['provider']
                    }
                )
                
                # Send success notification
                await self.notifications.send_withdrawal_success(
                    tx['user_id'], 
                    amount, 
                    tx['currency'],
                    transaction_id
                )
            
            logger.info(f"✅ Payment completed: {transaction_id} | Amount: {amount} {tx['currency']}")
            
        except Exception as e:
            logger.error(f"💥 Payment completion failed: {e}")
            
            # Mark transaction for manual review
            await self.supabase.table("payment_transactions").update({
                "status": "requires_review",
                "error_message": str(e),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", transaction_id).execute()
            
            # Alert operations team
            await self.notifications.send_admin_alert(
                f"Payment completion failed for {transaction_id}: {str(e)}"
            )
    
    async def _handle_failed_payment(self, transaction_id: str, error_message: str):
        """Process failed payment with proper cleanup"""
        
        try:
            # Update transaction status
            await self.supabase.table("payment_transactions").update({
                "status": "failed",
                "error_message": error_message,
                "failed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", transaction_id).execute()
            
            # Get transaction details for notification
            tx_result = await self.supabase.table("payment_transactions")\
                .select("user_id, amount, currency, transaction_type")\
                .eq("id", transaction_id)\
                .single()
            
            if tx_result.data:
                tx = tx_result.data
                
                # Log failed transaction
                await self.audit.log_event(
                    AuditEventType.PAYMENT_FAILED,
                    user_id=tx['user_id'],
                    resource_id=transaction_id,
                    details={
                        "transaction_type": tx['transaction_type'],
                        "amount": tx['amount'],
                        "currency": tx['currency'],
                        "error_message": error_message
                    }
                )
                
                # Send failure notification to user
                await self.notifications.send_payment_failure(
                    tx['user_id'],
                    Decimal(str(tx['amount'])),
                    tx['currency'],
                    tx['transaction_type'],
                    error_message
                )
            
            logger.warning(f"⚠️ Payment failed: {transaction_id} - {error_message}")
            
        except Exception as e:
            logger.error(f"💥 Failed payment handling error: {e}")
    
    # =============================================================================
    # CROSS-BORDER P2P TRANSFERS (SEAMOUNT CORE FEATURE)
    # =============================================================================
    
    async def initiate_cross_border_transfer(self,
                                           sender_id: str,
                                           recipient_id: str,
                                           amount: Decimal,
                                           sender_currency: str,
                                           recipient_currency: str) -> Dict[str, Any]:
        """Core cross-border P2P transfer using USDS as bridge currency"""
        
        transfer_id = f"XBT_{uuid4().hex[:8]}"
        logger.info(f"🌍 Cross-border transfer {transfer_id}: {amount} {sender_currency} → {recipient_currency}")
        
        try:
            # Validate balances and limits
            sender_balance = await self.algorand_service.get_usds_balance(sender_id)
            if sender_balance < amount:
                raise HTTPException(status_code=400, detail="Insufficient USDS balance")
            
            # Check transfer limits and KYC
            await self.kyc_service.validate_transfer_limits(sender_id, amount, sender_currency)
            
            # Calculate exchange rates and fees
            rate_info = await self._calculate_cross_border_rates(
                amount, sender_currency, recipient_currency
            )
            
            # Create transfer record
            transfer_data = {
                "id": transfer_id,
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "status": "pending",
                "sender_amount": float(amount),
                "sender_currency": sender_currency,
                "recipient_amount": float(rate_info['recipient_amount']),
                "recipient_currency": recipient_currency,
                "exchange_rate": float(rate_info['exchange_rate']),
                "fee_amount": float(rate_info['fee']),
                "usds_amount": float(amount),  # USDS bridge amount
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.supabase.table("cross_border_transfers").insert(transfer_data).execute()
            
            # Execute USDS transfer (sender → recipient)
            transfer_result = await self.algorand_service.transfer_usds(
                sender_id=sender_id,
                recipient_id=recipient_id,
                amount=amount,
                reference=transfer_id
            )
            
            # Update transfer with blockchain transaction
            await self.supabase.table("cross_border_transfers").update({
                "status": "completed",
                "algorand_tx_id": transfer_result['txn_id'],
                "completed_at": datetime.utcnow().isoformat()
            }).eq("id", transfer_id).execute()
            
            # Log successful transfer
            await self.audit.log_event(
                AuditEventType.CROSS_BORDER_TRANSFER,
                user_id=sender_id,
                resource_id=transfer_id,
                details={
                    "recipient_id": recipient_id,
                    "sender_amount": float(amount),
                    "sender_currency": sender_currency,
                    "recipient_amount": float(rate_info['recipient_amount']),
                    "recipient_currency": recipient_currency,
                    "algorand_tx": transfer_result['txn_id']
                }
            )
            
            # Notify both parties
            await self.notifications.send_transfer_notifications(
                sender_id, recipient_id, transfer_id, rate_info
            )
            
            logger.info(f"✅ Cross-border transfer completed: {transfer_id}")
            
            return {
                "transfer_id": transfer_id,
                "status": "completed",
                "sender_amount": float(amount),
                "recipient_amount": float(rate_info['recipient_amount']),
                "exchange_rate": float(rate_info['exchange_rate']),
                "fee": float(rate_info['fee']),
                "algorand_tx_id": transfer_result['txn_id'],
                "estimated_arrival": "Instant"
            }
            
        except Exception as e:
            logger.error(f"💥 Cross-border transfer failed: {e}")
            
            # Update transfer status
            try:
                await self.supabase.table("cross_border_transfers").update({
                    "status": "failed",
                    "error_message": str(e),
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", transfer_id).execute()
            except:
                pass
                
            raise HTTPException(status_code=400, detail=f"Transfer failed: {e}")
    
    async def _calculate_cross_border_rates(self, 
                                          amount: Decimal, 
                                          from_currency: str, 
                                          to_currency: str) -> Dict[str, Decimal]:
        """Calculate real-time exchange rates with minimal fees"""
        
        try:
            # For MVP: Use 1:1 rate for USDS bridge (currencies pegged to USD)
            # TODO: Integrate real-time FX rates (e.g., CurrencyAPI, Fixer.io)
            
            base_rate = Decimal('1.0')  # 1:1 for stablecoin transfers
            seamount_fee = amount * Decimal('0.005')  # 0.5% Seamount fee
            
            recipient_amount = amount - seamount_fee
            
            return {
                'exchange_rate': base_rate,
                'recipient_amount': recipient_amount,
                'fee': seamount_fee,
                'fee_percentage': Decimal('0.5')
            }
            
        except Exception as e:
            logger.error(f"Rate calculation failed: {e}")
            raise ValueError(f"Unable to calculate exchange rates: {e}")
    
    # =============================================================================
    # YIELD FARMING INTEGRATION
    # =============================================================================
    
    async def stake_usds_for_yield(self, user_id: str, amount: Decimal, pool_id: str) -> Dict[str, Any]:
        """Stake USDS in yield farming pools"""
        
        stake_id = f"STK_{uuid4().hex[:8]}"
        logger.info(f"🌾 Staking {amount} USDS for user {user_id} in pool {pool_id}")
        
        try:
            # Validate balance
            balance = await self.algorand_service.get_usds_balance(user_id)
            if balance < amount:
                raise HTTPException(status_code=400, detail="Insufficient USDS balance")
            
            # Transfer USDS to staking contract
            stake_result = await self.algorand_service.stake_usds(
                user_id=user_id,
                amount=amount,
                pool_id=pool_id,
                reference=stake_id
            )
            
            # Record staking transaction
            await self.supabase.table("yield_stakes").insert({
                "id": stake_id,
                "user_id": user_id,
                "pool_id": pool_id,
                "amount": float(amount),
                "status": "active",
                "algorand_tx_id": stake_result['txn_id'],
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(f"✅ USDS staked: {stake_id}")
            
            return {
                "stake_id": stake_id,
                "amount_staked": float(amount),
                "pool_id": pool_id,
                "transaction_id": stake_result['txn_id'],
                "status": "active"
            }
            
        except Exception as e:
            logger.error(f"💥 Staking failed: {e}")
            raise HTTPException(status_code=400, detail=f"Staking failed: {e}")
    
    # =============================================================================
    # TRANSACTION MONITORING & ANALYTICS
    # =============================================================================
    
    async def get_payment_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive payment routing analytics"""
        
        try:
            # Get analytics from database function
            result = await self.supabase.rpc('get_payment_analytics', {'days_back': days}).execute()
            
            if not result.data:
                return {"error": "No analytics data available"}
            
            analytics = result.data[0] if isinstance(result.data, list) else result.data
            
            return {
                "period_days": days,
                "total_volume_usd": analytics.get('total_volume', 0),
                "total_transactions": analytics.get('transaction_count', 0),
                "total_fees_saved": analytics.get('fees_saved', 0),
                "success_rate": analytics.get('success_rate', 0),
                "avg_processing_time": analytics.get('avg_processing_time', 0),
                "provider_breakdown": {
                    "paystack": {
                        "volume": analytics.get('paystack_volume', 0),
                        "transactions": analytics.get('paystack_count', 0),
                        "avg_fee_pct": 1.2
                    },
                    "flutterwave": {
                        "volume": analytics.get('flutterwave_volume', 0),
                        "transactions": analytics.get('flutterwave_count', 0),
                        "avg_fee_pct": 3.8
                    },
                    "sterling_bank": {
                        "volume": analytics.get('sterling_volume', 0),
                        "transactions": analytics.get('sterling_count', 0),
                        "avg_fee_pct": 1.5
                    }
                },
                "route_performance": {
                    "nigeria_local_savings": f"{analytics.get('nigeria_savings_pct', 0)}%",
                    "africa_corridor_savings": f"{analytics.get('africa_savings_pct', 0)}%",
                    "global_optimization_pending": "Circle CCTP integration"
                }
            }
            
        except Exception as e:
            logger.error(f"💥 Analytics query failed: {e}")
            return {"error": f"Analytics unavailable: {str(e)}"}
    
    async def get_user_transaction_history(self, user_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get paginated transaction history for user"""
        
        try:
            # Get payment transactions
            payments_result = await self.supabase.table("payment_transactions")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            # Get cross-border transfers (as sender or recipient)
            transfers_result = await self.supabase.table("cross_border_transfers")\
                .select("*")\
                .or_(f"sender_id.eq.{user_id},recipient_id.eq.{user_id}")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            # Combine and sort by timestamp
            all_transactions = []
            
            for tx in payments_result.data:
                all_transactions.append({
                    "id": tx['id'],
                    "type": tx['transaction_type'],
                    "amount": tx['amount'],
                    "currency": tx['currency'],
                    "status": tx['status'],
                    "provider": tx['provider'],
                    "created_at": tx['created_at'],
                    "completed_at": tx.get('completed_at')
                })
            
            for tx in transfers_result.data:
                tx_type = "transfer_sent" if tx['sender_id'] == user_id else "transfer_received"
                amount = tx['sender_amount'] if tx_type == "transfer_sent" else tx['recipient_amount']
                currency = tx['sender_currency'] if tx_type == "transfer_sent" else tx['recipient_currency']
                
                all_transactions.append({
                    "id": tx['id'],
                    "type": tx_type,
                    "amount": amount,
                    "currency": currency,
                    "status": tx['status'],
                    "created_at": tx['created_at'],
                    "completed_at": tx.get('completed_at'),
                    "counterparty": tx['recipient_id'] if tx_type == "transfer_sent" else tx['sender_id']
                })
            
            # Sort by creation date
            all_transactions.sort(key=lambda x: x['created_at'], reverse=True)
            
            return {
                "transactions": all_transactions[:limit],
                "total_count": len(all_transactions),
                "has_more": len(all_transactions) >= limit
            }
            
        except Exception as e:
            logger.error(f"💥 Transaction history query failed: {e}")
            return {"error": f"Unable to fetch transaction history: {str(e)}"}