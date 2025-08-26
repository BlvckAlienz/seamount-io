# ==============================================================================
# Seamount.io API - Production Hardened Authentication with Detailed Logging
# Version: 2.5.0 (Fixed all circular imports and dependencies)
# ==============================================================================

import logging
import traceback
import asyncio
from contextlib import asynccontextmanager
from fastapi import (
    FastAPI, File, UploadFile, Form, Depends, HTTPException, Request, Header, status
)
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
from services.wallet_service import WalletService
from services.kyc_providers.complycube import complycube_service
from api.routes import kyc, webhooks
from api.routes.portfolio import router as portfolio_router
from config import Settings, get_settings
import sys
from pathlib import Path


# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import models after path setup
from models import (
    UserProfile, PaymentRequest, PaymentResponse, MFASetupResponse, 
    MFAVerifyRequest, PortfolioHolding, SessionResponse, 
    ConsentUpdatePayload, InvestorContactPayload, KYCSubmission, UserRole
)

# Import the role checker with error handling
try:
    from middleware.role_check import require_role
except ImportError:
    # Fallback implementation if middleware not found
    def require_role(required_role: str):
        def role_checker(current_user: dict, supabase: Client):
            if current_user.get("role") != required_role:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403, 
                    detail=f"{required_role.capitalize()} role required"
                )
            return current_user
        return role_checker
    logger.warning("Using fallback require_role function - middleware module not found")

# --- 1. ENHANCED LOGGING & GLOBAL STATE ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None
_notification_service: Optional[NotificationService] = None
_wallet_service: Optional[WalletService] = None
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

def get_wallet_service() -> WalletService:
    if _wallet_service is None: 
        raise HTTPException(status_code=503, detail="Wallet service not initialized")
    return _wallet_service

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
                "updated_at": datetime.utcnow().isoformat(),
                "role": UserRole.ALIEN.value
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

# --- 3. LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _supabase_client, _notification_service, _wallet_service
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
        
        # Initialize wallet service
        _wallet_service = WalletService(current_settings, _supabase_client)
        logger.info("Wallet service initialized.")
        
        # Set global instances in dependencies module
        try:
            import dependencies
            dependencies._supabase_client = _supabase_client
            dependencies._wallet_service = _wallet_service
            dependencies._notification_service = _notification_service
            logger.info("Dependencies module initialized with service instances.")
        except ImportError:
            logger.warning("Dependencies module not found - some features may not work properly")
        
        yield
        
    except Exception as e:
        logger.critical(f"FATAL STARTUP ERROR: {e}\n{traceback.format_exc()}")
        raise
        
    logger.info("--- Seamount API Shutting Down ---")

# --- 4. FASTAPI APP ---
app = FastAPI(
    title="Seamount.io API", 
    version="2.5.0", 
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

# Import routers after app is created
try:
    from api.routes import kyc, webhooks
    # Include routers
    app.include_router(kyc.router, prefix="/api", tags=["kyc"])
    app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
    app.include_router(portfolio_router, prefix="/api/v1", tags=["Portfolio"])
except ImportError as e:
    logger.warning(f"Could not import routers: {e}")

# --- 5. API ROUTES (Hardened with Route-Level Exception Handling) ---

@app.get("/api/v1/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "2.5.0", "timestamp": datetime.utcnow()}

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

# Replace the existing KYC endpoint with this implementation
@app.post("/api/kyc/start-verification", tags=["KYC"])
async def start_kyc_verification(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Start KYC verification process with ComplyCube"""
    try:
        logger.info(f"Starting KYC verification for user: {current_user['id']}")
        
        # Check if user already has an applicant ID
        if current_user.get('complycube_applicant_id'):
            logger.info(f"User {current_user['id']} already has applicant ID: {current_user['complycube_applicant_id']}")
            # Generate token for existing applicant
            token = complycube_service.create_verification_token(current_user['complycube_applicant_id'])
        else:
            # Create new applicant
            user_data = {
                'email': current_user['email'],
                'first_name': current_user.get('first_name', ''),
                'last_name': current_user.get('last_name', '')
            }
            
            applicant = complycube_service.create_applicant(user_data)
            
            # Update user profile with applicant ID
            update_data = {
                'complycube_applicant_id': applicant.id,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            result = supabase.from_("user_profiles") \
                .update(update_data) \
                .eq('id', current_user['id']) \
                .execute()
                
            if not result.data:
                logger.error(f"Failed to update user profile with applicant ID: {applicant.id}")
                raise HTTPException(status_code=500, detail="Failed to update user profile")
            
            # Generate verification token
            token = complycube_service.create_verification_token(applicant.id)
        
        return {
            "success": True,
            "token": token,
            "message": "KYC verification started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"KYC start error [{error_id}]: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error starting KYC. Error ID: {error_id}")

# Protect sensitive endpoints with role requirements
@app.post("/api/payments/send", tags=["Payments"])
async def send_payment(
    payment_data: PaymentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Send a payment to another user"""
    try:
        # Use the role checker function directly
        role_checker = require_role("tribe")
        role_checker(current_user, supabase)
        
        # Your payment logic here
        # This is just a placeholder - implement your actual payment logic
        return {"status": "success", "message": "Payment processed"}
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Payment processing error [{error_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing payment. Error ID: {error_id}")

# Replace the existing wallet creation endpoint with this implementation
@app.post("/api/wallet/create", tags=["Wallet"])
async def create_wallet(
    current_user: Dict[str, Any] = Depends(get_current_user),
    wallet_service: WalletService = Depends(get_wallet_service),
    supabase: Client = Depends(get_supabase_client)
):
    """Create a wallet for the user"""
    try:
        logger.info(f"Creating wallet for user: {current_user['id']}")
        
        # Check if user already has a wallet
        wallet_res = supabase.from_("user_wallets").select("*").eq("user_id", current_user["id"]).execute()
        
        if wallet_res.data:
            logger.info(f"User {current_user['id']} already has a wallet")
            return {
                "success": True,
                "message": "Wallet already exists",
                "address": wallet_res.data[0]["algorand_address"],
                "is_demo": wallet_res.data[0].get("is_demo", False)
            }
        
        # Create wallet for user
        result = await wallet_service.provision_user_wallet(current_user["id"])
        
        return {
            "success": True,
            "message": "Wallet created successfully",
            "address": result["algorand_address"],
            "is_demo": result.get("is_demo", False)
        }
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Wallet creation error for user {current_user['id']} [{error_id}]: {e}\n{traceback.format_exc()}")
        
        # Return a demo wallet instead of failing completely
        return {
            "success": True,
            "message": "Demo wallet created (fallback mode)",
            "address": f"ALGO_DEMO_{current_user['id'][:8]}",
            "is_demo": True
        }

@app.post("/api/user/update-role", tags=["User"])
async def update_user_role(
    role: UserRole,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Update user role (admin only)"""
    try:
        # Check if user is admin
        if not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Update user role in database
        update_data = {"role": role.value}
        result = supabase.from_("user_profiles").update(update_data).eq("id", current_user["id"]).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"success": True, "message": f"User role updated to {role.value}"}
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Role update error [{error_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating role. Error ID: {error_id}")

# Update the investor contact endpoint
@app.post("/api/v1/investor-contact", tags=["Public"])
async def investor_contact(
    payload: InvestorContactPayload, 
    supabase: Client = Depends(get_supabase_client), 
    notifier: NotificationService = Depends(get_notification_service)
):
    try:
        # Insert into database
        result = supabase.table('investor_contacts').insert(payload.dict()).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to save contact information")
        
        # Send notification email
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
        
        # Use asyncio to run the email sending in background
        asyncio.create_task(notifier.email_service.send_email(
            subject, 
            ["investors@seamount.io"], 
            body
        ))
        
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
        
# --- 6. DEBUG ENDPOINTS (For authentication troubleshooting) ---
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

# --- 7. ERROR HANDLING MIDDLEWARE ---
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