# File Location: backend/services/compliance_service.py
# Description: The definitive, multi-jurisdictional compliance engine for Seamount.io.

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from supabase import Client
from fastapi import HTTPException

# --- Core Dependencies ---
from ..config import Settings
from .audit_service import AuditService, AuditEventType
from .kyc_service import KYCService
from .database_service import DatabaseService

logger = logging.getLogger(__name__)

class ComplianceService:
    """
    Handles all compliance operations: KYC/AML, transaction monitoring, sanctions screening,
    and regulatory rule enforcement. It is the central authority for approving or denying transactions.
    """

    def __init__(self, settings: Settings, db_service: DatabaseService, kyc_service: KYCService, audit_service: AuditService):
        self.settings = settings
        self.db = db_service
        self.kyc_service = kyc_service
        self.audit = audit_service

        # --- Regulatory Thresholds (configurable via settings) ---
        self.ctr_thresholds = {"NG": 5000, "US": 10000, "EU": 10000} # Currency Transaction Report
        self.travel_rule_threshold = 1000 # Universal threshold for Travel Rule data exchange (USD)

    def _get_user_tier_info(self, country_code: str) -> str:
        """Helper to determine a user's geographic tier."""
        for tier, countries in self.settings.GEOGRAPHIC_TIERS.items():
            if country_code.upper() in countries:
                return tier
        return 'tier_3' # Default to most restrictive tier

    def get_transaction_limits(self, user_kyc_level: int, country_code: str) -> Dict[str, Any]:
        """
        Determines transaction limits based on user's KYC level and geography.
        This enforces the progressive access rules.
        """
        # Base limits on KYC level
        limits = {
            0: {"daily": Decimal(0), "single": Decimal(0)},
            1: {"daily": Decimal(1000), "single": Decimal(500)},
            2: {"daily": Decimal(10000), "single": Decimal(5000)},
            3: {"daily": Decimal(100000), "single": Decimal(25000)},
        }
        user_limits = limits.get(user_kyc_level, {"daily": Decimal(0), "single": Decimal(0)})
        
        # Adjust limits based on country risk (future implementation)
        # tier = self._get_user_tier_info(country_code)
        # if tier == 'tier_3':
        #     user_limits["daily"] *= Decimal('0.5')

        return user_limits

    async def _check_transaction_velocity(self, user_id: str, amount: Decimal) -> (bool, str):
        """Checks if the user has exceeded their daily transaction limits."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        # This call should be delegated to the database service for efficiency
        # For clarity, the query logic is shown here.
        response = await self.db.supabase.table("payment_transactions") \
            .select("amount") \
            .eq("user_id", user_id) \
            .eq("status", "completed") \
            .gte("created_at", today_start) \
            .execute()
            
        daily_total = sum(Decimal(str(tx['amount'])) for tx in response.data)
        
        user_profile = await self.db.get_user_profile_by_id(user_id)
        limits = self.get_transaction_limits(user_profile.get('kyc_level', 0), user_profile.get('country_code'))

        if (daily_total + amount) > limits['daily']:
            reason = f"Daily limit of ${limits['daily']} exceeded. Current daily total: ${daily_total}."
            return False, reason
        
        if amount > limits['single']:
            reason = f"Single transaction limit of ${limits['single']} exceeded."
            return False, reason

        return True, "Within limits"

    async def _perform_sanctions_screening(self, user_profile: Dict, recipient_info: Dict) -> (bool, str):
        """
        Performs sanctions screening against known watchlists.
        In production, this would integrate with a provider like Chainalysis or Elliptic.
        """
        # SIMULATION: Check against an internal watchlist table in your DB.
        # This table would be periodically updated from official sources (e.g., OFAC).
        
        addresses_to_check = [
            user_profile.get('algorand_address'),
            recipient_info.get('algorand_address')
        ]
        
        response = await self.db.supabase.table("sanctions_watchlist") \
            .select("address") \
            .in_("address", [addr for addr in addresses_to_check if addr]) \
            .execute()
            
        if response.data:
            hit_address = response.data[0]['address']
            reason = f"Sanctions hit on address: {hit_address}"
            return False, reason

        return True, "Screening clear"

    async def _handle_travel_rule(self, sender_profile: Dict, recipient_profile: Dict, amount: Decimal, tx_id: str):
        """
        Manages the FATF Travel Rule data exchange for transactions over the threshold.
        """
        if amount < self.travel_rule_threshold:
            return # Not applicable
            
        logger.info(f"Travel Rule triggered for transaction {tx_id}.")
        
        # Assemble required Originator (sender) and Beneficiary (recipient) data
        originator_data = {
            "name": f"{sender_profile.get('first_name')} {sender_profile.get('last_name')}",
            "address": sender_profile.get('algorand_address')
        }
        beneficiary_data = {
             "name": f"{recipient_profile.get('first_name')} {recipient_profile.get('last_name')}",
            "address": recipient_profile.get('algorand_address')
        }
        
        # In a production environment, this data would be sent to the recipient's VASP
        # using a protocol like TRISA or TRP. For now, we log it.
        await self.audit.log_event(
            AuditEventType.COMPLIANCE_CHECK,
            user_id=str(sender_profile['id']),
            resource_id=tx_id,
            details={
                "check": "travel_rule_data_prepared",
                "originator": originator_data,
                "beneficiary": beneficiary_data
            }
        )
        return True

    async def verify_transaction(self, sender_id: str, recipient_address: str, amount: Decimal) -> Dict[str, Any]:
        """
        The main gatekeeper function. Performs a full compliance check on a proposed transaction.
        """
        transaction_id = f"COMPLIANCE_CHECK_{uuid4()}"
        reasons = []
        is_compliant = True
        
        try:
            # Step 1: Fetch all necessary profiles
            sender_profile = await self.db.get_user_profile_by_id(sender_id)
            recipient_profile = await self.db.get_user_profile_by_algorand_address(recipient_address)

            if not sender_profile or not recipient_profile:
                raise ValueError("Sender or recipient profile not found.")

            # Step 2: Check Transaction Velocity & Limits
            velocity_ok, velocity_reason = await self._check_transaction_velocity(sender_id, amount)
            if not velocity_ok:
                is_compliant = False
                reasons.append(velocity_reason)

            # Step 3: Sanctions Screening (AML)
            sanctions_ok, sanctions_reason = await self._perform_sanctions_screening(sender_profile, recipient_profile)
            if not sanctions_ok:
                is_compliant = False
                reasons.append(sanctions_reason)

            # Step 4: Handle Travel Rule
            await self._handle_travel_rule(sender_profile, recipient_profile, amount, transaction_id)

            # ... Future checks (e.g., fraud scoring) would be added here ...

            result = {
                "is_compliant": is_compliant,
                "reasons": reasons,
                "checked_at": datetime.utcnow().isoformat()
            }

            await self.audit.log_event(AuditEventType.COMPLIANCE_CHECK, user_id=sender_id, resource_id=transaction_id, details=result)
            return result
            
             # --- NEW DASHBOARD METHODS ---

    async def get_dashboard_metrics(self, country_code: str = None) -> Dict[str, Any]:
        """
        Calculates and returns the key performance indicators for the compliance dashboard.
        """
        try:
            # This is where you'd perform complex aggregations. We'll use our DatabaseService for this.
            
            # 1. Alert Statistics
            alert_stats = await self.db.get_alert_summary(country_code)

            # 2. KYC Statistics
            kyc_stats = await self.db.get_kyc_summary(country_code)

            # 3. Transaction Monitoring Stats
            tx_stats = await self.db.get_transaction_summary(country_code, days=30)

            # 4. Overall Compliance Score Calculation
            total_users = kyc_stats.get('total', 1)
            verified_users = kyc_stats.get('verified_count', 0)
            pending_alerts = alert_stats.get('pending_count', 0)
            
            # A simple scoring model: high verification rate is good, pending alerts are bad.
            verification_score = (verified_users / total_users) * 100 if total_users > 0 else 100
            alert_penalty = min(pending_alerts * 5, 50) # 5 points off per pending alert, max 50 penalty
            compliance_score = max(0, verification_score - alert_penalty)

            return {
                "compliance_score": round(compliance_score, 2),
                "alerts": alert_stats,
                "kyc": kyc_stats,
                "transactions": tx_stats,
                "generated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to generate compliance dashboard metrics: {e}")
            raise

    async def get_alerts_for_review(self, status: str, severity: str, limit: int, offset: int) -> List[Dict[str, Any]]:
        """Retrieves a list of alerts for manual review by a compliance officer."""
        return await self.db.get_alerts(status=status, severity=severity, limit=limit, offset=offset)

    async def update_alert_status(self, alert_id: str, new_status: str, notes: str, officer_id: str) -> Dict[str, Any]:
        """Updates the status of an alert after review."""
        # ... [Logic to update alert in DB via self.db] ...
        # This should also log an audit event.
        pass

        except Exception as e:
            logger.error(f"Compliance verification for user {sender_id} failed: {e}")
            return {"is_compliant": False, "reasons": ["Internal compliance system error."]}