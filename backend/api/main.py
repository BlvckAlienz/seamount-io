# ==============================================================================
# Seamount.io API - Main Application
# Version: 1.1.2 (Audit Log Hotfix)
# ==============================================================================

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, EmailStr
from supabase import create_client, Client
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timedelta
import os
import aiohttp
import smtplib
from email.mime.text import MIMEText
from jose import JWTError, jwt
from passlib.context import CryptContext
import pyotp
import json
import base64
from cryptography.hazmat.primitives.asymmetric import rsa

# --- 1. SETUP LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 2. GLOBAL STATE (Managed by Lifespan) ---
_supabase_client: Optional[Client] = None
_database_service: Optional['DatabaseService'] = None
_audit_service: Optional['AuditService'] = None
jwks_cache: Dict[str, Any] = {}
jwks_cache_expiry: Optional[datetime] = None

# --- 3. CONFIGURATION ---
class Settings:
    VITE_SUPABASE_URL: str = os.getenv("VITE_SUPABASE_URL")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY")
    PORT: int = int(os.getenv("PORT", 8000))
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "")
    MAIL_SERVER: Optional[str] = os.getenv("MAIL_SERVER")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))
    MAIL_USERNAME: Optional[str] = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: Optional[str] = os.getenv("MAIL_PASSWORD")
    MAIL_FROM: Optional[str] = os.getenv("MAIL_FROM")
    
    @property
    def JWKS_URL(self) -> Optional[str]:
        if not self.VITE_SUPABASE_URL: return None
        return f"{self.VITE_SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def ALLOWED_ORIGINS_LIST(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')] if self.ALLOWED_ORIGINS else []

settings = Settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- 4. AUTHENTICATION & DEPENDENCIES ---
async def fetch_jwks() -> Dict[str, Any]:
    global jwks_cache, jwks_cache_expiry
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry:
        return jwks_cache
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(settings.JWKS_URL) as response:
                response.raise_for_status()
                jwks_data = await response.json()
                jwks_cache, jwks_cache_expiry = jwks_data, datetime.utcnow() + timedelta(hours=1)
                logger.info("JWKS fetched and cached successfully")
                return jwks_data
    except Exception as e:
        logger.error(f"FATAL: JWKS fetch failed: {e}")
        raise HTTPException(status_code=503, detail="Authentication service is unavailable.")

def jwk_to_pem(jwk: Dict[str, Any]) -> bytes:
    if jwk.get('kty') != 'RSA': raise ValueError("Unsupported key type")
    n = int.from_bytes(base64.urlsafe_b64decode(jwk['n'] + '=='), 'big')
    e = int.from_bytes(base64.urlsafe_b64decode(jwk['e'] + '=='), 'big')
    return rsa.RSAPublicNumbers(e, n).public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

async def verify_token(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid, alg = unverified_header.get('kid'), unverified_header.get('alg')
        if not kid or alg != 'RS256': raise JWTError("Invalid token format")
        
        jwks = await fetch_jwks()
        key = next((k for k in jwks.get('keys', []) if k.get('kid') == kid), None)
        if not key: raise JWTError("Public key for token not found")

        return jwt.decode(token, jwk_to_pem(key), algorithms=[alg], audience='authenticated')
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

# Service Dependencies
def get_supabase_client() -> Client:
    if _supabase_client is None: raise HTTPException(status_code=503, detail="Database client not initialized")
    return _supabase_client
def get_db() -> 'DatabaseService':
    if _database_service is None: raise HTTPException(status_code=503, detail="Database service not initialized")
    return _database_service
def get_audit() -> 'AuditService':
    if _audit_service is None: raise HTTPException(status_code=503, detail="Audit service not initialized")
    return _audit_service

# User Dependencies
async def get_current_user(payload: Dict[str, Any] = Depends(verify_token), supabase: Client = Depends(get_supabase_client)) -> Dict[str, Any]:
    user_id = payload.get("sub")
    if not user_id: raise HTTPException(status_code=401, detail="Invalid token payload")
    
    profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).single().execute()
    if profile_res.data:
        return profile_res.data

    logger.warning(f"Profile for user {user_id} not found. Attempting to auto-create.")
    new_profile_data = {"id": user_id, "email": payload.get("email")}
    creation_res = supabase.from_("user_profiles").insert(new_profile_data, returning="representation").single().execute()
    if not creation_res.data:
        raise HTTPException(status_code=500, detail="Failed to retrieve or create user profile.")
    return creation_res.data

def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)):
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin privileges required")

# --- 5. DATA MODELS (PYDANTIC) ---
class UserProfile(BaseModel):
    id: str; email: EmailStr; first_name: Optional[str] = None; last_name: Optional[str] = None;
