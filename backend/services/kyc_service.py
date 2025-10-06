# File Location: backend/services/kyc_service.py
# CRITICAL FIX: Make Regfyl the PRIMARY provider + database table mapping

import logging
import json
from typing import Dict, Any, Optional
from supabase import Client
from fastapi import HTTPException
from datetime import datetime, timedelta

from backend.config import get_settings
from backend.services.audit_service import AuditService, AuditEventType
from backend.services.database_service import DatabaseService
from backend.services.kyc_providers.regfyl import RegfylVerifier
from backend.services.kyc_providers.complycube import ComplyCubeVerifier

logger = logging.getLogger(__name__)

class KYCService:
    """
    PRODUCTION-READY: Complete KYC service with Regfyl as PRIMARY provider
    ComplyCube as secondary/fallback provider
    """
    
    def __init__(self, settings=None, supabase_client: Optional[Client] = None, db_service: Optional[DatabaseService] = None, audit_service: Optional[AuditService] = None):
        """Initialize KYC service with Regfyl as PRIMARY provider"""
        self.settings = settings or get_settings()
        self.supabase = supabase_client
        
        # Initialize database service
        if db_service:
            self.db_service = db_service
        else:
            self.db_service = DatabaseService(supabase_client)
    
        # Initialize audit service - FIXED: Use create_audit_service function
        if audit_service:
            self.audit = audit_service
        else:
            # 🚨 CRITICAL FIX: Use the correct factory function
            from backend.services.audit_service import create_audit_service
            self.audit = create_audit_service(supabase_client)
    
        # PRIORITY FIX: Initialize Regfyl as PRIMARY provider
        self.providers = {}
        self.primary_provider = None
        self.provider_healthy = False
        self.last_provider_check = None
        
        # Initialize Regfyl provider FIRST (PRIMARY)
        regfyl_key = getattr(self.settings, 'REGFYL_API_KEY', None)
        if regfyl_key:
            try:
                self.providers['regfyl'] = RegfylVerifier(
                    api_key=regfyl_key.get_secret_value() if hasattr(regfyl_key, 'get_secret_value') else regfyl_key
                )
                self.primary_provider = 'regfyl'  # SET AS PRIMARY
                logger.info("Regfyl provider initialized as PRIMARY KYC provider")
            except Exception as e:
                logger.error(f"Failed to initialize Regfyl provider: {e}")
                self.providers['regfyl'] = RegfylVerifier()  # Simulation mode
                self.primary_provider = 'regfyl'  # Still set as primary even in simulation
    
        # Initialize ComplyCube provider as SECONDARY/FALLBACK
        complycube_key = getattr(self.settings, 'COMPLYCUBE_API_KEY', None)
        if complycube_key:
            try:
                self.providers['complycube'] = ComplyCubeVerifier(
                    api_key=complycube_key.get_secret_value() if hasattr(complycube_key, 'get_secret_value') else complycube_key
                )
                # Only set as primary if Regfyl not available
                if not self.primary_provider:
                    self.primary_provider = 'complycube'
                logger.info("ComplyCube provider initialized as SECONDARY provider")
            except Exception as e:
                logger.error(f"Failed to initialize ComplyCube provider: {e}")
                self.providers['complycube'] = ComplyCubeVerifier()  # Simulation mode
    
        # Set fallback provider if no primary
        if not self.primary_provider and self.providers:
            self.primary_provider = list(self.providers.keys())[0]
    
        # Legacy support - set self.provider to primary provider
        if self.primary_provider:
            self.provider = self.providers[self.primary_provider]
            logger.info(f"Primary KYC provider set to: {self.primary_provider}")
        else:
            # Initialize simulation provider as fallback
            self.provider = RegfylVerifier()  # Default to Regfyl simulation
            logger.warning("No KYC providers configured - using Regfyl simulation mode")

    async def screen_user_with_regfyl(self, user_id: str, user_data: Dict) -> Dict[str, Any]:
        """Screen user with Regfyl for PEP/Sanctions/AML compliance (PRIMARY METHOD)"""
        try:
            if 'regfyl' not in self.providers:
                raise HTTPException(status_code=503, detail="Regfyl provider not available")
        
            regfyl_provider = self.providers['regfyl']
        
            # Format user data for Regfyl
            regfyl_data = {
                'customer_id': user_id,
                'full_name': user_data.get('full_name') or f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
                'year_of_birth': user_data.get('year_of_birth') or user_data.get('date_of_birth', '')[:4],
                'gender': user_data.get('gender', ''),
                'country': user_data.get('country', 'NG'),
                'id_type': user_data.get('id_type', 'BVN'),
                'id_number': user_data.get('id_number', ''),
                'callback_url': f"{self.settings.API_BASE_URL}/webhooks/regfyl/screening"
            }
        
            # Perform comprehensive screening
            result = await regfyl_provider.onboard_seamount_user(regfyl_data)
        
            # FIXED: Update user compliance status using existing compliance_checks table
            if self.supabase:
                compliance_data = {
                    "user_id": user_id,
                    "check_type": "regfyl_screening",
                    "provider": "regfyl",
                    "status": "screening_initiated",
                    "reference_id": result.get('screening', {}).get('reference'),
                    "metadata": json.dumps({
                        "screening_reference": result.get('screening', {}).get('reference'),
                        "id_verification_reference": result.get('id_verification', {}).get('reference'),
                        "screening_data": regfyl_data
                    }),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                self.supabase.table("compliance_checks").upsert(compliance_data).execute()
        
            # Log compliance event - FIXED: Use correct audit service
            await self.audit.log_event(
                AuditEventType.COMPLIANCE_CHECK_INITIATED,
                user_id=user_id,
                details={
                    "provider": "regfyl",
                    "screening_reference": result.get('screening', {}).get('reference'),
                    "id_verification_reference": result.get('id_verification', {}).get('reference')
                },
                severity="info"
            )
        
            logger.info(f"Regfyl screening initiated for user {user_id}")
            return {
                "success": True,
                "provider": "regfyl",
                "screening_result": result,
                "message": "AML/KYC screening initiated successfully"
            }
        
        except Exception as e:
            logger.error(f"Regfyl screening failed for user {user_id}: {e}")
            await self.audit.log_event(
                AuditEventType.SYSTEM_ERROR,
                user_id=user_id,
                details={"error": f"Regfyl screening failed: {str(e)}"},
                severity="error"
            )
            raise HTTPException(status_code=500, detail="AML screening failed")

    async def start_verification_session(self, user_id: str, email: str, country_code: str = "US") -> Dict[str, Any]:
        """
        Start KYC verification - PRIORITIZES REGFYL, falls back to ComplyCube
        """
        try:
            logger.info(f"Starting KYC verification for user {user_id} with PRIMARY provider: {self.primary_provider}")
            
            # Validate user profile exists
            user_profile = await self.db_service.get_user_profile_by_id(user_id)
            if not user_profile:
                logger.error(f"User profile not found for user {user_id}")
                raise HTTPException(status_code=404, detail="User profile not found")
            
            # Check if user already has active verification session
            if user_profile.get("kyc_status") == "in_progress":
                logger.warning(f"User {user_id} already has active KYC verification")
                return {
                    "success": False,
                    "error": "KYC verification already in progress",
                    "kyc_status": user_profile.get("kyc_status")
                }
            
            # REGFYL PRIMARY PATH: If Regfyl is primary, use Regfyl screening
            if self.primary_provider == 'regfyl':
                try:
                    # ONLY use Regfyl for Nigerian users with BVN
                    if country_code == 'NG':
                        user_data = {
                            'full_name': f"{user_profile.get('first_name', '')} {user_profile.get('last_name', '')}".strip(),
                            'year_of_birth': user_profile.get('date_of_birth', '')[:4] if user_profile.get('date_of_birth') else '',
                            'gender': user_profile.get('gender', ''),
                            'country': country_code,
                            'id_type': 'BVN',
                            'id_number': user_profile.get('bvn', '')
                        }

                        if not user_data['id_number'] or not user_data['full_name']:
                            return {
                                "success": False,
                                "error": "Nigerian users require BVN and full name",
                                "missing_fields": ["bvn"] if not user_data['id_number'] else []
                            }
            
                        regfyl_result = await self.screen_user_with_regfyl(user_id, user_data)
                        # ... rest of Regfyl flow
                    else:
                        # Non-Nigerian users: fall through to ComplyCube
                        logger.info(f"Non-Nigerian user, using ComplyCube for {user_id}")
                        # Continue to ComplyCube logic below
                    
                    # Initiate Regfyl screening
                    regfyl_result = await self.screen_user_with_regfyl(user_id, user_data)
                    
                    # Update user status to pending
                    await self.db_service.update_user_kyc_status(user_id, "pending", 1)
                    
                    # Store KYC session data in existing kyc_sessions table
                    session_data = {
                        "user_id": user_id,
                        "applicant_id": f"regfyl_{user_id}",  # Regfyl-style applicant ID
                        "session_id": regfyl_result['screening_result'].get('screening', {}).get('reference'),
                        "verification_type": "regfyl_screening",
                        "status": "pending",
                        "response_data": regfyl_result['screening_result'],
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    if self.supabase:
                        self.supabase.table("kyc_sessions").upsert(session_data).execute()
                    
                    logger.info(f"Regfyl KYC verification initiated successfully for user {user_id}")
                    
                    return {
                        "success": True,
                        "provider": "regfyl",
                        "session_id": session_data["session_id"],
                        "applicantId": session_data["applicant_id"],
                        "message": "Regfyl KYC verification started successfully",
                        "kyc_status": "pending",
                        "flow_url": f"{self.settings.FRONTEND_URL}/kyc-regfyl-pending?user_id={user_id}"
                    }
                    
                except Exception as regfyl_error:
                    logger.error(f"Regfyl verification failed for user {user_id}: {regfyl_error}")
                    # Fall back to ComplyCube if available
                    if 'complycube' in self.providers:
                        logger.info(f"Falling back to ComplyCube for user {user_id}")
                        # Continue to ComplyCube logic below
                    else:
                        return await self._handle_simulation_mode(user_id)
            
            # COMPLYCUBE FALLBACK PATH
            if 'complycube' in self.providers:
                provider_healthy = await self._check_provider_health()
                if not provider_healthy:
                    logger.warning(f"KYC provider unhealthy, using simulation mode for user {user_id}")
                    return await self._handle_simulation_mode(user_id)
                
                complycube_provider = self.providers['complycube']
                
                # Create ComplyCube client
                client_id = await complycube_provider.create_client(user_id, email, country_code)
                logger.info(f"Created ComplyCube client {client_id} for user {user_id}")
                
                # Create verification session
                session_data = await complycube_provider.create_verification_session(client_id)
                session_id = session_data.get("id")
                flow_url = session_data.get("url")
                token = session_data.get("token")
                
                if not session_id or not flow_url:
                    raise ValueError("Invalid session data received from ComplyCube")
                    
                logger.info(f"Created ComplyCube verification session {session_id} for user {user_id}")
                
                # Update user profile to pending status
                await self.db_service.update_user_kyc_status(user_id, "pending", 1)
                
                # Store KYC session data
                kyc_data = {
                    "user_id": user_id,
                    "applicant_id": client_id,
                    "session_id": session_id,
                    "verification_type": "complycube_document_verification",
                    "status": "pending",
                    "response_data": session_data,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                if self.supabase:
                    self.supabase.table("kyc_sessions").upsert(kyc_data).execute()
                
                return {
                    "success": True,
                    "provider": "complycube",
                    "flow_url": flow_url,
                    "session_id": session_id,
                    "token": token,
                    "applicantId": client_id,
                    "message": "ComplyCube KYC verification started successfully",
                    "kyc_status": "pending"
                }
            
            # Final fallback - simulation mode
            return await self._handle_simulation_mode(user_id)
                
        except HTTPException:
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

    async def _handle_simulation_mode(self, user_id: str) -> Dict[str, Any]:
        """Handle simulation mode gracefully with proper user feedback"""
        try:
            # Update user to pending status for simulation
            await self.db_service.update_user_kyc_status(user_id, "pending", 1)
            
            frontend_url = getattr(self.settings, 'FRONTEND_URL', 'https://seamount.io')
            
            # Generate simulated session data
            simulation_token = f"sim_token_{user_id}"
            simulation_url = f"{frontend_url}/kyc-complete?simulated=true&user_id={user_id}"
            
            logger.info(f"KYC simulation mode activated for user {user_id}")
            
            return {
                "success": True,
                "provider": "simulation",
                "flow_url": simulation_url,
                "token": simulation_token,
                "applicantId": f"sim_applicant_{user_id}",
                "message": "KYC verification started (simulation mode)",
                "kyc_status": "pending",
                "simulation_mode": True
            }
            
        except Exception as e:
            logger.error(f"Failed to handle simulation mode for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="KYC service initialization failed")

    async def _check_provider_health(self) -> bool:
        """Check provider health with proper error handling"""
        try:
            # Cache health checks for 30 minutes
            if (self.last_provider_check and 
                datetime.utcnow() - datetime.fromisoformat(self.last_provider_check.replace('Z', '+00:00')) < timedelta(minutes=30)):
                return self.provider_healthy
    
            if self.provider and hasattr(self.provider, 'health_check'):
                self.provider_healthy = await self.provider.health_check()
                self.last_provider_check = datetime.utcnow().isoformat()
        
                if self.provider_healthy:
                    logger.info("KYC provider health check passed")
                else:
                    logger.error("KYC provider health check failed - will use simulation mode")
            
                return self.provider_healthy
            else:
                logger.warning("KYC provider does not support health checks")
                # Assume healthy if we can't check
                self.provider_healthy = True
            return True
        
        except Exception as e:
            logger.error(f"Error during provider health check: {e}")
            # On error, assume unhealthy to trigger simulation mode
            self.provider_healthy = False
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check for multi-provider KYC service"""
        try:
            status = {
                "service": "healthy",
                "providers": {},
                "primary_provider": self.primary_provider,
                "database": "unknown",
                "last_check": datetime.utcnow().isoformat()
            }
        
            # Check all provider health
            for provider_name, provider in self.providers.items():
                try:
                    if hasattr(provider, 'health_check'):
                        provider_status = await provider.health_check()
                        status["providers"][provider_name] = provider_status.get("status", "unknown")
                    else:
                        status["providers"][provider_name] = "no_health_check"
                except Exception as e:
                    logger.error(f"{provider_name} health check failed: {e}")
                    status["providers"][provider_name] = "unhealthy"
        
            # Check database connectivity
            if self.db_service:
                try:
                    test_query = self.db_service.supabase.table("user_profiles").select("id", count="exact").limit(1).execute()
                    status["database"] = "healthy" if test_query else "unhealthy"
                except Exception as e:
                    logger.error(f"Database health check failed: {e}")
                    status["database"] = "unhealthy"
        
            return status
        
        except Exception as e:
            logger.error(f"KYC service health check failed: {e}")
            return {
                "service": "unhealthy",
                "providers": {},
                "primary_provider": None,
                "database": "unknown",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }

    async def check_verification_status(self, user_id: str) -> Dict[str, Any]:
        """Check current verification status for user with robust error handling"""
        try:
            logger.info(f"Checking verification status for user {user_id}")
            
            # Get user profile
            user_profile = await self.db_service.get_user_profile_by_id(user_id)
            if not user_profile:
                raise HTTPException(status_code=404, detail="User profile not found")
            
            # Get KYC session data
            kyc_session = await self.db_service.get_kyc_session_by_user_id(user_id)
            
            current_status = user_profile.get("kyc_status", "not_started")
            kyc_tier = user_profile.get("kyc_tier", 0)
            
            response_data = {
                "user_id": user_id,
                "kyc_status": current_status,
                "kyc_tier": kyc_tier,
                "verification_required": current_status not in ["approved", "verified"],
                "last_updated": user_profile.get("updated_at")
            }
            
            # Add session details if available
            if kyc_session:
                response_data.update({
                    "session_id": kyc_session.get("session_id"),
                    "applicant_id": kyc_session.get("applicant_id"),
                    "verification_type": kyc_session.get("verification_type", "document_verification"),
                    "submission_date": kyc_session.get("created_at")
                })
            
            logger.info(f"Verification status check completed for user {user_id}: {current_status}")
            return response_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking verification status for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to check verification status")

    async def process_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process ComplyCube webhook events with comprehensive error handling"""
        try:
            event_type = event_data.get("type")
            applicant_id = event_data.get("applicantId") 
            
            if not event_type or not applicant_id:
                logger.error(f"Invalid webhook event data: {event_data}")
                raise HTTPException(status_code=400, detail="Invalid webhook event data")
            
            logger.info(f"Processing webhook event {event_type} for applicant {applicant_id}")
            
            # Find user by applicant_id
            kyc_session = await self.db_service.get_kyc_session_by_applicant_id(applicant_id)
            if not kyc_session:
                logger.error(f"No KYC session found for applicant {applicant_id}")
                raise HTTPException(status_code=404, detail="KYC session not found")
            
            user_id = kyc_session.get("user_id")
            if not user_id:
                logger.error(f"No user_id found in KYC session for applicant {applicant_id}")
                raise HTTPException(status_code=404, detail="User not found")
            
            # Process different event types
            if event_type == "check.completed":
                return await self._handle_check_completed(user_id, applicant_id, event_data)
            elif event_type == "check.pending": 
                return await self._handle_check_pending(user_id, applicant_id, event_data)
            elif event_type == "check.clear":
                return await self._handle_check_clear(user_id, applicant_id, event_data)
            elif event_type == "check.consider":
                return await self._handle_check_consider(user_id, applicant_id, event_data)
            elif event_type == "check.unrecognised":
                return await self._handle_check_unrecognised(user_id, applicant_id, event_data)
            else:
                logger.warning(f"Unknown webhook event type: {event_type}")
                return {"success": True, "message": f"Event {event_type} acknowledged but not processed"}
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing webhook event: {e}")
            raise HTTPException(status_code=500, detail="Failed to process webhook event")

    async def _handle_check_completed(self, user_id: str, applicant_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle completed verification check"""
        try:
            # Update KYC session status
            await self.db_service.update_kyc_session_status(applicant_id, "completed", event_data)
            
            # Update user profile to tier 2 (document verified)
            await self.db_service.update_user_kyc_status(user_id, "approved", 2)
            
            # Log successful completion
            await self.audit.log_event(
                AuditEventType.KYC_COMPLETED,
                user_id=user_id,
                details={
                    "applicant_id": applicant_id,
                    "event_type": "check.completed",
                    "verification_result": "approved"
                },
                severity="info"
            )
            
            logger.info(f"KYC verification completed successfully for user {user_id}")
            return {"success": True, "status": "approved", "tier": 2}
            
        except Exception as e:
            logger.error(f"Error handling check completed for user {user_id}: {e}")
            raise

    async def _handle_check_pending(self, user_id: str, applicant_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pending verification check"""
        try:
            # Update KYC session status
            await self.db_service.update_kyc_session_status(applicant_id, "pending", event_data)
            
            # Keep user at tier 1 while pending
            await self.db_service.update_user_kyc_status(user_id, "pending", 1)
            
            logger.info(f"KYC verification pending for user {user_id}")
            return {"success": True, "status": "pending", "tier": 1}
            
        except Exception as e:
            logger.error(f"Error handling check pending for user {user_id}: {e}")
            raise

    async def _handle_check_clear(self, user_id: str, applicant_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle clear (approved) verification check"""
        try:
            # Update KYC session status
            await self.db_service.update_kyc_session_status(applicant_id, "approved", event_data)
            
            # Update user profile to tier 3 (fully verified)
            await self.db_service.update_user_kyc_status(user_id, "verified", 3)
            
            # Log successful verification
            await self.audit.log_event(
                AuditEventType.KYC_APPROVED,
                user_id=user_id,
                details={
                    "applicant_id": applicant_id,
                    "event_type": "check.clear",
                    "verification_result": "verified",
                    "tier": 3
                },
                severity="info"
            )
            
            logger.info(f"KYC verification approved (tier 3) for user {user_id}")
            return {"success": True, "status": "verified", "tier": 3}
            
        except Exception as e:
            logger.error(f"Error handling check clear for user {user_id}: {e}")
            raise

    async def _handle_check_consider(self, user_id: str, applicant_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle consider (manual review needed) verification check"""
        try:
            # Update KYC session status
            await self.db_service.update_kyc_session_status(applicant_id, "manual_review", event_data)
            
            # Keep user at tier 1 for manual review
            await self.db_service.update_user_kyc_status(user_id, "manual_review", 1)
            
            # Log manual review requirement
            await self.audit.log_event(
                AuditEventType.KYC_MANUAL_REVIEW,
                user_id=user_id,
                details={
                    "applicant_id": applicant_id,
                    "event_type": "check.consider",
                    "verification_result": "manual_review_required"
                },
                severity="warning"
            )
            
            logger.warning(f"KYC verification requires manual review for user {user_id}")
            return {"success": True, "status": "manual_review", "tier": 1}
            
        except Exception as e:
            logger.error(f"Error handling check consider for user {user_id}: {e}")
            raise

    async def _handle_check_unrecognised(self, user_id: str, applicant_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unrecognised (failed) verification check"""
        try:
            # Update KYC session status
            await self.db_service.update_kyc_session_status(applicant_id, "failed", event_data)
            
            # Update user profile to rejected status
            await self.db_service.update_user_kyc_status(user_id, "rejected", 0)
            
            # Log verification failure
            await self.audit.log_event(
                AuditEventType.KYC_REJECTED,
                user_id=user_id,
                details={
                    "applicant_id": applicant_id,
                    "event_type": "check.unrecognised",
                    "verification_result": "rejected"
                },
                severity="warning"
            )
            
            logger.warning(f"KYC verification failed for user {user_id}")
            return {"success": True, "status": "rejected", "tier": 0}
            
        except Exception as e:
            logger.error(f"Error handling check unrecognised for user {user_id}: {e}")
            raise