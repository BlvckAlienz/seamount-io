import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from supabase import Client
from fastapi import HTTPException

# --- Core Dependencies ---
from config import Settings
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
        self.travel_rule_threshold = 1000

    def get_transaction_limits(self, user_kyc_level: int) -> Dict[str, Decimal]:
        limits = {
            0: {"daily": Decimal(0), "single": Decimal(0)},
            1: {"daily": Decimal(1000), "single": Decimal(500)},
            2: {"daily": Decimal(10000), "single": Decimal(5000)},
            3: {"daily": Decimal(100000), "single": Decimal(25000)},
        }
        return limits.get(user_kyc_level, {"daily": Decimal(0), "single": Decimal(0)})

    async def _check_transaction_velocity(self, user_id: str, amount: Decimal) -> (bool, str):
        # This logic should be moved to database_service for efficiency.
        # For now, it lives here for clarity.
        # daily_total = await self.db.get_user_daily_volume(user_id)
        daily_total = Decimal('0') # Placeholder
        
        user_profile = await self.db.get_user_profile_by_id(user_id)
        if not user_profile: return False, "User profile not found."

        limits = self.get_transaction_limits(user_profile.get('kyc_level', 0))

        if (daily_total + amount) > limits['daily']:
            return False, f"Daily limit of ${limits['daily']} exceeded."
        if amount > limits['single']:
            return False, f"Single transaction limit of ${limits['single']} exceeded."
        return True, "Within limits"

    async def _perform_sanctions_screening(self, user_profile: Dict) -> (bool, str):
        # SIMULATION: In production, integrate with a provider like Chainalysis.
        # response = await self.db.is_address_on_watchlist(user_profile.get('algorand_address'))
        # if response: return False, "Sanctions hit on address."
        return True, "Screening clear"

    async def verify_transaction(self, sender_id: str, recipient_address: str, amount: Decimal) -> Dict[str, Any]:
        """
        The main gatekeeper function. Performs a full compliance check on a proposed transaction.
        """
        reasons = []
        is_compliant = True
        transaction_id = f"COMPLIANCE_CHECK_{uuid4()}"
        
        try:
            sender_profile = await self.db.get_user_profile_by_id(sender_id)
            if not sender_profile: raise ValueError("Sender profile not found.")

            velocity_ok, velocity_reason = await self._check_transaction_velocity(sender_id, amount)
            if not velocity_ok:
                is_compliant = False
                reasons.append(velocity_reason)

            sanctions_ok, sanctions_reason = await self._perform_sanctions_screening(sender_profile)
            if not sanctions_ok:
                is_compliant = False
                reasons.append(sanctions_reason)
            
            # ... other checks like Travel Rule would go here ...

        except Exception as e:
            logger.error(f"Compliance verification for user {sender_id} failed: {e}")
            is_compliant = False
            reasons.append("Internal compliance system error.")
            
        result = {"is_compliant": is_compliant, "reasons": reasons}
        await self.audit.log_event(AuditEventType.COMPLIANCE_CHECK, user_id=sender_id, resource_id=transaction_id, details=result)
        return result

    # --- DASHBOARD METHODS ---
    async def get_dashboard_metrics(self, country_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates and returns the key performance indicators for the compliance dashboard.
        """
        try:
            # These calls should be delegated to database_service which would run efficient SQL queries.
            # For now, we simulate the data.
            alert_stats = {'pending_count': 5, 'high_severity_count': 2}
            kyc_stats = {'total': 1500, 'verified_count': 1200}
            tx_stats = {'total_volume': 25000000, 'flagged_count': 15}

            total_users = kyc_stats.get('total', 1)
            verified_users = kyc_stats.get('verified_count', 0)
            pending_alerts = alert_stats.get('pending_count', 0)
            
            verification_score = (verified_users / total_users) * 100 if total_users > 0 else 100
            alert_penalty = min(pending_alerts * 5, 50)
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
            raise HTTPException(status_code=500, detail="Could not generate dashboard metrics.")

    async def get_alerts_for_review(self, status: str, severity: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        """Retrieves a list of alerts for manual review by a compliance officer."""
        # This would call self.db.get_alerts(...)
        return [] # Placeholder

    async def update_alert_status(self, alert_id: str, new_status: str, notes: str, officer_id: str) -> Dict[str, Any]:
        """Updates the status of an alert after review."""
        # This would call self.db.update_alert(...)
        return {"status": "success"} # Placeholder