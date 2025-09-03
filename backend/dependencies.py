# File Location: backend/dependencies.py
# SURGICAL MERGE: Combined advanced JWT verification with critical scoping/import fixes + OptionalAuth

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client, create_client  # CRITICAL: Added missing import
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
from functools import lru_cache
import aiohttp
from jose import JWTError, jwt
import json

from config import Settings, get_settings
from services.wallet_service import WalletService
from services.notification_service import NotificationService
from models import UserRole

logger = logging.getLogger(__name__)

# CRITICAL FIX: Proper global declarations
_supabase_client: Optional[Client] = None
_wallet_service: Optional[WalletService] = None
_notification_service: Optional[NotificationService] = None
jwks_cache: Dict[str, Any] = {}
jwks_cache_expiry: Optional[datetime] = None

# Security schemes - SURGICAL FIX: Added dual security modes
security = HTTPBearer(auto_error=False)  # For optional auth
security_required = HTTPBearer(auto_error=True)  # For required auth

@lru_cache()
def get_settings_cached():
    """Cached settings instance for performance"""
    return get_settings()

def initialize_dependencies(supabase_client: Client, wallet_service: WalletService, notification_service: NotificationService):
    """Initialize dependency services - used in main.py startup"""
    global _supabase_client, _wallet_service, _notification_service
    _supabase_client = supabase_client
    _wallet_service = wallet_service
    _notification_service = notification_service
    logger.info("✅ Dependencies initialized successfully")

def get_supabase_client() -> Client:
    """
    CRITICAL FIX: Proper singleton Supabase client with correct config attributes
    This was the root cause of the UnboundLocalError
    """
    global _supabase_client  # CRITICAL: Must declare global before use
    
    if _supabase_client is None:
        try:
            settings = get_settings_cached()
            # CRITICAL FIX: Use correct attribute names from your config.py
            supabase_url = settings.VITE_SUPABASE_URL  # Not SUPABASE_URL
            supabase_key = settings.SUPABASE_SERVICE_KEY.get_secret_value()  # Not SUPABASE_KEY
            
            _supabase_client = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: Supabase client initialization failed: {e}")
            raise RuntimeError(f"Database service unavailable: {e}")
    
    return _supabase_client

def get_wallet_service() -> WalletService:
    """Get wallet service instance"""
    if _wallet_service is None: 
        logger.error("❌ Wallet service not initialized")
        raise HTTPException(status_code=503, detail="Wallet service unavailable")
    return _wallet_service

def get_notification_service() -> NotificationService:
    """Get notification service instance"""
    if _notification_service is None: 
        logger.error("❌ Notification service not initialized")
        raise HTTPException(status_code=503, detail="Notification service unavailable")
    return _notification_service

async def fetch_jwks(settings: Settings = Depends(get_settings_cached)) -> Dict[str, Any]:
    """
    Fetch and cache Supabase JWKS for JWT verification
    Includes retry logic and proper error handling
    """
    global jwks_cache, jwks_cache_expiry
    
    # Return cached JWKS if still valid
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry: 
        logger.debug("🔄 Using cached JWKS")
        return jwks_cache
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(settings.SUPABASE_JWKS_URI) as response:
                    response.raise_for_status()
                    jwks_data = await response.json()
                    
                    # Cache for 1 hour
                    jwks_cache = jwks_data
                    jwks_cache_expiry = datetime.utcnow() + timedelta(hours=1)
                    
                    logger.info(f"✅ JWKS fetched successfully (attempt {attempt + 1})")
                    return jwks_data
                    
        except Exception as e:
            logger.warning(f"⚠️ JWKS fetch attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.critical(f"❌ CRITICAL: Could not fetch Supabase JWKS after {max_retries} attempts")
                raise HTTPException(
                    status_code=503, 
                    detail="Authentication service unavailable - JWKS fetch failed"
                )

async def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security_required),
    settings: Settings = Depends(get_settings_cached)
) -> Dict[str, Any]:
    """
    Advanced JWT verification using Supabase JWKS
    Includes proper error handling and logging for debugging
    """
    if not credentials:
        logger.error("❌ No authorization credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        token = credentials.credentials
        logger.debug(f"🔍 Verifying JWT token: {token[:20]}...")
        
        # Get unverified header for key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        alg = unverified_header.get('alg', 'RS256')
        
        if not kid:
            logger.error("❌ Token missing key ID (kid)")
            raise JWTError("Token missing key ID (kid)")
        
        logger.debug(f"🔑 Token KID: {kid}, Algorithm: {alg}")
        
        # Fetch JWKS and find matching key
        jwks = await fetch_jwks(settings)
        
        key = None
        for jwk_key in jwks.get('keys', []):
            if jwk_key.get('kid') == kid:
                key = jwk_key
                break
        
        if not key:
            logger.error(f"❌ Public key for KID {kid} not found in JWKS")
            raise JWTError(f"Public key for KID {kid} not found in JWKS")
        
        logger.debug(f"✅ Found matching key for KID: {kid}")
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256', 'ES256'],
            audience='authenticated',
            issuer=settings.SUPABASE_JWT_ISSUER,
            options={"verify_aud": True, "verify_exp": True, "verify_iss": True}
        )
        
        user_id = payload.get('sub')
        logger.info(f"✅ Token verified successfully for user: {user_id}")
        return payload
        
    except JWTError as e:
        logger.error(f"❌ JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error in token verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not process authentication token"
        )

