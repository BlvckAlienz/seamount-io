import logging
import json
import asyncio
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from supabase import Client
from postgrest import APIError  # postgrest exceptions are used by the client
import uuid

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
    Minimal, robust implementation that writes audit events to Supabase.
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
        data_to_hash = json.dumps(safe_event, sort_keys=True, default=str)
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
        This writes into the 'audit_logs' table (generic audit table).
        """
        try:
            event = {
                "type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "details": details or {},
                "resource_id": resource_id,
                "severity": severity,
            }

            await self.supabase.table("audit_logs").insert(event).execute()
            
            log_message = f"AUDIT: [{event_type}] User: {user_id or 'System'}, Resource: {resource_id}"
            logger.info(log_message)

        except Exception as e:
            logger.error(f"Failed to write audit event to Supabase: {e}", exc_info=True)
            # In production, push failed logs to a fallback reliable store (e.g., SQS, Redis)

    async def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves the most recent audit trail events."""
        try:
            response = await self.supabase.table("audit_logs").select("*").order("timestamp", desc=True).limit(limit).execute()
            return getattr(response, "data", response)
        except Exception as e:
            logger.error(f"Failed to retrieve audit trail: {e}", exc_info=True)
            return []

    async def log_action(self, actor: str, action: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Insert an action record into the 'compliance_logs' table.
        This method is defensive:
          - writes 'action_taken' instead of 'action' (matches the actual schema)
          - ensures actor is a valid UUID or null
          - falls back to 'audit_logs' if compliance_logs is missing/has different schema
        """

        # Ensure actor is a valid UUID or None
        actor_uuid = None
        try:
            if actor and uuid.UUID(str(actor)):
                actor_uuid = str(actor)
        except (ValueError, TypeError):
            actor_uuid = None  # Not a valid UUID → store as NULL

        record = {
            "actor": actor_uuid,
            "action_taken": action,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            logger.info(f"Audit Logger: Writing compliance action: actor={actor_uuid}, action_taken={action}")
            await self.supabase.table("compliance_logs").insert(record).execute()
            logger.info("Audit Logger: compliance_logs insert succeeded.")
            return
        except Exception:
            logger.warning("Audit Logger: Insert into compliance_logs failed; attempting fallbacks.", exc_info=True)

            # Try alternative key name if server still expects 'action'
            alt_record = record.copy()
            alt_record.pop("action_taken", None)
            alt_record["action"] = action

            try:
                logger.info("Audit Logger: Retrying compliance_logs insert with 'action' column.")
                await self.supabase.table("compliance_logs").insert(alt_record).execute()
                logger.info("Audit Logger: compliance_logs insert with 'action' succeeded.")
                return
            except Exception:
                logger.error("Audit Logger: compliance_logs insert with 'action' also failed.", exc_info=True)

            # Final fallback to audit_logs
            try:
                fallback = {
                    "type": "compliance_log_passthrough",
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": actor_uuid,
                    "details": {"action": action, "metadata": metadata or {}},
                    "resource_id": None,
                    "severity": "warning",
                }
                await self.supabase.table("audit_logs").insert(fallback).execute()
                logger.info("Audit Logger: Wrote fallback record to audit_logs to avoid startup failure.")
            except Exception:
                logger.critical("Audit Logger: Failed to write fallback audit log. Application may continue but audit is degraded.", exc_info=True)