class InvestorContactPayload(BaseModel):
    name: str; email: EmailStr; company: Optional[str] = None; checkSize: Optional[str] = None; message: Optional[str] = None
class KYCSubmission(BaseModel):
    document_type: str; document_data: str # Base64 encoded string
class PaymentRequest(BaseModel):
    recipient_email: EmailStr; amount: float; currency: str = "USDS"
class PaymentResponse(BaseModel):
    transaction_id: str; status: str; amount: float; currency: str; timestamp: datetime
class MFASetupResponse(BaseModel):
    secret: str; qr_code_url: str
class MFAVerifyRequest(BaseModel):
    token: str
class PortfolioHolding(BaseModel):
    id: str; user_id: str; asset: str; amount: float; value_usd: float
class ConsentPayload(BaseModel):
    preferences: Dict[str, bool]

# --- 6. SERVICE CLASSES ---
class DatabaseService:
    def __init__(self, supabase: Client): self.supabase = supabase
    def insert(self, table: str, data: Dict[str, Any], returning="minimal"):
        return self.supabase.from_(table).insert(data, returning=returning).execute()
    def update(self, table: str, match_query: Dict[str, Any], data: Dict[str, Any]):
        return self.supabase.from_(table).update(data).match(match_query).execute()

class AuditService:
    def __init__(self, db_service: DatabaseService): self.db = db_service
    async def log(self, user_id: Optional[str], action: str, details: Dict[str, Any]):
        try:
            self.db.insert("compliance_logs", {
                "user_id": user_id, "action_taken": action, "details": details
            })
            logger.info(f"AUDIT: {action} by {user_id or 'System'}")
        except Exception as e:
            logger.error(f"Failed to log audit action '{action}': {e}")

