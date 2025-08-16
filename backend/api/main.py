# ==============================================================================
# Seamount.io API - Main Application
# Version: 1.5.2 (Deployment Fix - Legacy Fields Removed)
# ==============================================================================

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
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

# --- Project-specific Imports ---
from config import get_settings, Settings
from services.email_service import EmailService
from services.notification_service import NotificationService

# --- 1. SETUP & GLOBAL STATE ---
logger = logging.getLogger(__name__)
_supabase_client: Optional[Client] = None
_notification_service: Optional[NotificationService] = None
jwks_cache: Dict[str, Any] = {}
jwks_cache_expiry: Optional[datetime] = None
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

# --- 2. AUTHENTICATION & DEPENDENCIES ---
async def fetch_jwks(current_settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    global jwks_cache, jwks_cache_expiry
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry: 
        return jwks_cache
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(current_settings.SUPABASE_JWKS_URI) as response:
                response.raise_for_status()
                jwks_data = await response.json()
                jwks_cache, jwks_cache_expiry = jwks_data, datetime.utcnow() + timedelta(hours=1)
                return jwks_data
    except Exception as e: 
        logger.error(f"JWKS fetch failed: {e}")
        raise HTTPException(status_code=503, detail=f"Authentication service unavailable: {e}")

def jwk_to_pem(jwk: Dict[str, Any]) -> bytes:
    n = int.from_bytes(base64.urlsafe_b64decode(jwk['n'] + '=='), 'big')
    e = int.from_bytes(base64.urlsafe_b64decode(jwk['e'] + '=='), 'big')
    return rsa.RSAPublicNumbers(e, n).public_key().public_bytes(
        encoding=serialization.Encoding.PEM, 
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

async def verify_token(token: str = Depends(oauth2_scheme), current_settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        jwks = await fetch_jwks(current_settings)
        key = next((k for k in jwks.get('keys', []) if k.get('kid') == kid), None)
        if not key: 
            raise JWTError("Public key for token not found")
        return jwt.decode(token, jwk_to_pem(key), algorithms=[key.get('alg', 'RS256')], audience='authenticated')
    except JWTError as e: 
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

def get_supabase_client() -> Client:
    if _supabase_client is None: 
        raise HTTPException(status_code=503, detail="Database client not initialized")
    return _supabase_client

async def get_current_user(payload: Dict[str, Any] = Depends(verify_token), supabase: Client = Depends(get_supabase_client)) -> Dict[str, Any]:
    user_id = payload.get("sub")
    if not user_id: 
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    try:
        profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).single().execute()
        if not profile_res.data: 
            raise HTTPException(status_code=404, detail="User profile not found")
        return profile_res.data
    except Exception as e:
        logger.error(f"Failed to fetch user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user data")

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
    logger.info("Application startup...")
    current_settings = get_settings()
    
    try:
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
        
    except Exception as e:
        logger.critical(f"Failed to initialize services: {e}")
        raise
    
    yield
    logger.info("Application shutdown completed.")

# --- 5. FASTAPI APP ---
app = FastAPI(
    title="Seamount.io API", 
    version="1.5.2", 
    lifespan=lifespan,
    description="P2P cross-border payments and yield-farming stablecoin network"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware, 
    allow_origins=get_settings().ALLOWED_ORIGINS, 
    allow_credentials=True, 
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
    allow_headers=["*"]
)

# --- 6. API ROUTES ---

# Section: Public & System Routes
@app.get("/api/v1/health", tags=["System"])
def health_check(): 
    return {"status": "healthy", "version": "1.5.2"}

@app.post("/api/v1/session/initialize", response_model=SessionResponse, tags=["Session"])
async def initialize_session(
    request: Request, 
    user_agent: Optional[str] = Header(None, alias="User-Agent"), 
    supabase: Client = Depends(get_supabase_client), 
    current_settings: Settings = Depends(get_settings)
):
    ip_address = request.client.host if request.client else "unknown"
    session_data = {
        "id": str(uuid4()), 
        "ip_address": ip_address, 
        "user_agent": user_agent or "unknown"
    }
    
    # IP enrichment
    try:
        if ip_address and ip_address != "unknown":
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as http_session:
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
    
    try:
        insert_res = supabase.from_("user_sessions").insert(session_data).execute()
        if not insert_res.data: 
            raise HTTPException(status_code=500, detail="Failed to create session.")
        
        session_id = insert_res.data[0]['id']
        response = JSONResponse(content={"session_id": session_id})
        response.set_cookie(
            key="seamount_session_id", 
            value=session_id, 
            max_age=31536000, 
            httponly=True, 
            samesite="lax", 
            secure=True
        )
        return response
    except Exception as e:
        logger.error(f"Session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize session")

@app.post("/api/v1/consent/update", tags=["Session"])
async def update_consent(
    payload: ConsentUpdatePayload, 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        res = supabase.from_("user_sessions").update({
            "consent_preferences": payload.preferences
        }).eq("id", str(payload.session_id)).execute()
        
        if not res.data: 
            raise HTTPException(status_code=404, detail="Session not found.")
        return {"message": "Consent updated successfully"}
    except Exception as e:
        logger.error(f"Consent update failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update consent")

@app.post("/api/v1/investor-contact", tags=["Public"])
async def investor_contact(
    payload: InvestorContactPayload, 
    supabase: Client = Depends(get_supabase_client), 
    notifier: NotificationService = Depends(get_notification_service)
):
    try:
        # Store contact request
        supabase.from_("investor_contacts").insert(payload.dict()).execute()
        
        # Send notification email
        subject = f"New Investor Contact: {payload.name}"
        body = f"""
        <html>
        <body>
        <h3>New Investor Contact Request</h3>
        <p><strong>Name:</strong> {payload.name}</p>
        <p><strong>Email:</strong> {payload.email}</p>
        <p><strong>Company:</strong> {payload.company or 'N/A'}</p>
        <p><strong>Check Size:</strong> {payload.checkSize or 'N/A'}</p>
        <p><strong>Message:</strong></p>
        <p>{payload.message or 'No message provided'}</p>
        </body>
        </html>
        """
        await notifier.email_service.send_email(subject, ["investors@seamount.io"], body)
        
        return {"message": "Contact request submitted successfully."}
    except Exception as e:
        logger.error(f"Investor contact submission failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit contact request")

# Section: Authenticated User Routes
@app.get("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user

@app.post("/api/v1/user/kyc", tags=["User"])
async def update_kyc(
    submission: KYCSubmission, 
    current_user: Dict[str, Any] = Depends(get_current_user), 
    notifier: NotificationService = Depends(get_notification_service), 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        user_id = current_user["id"]
        kyc_data = {
            "user_id": user_id, 
            "document_type": submission.document_type, 
            "document_data": submission.document_data, 
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.from_("kyc_documents").insert(kyc_data).execute()
        supabase.from_("user_profiles").update({
            "kyc_status": "in_progress"
        }).eq("id", user_id).execute()
        
        await notifier.send_kyc_update(
            current_user["email"], 
            "in_progress", 
            "Your documents have been received and are now under review."
        )
        
        return {"message": "KYC documents submitted for review."}
    except Exception as e:
        logger.error(f"KYC submission failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit KYC documents")

@app.post("/api/v1/payments/send", response_model=PaymentResponse, tags=["Payments"])
async def send_payment(
    req: PaymentRequest, 
    current_user: Dict[str, Any] = Depends(get_current_user), 
    supabase: Client = Depends(get_supabase_client), 
    notifier: NotificationService = Depends(get_notification_service)
):
    try:
        # Find recipient
        recipient_res = supabase.from_("user_profiles").select("id, email").eq("email", req.recipient_email).single().execute()
        if not recipient_res.data: 
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        # Create transaction
        tx_id = str(uuid4())
        tx_data = {
            "id": tx_id, 
            "sender_id": current_user["id"], 
            "recipient_id": recipient_res.data["id"], 
            "amount": req.amount, 
            "currency": req.currency, 
            "status": "completed",
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.from_("transactions").insert(tx_data).execute()
        
        # Send notifications
        await notifier.send_transfer_notifications(
            current_user["email"], 
            req.recipient_email, 
            req.amount, 
            fee=0.01
        )
        
        return PaymentResponse(**tx_data, timestamp=datetime.utcnow())
    except Exception as e:
        logger.error(f"Payment failed: {e}")
        raise HTTPException(status_code=500, detail="Payment processing failed")

@app.get("/api/v1/user/portfolio", response_model=List[PortfolioHolding], tags=["Portfolio"])
def get_portfolio(
    current_user: Dict[str, Any] = Depends(get_current_user), 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        holdings = supabase.from_("user_portfolios").select("*").eq("user_id", current_user["id"]).execute()
        return holdings.data or []
    except Exception as e:
        logger.error(f"Portfolio fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch portfolio")

@app.post("/api/v1/user/mfa/setup", response_model=MFASetupResponse, tags=["Security"])
async def setup_mfa(
    current_user: Dict[str, Any] = Depends(get_current_user), 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        secret = pyotp.random_base32()
        qr_url = pyotp.TOTP(secret).provisioning_uri(
            current_user["email"], 
            issuer_name="Seamount.io"
        )
        
        # Store MFA secret
        supabase.from_("user_mfa").insert({
            "user_id": current_user["id"], 
            "secret": secret, 
            "enabled": False
        }).execute()
        
        return MFASetupResponse(secret=secret, qr_code_url=qr_url)
    except Exception as e:
        logger.error(f"MFA setup failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to setup MFA")

@app.post("/api/v1/user/mfa/verify", tags=["Security"])
async def verify_mfa(
    req: MFAVerifyRequest, 
    current_user: Dict[str, Any] = Depends(get_current_user), 
    supabase: Client = Depends(get_supabase_client)
):
    try:
        user_id = current_user["id"]
        mfa_res = supabase.from_("user_mfa").select("secret").eq("user_id", user_id).single().execute()
        
        if not mfa_res.data or not pyotp.TOTP(mfa_res.data["secret"]).verify(req.token):
            raise HTTPException(status_code=401, detail="Invalid MFA token")
        
        supabase.from_("user_mfa").update({"enabled": True}).eq("user_id", user_id).execute()
        return {"message": "MFA verified and enabled successfully."}
    except Exception as e:
        logger.error(f"MFA verification failed: {e}")
        raise HTTPException(status_code=500, detail="MFA verification failed")

# Section: Admin Routes
@app.get("/api/v1/admin/users", response_model=List[UserProfile], tags=["Admin"], dependencies=[Depends(require_admin)])
def get_all_users(supabase: Client = Depends(get_supabase_client)):
    try:
        users = supabase.from_("user_profiles").select("*").execute()
        return users.data or []
    except Exception as e:
        logger.error(f"Admin user fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")