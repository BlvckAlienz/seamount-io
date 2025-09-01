# File Location: backend/services/licensing_service.py

import logging
from decimal import Decimal, getcontext
from typing import Dict, Any, Optional, List
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import HTTPException

# Core Dependencies
from supabase import Client
from config import Settings, BusinessModelConfig, LicenseTier, PricingRegion
from models import (
    LicensePurchaseRequest, LicensePurchaseResponse, LicenseInfo, 
    LicenseStatus, PaymentStatus, TierUpgradeRequest, LicenseUsageStats,
    TransactionFeeCalculation
)
from .payment_providers.flutterwave import FlutterwaveProcessor
from .audit_service import AuditService, AuditEventType
from .notification_service import NotificationService

# Set decimal precision for financial calculations
getcontext().prec = 28

logger = logging.getLogger(__name__)

class LicensingService:
    """
    Handles all SMB license purchases, tier management, and fee calculations.
    Integrates with existing payment infrastructure and business model config.
    """
    
    def __init__(
        self,
        settings: Settings,
        supabase_client: Client,
        audit_service: AuditService,
        notification_service: NotificationService
    ):
        self.settings = settings
        self.supabase = supabase_client
        self.audit = audit_service
        self.notifications = notification_service
        self.fiat_processor = FlutterwaveProcessor(settings)
        self.business_model = BusinessModelConfig()
        
        logger.info("LicensingService initialized with business model integration")

    async def get_user_license(self, user_id: str) -> Optional[LicenseInfo]:
        """Get user's current active license"""
        try:
            result = self.supabase.table("smb_licenses").select("*").eq("user_id", user_id).eq("status", "active").maybe_single().execute()
            
            if result.data:
                # Enrich with tier-specific features
                tier = LicenseTier(result.data["tier"])
                result.data["features"] = self._get_tier_features(tier)
                return LicenseInfo(**result.data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch license for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve license information")

    def _get_tier_features(self, tier: LicenseTier) -> List[str]:
        """Get feature list for each tier"""
        features_map = {
            LicenseTier.BASIC: [
                "Volume discount pricing (2.2%)",
                "Basic API access", 
                "Email support",
                "Standard settlement (24hrs)",
                "Up to 50 employees"
            ],
            LicenseTier.PRO: [
                "Enhanced volume discount (1.9%)",
                "Full API access with webhooks",
                "Priority support + success manager",
                "Fast settlement (1-4hrs)",
                "Yield farming integration", 
                "Multi-currency treasury",
                "Up to 500 employees"
            ],
            LicenseTier.ENTERPRISE: [
                "Premium volume discount (1.6%)",
                "Complete API suite + SDKs",
                "24/7 dedicated support",
                "Instant settlement",
                "Advanced yield strategies",
                "White-label solution",
                "Custom integrations",
                "Unlimited employees",
                "SLA guarantees"
            ]
        }
        return features_map.get(tier, [])

    async def initiate_license_purchase(self, user_id: str, user_email: str, request: LicensePurchaseRequest) -> LicensePurchaseResponse:
        """Start the license purchase process"""
        license_id = f"LIC_{uuid4()}"
        transaction_id = f"LICENSE_{uuid4()}"
        
        logger.info(f"Initiating license purchase {license_id} for user {user_id}, tier: {request.tier}")

        try:
            # Check if user already has an active license
            existing_license = await self.get_user_license(user_id)
            if existing_license:
                raise HTTPException(status_code=400, detail=f"User already has active {existing_license.tier} license")

            # Calculate license fee based on region
            region = PricingRegion(request.region) if request.region else PricingRegion.NIGERIA
            license_amount = self.business_model.calculate_license_fee(request.tier, region)
            
            # Determine currency based on region
            currency_map = {
                PricingRegion.NIGERIA: "NGN",
                PricingRegion.KENYA: "KES", 
                PricingRegion.DEFAULT: "USD"
            }
            currency = currency_map.get(region, "USD")

            # Create license record (pending payment)
            license_data = {
                "id": license_id,
                "user_id": user_id,
                "tier": request.tier.value,
                "status": LicenseStatus.PENDING.value,
                "purchase_amount": float(license_amount),
                "currency": currency,
                "region": request.region,
                "transaction_fee_rate": float(self.business_model.TRANSACTION_FEES[request.tier]),
                "employee_limit": self.business_model.EMPLOYEE_LIMITS.get(request.tier),
                "company_name": request.company_name,
                "employee_count": request.employee_count,
                "payment_transaction_id": transaction_id
            }
            
            self.supabase.table("smb_licenses").insert(license_data).execute()

            # Create payment transaction record
            payment_data = {
                "id": transaction_id,
                "user_id": user_id,
                "type": "license_purchase",
                "status": PaymentStatus.PENDING.value,
                "fiat_amount": float(license_amount),
                "fiat_currency": currency,
                "license_id": license_id,
                "license_tier": request.tier.value
            }
            
            self.supabase.table("license_payments").insert(payment_data).execute()

            # Initialize payment with Flutterwave
            payment_result = await self.fiat_processor.initialize_payment(
                amount=float(license_amount),
                currency=currency,
                email=user_email,
                tx_ref=transaction_id
            )

            if payment_result["status"] != "success":
                # Mark license and payment as failed
                self.supabase.table("smb_licenses").update({"status": "failed"}).eq("id", license_id).execute()
                self.supabase.table("license_payments").update({"status": "failed"}).eq("id", transaction_id).execute()
                
                raise HTTPException(status_code=400, detail=f"Payment initialization failed: {payment_result.get('message')}")

            # Update payment with provider reference
            self.supabase.table("license_payments").update({
                "provider_reference": payment_result["tx_ref"],
                "payment_link": payment_result["payment_link"]
            }).eq("id", transaction_id).execute()

            await self.audit.log_event(
                AuditEventType.PAYMENT_CREATED,
                user_id=user_id,
                resource_id=license_id,
                details={
                    "type": "license_purchase",
                    "tier": request.tier.value,
                    "amount": float(license_amount),
                    "currency": currency,
                    "region": request.region
                }
            )

            return LicensePurchaseResponse(
                license_id=license_id,
                transaction_id=transaction_id,
                payment_link=payment_result["payment_link"],
                amount=float(license_amount),
                currency=currency,
                tier=request.tier
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"License purchase initiation failed for {license_id}: {e}")
            await self.audit.log_event(
                AuditEventType.SYSTEM_ERROR,
                user_id=user_id,
                resource_id=license_id,
                details={"error": str(e)},
                severity="error"
            )
            raise HTTPException(status_code=500, detail="License purchase initialization failed")

    async def finalize_license_purchase(self, transaction_id: str) -> Dict[str, Any]:
        """Complete license purchase after payment confirmation (called by webhook)"""
        logger.info(f"Finalizing license purchase for transaction: {transaction_id}")
        
        try:
            # Verify payment with provider
            verification_data = await self.fiat_processor.verify_payment(transaction_id)
            if not verification_data.get("verified"):
                raise ValueError("Payment verification failed")

            # Get payment and license records
            payment_result = self.supabase.table("license_payments").select("*, smb_licenses(*)").eq("id", transaction_id).single().execute()
            
            if not payment_result.data:
                raise ValueError(f"Payment transaction {transaction_id} not found")
                
            payment_data = payment_result.data
            license_data = payment_data["smb_licenses"]
            user_id = payment_data["user_id"]
            license_id = license_data["id"]

            # Calculate license expiry (Enterprise = lifetime, others = 1 year)
            tier = LicenseTier(license_data["tier"])
            expires_at = None if tier == LicenseTier.ENTERPRISE else datetime.utcnow() + timedelta(days=365)

            # Activate license
            self.supabase.table("smb_licenses").update({
                "status": LicenseStatus.ACTIVE.value,
                "purchased_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None
            }).eq("id", license_id).execute()

            # Mark payment as completed
            self.supabase.table("license_payments").update({
                "status": PaymentStatus.COMPLETED.value,
                "completed_at": datetime.utcnow().isoformat()
            }).eq("id", transaction_id).execute()

            await self.audit.log_event(
                AuditEventType.PAYMENT_COMPLETED,
                user_id=user_id,
                resource_id=license_id,
                details={
                    "type": "license_activated",
                    "tier": license_data["tier"],
                    "transaction_id": transaction_id
                }
            )

            # Send welcome email with license details
            await self._send_license_activation_email(user_id, license_data)

            return {
                "status": "success",
                "license_id": license_id,
                "tier": license_data["tier"],
                "activated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"License purchase finalization failed for {transaction_id}: {e}")
            
            # Mark as failed but don't lose the payment
            self.supabase.table("license_payments").update({
                "status": "failed_activation",
                "error_message": str(e)
            }).eq("id", transaction_id).execute()
            
            await self.audit.log_event(
                AuditEventType.SYSTEM_ERROR,
                resource_id=transaction_id,
                details={"error": str(e)},
                severity="critical"
            )
            raise

    def calculate_smb_transaction_fee(self, user_id: str, amount: Decimal) -> TransactionFeeCalculation:
        """Calculate transaction fee based on user's license tier"""
        try:
            # Get user's license (this will be cached in production)
            license_result = self.supabase.table("smb_licenses").select("tier, status").eq("user_id", user_id).eq("status", "active").maybe_single().execute()
            
            if not license_result.data:
                # No license = individual rate
                fee = amount * self.business_model.INDIVIDUAL_BASE_RATE
                return TransactionFeeCalculation(
                    amount=amount,
                    tier=None,
                    base_rate=float(self.business_model.INDIVIDUAL_BASE_RATE),
                    calculated_fee=fee,
                    min_fee_applied=False,
                    max_fee_applied=False,
                    final_fee=fee,
                    effective_rate=float(fee / amount),
                    savings_vs_individual=Decimal("0")
                )

            # Calculate SMB tier fee
            tier = LicenseTier(license_result.data["tier"])
            final_fee, calculation_details = self.business_model.calculate_transaction_fee(amount, tier)
            
            # Calculate savings vs individual rate
            individual_fee = amount * self.business_model.INDIVIDUAL_BASE_RATE
            savings = individual_fee - final_fee

            return TransactionFeeCalculation(
                amount=amount,
                tier=tier,
                base_rate=calculation_details["base_rate"],
                calculated_fee=Decimal(str(calculation_details["calculated_fee"])),
                min_fee_applied=calculation_details["min_fee"] == calculation_details["final_fee"],
                max_fee_applied=calculation_details["max_fee"] == calculation_details["final_fee"],
                final_fee=final_fee,
                effective_rate=calculation_details["effective_rate"],
                savings_vs_individual=savings
            )

        except Exception as e:
            logger.error(f"Fee calculation failed for user {user_id}: {e}")
            # Fallback to individual rate
            fee = amount * self.business_model.INDIVIDUAL_BASE_RATE
            return TransactionFeeCalculation(
                amount=amount,
                tier=None,
                base_rate=float(self.business_model.INDIVIDUAL_BASE_RATE),
                calculated_fee=fee,
                min_fee_applied=False,
                max_fee_applied=False,
                final_fee=fee,
                effective_rate=float(fee / amount),
                savings_vs_individual=Decimal("0")
            )

    async def get_license_usage_stats(self, user_id: str) -> Optional[LicenseUsageStats]:
        """Get current month usage statistics for a license"""
        try:
            license = await self.get_user_license(user_id)
            if not license:
                return None

            # Get current month transactions (this would be more complex in production)
            current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            stats_result = self.supabase.table("payment_transactions").select("amount, fee").eq("user_id", user_id).gte("created_at", current_month_start.isoformat()).execute()
            
            current_month_volume = sum(Decimal(str(tx["amount"])) for tx in stats_result.data)
            current_month_transactions = len(stats_result.data)
            current_month_fees = sum(Decimal(str(tx["fee"])) for tx in stats_result.data)
            
            # Calculate savings vs individual rate
            individual_fees = current_month_volume * self.business_model.INDIVIDUAL_BASE_RATE
            total_savings = individual_fees - current_month_fees
            
            # Utilization vs employee limit
            utilization = min(100.0, (current_month_transactions / (license.employee_limit or 1000)) * 100) if license.employee_limit else 0

            return LicenseUsageStats(
                license_id=license.id,
                current_month_volume=current_month_volume,
                current_month_transactions=current_month_transactions,
                current_month_fees=current_month_fees,
                total_savings_vs_individual=total_savings,
                utilization_percentage=utilization
            )

        except Exception as e:
            logger.error(f"Failed to get usage stats for user {user_id}: {e}")
            return None

    async def _send_license_activation_email(self, user_id: str, license_data: Dict):
        """Send license activation confirmation email"""
        try:
            user_result = self.supabase.table("user_profiles").select("email, first_name").eq("id", user_id).single().execute()
            
            if user_result.data:
                tier = license_data["tier"].title()
                discount = self.business_model.get_discount_percentage(LicenseTier(license_data["tier"]))
                
                subject = f"Seamount {tier} License Activated!"
                
                body = f"""
                <h2>Welcome to Seamount {tier}!</h2>
                <p>Dear {user_result.data.get('first_name', 'Valued Customer')},</p>
                
                <p>Your {tier} license has been successfully activated. You're now saving <strong>{discount:.1f}%</strong> on all transactions!</p>
                
                <h3>Your Benefits:</h3>
                <ul>
                {"".join(f"<li>{feature}</li>" for feature in self._get_tier_features(LicenseTier(license_data["tier"])))}
                </ul>
                
                <p>Start using your new license benefits immediately in your Seamount dashboard.</p>
                
                <p>Questions? Contact your dedicated success manager at success@seamount.io</p>
                
                <p>Best regards,<br>The Seamount Team</p>
                """
                
                await self.notifications.email_service.send_email(subject, [user_result.data["email"]], body)
                
        except Exception as e:
            logger.error(f"Failed to send activation email for user {user_id}: {e}")