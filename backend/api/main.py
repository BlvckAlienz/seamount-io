# ==============================================================================
# Seamount.io API - Production Hardened Authentication with Detailed Logging
# Version: 2.4.1 (Fixed Table Name)
# ==============================================================================

import logging
import traceback
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, Header, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, ValidationError
from supabase import create_client, Client
from typing import List, Dict, Any, Optional
from uuid import uuid4, UUID
from datetime import datetime, timedelta
import aiohttp
from jose import JWTError, jwt, jwk
from jose.utils import base64url_decode
import json
import base64
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import pyotp
from services.notification_service import NotificationService
from services.email_service import EmailService
from config import Settings, get_settings

# --- 1. ENHANCED LOGGING & GLOBAL STATE ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None
_notification_service: Optional[NotificationService] = None
jwks_cache: Dict[str, Any] = {}
jwks_cache_expiry: Optional[datetime] = None
security = HTTPBearer()

# --- 2. AUTHENTICATION & DEPENDENCIES (Fixed for Supabase) ---
async def fetch_jwks(current_settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    global jwks_cache, jwks_cache_expiry
    
    # Return cached JWKS if still valid
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry:
        logger.debug("Using cached JWKS")
        return jwks_cache
    
    try:
        logger.info(f"Fetching JWKS from: {current_settings.SUPABASE_JWKS_URI}")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(current_settings.SUPABASE_JWKS_URI) as response:
                response.raise_for_status()
                jwks_data = await response.json()
                jwks_cache = jwks_data
                jwks_cache_expiry = datetime.utcnow() + timedelta(hours=1)
                logger.info(f"JWKS fetched successfully. Keys found: {len(jwks_data.get('keys', []))}")
                return jwks_data
    except Exception as e:
        logger.error(f"CRITICAL: Could not fetch JWKS from {current_settings.SUPABASE_JWKS_URI}. Error: {e}")
        raise HTTPException(status_code=503, detail="Authentication service is currently unavailable.")

async def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Properly verify Supabase JWT tokens using their JWKS
    """
    try:
        token = credentials.credentials
        logger.info(f"Starting JWT verification for token: {token[:20]}...")
        
        # Get unverified header to extract key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        alg = unverified_header.get('alg', 'RS256')
        
        if not kid:
            logger.error("Token missing key ID (kid)")
            raise JWTError("Token missing key ID (kid)")
        
        logger.info(f"Token KID: {kid}, Algorithm: {alg}")
        
        # Fetch JWKS
        jwks = await fetch_jwks(current_settings)
        
        # Find the matching key
        key = None
        for jwk_key in jwks.get('keys', []):
            if jwk_key.get('kid') == kid:
                key = jwk_key
                break
        
        if not key:
            logger.error(f"Public key for KID {kid} not found in JWKS")
            raise JWTError(f"Public key for KID {kid} not found in JWKS")
        
        logger.info(f"Found matching key for KID: {kid}")
        
        # Verify and decode token using the correct key
        payload = jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience='authenticated',
            options={"verify_aud": True, "verify_exp": True}
        )
        
        logger.info(f"Token verified successfully for user: {payload.get('sub')}")
        return payload
        
    except JWTError as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Unexpected error in token verification [{error_id}]: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not process token. Error ID: {error_id}"
        )

def get_supabase_client() -> Client:
    if _supabase_client is None: 
        raise HTTPException(status_code=503, detail="Database client not initialized")
    return _supabase_client

async def get_current_user(
    payload: Dict[str, Any] = Depends(verify_supabase_token),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    user_id = payload.get("sub")
    if not user_id: 
        raise HTTPException(status_code=401, detail="Invalid token payload: missing user identifier.")
    
    try:
        # Try to get user profile from the user_profiles table
        profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).execute()
        
        if not profile_res.data:
            # If profile doesn't exist, try to create it from auth data
            logger.info(f"Profile not found for user {user_id}, creating new profile")
            
            # Get user info from auth
            auth_user = supabase.auth.admin.get_user(user_id)
            if not auth_user.user:
                raise HTTPException(status_code=404, detail="User not found in auth system")
                
            # Create profile
            new_profile = {
                "id": user_id,
                "email": auth_user.user.email,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            profile_res = supabase.from_("user_profiles").insert(new_profile).execute()
            
            if not profile_res.data:
                raise HTTPException(status_code=500, detail="Failed to create user profile")
        
        logger.debug(f"User profile retrieved for: {user_id}")
        return profile_res.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Failed to fetch profile for user {user_id} [{error_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving user profile. Error ID: {error_id}")

def get_notification_service() -> NotificationService:
    if _notification_service is None: 
        raise HTTPException(status_code=503, detail="Notification service not initialized")
    return _notification_service
    
def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)):
    if not current_user.get("is_admin", False): 
        raise HTTPException(status_code=403, detail="Admin privileges required")

# --- 3. PYDANTIC MODELS ---
class UserProfile(BaseModel): 
    id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class SessionResponse(BaseModel): 
    session_id: UUID

class ConsentUpdatePayload(BaseModel): 
    session_id: UUID
    preferences: Dict[str, bool]

class InvestorContactPayload(BaseModel): 
    name: str
    email: EmailStr
    company: Optional[str] = None
    checkSize: Optional[str] = None
    message: Optional[str] = None

class KYCSubmission(BaseModel): 
    document_type: str
    document_data: str

class PaymentRequest(BaseModel): 
    recipient_email: EmailStr
    amount: float
    currency: str = "USDS"

class PaymentResponse(BaseModel): 
    transaction_id: str
    status: str
    amount: float
    currency: str
    timestamp: datetime

class MFASetupResponse(BaseModel): 
    secret: str
    qr_code_url: str

class MFAVerifyRequest(BaseModel): 
    token: str

class PortfolioHolding(BaseModel): 
    id: str
    user_id: str
    asset: str
    amount: float
    value_usd: float

# --- 4. LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _supabase_client, _notification_service
    logger.info("--- Seamount API Starting Up ---")
    
    try:
        current_settings = get_settings()
        logger.info(f"Environment: {current_settings.ENVIRONMENT}")
        
        # Initialize Supabase client
        _supabase_client = create_client(
            current_settings.VITE_SUPABASE_URL, 
            current_settings.SUPABASE_SERVICE_KEY.get_secret_value()
        )
        
        # Test connection with the correct table name
        _supabase_client.from_("user_profiles").select("id").limit(1).execute()
        logger.info("Supabase client connected successfully.")
        
        # Initialize notification service
        email_service = EmailService(current_settings)
        _notification_service = NotificationService(email_service)
        logger.info("Notification service initialized.")
        
        yield
        
    except Exception as e:
        logger.critical(f"FATAL STARTUP ERROR: {e}\n{traceback.format_exc()}")
        raise
        
    logger.info("--- Seamount API Shutting Down ---")

# --- 5. FASTAPI APP ---
app = FastAPI(
    title="Seamount.io API", 
    version="2.4.1", 
    lifespan=lifespan,
    docs_url="/api/docs" if get_settings().ENVIRONMENT != "production" else None,
    redoc_url=None
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=get_settings().ALLOWED_ORIGINS, 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"],
    expose_headers=["*"]
)

# --- 6. API ROUTES (Hardened with Route-Level Exception Handling) ---

@app.get("/api/v1/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "2.4.1", "timestamp": datetime.utcnow()}

@app.post("/api/v1/session/initialize", response_model=SessionResponse, tags=["Session"])
async def initialize_session(
    request: Request, 
    user_agent: Optional[str] = Header(None, alias="User-Agent"), 
    supabase: Client = Depends(get_supabase_client), 
    current_settings: Settings = Depends(get_settings)
):
    try:
        ip_address = request.client.host if request.client else "unknown"
        session_data = {
            "id": str(uuid4()), 
            "ip_address": ip_address, 
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # IP enrichment can fail gracefully
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as http_session:
                async with http_session.get(
                    f"https://ipinfo.io/{ip_address}?token={current_settings.IPINFO_TOKEN.get_secret_value()}"
                ) as response:
                    if response.status == 200: 
                        ip_data = await response.json()
                        session_data.update({
                            "isp": ip_data.get("org"), 
                            "country": ip_data.get("country"), 
                            "city": ip_data.get("city"), 
                            "is_vpn": ip_data.get("privacy", {}).get("vpn", False)
                        })
        except Exception as e: 
            logger.warning(f"IPinfo enrichment failed: {e}")
        
        insert_res = supabase.from_("user_sessions").insert(session_data).execute()
        if not insert_res.data: 
            raise Exception("Failed to create session record in database.")
        
        session_id = insert_res.data[0]['id']
        response = JSONResponse(content={"session_id": session_id})
        response.set_cookie(
            key="seamount_session_id", 
            value=session_id, 
            max_age=31536000, 
            httponly=True, 
            samesite="lax", 
            secure=(current_settings.ENVIRONMENT == "production")
        )
        return response
        
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Session initialization failed [{error_id}]: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Could not initialize session. Error ID: {error_id}")

@app.post("/api/v1/investor-contact", tags=["Public"])
async def investor_contact(
    payload: InvestorContactPayload, 
    supabase: Client = Depends(get_supabase_client), 
    notifier: NotificationService = Depends(get_notification_service)
):
    try:
        supabase.from_("investor_contacts").insert(payload.dict()).execute()
        
        subject = f"New Investor Contact: {payload.name}"
        body = f"""
        <html>
            <body>
                <p>Name: {payload.name}</p>
                <p>Email: {payload.email}</p>
                <p>Company: {payload.company or 'Not provided'}</p>
                <p>Check Size: {payload.checkSize or 'Not provided'}</p>
                <p>Message: {payload.message or 'No message'}</p>
            </body>
        </html>
        """
        
        asyncio.create_task(notifier.email_service.send_email(subject, ["investors@seamount.io"], body))
        return {"message": "Contact request submitted successfully."}
        
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Investor contact submission failed [{error_id}]: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Could not process your request. Error ID: {error_id}")

@app.get("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        logger.info(f"Fetching profile for user: {current_user.get('id')}")
        return UserProfile(**current_user)
    except ValidationError as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Profile data validation failed for user {current_user.get('id')} [{error_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing profile data. Error ID: {error_id}")
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Failed to process user profile for {current_user.get('id')} [{error_id}]: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing profile data. Error ID: {error_id}")

# Add this route with your other API routes
@app.post("/api/v1/consent/update", tags=["Session"])
async def update_consent(
    payload: ConsentUpdatePayload,
    supabase: Client = Depends(get_supabase_client)
):
    try:
        # Update the user_sessions table with consent preferences
        update_data = {
            "consent_preferences": payload.preferences,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Update the session record with consent preferences
        result = supabase.from_("user_sessions").update(update_data).eq("id", str(payload.session_id)).execute()
        
        if not result.data:
            logger.warning(f"Session not found for consent update: {payload.session_id}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        logger.info(f"Consent preferences updated for session: {payload.session_id}")
        return {"message": "Consent preferences updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Consent update failed [{error_id}]: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Could not update consent preferences. Error ID: {error_id}")

@app.get("/api/v1/portfolio/summary", tags=["Portfolio"])
async def get_portfolio_summary(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get user portfolio summary"""
    try:
        # Return mock data for now - you can implement real logic later
        return {
            "total_balance": 0.0,
            "usds_balance": 0.0,
            "day_change": 0.0,
            "total_pnl": 0.0,
            "assets": []
        }
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Portfolio summary error [{error_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching portfolio. Error ID: {error_id}")
 
@app.post("/api/kyc/start-verification", tags=["KYC"])
async def start_kyc_verification(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Start KYC verification process"""
    try:
        # TODO: Implement ComplyCube integration here
        return {
            "success": True,
            "session_id": str(uuid4()),
            "message": "KYC verification started"
        }
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"KYC start error [{error_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting KYC. Error ID: {error_id}")

@app.post("/api/kyc/verify-documents", tags=["KYC"])
async def verify_documents(
    document_type: str = Form(...),
    id_document: UploadFile = File(...),
    selfie: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload and verify KYC documents"""
    try:
        # TODO: Implement document processing and ComplyCube integration
        return {
            "success": True,
            "message": "Documents received for verification"
        }
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Document verification error [{error_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"Error verifying documents. Error ID: {error_id}")
        
# --- 7. DEBUG ENDPOINTS (For authentication troubleshooting) ---
@app.get("/api/v1/debug/token", tags=["Debug"])
async def debug_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Endpoint to help debug JWT token issues"""
    try:
        token = credentials.credentials
        # Get unverified header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        # Get payload without verification
        unverified_payload = jwt.get_unverified_claims(token)
        
        return {
            "header": unverified_header,
            "payload": unverified_payload,
            "kid": kid,
            "message": "This is unverified data for debugging purposes only"
        }
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Token debug failed [{error_id}]: {e}")
        return {"error": f"Could not parse token: {e}", "error_id": error_id}

@app.get("/api/v1/debug/auth-test", tags=["Debug"])
async def debug_auth_test(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Test endpoint to verify authentication is working"""
    return {
        "status": "success",
        "user_id": current_user.get("id"),
        "email": current_user.get("email"),
        "message": "Authentication is working correctly!"
    }

# --- 8. ERROR HANDLING MIDDLEWARE ---
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Unhandled exception in request {request.url} [{error_id}]: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error. Error ID: {error_id}"}
        )