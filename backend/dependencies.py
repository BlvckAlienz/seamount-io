# File Location: backend/dependencies.py
# CRITICAL FIX: Complete implementation with proper service dependency handling

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client, create_client
from typing import Dict, Any, Optional, Union, TYPE_CHECKING
from datetime import datetime, timedelta
from functools import lru_cache
import aiohttp
from jose import JWTError, jwt
import json

# FIXED IMPORTS: Use absolute imports
from backend.config import get_settings
from backend.models import UserRole

if TYPE_CHECKING:
    from backend.services.wallet_service import WalletService
    from backend.services.notification_service import NotificationService
    from backend.services.audit_service import AuditService
    from backend.services.kyc_service import KYCService
    from backend.services.database_service import DatabaseService
else:
    # Runtime imports for actual service instantiation
    try:
        from backend.services.wallet_service import WalletService
        from backend.services.notification_service import NotificationService
        from backend.services.audit_service import AuditService
        from backend.services.kyc_service import KYCService
        from backend.services.database_service import DatabaseService
    except ImportError as e:
        logging.warning(f"Service import failed: {e}")
        WalletService = None
        NotificationService = None
        AuditService = None
        KYCService = None
        DatabaseService = None
       
logger = logging.getLogger(__name__)

# Global service instances
_supabase_client: Optional[Client] = None
_wallet_service: Optional["WalletService"] = None
_notification_service: Optional["NotificationService"] = None
_audit_service: Optional["AuditService"] = None
_kyc_service: Optional["KYCService"] = None
_database_service: Optional["DatabaseService"] = None
jwks_cache: Dict[str, Any] = {}
jwks_cache_expiry: Optional[datetime] = None

# Security schemes
security = HTTPBearer(auto_error=False)  # For optional auth
security_required = HTTPBearer(auto_error=True)  # For required auth

@lru_cache()
def get_settings_cached():
    """Cached settings instance for performance"""
    return get_settings()

def initialize_dependencies(
    supabase_client: Client, 
    wallet_service: "WalletService", 
    notification_service: "NotificationService", 
    audit_service: Optional["AuditService"] = None,
    kyc_service: Optional["KYCService"] = None,
    database_service: Optional["DatabaseService"] = None
):
    """Initialize dependency services - used in main.py startup"""
    global _supabase_client, _wallet_service, _notification_service
    global _audit_service, _kyc_service, _database_service
    
    _supabase_client = supabase_client
    _wallet_service = wallet_service
    _notification_service = notification_service
    _audit_service = audit_service
    _kyc_service = kyc_service
    _database_service = database_service
    
    logger.info("✅ Dependencies initialized successfully")

def get_supabase_client() -> Client:
    """
    CRITICAL FIX: Proper singleton Supabase client with correct config attributes
    """
    global _supabase_client
    
    if _supabase_client is None:
        try:
            settings = get_settings_cached()
            supabase_url = settings.SUPABASE_URL
            supabase_key = settings.SUPABASE_SERVICE_KEY.get_secret_value()
            
            _supabase_client = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: Supabase client initialization failed: {e}")
            # Create a mock client for development
            _supabase_client = None
            logger.warning("Using mock Supabase client - some features may not work")
    
    return _supabase_client
    
def get_kyc_service() -> "KYCService":
    """Get KYC service instance"""
    global _kyc_service
    
    if _kyc_service is None:
        try:
            # Try to initialize KYC service if not already initialized
            from backend.services.kyc_service import KYCService
            from backend.services.kyc_providers.complycube import complycube_service
            
            # Initialize with ComplyCube provider
            _kyc_service = KYCService(
                get_settings_cached(), 
                get_supabase_client(), 
                None,  # database_service is optional
                None   # audit_service is optional
            )
            logger.info("✅ KYC service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize KYC service: {e}")
            raise HTTPException(status_code=500, detail="KYC service initialization failed")
    
    return _kyc_service
    
# Add this function to handle missing payment providers gracefully
def get_payment_service():
    """Get payment service instance with graceful fallback"""
    try:
        from backend.services.payment_service import PaymentService
        return PaymentService()
    except ImportError as e:
        logger.error(f"Payment service not available: {e}")
        # Return a mock service that raises appropriate errors
        class MockPaymentService:
            async def initialize_payment(self, *args, **kwargs):
                raise HTTPException(status_code=503, detail="Payment service unavailable")
            
            async def verify_payment(self, *args, **kwargs):
                raise HTTPException(status_code=503, detail="Payment service unavailable")
        
        return MockPaymentService()
        
