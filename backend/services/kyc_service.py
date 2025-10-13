# File Location: backend/services/kyc_service.py
# COMPLETE FIX: Regfyl-only KYC service with proper error handling

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

logger = logging.getLogger(__name__)

class KYCService:
    """
    PRODUCTION-READY: Complete KYC service with Regfyl as ONLY provider
    """
    
    def __init__(self, settings=None, supabase_client: Optional[Client] = None, db_service: Optional[DatabaseService] = None, audit_service: Optional[AuditService] = None):
        """Initialize KYC service with Regfyl as ONLY provider"""
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
            from backend.services.audit_service import create_audit_service
            self.audit = create_audit_service(supabase_client)
    
        # Initialize Regfyl as ONLY provider
        self.providers = {}
        self.primary_provider = None
        
        # Initialize Regfyl provider
        regfyl_key = getattr(self.settings, 'REGFYL_API_KEY', None)
        if regfyl_key:
            try:
                self.providers['regfyl'] = RegfylVerifier(
                    api_key=regfyl_key.get_secret_value() if hasattr(regfyl_key, 'get_secret_value') else regfyl_key
                )
                self.primary_provider = 'regfyl'
                logger.info("Regfyl provider initialized as PRIMARY KYC provider")
            except Exception as e:
                logger.error(f"Failed to initialize Regfyl provider: {e}")
                self.providers['regfyl'] = RegfylVerifier()
                self.primary_provider = 'regfyl'
        else:
            logger.warning("Regfyl API key not configured - using simulation mode")
            self.providers['regfyl'] = RegfylVerifier()
            self.primary_provider = 'regfyl'

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
        
            # Save compliance data with proper error handling
            if self.supabase:
                try:
                    compliance_data = {
                        "user_id": user_id,
                        "check_type": "regfyl_screening",
                        "provider": "regfyl", 
                        "status": "screening_initiated",
                        "external_reference": result.get('screening', {}).get('reference'),
                        "metadata": {
                            "screening_reference": result.get('screening', {}).get('reference'),
                            "id_verification_reference": result.get('id_verification', {}).get('reference'),
                            "screening_data": regfyl_data
                        },
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    self.supabase.table("compliance_checks").upsert(compliance_data).execute()
                    
                except Exception as db_error:
                    logger.warning(f"Could not save to compliance_checks: {db_error}")
                    # Don't fail the entire process - just log and continue
        
            # Log compliance event
            try:
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
            except Exception as audit_error:
                logger.warning(f"Could not log audit event: {audit_error}")
        
            logger.info(f"Regfyl screening initiated for user {user_id}")
            return {
                "success": True,
                "provider": "regfyl", 
                "screening_result": result,
                "message": "AML/KYC screening initiated successfully"
            }
        
        except Exception as e:
            logger.error(f"Regfyl screening failed for user {user_id}: {e}")
            
            try:
                await self.audit.log_event(
                    AuditEventType.SYSTEM_ERROR,
                    user_id=user_id, 
                    details={"error": f"Regfyl screening failed: {str(e)}"},
                    severity="error"
                )
            except Exception:
                logger.error("Failed to log audit event for screening failure")
                
            raise HTTPException(status_code=500, detail="AML screening failed")

    async def start_verification_session(self, user_id: str, email: str, country_code: str = "US") -> Dict[str, Any]:
        """
        Start KYC verification using Regfyl for ALL users
        COMPLETELY REMOVES COMPLYCUBE LOGIC
        """
        try:
            logger.info(f"Starting KYC verification for user {user_id}, country: {country_code} - USING REGFYL")
            
            # 1. Validate user profile exists
            user_profile = await self.db_service.get_user_profile_by_id(user_id)
            if not user_profile:
                logger.error(f"User profile not found for user {user_id}")
                raise HTTPException(status_code=404, detail="User profile not found")
            
            # 2. Check for existing verification session - ALLOW RESTART IF NOT_STARTED OR REJECTED
            current_status = user_profile.get("kyc_status", "not_started")
            if current_status in ["approved", "verified", "in_progress"]:
                logger.warning(f"User {user_id} already has KYC status: {current_status}")
                return {
                    "success": False,
                    "error": f"KYC verification already {current_status}",
                    "kyc_status": current_status
                }
            
            # 3. FORCE REGFYL FOR ALL USERS - COMPLETELY REMOVE COMPLYCUBE FALLBACK
            if self.primary_provider == 'regfyl' and 'regfyl' in self.providers:
                # CRITICAL: Refresh profile from DB to get modal data
                fresh_profile = await self.db_service.get_user_profile_by_id(user_id)
                logger.info(f"[DEBUG] Fresh profile keys: {fresh_profile.keys() if fresh_profile else 'None'}")
                logger.info(f"[DEBUG] Fresh profile id_number: {fresh_profile.get('id_number') if fresh_profile else 'None'}")
                if not fresh_profile:
                    raise HTTPException(status_code=404, detail="Profile not found")
                return await self._start_regfyl_verification(user_id, fresh_profile, country_code)
            else:
                logger.error("REGFYL PROVIDER NOT CONFIGURED - NO FALLBACK TO COMPLYCUBE")
                raise HTTPException(status_code=503, detail="Verification service unavailable")
                
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error in start_verification_session: {e}")
            raise HTTPException(status_code=500, detail="KYC service unavailable")

    async def _start_regfyl_verification(self, user_id: str, user_profile: Dict, country_code: str) -> Dict[str, Any]:
        """Use RAW profile - don't re-fetch with formatter"""
        try:
            callback_url = f"{self.settings.API_BASE_URL}/webhooks/regfyl/screening"
            
            # ✅ FIX: Fetch UNFILTERED profile with ALL fields
            raw_profile = await self.db_service.get_user_profile_raw(user_id)
            if not raw_profile:
                raise HTTPException(status_code=404, detail="Profile not found")
            
            # Extract fields from raw profile
            bvn = (raw_profile.get('bvn') or '').strip()
            id_number = (raw_profile.get('id_number') or '').strip()
            id_type = (raw_profile.get('id_type') or 'NATIONAL_ID').strip()
            gender = (raw_profile.get('gender') or '').strip()
            dob = raw_profile.get('date_of_birth') or ''
            
            final_id = bvn or id_number
            
            logger.info(f"[Regfyl DEBUG] Raw profile: bvn={bool(bvn)}, id_number={bool(id_number)}, gender={gender}, dob={dob[:10] if dob else 'N/A'}")
            
            if not final_id:
                logger.error(f"[Regfyl] NO ID found for user {user_id}")
                raise HTTPException(status_code=400, detail="ID number required for verification")
            
            # Build payload
            user_data = {
                'customer_id': user_id,
                'full_name': f"{raw_profile.get('first_name', '')} {raw_profile.get('last_name', '')}".strip(),
                'year_of_birth': dob[:4] if dob else '2000',
                'gender': gender,
                'country': country_code,
                'id_type': id_type,
                'id_number': final_id,
                'callback_url': callback_url
            }
            
            logger.info(f"[Regfyl] ✅ Sending {id_type}: {final_id[:3]}*** for user {user_id}")
            logger.info(f"[Regfyl] FULL user_data DICT:\n{json.dumps(user_data, indent=2)}")
            
            # Submit to Regfyl - bypass wrapper, call provider directly
            regfyl_provider = self.providers['regfyl']
            screening_result = await regfyl_provider.onboard_seamount_user(user_data)
            
            # Check if country not supported yet
            id_verification = screening_result.get('id_verification', {})
            if id_verification.get('status') == 'pending_country_support':
                # Allow user to proceed without full verification
                logger.warning(f"[KYC] Country {country_code} not yet supported - granting limited access")
                await self.db_service.update_user_kyc_status(user_id, "pending", 1)
                
                return {
                    "success": True,
                    "provider": "regfyl",
                    "status": "pending_country_support",
                    "message": id_verification.get('message', 'ID verification will be available soon'),
                    "country": country_code,
                    "can_proceed": True,
                    "next_step": "wallet_creation"
                }
            
            # Update KYC status
            await self.db_service.update_user_kyc_status(user_id, "pending", 1)
            
            # Log session
            if self.supabase:
                try:
                    self.supabase.table("kyc_sessions").upsert({
                        "user_id": user_id,
                        "applicant_id": f"regfyl_{user_id}",
                        "session_id": screening_result.get('screening', {}).get('reference'),
                        "verification_type": "regfyl_screening",
                        "status": "pending",
                        "response_data": screening_result,
                        "created_at": datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    logger.warning(f"Session save: {e}")
            
            return {
                "success": True,
                "provider": "regfyl",
                "session_id": screening_result.get('screening', {}).get('reference'),
                "applicantId": f"regfyl_{user_id}",
                "message": "Verification submitted successfully",
                "status": "pending",
                "next_step": "await_review"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Regfyl failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    async def health_check(self) -> Dict[str, Any]:
        """Health check for KYC service"""
        try:
            status = {
                "service": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "primary_provider": self.primary_provider,
                "provider_status": "unknown",
                "database_status": "unknown"
            }
            
            # Check provider
            if self.primary_provider and self.primary_provider in self.providers:
                provider = self.providers[self.primary_provider]
                if hasattr(provider, 'health_check'):
                    try:
                        provider_status = await provider.health_check()
                        status["provider_status"] = provider_status.get("status", "unknown")
                    except Exception as e:
                        status["provider_status"] = f"error: {str(e)}"
                        status["service"] = "degraded"
                else:
                    status["provider_status"] = "no_health_check"
            else:
                status["provider_status"] = "no_provider"
                status["service"] = "unhealthy"
            
            # Check database
            if self.supabase:
                try:
                    result = self.supabase.table("user_profiles").select("id", count="exact").limit(1).execute()
                    status["database_status"] = "healthy" if result else "unhealthy"
                except Exception as e:
                    status["database_status"] = f"error: {str(e)}"
                    status["service"] = "unhealthy"
            
            return status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "service": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }