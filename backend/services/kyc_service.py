# File Location: backend/services/kyc_service.py
# PRODUCTION-READY: Complete KYC service with ComplyCube integration and robust error handling

import logging
from typing import Dict, Any, Optional
from supabase import Client
from fastapi import HTTPException
from datetime import datetime

from backend.config import get_settings
from backend.services.audit_service import AuditService, AuditEventType
from backend.services.database_service import DatabaseService
from backend.services.kyc_providers.complycube import ComplyCubeVerifier

logger = logging.getLogger(__name__)

class KYCService:
    """
    PRODUCTION-READY: Complete KYC service for user verification lifecycle
    Manages KYC sessions, compliance checks, and provider integrations
    """
    
    def __init__(self, settings=None, supabase_client: Optional[Client] = None, db_service: Optional[DatabaseService] = None, audit_service: Optional[AuditService] = None):
        """Initialize KYC service with proper dependency injection"""
        self.settings = settings or get_settings()
        self.supabase = supabase_client
        
        # Initialize database service
        if db_service:
            self.db_service = db_service
        else:
            self.db_service = DatabaseService(supabase_client)
        
        # Initialize audit service
        if audit_service:
            self.audit = audit_service
        else:
            self.audit = AuditService(supabase_client)
        
        # Initialize KYC provider
        complycube_key = getattr(self.settings, 'COMPLYCUBE_API_KEY', None)
        if complycube_key:
            try:
                self.provider = ComplyCubeVerifier(api_key=complycube_key.get_secret_value() if hasattr(complycube_key, 'get_secret_value') else complycube_key)
                logger.info("✅ KYC Service initialized with ComplyCube provider")
            except Exception as e:
                logger.error(f"Failed to initialize ComplyCube provider: {e}")
                self.provider = None
        else:
            self.provider = None
            logger.warning("⚠️  COMPLYCUBE_API_KEY not set. KYC service will operate in simulated mode")

    async def start_verification_session(self, user_id: str, email: str, country_code: str = "US") -> Dict[str, Any]:
        """
        Start a new KYC verification flow for Level 2 verification (document submission)
        This is the main entry point for user identity verification
        """
        try:
            logger.info(f"🔄 Starting KYC verification for user {user_id}")
            
            # Validate user profile exists
            user_profile = await self.db_service.get_user_profile_by_id(user_id)
            if not user_profile:
                logger.error(f"User profile not found for user {user_id}")
                raise HTTPException(status_code=404, detail="User profile not found")
            
            # Check if user already has active verification session (FIXED: only check in_progress, not pending)
            if user_profile.get("kyc_status") == "in_progress":
                logger.warning(f"User {user_id} already has active KYC verification")
                return {
                    "success": False,
                    "error": "KYC verification already in progress",
                    "kyc_status": user_profile.get("kyc_status")
                }
            
            # Handle simulated mode for testing
            if not self.provider:
                logger.warning(f"🧪 SIMULATING KYC session for user {user_id} - No provider configured")
                
                # Update user to pending status for simulation
                await self.db_service.update_user_kyc_status(user_id, "pending", 1)
                
                frontend_url = getattr(self.settings, 'FRONTEND_URL', 'https://seamount.io')
                return {
                    "success": True,
                    "flow_url": f"{frontend_url}/kyc-complete?simulated=true&user_id={user_id}",
                    "message": "KYC verification started (simulated mode)",
                    "kyc_status": "pending"
                }
            
            # Create ComplyCube client
            try:
                client_id = await self.provider.create_client(user_id, email, country_code)
                logger.info(f"📋 Created ComplyCube client {client_id} for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to create ComplyCube client for user {user_id}: {e}")
                await self.audit.log_event(
                    AuditEventType.SYSTEM_ERROR, 
                    user_id=user_id, 
                    details={"error": f"ComplyCube client creation failed: {str(e)}"}, 
                    severity="error"
                )
                raise HTTPException(status_code=500, detail="Failed to create KYC client")
            
            # Create verification session
            try:
                session_data = await self.provider.create_verification_session(client_id)
                session_id = session_data.get("id")
                flow_url = session_data.get("url")
                
                if not session_id or not flow_url:
                    raise ValueError("Invalid session data received from provider")
                    
                logger.info(f"🔗 Created verification session {session_id} for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to create verification session for user {user_id}: {e}")
                await self.audit.log_event(
                    AuditEventType.SYSTEM_ERROR, 
                    user_id=user_id, 
                    details={"error": f"ComplyCube client creation failed: {str(e)}"}, 
                    severity="error"
                )
                raise HTTPException(status_code=500, detail="Failed to create KYC client")
            
            # Create verification session
            try:
                session_data = await self.provider.create_verification_session(client_id)
                session_id = session_data.get("id")
                flow_url = session_data.get("url")
                
                if not session_id or not flow_url:
                    raise ValueError("Invalid session data received from provider")
                    
                logger.info(f"🔗 Created verification session {session_id} for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to create verification session for user {user_id}: {e}")
                await self.audit.log_event(
                    AuditEventType.SYSTEM_ERROR, 
                    user_id=user_id, 
                    details={"error": f"Verification session creation failed: {str(e)}"}, 
                    severity="error"
                )
                raise HTTPException(status_code=500, detail="Failed to create verification session")
            
            # Store session data and update user status
            try:
                # Update user profile to pending status
                await self.db_service.update_user_kyc_status(user_id, "pending", 1)
                
                # Store KYC session data
                kyc_data = {
                    "user_id": user_id,
                    "applicant_id": client_id,
                    "session_id": session_id,
                    "verification_type": "document_verification",
                    "status": "pending",
                    "response_data": session_data,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                await self.db_service.store_kyc_session(kyc_data)
                
                # Log successful session creation
                await self.audit.log_event(
                    AuditEventType.KYC_INITIATED, 
                    user_id=user_id, 
                    details={
                        "session_id": session_id, 
                        "client_id": client_id,
                        "verification_type": "document_verification"
                    },
                    severity="info"
                )
                
                logger.info(f"✅ KYC verification session created successfully for user {user_id}")
                
                return {
                    "success": True,
                    "flow_url": flow_url,
                    "session_id": session_id,
                    "message": "KYC verification started successfully",
                    "kyc_status": "pending"
                }
                
            except Exception as e:
                logger.error(f"Failed to store KYC session data for user {user_id}: {e}")
                await self.audit.log_event(
                    AuditEventType.SYSTEM_ERROR, 
                    user_id=user_id, 
                    details={"error": f"KYC session storage failed: {str(e)}"}, 
                    severity="error"
                )
                raise HTTPException(status_code=500, detail="Failed to store KYC session")
                
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting KYC verification for user {user_id}: {e}")
            await self.audit.log_event(
                AuditEventType.SYSTEM_ERROR, 
                user_id=user_id, 
                details={"error": f"Unexpected KYC initiation error: {str(e)}"}, 
                severity="critical"
            )
            raise HTTPException(status_code=500, detail="Internal server error during KYC verification")

    async def handle_webhook_event(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle webhook events from ComplyCube for verification status updates
        Processes document verification results and updates user status
        """
        try:
            event_type = webhook_data.get("type")
            applicant_id = webhook_data.get("payload", {}).get("id")
            
            if not event_type or not applicant_id:
                logger.error(f"Invalid webhook data received: {webhook_data}")
                return {"success": False, "error": "Invalid webhook data"}
            
            logger.info(f"🔔 Processing webhook event: {event_type} for applicant {applicant_id}")
            
            # Get user profile by applicant_id
            user_profile = await self.db_service.get_user_by_applicant_id(applicant_id)
            if not user_profile:
                logger.error(f"User not found for applicant_id: {applicant_id}")
                return {"success": False, "error": "User not found"}
            
            user_id = str(user_profile["id"])
            
            # Process different event types
            if event_type == "check.pending":
                await self._handle_verification_pending(user_id, applicant_id, webhook_data)
            elif event_type == "check.completed":
                await self._handle_verification_completed(user_id, applicant_id, webhook_data)
            elif event_type == "check.failed":
                await self._handle_verification_failed(user_id, applicant_id, webhook_data)
            else:
                logger.warning(f"⚠️ Unhandled webhook event type: {event_type}")
                return {"success": True, "message": f"Event type {event_type} noted but not processed"}
            
            return {"success": True, "message": "Webhook processed successfully"}
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return {"success": False, "error": "Internal server error"}

    async def _handle_verification_pending(self, user_id: str, applicant_id: str, webhook_data: Dict[str, Any]):
        """Handle pending verification status"""
        try:
            await self.db_service.update_user_kyc_status(user_id, "in_progress", 1)
            
            await self.audit.log_event(
                AuditEventType.KYC_STATUS_UPDATED,
                user_id=user_id,
                details={
                    "old_status": "pending",
                    "new_status": "in_progress", 
                    "applicant_id": applicant_id,
                    "webhook_data": webhook_data
                },
                severity="info"
            )
            
            logger.info(f"📋 KYC verification in progress for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling pending verification for user {user_id}: {e}")
            raise

    async def _handle_verification_completed(self, user_id: str, applicant_id: str, webhook_data: Dict[str, Any]):
        """Handle completed verification - check if passed or failed"""
        try:
            payload = webhook_data.get("payload", {})
            result = payload.get("result", "clear")
            
            if result == "clear":
                # Verification passed - upgrade to Level 2
                await self.db_service.update_user_kyc_status(user_id, "approved", 2)
                await self.db_service.update_user_access_level(user_id, "verified")
                
                await self.audit.log_event(
                    AuditEventType.KYC_APPROVED,
                    user_id=user_id,
                    details={
                        "kyc_level": 2,
                        "access_level": "verified",
                        "applicant_id": applicant_id,
                        "verification_result": result,
                        "webhook_data": payload
                    },
                    severity="info"
                )
                
                logger.info(f"✅ KYC verification APPROVED for user {user_id} - Level 2 access granted")
                
            else:
                # Verification failed
                rejection_reason = self._extract_rejection_reason(payload)
                await self.db_service.update_user_kyc_status(user_id, "rejected", 1, rejection_reason)
                
                await self.audit.log_event(
                    AuditEventType.KYC_REJECTED,
                    user_id=user_id,
                    details={
                        "rejection_reason": rejection_reason,
                        "applicant_id": applicant_id,
                        "verification_result": result,
                        "webhook_data": payload
                    },
                    severity="warning"
                )
                
                logger.warning(f"❌ KYC verification REJECTED for user {user_id}: {rejection_reason}")
                
        except Exception as e:
            logger.error(f"Error handling completed verification for user {user_id}: {e}")
            raise

    async def _handle_verification_failed(self, user_id: str, applicant_id: str, webhook_data: Dict[str, Any]):
        """Handle failed verification due to technical issues"""
        try:
            payload = webhook_data.get("payload", {})
            error_reason = payload.get("error", {}).get("message", "Verification failed due to technical issues")
            
            await self.db_service.update_user_kyc_status(user_id, "rejected", 1, error_reason)
            
            await self.audit.log_event(
                AuditEventType.SYSTEM_ERROR,
                user_id=user_id,
                details={
                    "error": "KYC verification failed",
                    "reason": error_reason,
                    "applicant_id": applicant_id,
                    "webhook_data": payload
                },
                severity="error"
            )
            
            logger.error(f"💥 KYC verification FAILED for user {user_id}: {error_reason}")
            
        except Exception as e:
            logger.error(f"Error handling failed verification for user {user_id}: {e}")
            raise

    def _extract_rejection_reason(self, payload: Dict[str, Any]) -> str:
        """Extract human-readable rejection reason from ComplyCube payload"""
        try:
            # Check for specific rejection reasons in payload
            breakdown = payload.get("breakdown", {})
            
            reasons = []
            
            # Document quality issues
            if breakdown.get("document_quality") == "rejected":
                reasons.append("Document quality insufficient")
            
            # Face match issues  
            if breakdown.get("face_match") == "rejected":
                reasons.append("Face verification failed")
                
            # Data validation issues
            if breakdown.get("data_validation") == "rejected":
                reasons.append("Document data validation failed")
                
            # PEP/Sanctions check
            if breakdown.get("pep_sanctions") == "rejected":
                reasons.append("PEP or sanctions list match")
            
            if reasons:
                return "; ".join(reasons)
            
            # Fallback to generic message if no specific reasons found
            return payload.get("result_description", "Identity verification requirements not met")
            
        except Exception as e:
            logger.error(f"Error extracting rejection reason: {e}")
            return "Identity verification failed"

    async def get_verification_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get current KYC verification status for a user
        Returns detailed status information for frontend display
        """
        try:
            user_profile = await self.db_service.get_user_profile_by_id(user_id)
            if not user_profile:
                raise HTTPException(status_code=404, detail="User profile not found")
            
            kyc_status = user_profile.get("kyc_status", "not_started")
            kyc_level = user_profile.get("kyc_level", 0)
            access_level = user_profile.get("access_level", "restricted")
            
            # Get latest KYC session if exists
            kyc_session = await self.db_service.get_latest_kyc_session(user_id)
            
            status_info = {
                "user_id": user_id,
                "kyc_status": kyc_status,
                "kyc_level": kyc_level,
                "access_level": access_level,
                "can_trade": kyc_level >= 2,
                "can_withdraw": kyc_level >= 2,
                "verification_initiated_at": user_profile.get("kyc_initiated_at"),
                "verification_completed_at": user_profile.get("kyc_completed_at"),
                "rejection_reason": user_profile.get("kyc_rejection_reason")
            }
            
            if kyc_session:
                status_info["session_id"] = kyc_session.get("session_id")
                status_info["applicant_id"] = kyc_session.get("applicant_id")
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting verification status for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get verification status")

    async def retry_failed_verification(self, user_id: str) -> Dict[str, Any]:
        """
        Allow users to retry KYC verification after rejection
        Creates a new verification session
        """
        try:
            user_profile = await self.db_service.get_user_profile_by_id(user_id)
            if not user_profile:
                raise HTTPException(status_code=404, detail="User profile not found")
            
            current_status = user_profile.get("kyc_status")
            if current_status not in ["rejected", "failed"]:
                return {
                    "success": False,
                    "error": f"Cannot retry verification. Current status: {current_status}",
                    "kyc_status": current_status
                }
            
            # Reset user status and start new verification
            await self.db_service.update_user_kyc_status(user_id, "not_started", 0)
            
            # Start new verification session
            email = user_profile.get("email")
            country_code = user_profile.get("country_code", "US")
            
            result = await self.start_verification_session(user_id, email, country_code)
            
            await self.audit.log_event(
                AuditEventType.KYC_RETRY,
                user_id=user_id,
                details={
                    "previous_status": current_status,
                    "retry_initiated": True
                },
                severity="info"
            )
            
            logger.info(f"🔄 KYC verification retry initiated for user {user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrying verification for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retry verification")

    async def skip_verification(self, user_id: str, admin_override: bool = False) -> Dict[str, Any]:
        """
        Skip KYC verification (for testing or special cases)
        Sets user to limited access without full verification
        """
        try:
            if not admin_override:
                # Check if skipping is allowed (e.g., during beta testing)
                skip_allowed = getattr(self.settings, 'ALLOW_KYC_SKIP', False)
                if not skip_allowed:
                    raise HTTPException(status_code=403, detail="KYC verification cannot be skipped")
            
            user_profile = await self.db_service.get_user_profile_by_id(user_id)
            if not user_profile:
                raise HTTPException(status_code=404, detail="User profile not found")
            
            # Update user status to skipped with limited access
            await self.db_service.update_user_kyc_status(user_id, "skipped", 1)
            await self.db_service.update_user_access_level(user_id, "limited")
            
            # Mark as skipped in profile
            await self.db_service.update_user_verification_skipped(user_id, True)
            
            await self.audit.log_event(
                AuditEventType.KYC_SKIPPED,
                user_id=user_id,
                details={
                    "admin_override": admin_override,
                    "access_level": "limited",
                    "kyc_level": 1
                },
                severity="warning"
            )
            
            logger.warning(f"⚠️ KYC verification SKIPPED for user {user_id} (admin_override: {admin_override})")
            
            return {
                "success": True,
                "message": "KYC verification skipped",
                "kyc_status": "skipped",
                "access_level": "limited",
                "kyc_level": 1
            }
            
        except Exception as e:
            logger.error(f"Error skipping verification for user {user_id}: {e}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail="Failed to skip verification")

    async def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired KYC sessions (older than 24 hours with pending status)
        Returns number of sessions cleaned up
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            expired_sessions = await self.db_service.get_expired_kyc_sessions(cutoff_time)
            
            cleanup_count = 0
            for session in expired_sessions:
                user_id = session.get("user_id")
                
                # Reset user status if still pending
                user_profile = await self.db_service.get_user_profile_by_id(str(user_id))
                if user_profile and user_profile.get("kyc_status") == "pending":
                    await self.db_service.update_user_kyc_status(str(user_id), "not_started", 0)
                
                # Archive the session
                await self.db_service.archive_kyc_session(session.get("id"))
                cleanup_count += 1
            
            if cleanup_count > 0:
                logger.info(f"🧹 Cleaned up {cleanup_count} expired KYC sessions")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Error during KYC session cleanup: {e}")
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for KYC service
        Returns service status and provider connectivity
        """
        try:
            status = {
                "service": "healthy",
                "provider": "not_configured",
                "database": "unknown"
            }
            
            # Check provider connectivity
            if self.provider:
                try:
                    provider_status = await self.provider.health_check()
                    status["provider"] = "healthy" if provider_status else "unhealthy"
                except Exception as e:
                    status["provider"] = f"error: {str(e)}"
            
            # Check database connectivity
            try:
                await self.db_service.test_connection()
                status["database"] = "healthy"
            except Exception as e:
                status["database"] = f"error: {str(e)}"
            
            return status
            
        except Exception as e:
            logger.error(f"Error during KYC service health check: {e}")
            return {"service": "unhealthy", "error": str(e)}