# SURGICAL FIX: Added the missing OptionalAuth dependency
async def verify_supabase_token_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    settings: Settings = Depends(get_settings_cached)
) -> Optional[Dict[str, Any]]:
    """
    SURGICAL FIX: Optional JWT verification - returns None if no token or invalid token
    This is the missing dependency that was causing 403 errors on public endpoints
    """
    if not credentials:
        logger.debug("🔓 No authorization credentials provided (optional auth)")
        return None
        
    try:
        # Reuse the main verification logic but handle errors gracefully
        token = credentials.credentials
        logger.debug(f"🔍 Attempting optional token verification: {token[:20]}...")
        
        # Get unverified header for key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        if not kid:
            logger.debug("🔓 Token missing key ID - skipping optional auth")
            return None
        
        # Fetch JWKS and find matching key
        jwks = await fetch_jwks(settings)
        
        key = None
        for jwk_key in jwks.get('keys', []):
            if jwk_key.get('kid') == kid:
                key = jwk_key
                break
        
        if not key:
            logger.debug(f"🔓 Public key for KID {kid} not found - skipping optional auth")
            return None
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256', 'ES256'],
            audience='authenticated',
            issuer=settings.SUPABASE_JWT_ISSUER,
            options={"verify_aud": True, "verify_exp": True, "verify_iss": True}
        )
        
        user_id = payload.get('sub')
        logger.info(f"✅ Optional token verified successfully for user: {user_id}")
        return payload
        
    except (JWTError, HTTPException):
        logger.debug("🔓 Token verification failed for optional auth - continuing without auth")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Unexpected error in optional token verification: {e}")
        return None

