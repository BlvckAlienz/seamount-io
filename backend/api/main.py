# ==============================================================================
# Seamount.io API - Main Application
# Version: 1.5.1 (Definitive & Fully Integrated)
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
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry: return jwks_cache
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(current_settings.SUPABASE_JWKS_URI) as response:
                response.raise_for_status()
                jwks_data = await response.json()
                jwks_cache, jwks_cache_expiry = jwks_data, datetime.utcnow() + timedelta(hours=1)
                return jwks_data
    except Exception as e: raise HTTPException(status_code=503, detail=f"Authentication service unavailable: {e}")

def jwk_to_pem(jwk: Dict[str, Any]) -> bytes:
    n = int.from_bytes(base64.urlsafe_b64decode(jwk['n'] + '=='), 'big')
    e = int.from_bytes(base64.urlsafe_b64decode(jwk['e'] + '=='), 'big')
    return rsa.RSAPublicNumbers(e, n).public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)

async def verify_token(token: str = Depends(oauth2_scheme), current_settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        jwks = await fetch_jwks(current_settings)
        key = next((k for k in jwks.get('keys', []) if k.get('kid') == kid), None)
        if not key: raise JWTError("Public key for token not found")
        return jwt.decode(token, jwk_to_pem(key), algorithms=[key.get('alg', 'RS256')], audience='authenticated')
    except JWTError as e: raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

def get_supabase_client() -> Client:
    if _supabase_client is None: raise HTTPException(status_code=503, detail="Database client not initialized")
    return _supabase_client

async def get_current_user(payload: Dict[str, Any] = Depends(verify_token), supabase: Client = Depends(get_supabase_client)) -> Dict[str, Any]:
    user_id = payload.get("sub")
    if not user_id: raise HTTPException(status_code=401, detail="Invalid token payload")
    profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).single().execute()
    if not profile_res.data: raise HTTPException(status_code=404, detail="User profile not found")
    return profile_res.data

def get_notification_service() -> NotificationService:
    if _notification_service is None: raise HTTPException(status_code=503, detail="Notification service not initialized")
    return _notification_service
    
def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)):
    if not current_user.get("is_admin", False): raise HTTPException(status_code=403, detail="Admin privileges required")

# --- 3. PYDANTIC MODELS ---
class UserProfile(BaseModel): id: str; email: EmailStr; first_name: Optional[str] = None; last_name: Optional[str] = None
class SessionResponse(BaseModel): session_id: UUID
class ConsentUpdatePayload(BaseModel): session_id: UUID; preferences: Dict[str, bool]
class InvestorContactPayload(BaseModel): name: str; email: EmailStr; company: Optional[str] = None; checkSize: Optional[str] = None; message: Optional[str] = None
class KYCSubmission(BaseModel): document_type: str; document_data: str
class PaymentRequest(BaseModel): recipient_email: EmailStr; amount: float; currency: str = "USDS"
class PaymentResponse(BaseModel): transaction_id: str; status: str; amount: float; currency: str; timestamp: datetime
class MFASetupResponse(BaseModel): secret: str; qr_code_url: str
class MFAVerifyRequest(BaseModel): token: str
class PortfolioHolding(BaseModel): id: str; user_id: str; asset: str; amount: float; value_usd: float

# --- 4. LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _supabase_client, _notification_service
    logger.info("Application startup...")
    current_settings = get_settings()
    
    _supabase_client = create_client(current_settings.VITE_SUPABASE_URL, current_settings.SUPABASE_SERVICE_KEY.get_secret_value())
    _supabase_client.from_("user_profiles").select("id").limit(1).execute()
    logger.info("Supabase client connected.")
    
    email_service = EmailService(current_settings)
    _notification_service = NotificationService(email_service)
    
    yield
    logger.info("Application shutdown.")

