# File Location: backend/services/audit_service.py
# CRITICAL FIX: Complete audit service for compliance and security logging

import logging
from typing import Dict, Any, Optional, List  # ← Added List import here
from supabase import Client
from datetime import datetime, timedelta  # ← Added timedelta import
from enum import Enum
import uuid
import json
import traceback

logger = logging.getLogger(__name__)

class AuditEventType(str, Enum):
    """Audit event types for compliance tracking"""
    USER_CREATED = "user_created"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    PROFILE_UPDATED = "profile_updated"
    
    KYC_INITIATED = "kyc_initiated"
    KYC_COMPLETED = "kyc_completed" 
    KYC_FAILED = "kyc_failed"
    KYC_SKIPPED = "kyc_skipped"
    
    WALLET_CREATED = "wallet_created"
    WALLET_ACCESSED = "wallet_accessed"
    
    TRANSACTION_INITIATED = "transaction_initiated"
    TRANSACTION_COMPLETED = "transaction_completed"
    TRANSACTION_FAILED = "transaction_failed"
    
    COMPLIANCE_CHECK = "compliance_check"
    COMPLIANCE_VIOLATION = "compliance_violation"
    
    SECURITY_EVENT = "security_event"
    SYSTEM_ERROR = "system_error"
    
    API_ACCESS = "api_access"
    RATE_LIMIT_HIT = "rate_limit_hit"
    
    ADMIN_ACTION = "admin_action"
    DATA_EXPORT = "data_export"