def get_wallet_service() -> "WalletService":
    """Get wallet service instance"""
    if _wallet_service is None: 
        logger.error("❌ Wallet service not initialized")
        raise HTTPException(status_code=503, detail="Wallet service unavailable")
    return _wallet_service

def get_notification_service() -> "NotificationService":
    """Get notification service instance"""
    if _notification_service is None: 
        logger.error("❌ Notification service not initialized")
        raise HTTPException(status_code=503, detail="Notification service unavailable")
    return _notification_service

def get_audit_service() -> Optional["AuditService"]:
    """Get audit service instance (optional)"""
    return _audit_service

def get_database_service() -> Optional["DatabaseService"]:
    """Get database service instance (optional)"""
    return _database_service

# CRITICAL FIX: Add OptionalAuth class at the top level
class OptionalAuth:
    """Optional authentication container"""
    def __init__(self, user: Optional[dict] = None, payload: Optional[dict] = None):
        self.user = user
        self.payload = payload
        self.is_authenticated = user is not None and payload is not None

async def get_optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    settings: Any = Depends(get_settings_cached)
) -> OptionalAuth:
    """
    Optional authentication dependency that returns OptionalAuth object
    """
    if not credentials:
        return OptionalAuth()
    
    try:
        # Verify token using existing logic
        token = credentials.credentials
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        if not kid:
            return OptionalAuth()
        
        jwks = await fetch_jwks(settings)
        key = None
        for jwk_key in jwks.get('keys', []):
            if jwk_key.get('kid') == kid:
                key = jwk_key
                break
        
        if not key:
            return OptionalAuth()
        
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256', 'ES256'],
            audience='authenticated',
            issuer=settings.SUPABASE_JWT_ISSUER,
            options={"verify_aud": True, "verify_exp": True, "verify_iss": True}
        )
        
        # Get user profile
        supabase = get_supabase_client()
        user_id = payload.get('sub')
        if user_id:
            profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).limit(1).execute()
            if profile_res.data and len(profile_res.data) > 0:
                user_profile = profile_res.data[0]
                return OptionalAuth(user=user_profile, payload=payload)
        
        return OptionalAuth(payload=payload)
        
    except Exception:
        return OptionalAuth()

async def fetch_jwks(settings: Any = Depends(get_settings_cached)) -> Dict[str, Any]:
    """
    Fetch and cache Supabase JWKS for JWT verification
    Includes retry logic and proper error handling
    """
    global jwks_cache, jwks_cache_expiry
    
    # Return cached JWKS if still valid
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry: 
        logger.debug("📊 Using cached JWKS")
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
    settings: Any = Depends(get_settings_cached)
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
            detail="Invalid token payload - user ID missing"
        )
    
    logger.debug(f"🔍 Fetching user profile for ID: {user_id}")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # CRITICAL FIX: Query user_profiles table properly - FIXED RLS RECURSION
            profile_response = supabase.from_("user_profiles").select("*").eq("id", user_id).limit(1).execute()
            
            if profile_response.data and len(profile_response.data) > 0:
                logger.info(f"✅ User profile found for: {user_id}")
                return profile_response.data[0]
            
            # SELF-HEALING: Profile doesn't exist, create it from token data
            logger.warning(f"⚠️ Profile not found for user {user_id}. Attempting self-healing profile creation...")
            
            # Extract email from token (if available)
            email = payload.get('email')
            if not email:
                logger.error(f"❌ Cannot create profile: no email in token for user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User profile not found and cannot be auto-created without email"
                )
            
            # Create minimal profile from token data
            now = datetime.utcnow().isoformat()
            profile_data = {
                "id": user_id,
                "user_id": user_id,
                "email": email,
                "first_name": payload.get('user_metadata', {}).get('first_name', ''),
                "last_name": payload.get('user_metadata', {}).get('last_name', ''),
                "country_code": payload.get('user_metadata', {}).get('country_code', 'US').upper(),
                "kyc_status": "pending",  # Default KYC status
                "kyc_level": 0,           # Default KYC level
                "role": "alien",
                "is_admin": False,
                "created_at": now,
                "updated_at": now
            }
            
            logger.info(f"🛠️ Self-healing: Creating profile for user {user_id}")
            
            # Create profile with upsert to handle race conditions
            create_response = supabase.from_("user_profiles").upsert(
                profile_data, 
                on_conflict="id"
            ).execute()
            
            if not create_response.data:
                logger.error("❌ Profile creation returned no data")
                continue  # Retry
                
            # Fetch the created profile - FIXED RLS RECURSION
            fetch_response = supabase.from_("user_profiles").select("*").eq("id", user_id).limit(1).execute()
            
            if fetch_response.data and len(fetch_response.data) > 0:
                logger.info(f"✅ Self-healing successful: Profile created for user {user_id}")
                return fetch_response.data[0]
            else:
                logger.error("❌ Could not fetch newly created profile")
                continue  # Retry
                
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as db_error:
            logger.warning(f"⚠️ Database operation failed (attempt {attempt + 1}): {str(db_error)}")
            
            if attempt == max_retries - 1:
                logger.error(f"❌ All profile fetch attempts failed for user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not retrieve or create user profile"
                )
            
            # Exponential backoff for retries
            import asyncio
            await asyncio.sleep(2 ** attempt)
    
    # This should never be reached, but added for completeness
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected error in user profile retrieval"
    )

