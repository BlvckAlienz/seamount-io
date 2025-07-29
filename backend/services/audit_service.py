"""
Seamount.io Cross-Border Payment Platform
Immutable Audit Logging Service

Provides comprehensive audit trail capabilities with tamper-proof logging
for all system transactions, user activities, and compliance events.
"""

import logging
import json
import os
import time
import asyncio
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
import aioredis
from supabase import create_client, Client

# Configure standard logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuditEventType:
    """Enumeration of audit event types"""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    KYC_INITIATED = "kyc_initiated"
    KYC_UPDATED = "kyc_updated"
    KYC_COMPLETED = "kyc_completed"
    PAYMENT_CREATED = "payment_created"
    PAYMENT_UPDATED = "payment_updated"
    PAYMENT_COMPLETED = "payment_completed"
    TRANSACTION_CREATED = "transaction_created"
    TRANSACTION_CONFIRMED = "transaction_confirmed"
    MINT_INITIATED = "mint_initiated"
    MINT_COMPLETED = "mint_completed"
    BURN_INITIATED = "burn_initiated"
    BURN_COMPLETED = "burn_completed"
    ADMIN_ACTION = "admin_action"
    COMPLIANCE_CHECK = "compliance_check"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SYSTEM_ERROR = "system_error"

class AuditLogger:
    """
    Immutable audit logging service that provides tamper-proof logs
    with cryptographic verification for regulatory compliance.
    """
    
    def __init__(self):
        # Initialize DB connections
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase = None
        self.redis = None
        self.log_buffer = []
        self.buffer_size = 100
        self.last_hash = None
        self._initialize_db()
        
        # Start background task for buffer flushing
        self.buffer_flush_task = None
        self._start_background_tasks()
    
    def _initialize_db(self):
        """Initialize database connections"""
        try:
            if self.supabase_url and self.supabase_key:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                logger.info("Audit Logger: Supabase connected")
            else:
                logger.warning("Audit Logger: No Supabase credentials provided")
            
            # Redis will be initialized asynchronously
        except Exception as e:
            logger.error(f"Audit Logger initialization failed: {e}")
    
    async def initialize_redis(self):
        """Initialize Redis connection asynchronously"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis = await aioredis.from_url(redis_url)
            logger.info("Audit Logger: Redis connected")
        except Exception as e:
            logger.error(f"Audit Logger Redis connection failed: {e}")
            self.redis = None
    
    def _start_background_tasks(self):
        """Start background tasks for the audit logger"""
        loop = asyncio.get_event_loop()
        self.buffer_flush_task = loop.create_task(self._flush_buffer_periodically())
    
    async def _flush_buffer_periodically(self):
        """Periodically flush the log buffer to persistent storage"""
        await self.initialize_redis()
        
        while True:
            try:
                if len(self.log_buffer) > 0:
                    await self._flush_buffer()
                await asyncio.sleep(60)  # Flush every minute
            except asyncio.CancelledError:
                # Handle graceful shutdown
                if len(self.log_buffer) > 0:
                    await self._flush_buffer()
                break
            except Exception as e:
                logger.error(f"Error in buffer flush task: {e}")
                await asyncio.sleep(60)  # Retry after a minute
    
    async def _flush_buffer(self):
        """Flush the current log buffer to persistent storage"""
        if not self.log_buffer:
            return
            
        # Make a copy and clear the buffer
        buffer_copy = self.log_buffer.copy()
        self.log_buffer = []
        
        try:
            if self.supabase:
                # Write to database in batches
                for i in range(0, len(buffer_copy), 50):
                    batch = buffer_copy[i:i+50]
                    response = await self.supabase.table("audit_logs").insert(batch).execute()
                    if hasattr(response, "error") and response.error:
                        logger.error(f"Failed to write audit logs to Supabase: {response.error}")
                        # Return the failed logs to buffer
                        self.log_buffer.extend(batch)
            else:
                logger.warning("No Supabase connection for audit logs")
                # Keep the logs in buffer
                self.log_buffer.extend(buffer_copy)
                
        except Exception as e:
            logger.error(f"Failed to flush audit log buffer: {e}")
            # Return the logs to buffer
            self.log_buffer.extend(buffer_copy)
    
    def _compute_hash(self, event: Dict[str, Any], previous_hash: Optional[str] = None) -> str:
        """Compute a cryptographic hash for an event including the previous hash for chaining"""
        data_to_hash = json.dumps(event, sort_keys=True)
        if previous_hash:
            data_to_hash = previous_hash + data_to_hash
        return hashlib.sha256(data_to_hash.encode()).hexdigest()
    
    async def log_event(self, 
                       event_type: str, 
                       user_id: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None,
                       ip_address: Optional[str] = None,
                       resource_id: Optional[str] = None,
                       severity: str = "info",
                       critical: bool = False) -> str:
        """
        Log an audit event with cryptographic hash chaining for tamper evidence
        
        Args:
            event_type: Type of event (see AuditEventType)
            user_id: ID of user who performed the action (if applicable)
            details: Additional details about the event
            ip_address: IP address of the user (if applicable)
            resource_id: ID of the resource affected (transaction ID, etc.)
            severity: Severity level (info, warning, error)
            critical: If True, force immediate persistence
            
        Returns:
            Event ID
        """
        # Create the event object
        event = {
            "id": f"evt_{int(time.time())}_{os.urandom(4).hex()}",
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "details": details or {},
            "ip_address": ip_address,
            "resource_id": resource_id,
            "severity": severity
        }
        
        # Add cryptographic hash for tamper evidence
        previous_hash = self.last_hash
        event["previous_hash"] = previous_hash
        event["hash"] = self._compute_hash(event, previous_hash)
        self.last_hash = event["hash"]
        
        # Add to local log buffer
        self.log_buffer.append(event)
        
        # Write to standard log as well
        log_message = f"AUDIT: [{event_type}] {user_id or 'System'}"
        if resource_id:
            log_message += f" - Resource: {resource_id}"
        if details:
            log_message += f" - {json.dumps(details)}"
            
        if severity == "error":
            logger.error(log_message)
        elif severity == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # If critical, flush immediately
        if critical and (self.supabase or self.redis):
            # Store immediately for critical events
            try:
                if self.supabase:
                    await self.supabase.table("audit_logs").insert(event).execute()
            except Exception as e:
                logger.error(f"Failed to write critical audit event: {e}")
        
        # If buffer is full, schedule a flush
        if len(self.log_buffer) >= self.buffer_size:
            asyncio.create_task(self._flush_buffer())
        
        return event["id"]
    
    async def get_audit_trail(self, 
                             filters: Optional[Dict[str, Any]] = None, 
                             limit: int = 100, 
                             offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail with optional filtering
        
        Args:
            filters: Optional dictionary of filters (user_id, type, etc.)
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of audit events
        """
        if not self.supabase:
            return []
            
        try:
            # Build the query
            query = self.supabase.table("audit_logs").select("*")
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if key == "from_date":
                        query = query.gte("timestamp", value)
                    elif key == "to_date":
                        query = query.lte("timestamp", value)
                    elif key == "severity":
                        query = query.eq("severity", value)
                    elif key == "type":
                        if isinstance(value, list):
                            query = query.in_("type", value)
                        else:
                            query = query.eq("type", value)
                    elif key == "user_id":
                        query = query.eq("user_id", value)
                    elif key == "resource_id":
                        query = query.eq("resource_id", value)
            
            # Apply pagination and ordering
            query = query.order("timestamp", {"ascending": False}).range(offset, offset + limit - 1)
            
            # Execute query
            response = await query.execute()
            
            if hasattr(response, "error") and response.error:
                logger.error(f"Failed to retrieve audit logs: {response.error}")
                return []
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit trail: {e}")
            return []
    
    async def verify_log_integrity(self, start_id: Optional[str] = None, end_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify the integrity of the audit log chain
        
        Args:
            start_id: Optional starting event ID
            end_id: Optional ending event ID
            
        Returns:
            Verification results including any tampering detected
        """
        if not self.supabase:
            return {"verified": False, "error": "No database connection"}
            
        try:
            # Build the query
            query = self.supabase.table("audit_logs").select("*")
            
            if start_id:
                # Get the timestamp of the start event
                start_event = await self.supabase.table("audit_logs").select("timestamp").eq("id", start_id).execute()
                if start_event.data:
                    query = query.gte("timestamp", start_event.data[0]["timestamp"])
            
            if end_id:
                # Get the timestamp of the end event
                end_event = await self.supabase.table("audit_logs").select("timestamp").eq("id", end_id).execute()
                if end_event.data:
                    query = query.lte("timestamp", end_event.data[0]["timestamp"])
            
            # Order by timestamp
            query = query.order("timestamp", {"ascending": True})
            
            # Execute query
            response = await query.execute()
            
            if hasattr(response, "error") and response.error:
                logger.error(f"Failed to retrieve audit logs for verification: {response.error}")
                return {"verified": False, "error": response.error}
            
            events = response.data or []
            
            # Verify hash chain
            previous_hash = None
            broken_chains = []
            
            for event in events:
                # Check if this event references the correct previous hash
                if previous_hash is not None and event["previous_hash"] != previous_hash:
                    broken_chains.append({
                        "event_id": event["id"],
                        "timestamp": event["timestamp"],
                        "expected": previous_hash,
                        "actual": event["previous_hash"]
                    })
                
                # Verify this event's hash
                computed_hash = self._compute_hash(
                    {k: v for k, v in event.items() if k not in ["hash", "previous_hash"]}, 
                    event["previous_hash"]
                )
                
                if computed_hash != event["hash"]:
                    broken_chains.append({
                        "event_id": event["id"],
                        "timestamp": event["timestamp"],
                        "hash_mismatch": True,
                        "expected": computed_hash,
                        "actual": event["hash"]
                    })
                
                # Update for next iteration
                previous_hash = event["hash"]
            
            return {
                "verified": len(broken_chains) == 0,
                "events_checked": len(events),
                "broken_chains": broken_chains,
                "start": events[0]["timestamp"] if events else None,
                "end": events[-1]["timestamp"] if events else None
            }
            
        except Exception as e:
            logger.error(f"Failed to verify audit log integrity: {e}")
            return {"verified": False, "error": str(e)}
    
    async def generate_audit_report(self, 
                                  start_date: str, 
                                  end_date: str,
                                  report_type: str = "standard") -> Dict[str, Any]:
        """
        Generate an audit report for a specified time period
        
        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format
            report_type: Report type (standard, compliance, regulatory)
            
        Returns:
            Audit report data
        """
        if not self.supabase:
            return {"error": "No database connection"}
            
        try:
            # Get all events in the time range
            events = await self.get_audit_trail({
                "from_date": start_date,
                "to_date": end_date
            }, limit=10000)
            
            if not events:
                return {
                    "report_type": report_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "generated_at": datetime.utcnow().isoformat(),
                    "event_count": 0,
                    "message": "No events found in the specified period"
                }
            
            # Aggregate events by type
            event_types = {}
            user_activity = {}
            resources_affected = {}
            severity_counts = {"info": 0, "warning": 0, "error": 0}
            
            for event in events:
                # Count by event type
                event_type = event["type"]
                event_types[event_type] = event_types.get(event_type, 0) + 1
                
                # Count by user
                user_id = event["user_id"]
                if user_id:
                    if user_id not in user_activity:
                        user_activity[user_id] = {"count": 0, "events": {}}
                    user_activity[user_id]["count"] += 1
                    user_activity[user_id]["events"][event_type] = user_activity[user_id]["events"].get(event_type, 0) + 1
                
                # Count by resource
                resource_id = event["resource_id"]
                if resource_id:
                    resources_affected[resource_id] = resources_affected.get(resource_id, 0) + 1
                
                # Count by severity
                severity = event["severity"]
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Create report based on type
            report = {
                "report_type": report_type,
                "start_date": start_date,
                "end_date": end_date,
                "generated_at": datetime.utcnow().isoformat(),
                "event_count": len(events),
                "summary": {
                    "event_types": event_types,
                    "active_users": len(user_activity),
                    "resources_affected": len(resources_affected),
                    "severity": severity_counts
                }
            }
            
            # Add specific data based on report type
            if report_type == "compliance":
                # Add compliance-specific data
                compliance_events = [e for e in events if e["type"] in [
                    AuditEventType.COMPLIANCE_CHECK, 
                    AuditEventType.SUSPICIOUS_ACTIVITY,
                    AuditEventType.KYC_COMPLETED
                ]]
                
                report["compliance"] = {
                    "checks_performed": len([e for e in compliance_events if e["type"] == AuditEventType.COMPLIANCE_CHECK]),
                    "suspicious_activities": len([e for e in compliance_events if e["type"] == AuditEventType.SUSPICIOUS_ACTIVITY]),
                    "kyc_completions": len([e for e in compliance_events if e["type"] == AuditEventType.KYC_COMPLETED])
                }
            
            elif report_type == "regulatory":
                # Add regulatory-specific data
                transaction_events = [e for e in events if e["type"] in [
                    AuditEventType.TRANSACTION_CREATED,
                    AuditEventType.TRANSACTION_CONFIRMED,
                    AuditEventType.MINT_COMPLETED,
                    AuditEventType.BURN_COMPLETED
                ]]
                
                # Aggregate transaction volumes
                total_volume = 0
                country_volumes = {}
                
                for event in transaction_events:
                    details = event["details"] or {}
                    amount = details.get("amount", 0)
                    country = details.get("country_code")
                    
                    total_volume += amount
                    
                    if country:
                        country_volumes[country] = country_volumes.get(country, 0) + amount
                
                report["transactions"] = {
                    "count": len(transaction_events),
                    "total_volume": total_volume,
                    "by_country": country_volumes
                }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate audit report: {e}")
            return {"error": str(e)}

# Create singleton instance
audit_logger = AuditLogger()

# Asynchronous function to log audit events
async def log_audit_event(
    event_type: str, 
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    resource_id: Optional[str] = None,
    severity: str = "info",
    critical: bool = False
) -> str:
    """Convenience function to log audit events"""
    return await audit_logger.log_event(
        event_type, user_id, details, ip_address, 
        resource_id, severity, critical
    )