class AuditSeverity(str, Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    CRITICAL = "critical"

class AuditService:
    """
    Centralized audit logging service for compliance, security, and operational monitoring
    All sensitive operations should be logged through this service
    """
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        logger.info("✅ AuditService initialized successfully")

    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Log an audit event with comprehensive context
        
        Args:
            event_type: Type of event being logged
            user_id: ID of user associated with event (if applicable)
            resource_id: ID of resource being acted upon (if applicable)
            details: Additional event-specific details
            severity: Event severity level
            ip_address: Client IP address
            user_agent: Client user agent string
            
        Returns:
            bool: True if logged successfully, False otherwise
        """
        try:
            event_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            audit_record = {
                "id": event_id,
                "event_type": event_type.value,
                "user_id": user_id,
                "resource_id": resource_id,
                "severity": severity.value,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "details": details or {},
                "timestamp": timestamp,
                "created_at": timestamp
            }
            
            # Log to console for immediate visibility
            log_level = {
                AuditSeverity.LOW: logging.INFO,
                AuditSeverity.MEDIUM: logging.INFO,
                AuditSeverity.HIGH: logging.WARNING,
                AuditSeverity.CRITICAL: logging.ERROR
            }.get(severity, logging.INFO)
            
            logger.log(
                log_level,
                f"[AUDIT] {event_type.value} | User: {user_id or 'N/A'} | "
                f"Resource: {resource_id or 'N/A'} | Severity: {severity.value}"
            )
            
            # Store in database for compliance
            response = self.supabase.from_("audit_logs").insert(audit_record).execute()
            
            if response.data:
                logger.debug(f"[AUDIT] Event logged successfully: {event_id}")
                return True
            else:
                logger.error(f"[AUDIT] Failed to log event: {event_type.value}")
                return False
                
        except Exception as e:
            logger.error(f"[AUDIT] Error logging event {event_type.value}: {str(e)}")
            logger.error(traceback.format_exc())
            # Don't raise - audit failures shouldn't break main functionality
            return False

    async def log_user_activity(
        self,
        user_id: str,
        activity: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """Convenience method for logging user activities"""
        return await self.log_event(
            event_type=AuditEventType.API_ACCESS,
            user_id=user_id,
            details={"activity": activity, **(details or {})},
            severity=AuditSeverity.LOW,
            ip_address=ip_address
        )

    async def log_security_event(
        self,
        event_description: str,
        user_id: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.HIGH,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """Log security-related events with high visibility"""
        return await self.log_event(
            event_type=AuditEventType.SECURITY_EVENT,
            user_id=user_id,
            details={
                "description": event_description,
                **(details or {})
            },
            severity=severity,
            ip_address=ip_address
        )

    async def log_compliance_check(
        self,
        user_id: str,
        check_type: str,
        result: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log compliance checks for regulatory reporting"""
        return await self.log_event(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            user_id=user_id,
            details={
                "check_type": check_type,
                "result": result,
                **(details or {})
            },
            severity=AuditSeverity.MEDIUM
        )

    async def log_transaction_event(
        self,
        user_id: str,
        transaction_id: str,
        event_type: AuditEventType,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        counterparty: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log transaction-related events for compliance"""
        transaction_details = {
            "amount": amount,
            "currency": currency,
            "counterparty": counterparty,
            **(details or {})
        }
        
        return await self.log_event(
            event_type=event_type,
            user_id=user_id,
            resource_id=transaction_id,
            details=transaction_details,
            severity=AuditSeverity.MEDIUM
        )

    async def log_admin_action(
        self,
        admin_user_id: str,
        action: str,
        target_user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log administrative actions for accountability"""
        return await self.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=admin_user_id,
            resource_id=target_user_id,
            details={
                "action": action,
                **(details or {})
            },
            severity=AuditSeverity.HIGH
        )

    async def get_user_audit_trail(
        self,
        user_id: str,
        limit: int = 100,
        event_types: Optional[List[AuditEventType]] = None
    ) -> List[Dict[str, Any]]:
        """Get audit trail for a specific user"""
        try:
            logger.debug(f"[AUDIT] Fetching audit trail for user: {user_id}")
            
            query = self.supabase.from_("audit_logs").select("*").eq("user_id", user_id)
            
            if event_types:
                event_type_values = [et.value for et in event_types]
                query = query.in_("event_type", event_type_values)
            
            response = query.order("timestamp", desc=True).limit(limit).execute()
            
            if response.data:
                logger.debug(f"[AUDIT] Retrieved {len(response.data)} audit events for user {user_id}")
                return response.data
            else:
                logger.debug(f"[AUDIT] No audit trail found for user {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"[AUDIT] Error fetching audit trail for user {user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return []

    async def get_security_events(
        self,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Get security events within specified time window"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            query = self.supabase.from_("audit_logs").select("*").eq("event_type", AuditEventType.SECURITY_EVENT.value)
            
            if severity:
                query = query.eq("severity", severity.value)
            
            response = query.gte("timestamp", cutoff_time.isoformat()).order("timestamp", desc=True).limit(limit).execute()
            
            if response.data:
                logger.debug(f"[AUDIT] Retrieved {len(response.data)} security events")
                return response.data
            else:
                return []
                
        except Exception as e:
            logger.error(f"[AUDIT] Error fetching security events: {str(e)}")
            return []

    async def get_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate compliance report for specified time period"""
        try:
            logger.info(f"[AUDIT] Generating compliance report: {start_date} to {end_date}")
            
            query = self.supabase.from_("audit_logs").select("*").gte("timestamp", start_date.isoformat()).lte("timestamp", end_date.isoformat())
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            response = query.execute()
            
            if not response.data:
                return {
                    "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                    "total_events": 0,
                    "summary": {},
                    "compliance_flags": []
                }
            
            events = response.data
            
            # Analyze events for compliance report
            event_summary = {}
            compliance_flags = []
            security_incidents = 0
            failed_transactions = 0
            
            for event in events:
                event_type = event.get("event_type", "unknown")
                event_summary[event_type] = event_summary.get(event_type, 0) + 1
                
                # Flag potential compliance issues
                if event_type == AuditEventType.SECURITY_EVENT.value and event.get("severity") in ["high", "critical"]:
                    security_incidents += 1
                    compliance_flags.append({
                        "type": "security_incident",
                        "timestamp": event.get("timestamp"),
                        "user_id": event.get("user_id"),
                        "severity": event.get("severity"),
                        "details": event.get("details", {})
                    })
                
                if event_type == AuditEventType.TRANSACTION_FAILED.value:
                    failed_transactions += 1
                    
                if event_type == AuditEventType.COMPLIANCE_VIOLATION.value:
                    compliance_flags.append({
                        "type": "compliance_violation",
                        "timestamp": event.get("timestamp"),
                        "user_id": event.get("user_id"),
                        "details": event.get("details", {})
                    })
            
            report = {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "total_events": len(events),
                "summary": event_summary,
                "metrics": {
                    "security_incidents": security_incidents,
                    "failed_transactions": failed_transactions,
                    "compliance_violations": len([f for f in compliance_flags if f["type"] == "compliance_violation"])
                },
                "compliance_flags": compliance_flags,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"[AUDIT] Compliance report generated with {len(events)} events")
            return report
            
        except Exception as e:
            logger.error(f"[AUDIT] Error generating compliance report: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat()
            }

    async def log_rate_limit_violation(
        self,
        ip_address: str,
        endpoint: str,
        user_id: Optional[str] = None,
        attempts: int = 1
    ) -> bool:
        """Log rate limit violations for monitoring"""
        return await self.log_event(
            event_type=AuditEventType.RATE_LIMIT_HIT,
            user_id=user_id,
            details={
                "endpoint": endpoint,
                "attempts": attempts,
                "rate_limit_type": "api_request"
            },
            severity=AuditSeverity.MEDIUM,
            ip_address=ip_address
        )

    async def log_data_export(
        self,
        user_id: str,
        export_type: str,
        data_categories: List[str],
        admin_user_id: Optional[str] = None
    ) -> bool:
        """Log data export operations for privacy compliance"""
        return await self.log_event(
            event_type=AuditEventType.DATA_EXPORT,
            user_id=admin_user_id or user_id,
            resource_id=user_id,
            details={
                "export_type": export_type,
                "data_categories": data_categories,
                "target_user": user_id if admin_user_id else None
            },
            severity=AuditSeverity.HIGH
        )

    async def log_kyc_event(
        self,
        user_id: str,
        kyc_event: str,
        provider: str,
        session_id: Optional[str] = None,
        outcome: Optional[str] = None,
        rejection_reason: Optional[str] = None
    ) -> bool:
        """Log KYC-specific events for compliance"""
        event_mapping = {
            "initiated": AuditEventType.KYC_INITIATED,
            "completed": AuditEventType.KYC_COMPLETED,
            "failed": AuditEventType.KYC_FAILED,
            "skipped": AuditEventType.KYC_SKIPPED
        }
        
        event_type = event_mapping.get(kyc_event, AuditEventType.KYC_INITIATED)
        
        details = {
            "provider": provider,
            "kyc_event": kyc_event
        }
        
        if session_id:
            details["session_id"] = session_id
        if outcome:
            details["outcome"] = outcome
        if rejection_reason:
            details["rejection_reason"] = rejection_reason
        
        return await self.log_event(
            event_type=event_type,
            user_id=user_id,
            resource_id=session_id,
            details=details,
            severity=AuditSeverity.HIGH if kyc_event in ["failed", "skipped"] else AuditSeverity.MEDIUM
        )

    async def search_audit_logs(
        self,
        search_criteria: Dict[str, Any],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search audit logs with flexible criteria"""
        try:
            logger.debug(f"[AUDIT] Searching audit logs with criteria: {search_criteria}")
            
            query = self.supabase.from_("audit_logs").select("*")
            
            # Apply search filters
            if "user_id" in search_criteria:
                query = query.eq("user_id", search_criteria["user_id"])
            
            if "event_type" in search_criteria:
                query = query.eq("event_type", search_criteria["event_type"])
            
            if "severity" in search_criteria:
                query = query.eq("severity", search_criteria["severity"])
            
            if "start_time" in search_criteria:
                query = query.gte("timestamp", search_criteria["start_time"])
            
            if "end_time" in search_criteria:
                query = query.lte("timestamp", search_criteria["end_time"])
            
            if "ip_address" in search_criteria:
                query = query.eq("ip_address", search_criteria["ip_address"])
            
            response = query.order("timestamp", desc=True).limit(limit).execute()
            
            if response.data:
                logger.debug(f"[AUDIT] Search returned {len(response.data)} results")
                return response.data
            else:
                return []
                
        except Exception as e:
            logger.error(f"[AUDIT] Error searching audit logs: {str(e)}")
            logger.error(traceback.format_exc())
            return []

    async def cleanup_old_logs(self, retention_days: int = 2555) -> Dict[str, int]:  # 7 years default retention
        """Clean up old audit logs based on retention policy"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            logger.info(f"[AUDIT] Starting cleanup of logs older than {cutoff_date}")
            
            # First, get count of records to be deleted
            count_response = self.supabase.from_("audit_logs").select("count", count="exact").lt("timestamp", cutoff_date.isoformat()).execute()
            records_to_delete = count_response.count or 0
            
            if records_to_delete == 0:
                logger.info("[AUDIT] No old records found for cleanup")
                return {"deleted": 0, "remaining": 0}
            
            # Delete old records
            delete_response = self.supabase.from_("audit_logs").delete().lt("timestamp", cutoff_date.isoformat()).execute()
            
            # Get remaining count
            remaining_response = self.supabase.from_("audit_logs").select("count", count="exact").execute()
            remaining_records = remaining_response.count or 0
            
            logger.info(f"[AUDIT] Cleanup completed: {records_to_delete} records deleted, {remaining_records} remaining")
            
            return {
                "deleted": records_to_delete,
                "remaining": remaining_records,
                "cutoff_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"[AUDIT] Error during log cleanup: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": str(e), "deleted": 0, "remaining": 0}

    async def get_audit_statistics(self) -> Dict[str, Any]:
        """Get comprehensive audit system statistics"""
        try:
            logger.debug("[AUDIT] Generating audit statistics")
            
            # Total events
            total_response = self.supabase.from_("audit_logs").select("count", count="exact").execute()
            total_events = total_response.count or 0
            
            # Events by type (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_response = self.supabase.from_("audit_logs").select("event_type").gte("timestamp", thirty_days_ago.isoformat()).execute()
            
            event_type_counts = {}
            if recent_response.data:
                for event in recent_response.data:
                    event_type = event.get("event_type", "unknown")
                    event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            
            # Critical events (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            critical_response = self.supabase.from_("audit_logs").select("*").eq("severity", "critical").gte("timestamp", week_ago.isoformat()).execute()
            critical_events = len(critical_response.data) if critical_response.data else 0
            
            statistics = {
                "total_events": total_events,
                "last_30_days_by_type": event_type_counts,
                "critical_events_last_7_days": critical_events,
                "system_health": {
                    "audit_logging": "operational",
                    "retention_policy": "active",
                    "last_cleanup": "manual"  # This would be updated by a scheduled job
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.debug(f"[AUDIT] Statistics generated: {total_events} total events")
            return statistics
            
        except Exception as e:
            logger.error(f"[AUDIT] Error generating audit statistics: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat()
            }

    async def log_wallet_operation(
        self,
        user_id: str,
        operation: str,
        wallet_address: Optional[str] = None,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        transaction_hash: Optional[str] = None
    ) -> bool:
        """Log wallet operations for security monitoring"""
        return await self.log_event(
            event_type=AuditEventType.WALLET_ACCESSED,
            user_id=user_id,
            resource_id=wallet_address,
            details={
                "operation": operation,
                "amount": amount,
                "currency": currency,
                "transaction_hash": transaction_hash,
                "wallet_type": "managed"
            },
            severity=AuditSeverity.MEDIUM
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check audit service health and connectivity"""
        try:
            logger.debug("[AUDIT] Performing health check")
            
            # Test database connectivity
            test_response = self.supabase.from_("audit_logs").select("count", count="exact").limit(1).execute()
            
            if test_response.count is not None:
                return {
                    "status": "healthy",
                    "database_connectivity": "operational",
                    "total_events": test_response.count,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "degraded",
                    "database_connectivity": "issues",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"[AUDIT] Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Convenience functions for common audit operations
async def log_user_login(audit_service: AuditService, user_id: str, ip_address: str, user_agent: str) -> bool:
    """Quick function to log user login"""
    return await audit_service.log_event(
        AuditEventType.USER_LOGIN,
        user_id=user_id,
        severity=AuditSeverity.LOW,
        ip_address=ip_address,
        user_agent=user_agent
    )

async def log_user_logout(audit_service: AuditService, user_id: str, ip_address: str) -> bool:
    """Quick function to log user logout"""
    return await audit_service.log_event(
        AuditEventType.USER_LOGOUT,
        user_id=user_id,
        severity=AuditSeverity.LOW,
        ip_address=ip_address
    )

async def log_failed_login(audit_service: AuditService, email: str, ip_address: str, reason: str) -> bool:
    """Quick function to log failed login attempts"""
    return await audit_service.log_security_event(
        event_description=f"Failed login attempt for {email}",
        severity=AuditSeverity.MEDIUM,
        details={"email": email, "reason": reason},
        ip_address=ip_address
    )

# Initialize audit service instance (to be imported by other services)
def create_audit_service(supabase_client) -> AuditService:
    """Factory function to create audit service instance"""
    return AuditService(supabase_client)