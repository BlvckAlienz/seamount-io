# File Location: backend/main.py
# Description: Production-ready API Gateway for Seamount.io on Vercel

import logging
import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import create_client, Client
from decimal import Decimal
from typing import List, Dict, Any, Optional

# --- Core Components ---
from config import get_settings, Settings
from models import UserProfile
from auth_dependency import get_current_user

# --- Services Import ---
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

# --- Configuration & Logging ---
settings: Settings = get_settings()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Supabase client
try:
    supabase_client: Client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")
    raise

# --- Service Initialization with Error Handling ---
try:
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
    logger.info("All services initialized successfully")
except Exception as e:
    logger.error(f"Service initialization failed: {e}")
    raise

# --- FastAPI App Configuration ---
app = FastAPI(
    title="Seamount.io API Gateway",
    description="Unified API for Seamount Financial Platform",
    version="1.0.0",
    docs_url="/api/docs" if os.getenv("ENVIRONMENT") == "development" else None,
    redoc_url="/api/redoc" if os.getenv("ENVIRONMENT") == "development" else None
)

# --- CORS Middleware (Critical for Vercel) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://seamount.io",
        "https://*.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class PaymentPayload(BaseModel):
    recipient_address: str
    amount: Decimal = Field(..., gt=0)
    memo: str = ""

class OnboardingStepPayload(BaseModel):
    current_step: int
    data: Dict[str, Any]

class AdminDependency:
    async def __call__(self, current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if not getattr(current_user, 'is_admin', False):
            raise HTTPException(status_code=403, detail="Administrator access required")
        return current_user

get_current_admin_user = AdminDependency()

# --- Error Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return {"error": "Internal server error", "detail": str(exc)}

# --- API Routes ---
@app.get("/api/health")
async def health_check():
    try:
        # Test critical dependencies
        await database_service.health_check() if hasattr(database_service, 'health_check') else None
        return {"status": "healthy", "service": "seamount-api", "version": "1.0.0"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# --- User & Onboarding ---
@app.get("/api/user/profile", response_model=UserProfile)
async def get_user_profile(current_user: UserProfile = Depends(get_current_user)):
    return current_user

@app.get("/api/onboarding/status")
async def get_onboarding_status(current_user: UserProfile = Depends(get_current_user)):
    try:
        return await onboarding_service.get_onboarding_status(str(current_user.id))
    except Exception as e:
        logger.error(f"Onboarding status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve onboarding status")

@app.post("/api/onboarding/advance")
async def advance_onboarding_step(
    payload: OnboardingStepPayload, 
    current_user: UserProfile = Depends(get_current_user)
):
    try:
        return await onboarding_service.advance_step(
            str(current_user.id), 
            payload.current_step, 
            payload.data
        )
    except Exception as e:
        logger.error(f"Onboarding advance error: {e}")
        raise HTTPException(status_code=500, detail="Failed to advance onboarding")

@app.post("/api/kyc/start-session")
async def start_kyc_session(current_user: UserProfile = Depends(get_current_user)):
    try:
        return await kyc_service.start_verification_session(
            str(current_user.id), 
            current_user.email, 
            current_user.country_code
        )
    except Exception as e:
        logger.error(f"KYC session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start KYC session")

# --- Wallet & Payments ---
@app.get("/api/wallet/balance")
async def get_wallet_balance(current_user: UserProfile = Depends(get_current_user)):
    if not current_user.algorand_address:
        raise HTTPException(status_code=400, detail="Wallet not provisioned")
    
    try:
        balance = await algorand_service.get_usds_balance(current_user.algorand_address)
        return {"address": current_user.algorand_address, "balance_usds": str(balance)}
    except Exception as e:
        logger.error(f"Balance retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve balance")

@app.post("/api/payments/p2p")
async def send_p2p_payment(
    payload: PaymentPayload, 
    current_user: UserProfile = Depends(get_current_user)
):
    if not current_user.algorand_address:
        raise HTTPException(status_code=400, detail="Wallet not provisioned")
    
    try:
        result = await payment_service.process_p2p_payment(
            sender_profile=current_user.dict(),
            recipient_address=payload.recipient_address,
            amount=payload.amount,
            memo=payload.memo
        )
        return result
    except ValueError as ve:
        logger.warning(f"Payment validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Payment processing error: {e}")
        raise HTTPException(status_code=500, detail="Payment failed")

@app.get("/api/payments/history")
async def get_payment_history(
    limit: int = 20, 
    current_user: UserProfile = Depends(get_current_user)
):
    try:
        return await database_service.get_payment_history(str(current_user.id), limit)
    except Exception as e:
        logger.error(f"Payment history error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve payment history")

# --- Market Data ---
@app.get("/api/market/price/{pair}")
async def get_market_price(pair: str):
    try:
        from_currency, to_currency = pair.upper().split('-')
        price, metadata = await oracle_service.get_price(from_currency, to_currency)
        return {"pair": pair, "price": str(price), "metadata": metadata}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid currency pair format")
    except Exception as e:
        logger.error(f"Price retrieval error: {e}")
        raise HTTPException(status_code=404, detail=f"Price unavailable for {pair}")

# --- Admin & Compliance ---
@app.get("/api/compliance/dashboard")
async def get_compliance_dashboard(
    country_code: Optional[str] = None,
    admin: UserProfile = Depends(get_current_admin_user)
):
    try:
        metrics = await compliance_service.get_dashboard_metrics(country_code)
        return metrics
    except Exception as e:
        logger.error(f"Compliance dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Dashboard metrics unavailable")

# --- Root Route for Vercel ---
@app.get("/")
async def root():
    return {"message": "Seamount.io API Gateway", "status": "operational"}

# Vercel serverless function handler
handler = app