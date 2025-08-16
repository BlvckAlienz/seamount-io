# ==============================================================================
# Seamount.io API - Main Application
# Version: 1.2.1 (Final & Comprehensive)
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
import os
import aiohttp
from jose import JWTError, jwt
import base64
from cryptography.hazmat.primitives.asymmetric import rsa

# --- 1. SETUP LOGGING & GLOBAL STATE ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None
jwks_cache: Dict[str, Any] = {}
jwks_cache_expiry: Optional[datetime] = None

# --- 2. CONFIGURATION ---
class Settings:
    VITE_SUPABASE_URL: str = os.getenv("VITE_SUPABASE_URL")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY")
    IPINFO_TOKEN: str = os.getenv("IPINFO_TOKEN")
    PORT: int = int(os.getenv("PORT", 8000))
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "")
    
    @property
    def JWKS_URL(self) -> Optional[str]:
        if not self.VITE_SUPABASE_URL: return None
        return f"{self.VITE_SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def ALLOWED_ORIGINS_LIST(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')] if self.ALLOWED_ORIGINS else []

settings = Settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

# --- 3. AUTHENTICATION & DEPENDENCIES ---
async def fetch_jwks() -> Dict[str, Any]:
    global jwks_cache, jwks_cache_expiry
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry: return jwks_cache
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(settings.JWKS_URL) as response:
                response.raise_for_status()
                jwks_data = await response.json()
                jwks_cache, jwks_cache_expiry = jwks_data, datetime.utcnow() + timedelta(hours=1)
                return jwks_data
    except Exception as e: raise HTTPException(status_code=503, detail=f"Authentication service unavailable: {e}")

def jwk_to_pem(jwk: Dict[str, Any]) -> bytes:
    n = int.from_bytes(base64.urlsafe_b64decode(jwk['n'] + '=='), 'big')
    e = int.from_bytes(base64.urlsafe_b64decode(jwk['e'] + '=='), 'big')
    return rsa.RSAPublicNumbers(e, n).public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)

async def verify_token(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        jwks = await fetch_jwks()
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
    
def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)):
    if not current_user.get("is_admin", False): raise HTTPException(status_code=403, detail="Admin privileges required")

# --- 4. PYDANTIC MODELS ---
class UserProfile(BaseModel): id: str; email: EmailStr; first_name: Optional[str] = None; last_name: Optional[str] = None;
class SessionResponse(BaseModel): session_id: UUID
class ConsentUpdatePayload(BaseModel): session_id: UUID; preferences: Dict[str, bool]
class InvestorContactPayload(BaseModel): name: str; email: EmailStr; company: Optional[str] = None; checkSize: Optional[str] = None; message: Optional[str] = None
class PaymentRequest(BaseModel): recipient_email: EmailStr; amount: float; currency: str = "USDS"
class PaymentResponse(BaseModel): transaction_id: str; status: str; amount: float; currency: str; timestamp: datetime

# --- 5. LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _supabase_client
    logger.info("Application startup...")
    try:
        if not all([settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY, settings.IPINFO_TOKEN]):
            raise ValueError("FATAL: VITE_SUPABASE_URL, SUPABASE_SERVICE_KEY, and IPINFO_TOKEN must be set.")
        _supabase_client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        _supabase_client.from_("user_profiles").select("id").limit(1).execute()
        logger.info("Supabase client connected.")
        yield
    finally: logger.info("Application shutdown.")

# --- 6. FASTAPI APP ---
app = FastAPI(title="Seamount.io API", version="1.2.1", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS_LIST, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- 7. API ROUTES ---
@app.get("/api/v1/health", tags=["System"])
def health_check(): return {"status": "healthy"}

@app.post("/api/v1/session/initialize", response_model=SessionResponse, tags=["Session"])
async def initialize_session(request: Request, user_agent: Optional[str] = Header(None, alias="User-Agent"), supabase: Client = Depends(get_supabase_client)):
    ip_address = request.client.host
    session_data = {"id": str(uuid4()), "ip_address": ip_address, "user_agent": user_agent}
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(f"https://ipinfo.io/{ip_address}?token={settings.IPINFO_TOKEN}") as response:
                if response.status == 200:
                    ip_data = await response.json()
                    session_data.update({
                        "isp": ip_data.get("org"), "country": ip_data.get("country"), "city": ip_data.get("city"),
                        "is_vpn": ip_data.get("privacy", {}).get("vpn", False)
                    })
    except Exception as e: logger.error(f"IPinfo enrichment failed for IP {ip_address}: {e}")
    
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
async def investor_contact(payload: InvestorContactPayload, supabase: Client = Depends(get_supabase_client)):
    supabase.from_("investor_contacts").insert(payload.dict()).execute()
    return {"message": "Contact request submitted successfully."}

@app.get("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user
    
@app.post("/api/v1/payments/send", response_model=PaymentResponse, tags=["Payments"])
async def send_payment(req: PaymentRequest, current_user: Dict[str, Any] = Depends(get_current_user), supabase: Client = Depends(get_supabase_client)):
    recipient_res = supabase.from_("user_profiles").select("id").eq("email", req.recipient_email).single().execute()
    if not recipient_res.data: raise HTTPException(status_code=404, detail="Recipient not found")
    
    tx_id = str(uuid4())
    tx_data = {"id": tx_id, "sender_id": current_user["id"], "recipient_id": recipient_res.data["id"], "amount": req.amount, "currency": req.currency, "status": "completed"}
    supabase.from_("transactions").insert(tx_data).execute()
    return PaymentResponse(**tx_data, timestamp=datetime.utcnow())
    
@app.get("/api/v1/admin/users", response_model=List[UserProfile], tags=["Admin"], dependencies=[Depends(require_admin)])
def get_all_users(supabase: Client = Depends(get_supabase_client)):
    return supabase.from_("user_profiles").select("*").execute().data or []