# --- 7. LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _supabase_client, _database_service, _audit_service
    logger.info("Application startup...")
    try:
        if not all([settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY]):
            raise ValueError("FATAL: VITE_SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        _supabase_client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        _supabase_client.from_("user_profiles").select("id").limit(1).execute()
        logger.info("Supabase client connected.")
        
        _database_service = DatabaseService(_supabase_client)
        _audit_service = AuditService(_database_service)
        
        if settings.JWKS_URL: await fetch_jwks()
        
        # CORRECTED: Pass None for system-level actions without a user.
        await _audit_service.log(user_id=None, action="api_startup", details={"status": "success"})
        
        yield
    finally:
        logger.info("Application shutdown.")
        if _audit_service:
            # CORRECTED: Pass None for system-level actions without a user.
            await _audit_service.log(user_id=None, action="api_shutdown", details={"status": "complete"})

# --- 8. FASTAPI APP ---
app = FastAPI(title="Seamount.io API", version="1.1.2", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS_LIST,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
@app.exception_handler(Exception)
async def general_exception_handler(req: Request, exc: Exception):
    logger.error(f"Unhandled exception for {req.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "An internal server error occurred."})

# --- 9. API ROUTES ---

# Section: Public Routes
@app.get("/api/v1/health", tags=["System"])
def health_check(): return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/api/v1/investor-contact", tags=["Public"])
async def investor_contact(payload: InvestorContactPayload, db: DatabaseService = Depends(get_db), audit: AuditService = Depends(get_audit)):
    contact_data = payload.dict()
    db.insert("investor_contacts", contact_data)
    await audit.log(user_id=None, action="investor_contact_form", details={"email": payload.email})
    return {"message": "Contact request submitted successfully."}

# Section: Authenticated User Routes
@app.get("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user

@app.post("/api/v1/user/kyc", tags=["User"])
async def update_kyc(submission: KYCSubmission, current_user: Dict[str, Any] = Depends(get_current_user), db: DatabaseService = Depends(get_db), audit: AuditService = Depends(get_audit)):
    user_id = current_user["id"]
    kyc_data = {"user_id": user_id, "document_type": submission.document_type, "document_data": submission.document_data, "status": "pending"}
    db.insert("kyc_documents", kyc_data)
    db.update("user_profiles", {"id": user_id}, {"kyc_status": "in_progress"})
    await audit.log(user_id, "kyc_submitted", {"document_type": submission.document_type})
    return {"message": "KYC documents submitted for review."}

@app.get("/api/v1/user/kyc-status", tags=["User"])
def get_kyc_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {"kyc_status": current_user.get("kyc_status", "pending"), "kyc_level": current_user.get("kyc_level", 0)}

@app.post("/api/v1/payments/send", response_model=PaymentResponse, tags=["Payments"])
async def send_payment(req: PaymentRequest, current_user: Dict[str, Any] = Depends(get_current_user), db: DatabaseService = Depends(get_db), audit: AuditService = Depends(get_audit), supabase: Client = Depends(get_supabase_client)):
    recipient_res = supabase.from_("user_profiles").select("id").eq("email", req.recipient_email).single().execute()
    if not recipient_res.data: raise HTTPException(status_code=404, detail="Recipient not found")
    
    tx_id = str(uuid4())
    tx_data = {"id": tx_id, "sender_id": current_user["id"], "recipient_id": recipient_res.data["id"], "amount": req.amount, "currency": req.currency, "status": "completed"}
    db.insert("transactions", tx_data)
    await audit.log(current_user["id"], "payment_sent", {"tx_id": tx_id, "to": req.recipient_email, "amount": req.amount})
    return PaymentResponse(**tx_data, timestamp=datetime.utcnow())

@app.get("/api/v1/payments/history", response_model=List[Dict], tags=["Payments"])
def get_payment_history(current_user: Dict[str, Any] = Depends(get_current_user), supabase: Client = Depends(get_supabase_client)):
    user_id = current_user["id"]
    sent = supabase.from_("transactions").select("*").eq("sender_id", user_id).execute().data or []
    received = supabase.from_("transactions").select("*").eq("recipient_id", user_id).execute().data or []
    return sorted(sent + received, key=lambda x: x.get("created_at", ""), reverse=True)

@app.get("/api/v1/user/portfolio", response_model=List[PortfolioHolding], tags=["Portfolio"])
def get_portfolio(current_user: Dict[str, Any] = Depends(get_current_user), supabase: Client = Depends(get_supabase_client)):
    holdings = supabase.from_("user_portfolios").select("*").eq("user_id", current_user["id"]).execute()
    return holdings.data or []

@app.post("/api/v1/user/consent", tags=["User"])
async def update_consent(consent: ConsentPayload, current_user: Dict[str, Any] = Depends(get_current_user), db: DatabaseService = Depends(get_db), audit: AuditService = Depends(get_audit)):
    user_id = current_user["id"]
    db.update("user_profiles", {"id": user_id}, {"consent": consent.preferences})
    await audit.log(user_id, "consent_updated", consent.preferences)
    return {"message": "Consent preferences updated."}

# Section: Security Routes
@app.post("/api/v1/user/mfa/setup", response_model=MFASetupResponse, tags=["Security"])
async def setup_mfa(current_user: Dict[str, Any] = Depends(get_current_user), db: DatabaseService = Depends(get_db), audit: AuditService = Depends(get_audit)):
    secret = pyotp.random_base32()
    qr_url = pyotp.TOTP(secret).provisioning_uri(current_user["email"], issuer_name="Seamount.io")
    db.insert("user_mfa", {"user_id": current_user["id"], "secret": secret, "enabled": False}, returning="minimal")
    await audit.log(current_user["id"], "mfa_setup_initiated", {})
    return MFASetupResponse(secret=secret, qr_code_url=qr_url)

@app.post("/api/v1/user/mfa/verify", tags=["Security"])
async def verify_mfa(req: MFAVerifyRequest, current_user: Dict[str, Any] = Depends(get_current_user), db: DatabaseService = Depends(get_db), audit: AuditService = Depends(get_audit), supabase: Client = Depends(get_supabase_client)):
    user_id = current_user["id"]
    mfa_res = supabase.from_("user_mfa").select("secret").eq("user_id", user_id).single().execute()
    if not mfa_res.data or not pyotp.TOTP(mfa_res.data["secret"]).verify(req.token):
        raise HTTPException(status_code=401, detail="Invalid MFA token")
    db.update("user_mfa", {"user_id": user_id}, {"enabled": True})
    await audit.log(user_id, "mfa_enabled", {})
    return {"message": "MFA verified and enabled successfully."}

# Section: Admin Routes
@app.get("/api/v1/admin/users", response_model=List[UserProfile], tags=["Admin"], dependencies=[Depends(require_admin)])
def get_all_users(supabase: Client = Depends(get_supabase_client)):
    return supabase.from_("user_profiles").select("*").execute().data or []

@app.post("/api/v1/admin/kyc/approve/{user_id}", tags=["Admin"], dependencies=[Depends(require_admin)])
async def approve_kyc(user_id: str, current_user: Dict[str, Any] = Depends(get_current_user), db: DatabaseService = Depends(get_db), audit: AuditService = Depends(get_audit)):
    db.update("user_profiles", {"id": user_id}, {"kyc_status": "approved", "kyc_level": 2})
    await audit.log(current_user["id"], "admin_kyc_approved", {"target_user_id": user_id})
    return {"message": f"KYC for user {user_id} approved."}

# --- 10. MAIN EXECUTION ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)