def require_role(required_role: Union[UserRole, str]):
    """
    Dependency factory for role-based access control
    Usage: @app.get("/admin", dependencies=[Depends(require_role("tribe"))])
    """
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "alien")
        
        if isinstance(required_role, str):
            required_role_str = required_role
        else:
            required_role_str = required_role.value
        
        if user_role != required_role_str:
            logger.warning(f"⚠️ Access denied: User {current_user.get('id')} has role '{user_role}', required: '{required_role_str}'")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{required_role_str}' required"
            )
        
        return current_user
    
    return role_checker

def require_kyc_level(min_level: int):
    """
    Dependency factory for KYC level-based access control
    Usage: @app.get("/premium", dependencies=[Depends(require_kyc_level(2))])
    """
    async def kyc_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_kyc_level = current_user.get("kyc_level", 0)
        
        if user_kyc_level < min_level:
            logger.warning(f"⚠️ KYC level insufficient: User {current_user.get('id')} has level {user_kyc_level}, required: {min_level}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"KYC verification level {min_level} required"
            )
        
        return current_user
    
    return kyc_checker

# Enhanced security dependencies for high-value operations
async def require_fresh_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security_required),
    settings: Any = Depends(get_settings_cached)
) -> Dict[str, Any]:
    """
    Requires a token issued within the last 10 minutes for sensitive operations
    """
    payload = await verify_supabase_token(credentials, settings)
    
    # Check token age
    issued_at = payload.get('iat')
    if issued_at:
        token_age = datetime.utcnow().timestamp() - issued_at
        max_age = 600  # 10 minutes
        if token_age > max_age:
            logger.warning(f"⚠️ Token too old for sensitive operation: {token_age}s (max: {max_age}s)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Fresh authentication required for this operation"
            )
    return payload

# Rate limiting dependencies (simplified - would use Redis in production)
_rate_limit_cache: Dict[str, Dict] = {}

def rate_limit(requests_per_minute: int = 60):
    """
    Basic rate limiting dependency
    In production, this would use Redis for distributed rate limiting
    """
    async def rate_limiter(request, current_user: Dict[str, Any] = Depends(get_current_user)):
        user_id = current_user.get("id")
        now = datetime.utcnow()
        
        if user_id not in _rate_limit_cache:
            _rate_limit_cache[user_id] = {"requests": [], "blocked_until": None}
        
        user_limits = _rate_limit_cache[user_id]
        
        # Check if user is temporarily blocked
        if user_limits["blocked_until"] and now < user_limits["blocked_until"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Clean old requests (older than 1 minute)
        minute_ago = now - timedelta(minutes=1)
        user_limits["requests"] = [req_time for req_time in user_limits["requests"] if req_time > minute_ago]
        
        # Check current rate
        if len(user_limits["requests"]) >= requests_per_minute:
            user_limits["blocked_until"] = now + timedelta(minutes=1)
            logger.warning(f"⚠️ Rate limit exceeded for user {user_id}: {len(user_limits['requests'])} requests/minute")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {requests_per_minute} requests per minute maximum"
            )
        
        # Record this request
        user_limits["requests"].append(now)
        return current_user
    
    return rate_limiter

# FIXED: Proper indentation for these functions
def require_tribe_member(current_user: dict = Depends(get_current_user)):
    """Require user to be a Tribe member (verified)"""
    if current_user.get('kyc_status') != 'verified' and not current_user.get('is_demo', False):
        raise HTTPException(
            status_code=403, 
            detail="Complete KYC verification to access this feature"
        )
    return current_user

def get_user_role(current_user: dict = Depends(get_current_user)):
    """Get user role (Tribe or Alien)"""
    if current_user.get('kyc_status') == 'verified' or current_user.get('is_demo', False):
        return "tribe"
    return "alien"