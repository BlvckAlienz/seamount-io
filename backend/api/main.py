# ==============================================================================
# Seamount.io API - Production Hardened Authentication with Detailed Logging
# Version: 2.3.0
# ==============================================================================

import logging
import traceback
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, ValidationError
from supabase import create_client, Client
from typing import List, Dict, Any, Optional
from uuid import uuid4, UUID
from datetime import datetime, timedelta
import aiohttp
from jose import JWTError, jwt
import base64
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import pyotp

# --- 1. ENHANCED LOGGING & GLOBAL STATE ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None
_notification_service: Optional[NotificationService] = None
jwks_cache: Dict[str, Any] = {}
jwks_cache_expiry: Optional[datetime] = None
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

# --- 2. AUTHENTICATION & DEPENDENCIES (Hardened) ---
async def fetch_jwks(current_settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    global jwks_cache, jwks_cache_expiry
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry:
        logger.debug("Using cached JWKS")
        return jwks_cache
    
    try:
        logger.info(f"Fetching JWKS from: {current_settings.SUPABASE_JWKS_URI}")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(current_settings.SUPABASE_JWKS_URI) as response:
                response.raise_for_status()
                jwks_data = await response.json()
                jwks_cache, jwks_cache_expiry = jwks_data, datetime.utcnow() + timedelta(hours=1)
                logger.info(f"JWKS fetched successfully. Keys found: {len(jwks_data.get('keys', []))}")
                return jwks_data
    except Exception as e:
        logger.error(f"CRITICAL: Could not fetch JWKS from {current_settings.SUPABASE_JWKS_URI}. Error: {e}")
        raise HTTPException(status_code=503, detail="Authentication service is currently unavailable.")

def jwk_to_pem(jwk: Dict[str, Any]) -> str:
    try:
        # Check if this is an RSA key
        if jwk.get('kty') != 'RSA':
            raise JWTError(f"Unsupported key type: {jwk.get('kty')}")
        
        # Ensure required parameters are present
        if 'n' not in jwk or 'e' not in jwk:
            raise JWTError("JWK missing required RSA parameters (n or e)")
        
        # Decode the base64url-encoded values with proper padding
        n = base64.urlsafe_b64decode(jwk['n'] + '=='[: (4 - len(jwk['n']) % 4) % 4])
        e = base64.urlsafe_b64decode(jwk['e'] + '=='[: (4 - len(jwk['e']) % 4) % 4])
        
        # Convert to integers
        n_int = int.from_bytes(n, 'big')
        e_int = int.from_bytes(e, 'big')
        
        # Create RSA public key
        public_numbers = rsa.RSAPublicNumbers(e_int, n_int)
        public_key = public_numbers.public_key()
        
        # Serialize to PEM format
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return pem.decode('utf-8')
    except Exception as e:
        logger.error(f"JWK to PEM conversion failed for JWK: {jwk}. Error: {e}")
        raise JWTError(f"Invalid key format in JWKS: {e}")

async def verify_token(token: str = Depends(oauth2_scheme), current_settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    try:
        logger.info(f"Starting JWT verification for token: {token[:50]}...")
        
        # Decode token header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        logger.info(f"Token KID: {kid}")
        
        if not kid:
            logger.error("Token missing key ID (kid)")
            raise JWTError("Token missing key ID (kid)")
        
        # Fetch JWKS
        jwks = await fetch_jwks(current_settings)
        logger.info(f"JWKS contains {len(jwks.get('keys', []))} keys")
        
        # Find the matching key
        key = next((k for k in jwks.get('keys', []) if k.get('kid') == kid), None)
        if not key:
            logger.error(f"Public key for KID {kid} not found in JWKS. Available KIDs: {[k.get('kid') for k in jwks.get('keys', [])]}")
            raise JWTError("Public key for token not found in JWKS.")
        
        logger.info(f"Found matching key for KID: {kid}")
        
        # Convert JWK to PEM format
        public_key = jwk_to_pem(key)
        logger.debug(f"Converted public key: {public_key[:100]}...")
        
        # Verify and decode token
        payload = jwt.decode(
            token, 
            public_key, 
            algorithms=[key.get('alg', 'RS256')], 
            audience='authenticated',
            options={"verify_aud": True}
        )
        
        logger.info(f"Token verified successfully for user: {payload.get('sub')}")
        return payload
        
    except JWTError as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Unexpected error in token verification [{error_id}]: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Could not process token. Error ID: {error_id}")

# ... rest of your main.py code remains the same ...

def get_supabase_client() -> Client:
    if _supabase_client is None: 
        raise HTTPException(status_code=503, detail="Database client not initialized")
    return _supabase_client

async def get_current_user(payload: Dict[str, Any] = Depends(verify_token), supabase: Client = Depends(get_supabase_client)) -> Dict[str, Any]:
    user_id = payload.get("sub")
    if not user_id: 
        raise HTTPException(status_code=401, detail="Invalid token payload: missing user identifier.")
    
    try:
        profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).single().execute()
        if not profile_res.data: 
            raise HTTPException(status_code=404, detail="User profile not found.")
        
        logger.debug(f"User profile retrieved for: {user_id}")
        return profile_res.data
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
        
        # Test connection
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
    version="2.2.0", 
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
    return {"status": "healthy", "version": "2.2.0", "timestamp": datetime.utcnow()}

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

# --- 7. DEBUG ENDPOINT (For authentication troubleshooting) ---
@app.get("/api/v1/debug/token", tags=["Debug"])
async def debug_token(token: str = Depends(oauth2_scheme)):
    """Endpoint to help debug JWT token issues"""
    try:
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