# --- 5. FASTAPI APP ---
app = FastAPI(title="Seamount.io API", version="1.5.1", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- 6. API ROUTES ---

# Section: Public & System Routes
@app.get("/api/v1/health", tags=["System"])
def health_check(): return {"status": "healthy"}

@app.post("/api/v1/session/initialize", response_model=SessionResponse, tags=["Session"])
async def initialize_session(request: Request, user_agent: Optional[str] = Header(None, alias="User-Agent"), supabase: Client = Depends(get_supabase_client), current_settings: Settings = Depends(get_settings)):
    ip_address = request.client.host
    session_data = {"id": str(uuid4()), "ip_address": ip_address, "user_agent": user_agent}
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(f"https://ipinfo.io/{ip_address}?token={current_settings.IPINFO_TOKEN.get_secret_value()}") as response:
                if response.status == 200:
                    ip_data = await response.json()
                    session_data.update({"isp": ip_data.get("org"), "country": ip_data.get("country"), "city": ip_data.get("city"), "is_vpn": ip_data.get("privacy", {}).get("vpn", False)})
    except Exception as e: logger.error(f"IPinfo enrichment failed: {e}")
    
    insert_res = supabase.from_("user_sessions").insert(session_data).execute()
    if not insert_res.data: raise HTTPException(status_code=500, detail="Failed to create session.")
    
    session_id = insert_res.data[0]['id']
    response = JSONResponse(content={"session_id": session_id})
    response.set_cookie(key="seamount_session_id", value=session_id, max_age=31536000, httponly=True, samesite="lax", secure=True)
    return response

@app.post("/api/v1/consent/update", tags=["Session"])
async def update_consent(payload: ConsentUpdatePayload, supabase: Client = Depends(get_supabase_client)):
    res = supabase.from_("user_sessions").update({"consent_preferences": payload.preferences}).eq("id", str(payload.session_id)).execute()
    if not res.data: raise HTTPException(status_code=404, detail="Session not found.")
    return {"message": "Consent updated successfully"}

@app.post("/api/v1/investor-contact", tags=["Public"])
async def investor_contact(payload: InvestorContactPayload, supabase: Client = Depends(get_supabase_client), notifier: NotificationService = Depends(get_notification_service)):
    supabase.from_("investor_contacts").insert(payload.dict()).execute()
    subject = f"New Investor Contact: {payload.name}"
    body = f"""<html><body><p><strong>Name:</strong> {payload.name}</p><p><strong>Email:</strong> {payload.email}</p></body></html>"""
    await notifier.email_service.send_email(subject, ["investors@seamount.io"], body)
    return {"message": "Contact request submitted successfully."}

# Section: Authenticated User Routes
@app.get("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user

@app.post("/api/v1/user/kyc", tags=["User"])
async def update_kyc(submission: KYCSubmission, current_user: Dict[str, Any] = Depends(get_current_user), notifier: NotificationService = Depends(get_notification_service), supabase: Client = Depends(get_supabase_client)):
    user_id = current_user["id"]
    kyc_data = {"user_id": user_id, "document_type": submission.document_type, "document_data": submission.document_data, "status": "pending"}
    supabase.from_("kyc_documents").insert(kyc_data).execute()
    supabase.from_("user_profiles").update({"kyc_status": "in_progress"}).eq("id", user_id).execute()
    await notifier.send_kyc_update(current_user["email"], "in_progress", "Your documents have been received and are now under review.")
    return {"message": "KYC documents submitted for review."}

@app.post("/api/v1/payments/send", response_model=PaymentResponse, tags=["Payments"])
async def send_payment(req: PaymentRequest, current_user: Dict[str, Any] = Depends(get_current_user), supabase: Client = Depends(get_supabase_client), notifier: NotificationService = Depends(get_notification_service)):
    recipient_res = supabase.from_("user_profiles").select("id").eq("email", req.recipient_email).single().execute()
    if not recipient_res.data: raise HTTPException(status_code=404, detail="Recipient not found")
    
    tx_id = str(uuid4())
    tx_data = {"id": tx_id, "sender_id": current_user["id"], "recipient_id": recipient_res.data["id"], "amount": req.amount, "currency": req.currency, "status": "completed"}
    supabase.from_("transactions").insert(tx_data).execute()
    # Assuming a fee for notification purposes
    await notifier.send_transfer_notifications(current_user["email"], req.recipient_email, req.amount, fee=0.01)
    return PaymentResponse(**tx_data, timestamp=datetime.utcnow())

@app.get("/api/v1/user/portfolio", response_model=List[PortfolioHolding], tags=["Portfolio"])
def get_portfolio(current_user: Dict[str, Any] = Depends(get_current_user), supabase: Client = Depends(get_supabase_client)):
    holdings = supabase.from_("user_portfolios").select("*").eq("user_id", current_user["id"]).execute()
    return holdings.data or []

@app.post("/api/v1/user/mfa/setup", response_model=MFASetupResponse, tags=["Security"])
async def setup_mfa(current_user: Dict[str, Any] = Depends(get_current_user), supabase: Client = Depends(get_supabase_client)):
    secret = pyotp.random_base32()
    qr_url = pyotp.TOTP(secret).provisioning_uri(current_user["email"], issuer_name="Seamount.io")
    supabase.from_("user_mfa").insert({"user_id": current_user["id"], "secret": secret, "enabled": False}).execute()
    return MFASetupResponse(secret=secret, qr_code_url=qr_url)

@app.post("/api/v1/user/mfa/verify", tags=["Security"])
async def verify_mfa(req: MFAVerifyRequest, current_user: Dict[str, Any] = Depends(get_current_user), supabase: Client = Depends(get_supabase_client)):
    user_id = current_user["id"]
    mfa_res = supabase.from_("user_mfa").select("secret").eq("user_id", user_id).single().execute()
    if not mfa_res.data or not pyotp.TOTP(mfa_res.data["secret"]).verify(req.token):
        raise HTTPException(status_code=401, detail="Invalid MFA token")
    supabase.from_("user_mfa").update({"enabled": True}).eq("user_id", user_id).execute()
    return {"message": "MFA verified and enabled successfully."}

# Section: Admin Routes
@app.get("/api/v1/admin/users", response_model=List[UserProfile], tags=["Admin"], dependencies=[Depends(require_admin)])
def get_all_users(supabase: Client = Depends(get_supabase_client)):
    return supabase.from_("user_profiles").select("*").execute().data or []