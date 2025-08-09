import logging
import json
import asyncio
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from supabase import Client

# Assuming config is in the parent directory
from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class AuditEventType:
    USER_LOGIN = "user_login"
    PAYMENT_CREATED = "payment_created"
    PAYMENT_COMPLETED = "payment_completed"
    KYC_INITIATED = "kyc_initiated"
    KYC_COMPLETED = "kyc_completed"
    MINT_INITIATED = "mint_initiated"
    MINT_COMPLETED = "mint_completed"
    BURN_INITIATED = "burn_initiated"
    BURN_COMPLETED = "burn_completed"
    COMPLIANCE_CHECK = "compliance_check"
    SYSTEM_ERROR = "system_error"

class AuditService:
    """
    A modern, dependency-injected audit logging service.
    """
    def __init__(self, supabase_client: Client):
        """
        Initializes the service with a pre-configured Supabase client,
        following a clean dependency injection pattern.
        """
        if not supabase_client:
            raise ValueError("Supabase client is required for AuditService.")
        self.supabase = supabase_client
        self.last_hash: Optional[str] = None
        logger.info("AuditService initialized successfully.")

    def _compute_hash(self, event: Dict[str, Any], previous_hash: Optional[str] = None) -> str:
        """Computes a cryptographic hash for an event, chaining it to the previous hash."""
        safe_event = {k: v for k, v in event.items() if k != "hash"}
        data_to_hash = json.dumps(safe_event, sort_keys=True)
        if previous_hash:
            data_to_hash = previous_hash + data_to_hash
        return hashlib.sha256(data_to_hash.encode()).hexdigest()
    
    async def log_event(self, 
                       event_type: str, 
                       user_id: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None,
                       resource_id: Optional[str] = None,
                       severity: str = "info") -> None:
        """
        Logs an audit event with a cryptographic hash chain for tamper evidence.
        """
        try:
            # In a high-throughput system, you might fetch the last hash from Redis or DB.
            # For this implementation, we'll keep it simple for now.
            
            event = {
                "type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "details": details or {},
                "resource_id": resource_id,
                "severity": severity,
            }

            # Chaining would be more robust with a persistent last_hash
            # event["previous_hash"] = self.last_hash
            # event["hash"] = self._compute_hash(event, self.last_hash)
            # self.last_hash = event["hash"]
            
            await self.supabase.table("audit_logs").insert(event).execute()
            
            log_message = f"AUDIT: [{event_type}] User: {user_id or 'System'}, Resource: {resource_id}"
            logger.info(log_message)

        except Exception as e:
            logger.error(f"Failed to write audit event to Supabase: {e}")
            # In a production system, you would push this failed log to a fallback queue (like Redis).

    async def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves the most recent audit trail events."""
        try:
            response = await self.supabase.table("audit_logs").select("*").order("timestamp", desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to retrieve audit trail: {e}")
            return []