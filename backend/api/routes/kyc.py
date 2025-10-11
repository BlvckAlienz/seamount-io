# File Location: backend/api/routes/kyc.py
# TRANSFORMATION FIX: Regfyl as PRIMARY provider + proper error handling

import logging
import hmac
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request
from supabase import Client
from typing import Dict, Any, Optional, List
import traceback
import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user, get_supabase_client, get_kyc_service
from backend.services.kyc_service import KYCService
from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

class RegfylScreeningRequest(BaseModel):
    """Request model for Regfyl screening"""
    full_name: str = Field(..., description="User's full legal name")
    year_of_birth: str = Field(..., description="Year of birth (YYYY format)")
    gender: Optional[str] = Field(None, description="Gender (M/F/Other)")
    country: str = Field(default="NG", description="Country code (ISO 2-letter)")
    id_type: str = Field(..., description="ID type (BVN/NIN/PHONE_NUMBER)")
    id_number: str = Field(..., description="ID number for verification")

@router.get("/profile-check")
async def check_profile_completeness(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """Check if user profile is complete for KYC"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        logger.info(f"[KYC Profile Check] User: {user_id}")
        
        profile = current_user
        required_fields = ['first_name', 'last_name', 'email']
        missing_fields = []
        
        for field in required_fields:
            field_value = profile.get(field)
            if not field_value or (isinstance(field_value, str) and field_value.strip() == ""):
                missing_fields.append(field)
        
        email = profile.get('email', '').strip()
        if email and '@' not in email:
            missing_fields.append('email')
        
        profile_complete = len(missing_fields) == 0
        kyc_status = profile.get('kyc_status', 'not_started')
        
        return {
            "profile_complete": profile_complete,
            "missing_fields": missing_fields,
            "can_start_kyc": profile_complete,
            "kyc_status": kyc_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[KYC Profile Check] Error: {str(e)}")
        return {
            "profile_complete": False,
            "missing_fields": ["first_name", "last_name", "email"],
            "can_start_kyc": False,
            "kyc_status": "not_started"
        }

@router.post("/submit-kyc-data")
async def submit_kyc_data(
    request: Request,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    Store user KYC data BEFORE starting verification
    """
    try:
        user_id = current_user.get('id')
        data = await request.json()
        
        logger.info(f"[KYC Data Submit] User: {user_id}, Data: {data}")
        
        # Update user profile with KYC data
        update_data = {
            'bvn': data.get('bvn'),
            'id_number': data.get('bvn'),  # Store as id_number too
            'id_type': data.get('id_type', 'BVN'),
            'date_of_birth': data.get('date_of_birth'),
            'gender': data.get('gender'),
            'phone': data.get('phone'),
            'country_code': data.get('country_code', 'NG'),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('user_profiles').update(update_data).eq('id', user_id).execute()
        
        logger.info(f"[KYC Data Submit] Data stored for user {user_id}")
        
        return {
            "success": True,
            "message": "KYC data stored successfully"
        }
        
    except Exception as e:
        logger.error(f"[KYC Data Submit] Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to store KYC data")

@router.post("/start-verification")
async def start_kyc_verification(
    current_user: dict = Depends(get_current_user),
    kyc_service: KYCService = Depends(get_kyc_service),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """Start KYC verification - DIAGNOSTIC VERSION"""
    try:
        user_id = current_user.get('id')
        logger.info(f"[KYC] Starting verification for user: {user_id}")
        logger.info(f"[KYC] User data: {current_user}")
        
        # Simple validation
        if not current_user.get('first_name') or not current_user.get('last_name'):
            raise HTTPException(status_code=400, detail="Name required")
        
        # Try to start verification
        try:
            result = await kyc_service.start_verification_session(
                user_id,
                current_user.get('email'),
                current_user.get('country_code', 'US')
            )
            
            logger.info(f"[KYC] Verification result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[KYC] Service error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Service error: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[KYC] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/webhook")
async def kyc_webhook_handler(
    request: Request,
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    TRANSFORMATION FIX: Unified webhook handler for Regfyl + ComplyCube
    """
    try:
        # Verify webhook signature if secret is configured
        webhook_secret = settings.REGFYL_WEBHOOK_SECRET
        if webhook_secret:
            signature_header = request.headers.get('X-Webhook-Signature')
            if signature_header:
                body = await request.body()
                
                # Verify signature
                try:
                    signature_data = {}
                    for part in signature_header.split(','):
                        if '=' in part:
                            key, value = part.split('=', 1)
                            signature_data[key] = value
                    
                    timestamp = signature_data.get('t')
                    signature = signature_data.get('v1')
                    
                    if timestamp and signature:
                        current_time = int(datetime.utcnow().timestamp())
                        if current_time - int(timestamp) > 300:
                            raise HTTPException(status_code=401, detail="Timestamp too old")
                        
                        signed_payload = f"{timestamp}.{body.decode('utf-8')}"
                        expected_signature = hmac.new(
                            webhook_secret.get_secret_value().encode('utf-8') if hasattr(webhook_secret, 'get_secret_value') else webhook_secret.encode('utf-8'),
                            signed_payload.encode('utf-8'),
                            hashlib.sha256
                        ).hexdigest()
                        
                        if not hmac.compare_digest(signature, expected_signature):
                            raise HTTPException(status_code=401, detail="Invalid signature")
                            
                    logger.info("Webhook signature verified")
                    
                except (ValueError, AttributeError) as e:
                    logger.error(f"Signature verification failed: {str(e)}")
                    raise HTTPException(status_code=401, detail="Invalid signature format")
        
        webhook_data = await request.json()
        logger.info(f"[KYC Webhook] Received: {webhook_data.get('type', 'unknown')}")
        
        # Extract user reference
        user_reference = webhook_data.get('user_reference') or webhook_data.get('reference') or webhook_data.get('clientId') or webhook_data.get('customer_id')
        status = webhook_data.get('status', 'unknown').lower()
        event_type = webhook_data.get('type', '').lower()
        
        if not user_reference:
            logger.error(f"[KYC Webhook] Missing user reference")
            raise HTTPException(status_code=400, detail="Missing user reference")
        
        # Map provider status to internal status
        status_mapping = {
            # Regfyl statuses
            'approved': 'verified',
            'completed': 'verified',
            'clear': 'verified',
            'passed': 'verified',
            # Pending/Review statuses
            'pending': 'in_progress',
            'in_progress': 'in_progress',
            'processing': 'in_progress',
            'consider': 'under_review',
            'check.consider': 'under_review',
            # Rejection statuses
            'rejected': 'rejected',
            'failed': 'rejected',
            'declined': 'rejected',
            'check.unrecognised': 'rejected'
        }
        
        # Use event type if available
        if event_type and event_type.startswith('check.'):
            status = event_type
        
        internal_status = status_mapping.get(status, 'in_progress')
        
        # Find user
        user_response = supabase.table('user_profiles').select('id').eq('id', user_reference).execute()
        
        if not user_response.data:
            if user_reference.startswith('applicant_'):
                actual_user_id = user_reference.replace('applicant_', '')
                user_response = supabase.table('user_profiles').select('id').eq('id', actual_user_id).execute()
        
        if not user_response.data:
            logger.error(f"[KYC Webhook] User not found: {user_reference}")
            return {"success": False, "error": "User not found"}
        
        user_id = user_response.data[0]['id']
        
        # Update user status
        update_data = {
            'kyc_status': internal_status,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if internal_status == 'verified':
            update_data['kyc_completed_at'] = datetime.utcnow().isoformat()
            update_data['kyc_level'] = 3
            update_data['role'] = 'tribe'
        
        if internal_status == 'rejected':
            update_data['kyc_rejection_reason'] = webhook_data.get('reason', 'Verification failed')
        
        supabase.table('user_profiles').update(update_data).eq('id', user_id).execute()
        
        logger.info(f"[KYC Webhook] Status updated for user {user_id}: {internal_status}")
        
        return {
            "success": True,
            "message": f"KYC status updated for user {user_id}",
            "user_id": user_id,
            "new_status": internal_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[KYC Webhook] Error [ID: {error_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed. Error ID: {error_id}")

@router.get("/status/{user_id}")
async def get_kyc_status(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """Get KYC status for user"""
    try:
        if current_user.get('id') != user_id and current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Access denied")
        
        profile_response = supabase.table('user_profiles').select(
            'kyc_status, kyc_level, kyc_completed_at, kyc_rejection_reason'
        ).eq('id', user_id).execute()
        
        if not profile_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        profile = profile_response.data[0]
        
        return {
            "user_id": user_id,
            "kyc_status": profile.get('kyc_status', 'not_started'),
            "kyc_level": profile.get('kyc_level', 0),
            "completed_at": profile.get('kyc_completed_at'),
            "rejection_reason": profile.get('kyc_rejection_reason'),
            "can_upgrade": profile.get('kyc_level', 0) < 3
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[KYC Status] Error [ID: {error_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch KYC status. Error ID: {error_id}")

@router.post("/skip-verification")
async def skip_kyc_verification(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """Allow users to skip KYC for limited access"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        update_data = {
            'kyc_status': 'skipped',
            'kyc_level': 1,
            'verification_skipped': True,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('user_profiles').update(update_data).eq('id', user_id).execute()
        
        return {
            "success": True,
            "message": "Verification skipped. Limited access granted.",
            "kyc_status": "skipped",
            "kyc_level": 1
        }
        
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[KYC Skip] Error [ID: {error_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to skip verification. Error ID: {error_id}")
    
class KYCDataRequest(BaseModel):
    bvn: str = Field(..., description="Bank Verification Number")
    date_of_birth: str = Field(..., description="Date of birth (YYYY-MM-DD)")
    gender: str = Field(..., description="Gender (M/F/Other)")

# ADD TO kyc.py - New endpoint for progressive KYC data
class KYCDataSubmission(BaseModel):
    bvn: Optional[str] = None
    id_number: Optional[str] = None
    date_of_birth: str
    gender: str
    country_code: str = "US"

@router.get("/detect-country")
async def detect_country(
    request: Request,
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    UPDATED: Enhanced country detection with ID requirements
    """
    try:
        # Try IPInfo service first
        from backend.services.ipinfo_service import IPInfoService
        
        # Get client IP
        client_ip = request.headers.get('x-forwarded-for', '').split(',')[0].strip()
        if not client_ip:
            client_ip = request.client.host
        
        # Detect country
        ipinfo = IPInfoService()
        ip_data = await ipinfo.get_ip_info(client_ip)
        
        if ip_data and ip_data.get('country'):
            country_code = ip_data.get('country', 'US')
            
            # Determine requirements
            requirements = {
                'NG': {'requires_id': True, 'id_types': ['BVN'], 'provider': 'regfyl'},
                'KE': {'requires_id': True, 'id_types': ['National ID'], 'provider': 'regfyl'},
                'GH': {'requires_id': True, 'id_types': ['Ghana Card'], 'provider': 'regfyl'},
                'DEFAULT': {'requires_id': False, 'id_types': ['Passport', 'Driver License'], 'provider': 'regfyl'}
            }
            
            country_req = requirements.get(country_code, requirements['DEFAULT'])
            
            return {
                "success": True,
                "country_code": country_code,
                "country_name": _get_country_name(country_code),
                "city": ip_data.get('city'),
                "requires_id": country_req['requires_id'],
                "id_types": country_req['id_types'],
                "provider": country_req['provider'],
                "detection_method": "ip_geolocation"
            }
        
        # Fallback
        return {
            "success": True,
            "country_code": "US",
            "country_name": "United States", 
            "requires_id": False,
            "id_types": ["PASSPORT", "DRIVERS_LICENSE"],
            "provider": "regfyl",
            "detection_method": "fallback"
        }
        
    except Exception as e:
        logger.error(f"[Country Detection] Error: {str(e)}")
        return {
            "success": True,
            "country_code": "US",
            "country_name": "United States",
            "requires_id": False,
            "id_types": ["PASSPORT", "DRIVERS_LICENSE"],
            "provider": "regfyl",
            "detection_method": "error_fallback"
        }

def _get_country_name(code: str) -> str:
    """Get country name from code"""
    countries = {
        "NG": "Nigeria",
        "KE": "Kenya",
        "GH": "Ghana",
        "ZA": "South Africa",
        "US": "United States",
        "GB": "United Kingdom",
        "CA": "Canada"
    }
    return countries.get(code, code)

def _get_id_types(country_code: str) -> List[str]:
    """Get supported ID types per country"""
    id_mapping = {
        "NG": ["BVN", "NIN", "PASSPORT", "DRIVERS_LICENSE"],
        "KE": ["NATIONAL_ID", "PASSPORT"],
        "GH": ["GHANA_CARD", "PASSPORT"],
        "ZA": ["ID_BOOK", "ID_CARD", "PASSPORT"],
        "US": ["PASSPORT", "DRIVERS_LICENSE", "STATE_ID"],
        "GB": ["PASSPORT", "DRIVERS_LICENSE"],
        "CA": ["PASSPORT", "DRIVERS_LICENSE"]
    }
    return id_mapping.get(country_code, ["PASSPORT", "NATIONAL_ID"])