async def get_current_user(
    payload: Dict[str, Any] = Depends(verify_supabase_token),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    Get current user profile with self-healing capabilities
    Creates profile if it doesn't exist (handles new user edge cases)
    """
    user_id = payload.get("sub")
    if not user_id:
        logger.error("❌ Invalid token payload: user ID missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token payload: user ID missing"
        )
    
    try:
        # Fetch user profile from database
        logger.debug(f"🔍 Fetching profile for user: {user_id}")
        profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).maybe_single().execute()
        
        if profile_res.data:
            logger.debug(f"✅ Profile found for user: {user_id}")
            return profile_res.data
        
        # SELF-HEALING: Create profile if it doesn't exist
        logger.warning(f"⚠️ Profile not found for user {user_id}. Auto-creating from JWT data...")
        
        user_metadata = payload.get('user_metadata', {})
        app_metadata = payload.get('app_metadata', {})
        
        new_profile_data = {
            "id": user_id,
            "email": payload.get('email', ''),
            "first_name": user_metadata.get("first_name", ""),
            "last_name": user_metadata.get("last_name", ""),
            "country_code": user_metadata.get("country_code", "US"),
            "kyc_status": "not_started",
            "access_level": "limited",
            "role": UserRole.ALIEN.value,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Insert new profile
        insert_res = supabase.from_("user_profiles").insert(new_profile_data).execute()
        
        if not insert_res.data or len(insert_res.data) == 0:
            logger.error(f"❌ Failed to create profile for user {user_id}")
            raise HTTPException(
                status_code=500, 
                detail="Could not create user profile"
            )
        
        logger.info(f"✅ Successfully auto-created profile for user: {user_id}")
        return insert_res.data[0]
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Profile fetch/creation error for user {user_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving user profile: {str(e)}"
        )

# SURGICAL FIX: The missing OptionalAuth user dependency
async def get_current_user_optional(
    payload: Optional[Dict[str, Any]] = Depends(verify_supabase_token_optional),
    supabase: Client = Depends(get_supabase_client)
) -> Optional[Dict[str, Any]]:
    """
    SURGICAL FIX: Optional user profile fetching - returns None if no valid token
    This was the missing dependency causing 403 errors on public endpoints like /users/me
    """
    if not payload:
        logger.debug("🔓 No payload from optional token verification")
        return None
        
    try:
        user_id = payload.get("sub")
        if not user_id:
            logger.debug("🔓 No user ID in optional payload")
            return None
            
        logger.debug(f"🔍 Fetching optional profile for user: {user_id}")
        profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).maybe_single().execute()
        
        if profile_res.data:
            logger.debug(f"✅ Optional profile found for user: {user_id}")
            return profile_res.data
        else:
            logger.debug(f"🔓 No profile found for optional user: {user_id}")
            return None
        
    except Exception as e:
        logger.warning(f"⚠️ Optional user profile fetch failed: {e}")
        return None

# SURGICAL FIX: Added OptionalAuth class for easier dependency injection
class OptionalAuth:
    """
    SURGICAL FIX: Optional authentication dependency class
    Use this for endpoints that should work with or without authentication
    """
    def __init__(self):
        self.user: Optional[Dict[str, Any]] = None
        self.payload: Optional[Dict[str, Any]] = None
        self.is_authenticated: bool = False
    
    @classmethod
    async def create(
        cls,
        payload: Optional[Dict[str, Any]] = Depends(verify_supabase_token_optional),
        user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
    ) -> 'OptionalAuth':
        """Factory method to create OptionalAuth instance"""
        auth = cls()
        auth.payload = payload
        auth.user = user
        auth.is_authenticated = payload is not None and user is not None
        
        if auth.is_authenticated:
            logger.debug(f"🔓 Optional auth successful for user: {user.get('id', 'unknown')}")
        else:
            logger.debug("🔓 No authentication provided for optional endpoint")
        
        return auth

async def verify_api_key(api_key: Optional[str] = None) -> bool:
    """
    Verify whitelisted API key for service-to-service communication
    Used for webhook endpoints and internal service calls
    """
    if not api_key:
        return False
        
    try:
        settings = get_settings_cached()
        is_valid = api_key in settings.WHITELISTED_API_KEYS
        
        if is_valid:
            logger.info(f"✅ Valid API key used: {api_key[:8]}...")
        else:
            logger.warning(f"❌ Invalid API key attempted: {api_key[:8]}...")
            
        return is_valid
        
    except Exception as e:
        logger.error(f"❌ API key verification error: {e}")
        return False

# DIAGNOSTIC FUNCTIONS FOR DEBUGGING

async def get_token_info(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Debug function to inspect token without full verification
    Remove in production - useful for troubleshooting auth issues
    """
    if not credentials:
        return {"error": "No token provided"}
        
    try:
        token = credentials.credentials
        unverified_header = jwt.get_unverified_header(token)
        unverified_payload = jwt.get_unverified_claims(token)
        
        return {
            "header": unverified_header,
            "payload": {
                "sub": unverified_payload.get("sub"),
                "email": unverified_payload.get("email"),
                "exp": unverified_payload.get("exp"),
                "iat": unverified_payload.get("iat"),
                "aud": unverified_payload.get("aud"),
                "iss": unverified_payload.get("iss")
            },
            "token_length": len(token)
        }
    except Exception as e:
        return {"error": f"Token inspection failed: {str(e)}"}

# Health check dependency
async def check_dependencies_health() -> Dict[str, str]:
    """Health check for all critical dependencies"""
    health_status = {}
    
    # Check Supabase client
    try:
        supabase = get_supabase_client()
        health_status["supabase"] = "healthy"
    except Exception as e:
        health_status["supabase"] = f"unhealthy: {str(e)}"
    
    # Check services
    try:
        get_wallet_service()
        health_status["wallet_service"] = "healthy"
    except Exception:
        health_status["wallet_service"] = "not initialized"
    
    try:
        get_notification_service()
        health_status["notification_service"] = "healthy"
    except Exception:
        health_status["notification_service"] = "not initialized"
    
    # Check JWKS cache
    health_status["jwks_cache"] = "cached" if jwks_cache else "empty"
    
    return health_status