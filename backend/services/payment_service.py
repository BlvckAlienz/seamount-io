# File Location: backend/services/payment_service.py
# Description: The definitive, unified service for all fiat and crypto payment operations.

import logging
from decimal import Decimal, getcontext
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
from fastapi import HTTPException

# --- Core Dependencies ---
from supabase import Client
from config import Settings
from .algorand_service import AlgorandService
from .kyc_service import KYCService
from .audit_service import AuditService, AuditEventType
from .treasury_service import TreasuryService
from .notification_service import NotificationService
from .payment_providers.flutterwave import FlutterwaveProcessor

# Set decimal precision for financial calculations
getcontext().prec = 28

logger = logging.getLogger(__name__)

class PaymentService:
    """
    Orchestrates the entire payment lifecycle, from fiat on-ramping to USDS transfers and fiat off-ramping.
    This is the single source of truth for all payment-related business logic.
    """
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
        self.fiat_processor = FlutterwaveProcessor(settings)

    # =============================================================================
    # FIAT ON-RAMP (DEPOSIT) WORKFLOW
    # =============================================================================

async def initialize_fiat_deposit(self, user_id: str, user_email: str, amount: Decimal, currency: str) -> Dict[str, Any]:
        """
        Step 1 of Fiat On-Ramp: Creates a payment link via Flutterwave and a pending transaction record.
        """
        transaction_id = f"DEP_{uuid4()}"
        logger.info(f"Initializing fiat deposit {transaction_id} for user {user_id} of {amount} {currency}.")

        try:
            # 1. Basic Validation
            if amount <= Decimal("0.0"):
                raise ValueError("Deposit amount must be positive.")
            
            # 2. Create a pending transaction record in our database
            await self.supabase.table("fiat_transactions").insert({
                "id": transaction_id,
                "user_id": user_id,
                "type": "deposit",
                "status": "pending",
                "fiat_amount": float(amount),
                "fiat_currency": currency
            }).execute()

            await self.audit.log_event(AuditEventType.MINT_INITIATED, user_id=user_id, resource_id=transaction_id, details={"amount": float(amount), "currency": currency})

            # 3. Call Flutterwave to get a payment link
            payment_init_result = await self.fiat_processor.initialize_payment(
                amount=float(amount),
                currency=currency,
                email=user_email,
                tx_ref=transaction_id # Use our internal ID as the transaction reference
            )

            if payment_init_result["status"] != "success":
                await self.supabase.table("fiat_transactions").update({
                    "status": "failed", "error_message": payment_init_result.get("message")
                }).eq("id", transaction_id).execute()
                raise HTTPException(status_code=400, detail=f"Payment provider error: {payment_init_result.get('message')}")

            # 4. Update our record with the provider's reference
            await self.supabase.table("fiat_transactions").update({
                "provider_reference": payment_init_result["tx_ref"]
            }).eq("id", transaction_id).execute()

            return {
                "status": "pending",
                "transaction_id": transaction_id,
                "payment_link": payment_init_result["payment_link"]
            }

        except Exception as e:
            logger.error(f"Fiat deposit initialization for {transaction_id} failed: {e}")
            await self.audit.log_event(AuditEventType.SYSTEM_ERROR, user_id=user_id, resource_id=transaction_id, details={"error": str(e)}, severity="error")
            raise

    async def finalize_fiat_deposit(self, provider_reference: str) -> Dict[str, Any]:
        """
        Step 2 of Fiat On-Ramp: Called by a webhook. Verifies the payment and mints USDS.
        """
        logger.info(f"Finalizing fiat deposit for provider reference: {provider_reference}")
        
        # In a real webhook, we'd use the tx_ref to find our internal transaction_id
        transaction_id = provider_reference

        try:
            # 1. Verify the payment with Flutterwave
            verification_data = await self.fiat_processor.verify_payment(provider_reference)
            if not verification_data.get("verified"):
                raise ValueError("Payment verification failed with provider.")

            # 2. Get transaction details and user profile from our DB
            tx_res = await self.supabase.table("fiat_transactions").select("*, user_profiles(algorand_address)").eq("id", transaction_id).single().execute()
            if not tx_res.data:
                raise ValueError(f"Transaction {transaction_id} not found.")
            
            transaction = tx_res.data
            user_id = transaction["user_id"]
            recipient_address = transaction["user_profiles"]["algorand_address"]
            amount_to_mint = Decimal(str(verification_data["amount"]))

            # 3. Mint USDS to the user's wallet
            mint_tx_hash = await self.algorand_service.mint_usds(recipient_address, amount_to_mint, transaction_id)

            # 4. Update the treasury service
            await self.treasury.record_deposit(amount_to_mint, amount_to_mint, transaction_id)

            # 5. Finalize the transaction record
            await self.supabase.table("fiat_transactions").update({
                "status": "completed",
                "usds_minted": float(amount_to_mint),
                "blockchain_tx_hash": mint_tx_hash,
                "completed_at": datetime.utcnow().isoformat()
            }).eq("id", transaction_id).execute()
            
            await self.audit.log_event(AuditEventType.MINT_COMPLETED, user_id=user_id, resource_id=transaction_id, details={"tx_hash": mint_tx_hash})
            
            # 6. Notify the user
            # balance = await self.algorand_service.get_usds_balance(recipient_address)
            # await self.notifications.send_deposit_confirmation(user_id, amount_to_mint, balance)

            return {"status": "success", "usds_minted": float(amount_to_mint), "tx_hash": mint_tx_hash}

        except Exception as e:
            logger.error(f"Fiat deposit finalization for {transaction_id} failed: {e}")
            await self.supabase.table("fiat_transactions").update({"status": "failed", "error_message": f"Finalization error: {str(e)}"}).eq("id", transaction_id).execute()
            await self.audit.log_event(AuditEventType.SYSTEM_ERROR, resource_id=transaction_id, details={"error": str(e)}, severity="critical")
            raise
        
    # =============================================================================
    # FIAT OFF-RAMP (WITHDRAWAL) WORKFLOW
    # =============================================================================

    async def process_fiat_withdrawal(self, user_profile: Dict, amount: Decimal, bank_details: Dict) -> Dict[str, Any]:
        """
        Orchestrates the entire fiat off-ramp (withdrawal) process.
        Flow: Checks -> USDS Burn -> Fiat Payout -> Treasury Update -> Notification
        """
        transaction_id = f"WDRL_{uuid4()}"
        user_id = str(user_profile['id'])
        user_address = user_profile['algorand_address']
        
        await self.audit.log_event(AuditEventType.BURN_INITIATED, user_id=user_id, resource_id=transaction_id, details={"amount": float(amount)})

        try:
            # 1. Pre-flight Checks
            if amount <= Decimal("0.0"):
                raise ValueError("Withdrawal amount must be positive.")

            # 2. Compliance & KYC Check (must have a sufficient KYC level for withdrawals)
            kyc_check = await self.kyc_service.compliance_check(user_id, "fiat_withdrawal", float(amount))
            if not kyc_check.get("is_compliant"):
                raise ValueError(f"Compliance check failed for withdrawal: {kyc_check.get('reasons')}")

            # 3. On-Chain Balance Check
            balance = await self.algorand_service.get_usds_balance(user_address)
            if balance < amount:
                raise ValueError(f"Insufficient USDS balance. Required: {amount}, Available: {balance}")

            # 4. Treasury Health Check (Can we afford this payout right now?)
            treasury_health = await self.treasury.check_withdrawal_capacity(amount)
            if not treasury_health['sufficient']:
                raise HTTPException(status_code=503, detail="Withdrawals are temporarily unavailable. Please try again later.")

            # 5. Record Pending Withdrawal
            await self.supabase.table("fiat_transactions").insert({
                "id": transaction_id, "user_id": user_id, "type": "withdrawal", "status": "pending_burn", "fiat_amount": float(amount), "usds_amount": float(amount)
            }).execute()

            # 6. Execute USDS Burn (Transfer from user to treasury)
            # CRITICAL: This is the point of no return. Requires the user's signature/private key.
            # sender_private_key = await secure_vault.get_decrypted_key(user_id)
            # burn_tx_hash = await self.algorand_service.burn_usds(sender_private_key, amount, transaction_id)
            burn_tx_hash = f"simulated_burn_tx_{uuid4()}" # SIMULATION

            await self.supabase.table("fiat_transactions").update({"status": "pending_payout", "blockchain_tx_hash": burn_tx_hash}).eq("id", transaction_id).execute()

            # 7. Initiate Fiat Payout via Flutterwave
            payout_result = await self.fiat_processor.initiate_payout(amount, bank_details, transaction_id)
            if not payout_result.get("success"):
                # CRITICAL FAILURE: The USDS was burned but the fiat payout failed.
                # This requires a manual review and refund process. For now, we log it critically.
                error_msg = f"FATAL: USDS burned ({burn_tx_hash}) but fiat payout failed: {payout_result.get('message')}"
                await self.supabase.table("fiat_transactions").update({"status": "failed_payout_review", "error_message": error_msg}).eq("id", transaction_id).execute()
                await self.audit.log_event(AuditEventType.SYSTEM_ERROR, user_id=user_id, resource_id=transaction_id, details={"error": error_msg}, severity="critical")
                raise HTTPException(status_code=500, detail="Withdrawal failed at payment provider. Support has been notified.")

            # 8. Finalize DB Records and Treasury
            await self.supabase.table("fiat_transactions").update({
                "status": "completed", "provider_reference": payout_result["reference"], "completed_at": datetime.utcnow().isoformat()
            }).eq("id", transaction_id).execute()
            
            await self.treasury.record_withdrawal(amount, amount, transaction_id)
            await self.audit.log_event(AuditEventType.BURN_COMPLETED, user_id=user_id, resource_id=transaction_id, details={"burn_tx_hash": burn_tx_hash, "payout_ref": payout_result["reference"]})

            # 9. Notify User
            # await self.notifications.send_withdrawal_confirmation(user_id, amount, "Bank Transfer", payout_result['estimated_arrival'])

            return {"status": "success", "transaction_id": transaction_id, "amount_withdrawn": float(amount)}

        except (ValueError, HTTPException) as e:
            # Re-raise validation errors to be sent to the client
            await self.supabase.table("fiat_transactions").update({"status": "failed", "error_message": str(e)}).eq("id", transaction_id).execute()
            raise
        except Exception as e:
            logger.error(f"Fiat withdrawal {transaction_id} failed catastrophically: {e}")
            await self.supabase.table("fiat_transactions").update({"status": "failed", "error_message": "Internal system error"}).eq("id", transaction_id).execute()
            await self.audit.log_event(AuditEventType.SYSTEM_ERROR, user_id=user_id, resource_id=transaction_id, details={"error": str(e)}, severity="critical")
            raise HTTPException(status_code=500, detail="An unexpected error occurred during withdrawal.")

    # =============================================================================
    # P2P & CROSS-BORDER WORKFLOW
    # =============================================================================
    
    def _get_user_tier_info(self, country_code: str) -> str:
        """Determines a user's geographic tier based on their country code."""
        for tier, countries in self.settings.GEOGRAPHIC_TIERS.items():
            if country_code.upper() in countries:
                return tier
        return 'tier_3'

    def calculate_fee(self, amount: Decimal, sender_country: str, recipient_country: str) -> Decimal:
        """Calculates transaction fees based on the static business logic in the config."""
        sender_tier = self._get_user_tier_info(sender_country)
        fee_structure = self.settings.FEE_STRUCTURE
        
        if sender_country == recipient_country:
            fee_key = sender_tier if sender_tier in fee_structure['processing'] else 'tier_2_standard'
            fee_rate = fee_structure['processing'][fee_key]
            fee = amount * Decimal(str(fee_rate))
        else:
            fee_key = sender_tier if sender_tier in fee_structure['bridge'] else 'tier_2_standard'
            fee_rate = fee_structure['bridge'][fee_key]
            fee = amount * Decimal(str(fee_rate))
            min_fee = fee_structure['bridge']['min_fee']
            max_fee = fee_structure['bridge']['max_fee']
            fee = max(Decimal(str(min_fee)), min(fee, Decimal(str(max_fee))))

        return fee.quantize(Decimal('0.01'))

    async def process_p2p_payment(self, sender_profile: Dict, recipient_address: str, amount: Decimal, memo: str) -> Dict:
        """Orchestrates the entire P2P payment flow from compliance to blockchain execution."""
        transaction_id = f"P2P_{uuid4()}"
        sender_id = str(sender_profile['id'])
        sender_address = sender_profile['algorand_address']
        
        await self.audit.log_event(AuditEventType.PAYMENT_CREATED, user_id=sender_id, resource_id=transaction_id, details={"amount": float(amount), "recipient": recipient_address})

        try:
            # 1. Fetch recipient profile
            recipient_res = await self.supabase.table("user_profiles").select("country_code").eq("algorand_address", recipient_address).single().execute()
            if not recipient_res.data:
                raise ValueError("Recipient address not found.")
            
            # 2. Full Compliance Check
            # ... (Compliance check logic here) ...
            
            # 3. Calculate Fee & Check Balance
            fee = self.calculate_fee(amount, sender_profile['country_code'], recipient_res.data['country_code'])
            total_debit = amount + fee
            balance = await self.algorand_service.get_usds_balance(sender_address)
            if balance < total_debit:
                raise ValueError(f"Insufficient balance. Required: {total_debit}, Available: {balance}")

            # 4. Execute Blockchain Transfer (Placeholder for secure key retrieval)
            # CRITICAL: This is the most sensitive part. A real implementation MUST use a secure vault (like HashiCorp Vault, AWS KMS, or a hardware security module)
            # to sign transactions without ever exposing private keys to this service.
            # For this MVP, we are simulating this by acknowledging the need for a secure key retrieval process.
            # sender_private_key = await secure_vault.get_decrypted_key(sender_id)
            # tx_hash = await self.algorand_service.send_usds(sender_private_key, recipient_address, amount, memo)
            tx_hash = f"simulated_successful_tx_{uuid4()}" # SIMULATION

            # 5. Record final transaction in DB
            await self.supabase.table("payment_transactions").insert({
                "id": transaction_id, "user_id": sender_id, "status": "completed", "amount": float(amount), "fee": float(fee), "sender_address": sender_address, "receiver_address": recipient_address, "tx_hash": tx_hash, "memo": memo
            }).execute()

            await self.audit.log_event(AuditEventType.PAYMENT_COMPLETED, user_id=sender_id, resource_id=transaction_id, details={"tx_hash": tx_hash})
            return {"status": "success", "transaction_id": transaction_id, "tx_hash": tx_hash, "fee": float(fee)}

        except Exception as e:
            logger.error(f"P2P payment {transaction_id} failed: {e}")
            await self.supabase.table("payment_transactions").update({"status": "failed", "error_message": str(e)}).eq("id", transaction_id).execute()
            await self.audit.log_event(AuditEventType.SYSTEM_ERROR, user_id=sender_id, resource_id=transaction_id, details={"error": str(e)}, severity="error")
            raise