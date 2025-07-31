# File Location: backend/main.py
# Description: The definitive, production-ready API Gateway for Seamount.io.

import logging
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from supabase import create_client, Client
from decimal import Decimal
from typing import List, Dict, Any, Optional

# --- Core Components: The Foundation ---
from config import get_settings, Settings
from models import UserProfile
from auth_dependency import get_current_user

# --- The Orchestra: Import ALL Core Services ---
from services.audit_service import AuditService
from services.email_service import EmailService
from services.notification_service import NotificationService
from services.database_service import DatabaseService
from services.kyc_service import KYCService
from services.wallet_service import WalletService
from services.algorand_service import AlgorandService
from services.onboarding_service import OnboardingService
from services.payment_service import PaymentService
from services.trading_service import TradingService
from services.treasury_service import TreasuryService
from services.oracle_service import OracleService
from services.compliance_service import ComplianceService

# --- Configuration & Initialization ---
settings: Settings = get_settings()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

supabase_client: Client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

# --- Service Instantiation (The Dependency Injection Container) ---
database_service = DatabaseService(settings)
audit_service = AuditService(supabase_client)
email_service = EmailService(settings)
notification_service = NotificationService(email_service)
kyc_service = KYCService(settings, supabase_client, database_service, audit_service)
wallet_service = WalletService(settings, supabase_client)
algorand_service = AlgorandService(settings)
treasury_service = TreasuryService(settings, database_service, algorand_service)
onboarding_service = OnboardingService(settings, supabase_client, wallet_service, kyc_service)
compliance_service = ComplianceService(settings, database_service, kyc_service, audit_service)
oracle_service = OracleService()
payment_service = PaymentService(settings, supabase_client, algorand_service, kyc_service, audit_service, treasury_service, compliance_service)
trading_service = TradingService(supabase_client, algorand_service)

app = FastAPI(
    title="Seamount.io API Gateway",
    description="The single, unified entry point for the Seamount Financial Platform.",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc"
)

# --- Global Exception Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception for request {request.method} {request.url}: {exc}", exc_info=True)
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(status_code=500, content={"detail": "An internal server error occurred."})

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for API Payloads ---
class PaymentPayload(BaseModel):
    recipient_address: str
    amount: Decimal = Field(..., gt=0)
    memo: str = ""

class OnboardingStepPayload(BaseModel):
    current_step: int
    data: Dict[str, Any]
    
class InvestorContactPayload(BaseModel):
    name: str
    email: EmailStr
    company: str
    checkSize: str
    message: Optional[str] = ""

class CookieConsentPayload(BaseModel):
    preferences: Dict[str, bool]

class AdminDependency:
    async def __call__(self, current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if not getattr(current_user, 'is_admin', False):
            raise HTTPException(status_code=403, detail="Administrator access required")
        return current_user

get_current_admin_user = AdminDependency()

# =============================================================================
# API ROUTES
# =============================================================================

@app.get("/api/v1/health", tags=["System"])
async def health_check():
    return {"status": "healthy"}

@app.post("/api/v1/investor-contact", tags=["Public"])
async def investor_contact(payload: InvestorContactPayload):
    logger.info(f"Received investor contact from: {payload.name} ({payload.email})")
    return {"status": "success", "message": "Your message has been received."}

@app.post("/api/v1/consent/cookies", tags=["Public"])
async def save_cookie_consent(payload: CookieConsentPayload, request: Request, current_user: Optional[UserProfile] = Depends(get_current_user)):
    user_id = str(current_user.id) if current_user else None
    consent_data = { "user_id": user_id, "ip_address": request.client.host, "user_agent": request.headers.get("user-agent"), "consent_type": "cookies", "preferences": payload.preferences }
    await database_service.log_event("user_consent", consent_data)
    return {"status": "success", "message": "Consent preferences saved."}

@app.get("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
async def get_user_profile(current_user: UserProfile = Depends(get_current_user)):
    return current_user

@app.post("/api/v1/user/provision-wallet", tags=["User"])
async def provision_wallet(current_user: UserProfile = Depends(get_current_user)):
    if current_user.algorand_address:
        raise HTTPException(status_code=400, detail="Wallet already provisioned.")
    return await wallet_service.provision_user_wallet(str(current_user.id))
    
@app.post("/api/v1/onboarding/advance", tags=["Onboarding"])
async def advance_onboarding_step(payload: OnboardingStepPayload, current_user: UserProfile = Depends(get_current_user)):
    return await onboarding_service.advance_step(str(current_user.id), payload.current_step, payload.data)

@app.post("/api/v1/kyc/start-session", tags=["Onboarding"])
async def start_kyc_session(current_user: UserProfile = Depends(get_current_user)):
    if not current_user.country_code:
        raise HTTPException(status_code=400, detail="User country code is required to start KYC.")
    return await kyc_service.start_verification_session(str(current_user.id), current_user.email, current_user.country_code)

@app.get("/api/v1/wallet/balance", tags=["Payments"])
async def get_wallet_balance(current_user: UserProfile = Depends(get_current_user)):
    if not current_user.algorand_address:
        raise HTTPException(status_code=400, detail="User wallet not provisioned")
    balance = await algorand_service.get_usds_balance(current_user.algorand_address)
    return {"address": current_user.algorand_address, "balance_usds": str(balance)}

@app.post("/api/v1/payments/p2p", tags=["Payments"])
async def send_p2p_payment(payload: PaymentPayload, current_user: UserProfile = Depends(get_current_user)):
    if not current_user.algorand_address:
        raise HTTPException(status_code=400, detail="Wallet not provisioned")
    try:
        return await payment_service.process_p2p_payment(
            sender_profile=current_user.dict(),
            recipient_address=payload.recipient_address,
            amount=payload.amount,
            memo=payload.memo
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@app.get("/api/v1/payments/history", tags=["Payments"])
async def get_payment_history(limit: int = 20, current_user: UserProfile = Depends(get_current_user)):
    return await database_service.get_payment_history(str(current_user.id), limit)

@app.get("/api/v1/compliance/dashboard", tags=["Admin"])
async def get_compliance_dashboard(country_code: Optional[str] = None, admin: UserProfile = Depends(get_current_admin_user)):
    return await compliance_service.get_dashboard_metrics(country_code)