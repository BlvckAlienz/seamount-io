import logging
from fastapi import FastAPI, Depends, HTTPException, Request, Security, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field, EmailStr
from supabase import create_client, Client
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timedelta
import os

# --- Core Config & Models ---
from config import get_settings, Settings
from models import UserProfile
from auth_dependency import get_current_user

# --- Core Services (ALL kept for future use) ---
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
from services.swap_service import SwapService

# --- Initialization ---
settings: Settings = get_settings()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)
supabase_client: Client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY.get_secret_value())

# --- Service Instances ---
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
oracle_service = OracleService(settings, database_service)
payment_service = PaymentService(settings, supabase_client, algorand_service, kyc_service, audit_service, treasury_service, notification_service)
swap_service = SwapService(settings, algorand_service, database_service, wallet_service)
trading_service = TradingService(settings, supabase_client, database_service, algorand_service, swap_service)

# --- App Setup ---
app = FastAPI(
    title="Seamount.io API Gateway",
    description="Unified API for Seamount Financial Platform",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc"
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://seamount.io",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Key ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key in settings.WHITELISTED_API_KEYS:
        return api_key
    raise HTTPException(status_code=403, detail="Invalid or missing API Key")

# --- Global Exception Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {request.method} {request.url} - {exc}", exc_info=True)
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# --- Payload Schemas ---
class PaymentPayload(BaseModel):
    recipient_address: str
    amount: Decimal = Field(..., gt=0)
    memo: Optional[str] = ""

class InvestorContactPayload(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    checkSize: Optional[str] = None
    message: Optional[str] = ""

class WhitelabelQuotePayload(BaseModel):
    from_currency: str
    to_currency: str
    amount: float

class DepositPayload(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str

class ConsentPayload(BaseModel):
    preferences: Dict[str, bool]

# --- Health Routes ---
@app.get("/", tags=["System"])
async def root():
    return {"status": "healthy", "service": "Seamount.io API Gateway"}

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}

# --- Public Routes ---
@app.post("/api/v1/investor-contact", tags=["Public"])
async def investor_contact(payload: InvestorContactPayload):
    logger.info(f"Investor contact: {payload.name} ({payload.email}) - {payload.message}")
    try:
        subject = f"Investor Inquiry from {payload.name}"
        body = f"""
        <html>
            <body>
                <p>Name: {payload.name}</p>
                <p>Email: {payload.email}</p>
                <p>Company: {payload.company or 'N/A'}</p>
                <p>Check Size: {payload.checkSize or 'N/A'}</p>
                <p>Message: {payload.message or 'None'}</p>
            </body>
        </html>
        """
        await email_service.send_email(subject, ["investors@seamount.io"], body)
    except Exception as e:
        logger.error(f"Investor contact email send failed for {payload.email}: {e}")
    return {"status": "success", "message": "Your message has been received."}

# --- User & Payments ---
@app.get("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
async def get_user_profile(current_user: UserProfile = Depends(get_current_user)):
    return current_user

@app.post("/api/v1/payments/p2p", tags=["Payments"])
async def send_p2p_payment(payload: PaymentPayload, current_user: UserProfile = Depends(get_current_user)):
    if not current_user.algorand_address:
        raise HTTPException(status_code=400, detail="Wallet not provisioned")
    return await payment_service.process_p2p_payment(
        sender_profile=current_user.dict(),
        recipient_address=payload.recipient_address,
        amount=payload.amount,
        memo=payload.memo
    )

@app.post("/api/v1/payments/initialize-deposit", tags=["Payments"])
async def initialize_deposit(payload: DepositPayload, current_user: UserProfile = Depends(get_current_user)):
    logger.info(f"Initializing deposit: {payload.amount} {payload.currency} for user {current_user.id}")
    return await payment_service.initialize_fiat_deposit(
        user_id=str(current_user.id),
        user_email=current_user.email,
        amount=payload.amount,
        currency=payload.currency
    )

# --- Market Data ---
@app.get("/api/v1/market/price/{base_currency}/{quote_currency}", tags=["Market Data"])
async def get_market_price(base_currency: str, quote_currency: str, current_user: UserProfile = Depends(get_current_user)):
    try:
        price, metadata = await oracle_service.get_price(base_currency, quote_currency)
        return {"price": str(price), "metadata": metadata}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception:
        raise HTTPException(status_code=500, detail="Could not retrieve market price.")

# --- Whitelabel ---
@app.post("/api/v1/whitelabel/quote", tags=["Whitelabel Services"])
async def get_payment_quote(payload: WhitelabelQuotePayload, api_key: str = Depends(get_api_key)):
    fee = payload.amount * 0.03
    return {
        "from_currency": payload.from_currency.upper(),
        "to_currency": payload.to_currency.upper(),
        "amount_to_send": payload.amount,
        "estimated_fee": fee,
        "estimated_amount_to_receive": payload.amount - fee,
        "quote_id": f"quote_{uuid4()}",
        "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    }

# --- Portfolio ---
@app.get("/api/v1/portfolio/summary", tags=["Portfolio"])
async def get_portfolio_summary(current_user: UserProfile = Depends(get_current_user)):
    # Mocked — integrate with trading_service in future
    return {"total_value": 0.0, "assets": [], "yield": 0.0}

# --- Wallet ---
@app.get("/api/v1/wallet/balance", tags=["Wallet"])
async def get_wallet_balance(current_user: UserProfile = Depends(get_current_user)):
    if not current_user.algorand_address:
        raise HTTPException(status_code=400, detail="Wallet not provisioned")
    balance = await algorand_service.get_usds_balance(current_user.algorand_address)
    return {"balance": str(balance)}

@app.post("/api/v1/user/provision-wallets", tags=["User"])
async def provision_wallets(current_user: UserProfile = Depends(get_current_user)):
    return await wallet_service.provision_user_wallet(str(current_user.id))

# --- Compliance ---
@app.get("/api/v1/compliance/alerts", tags=["Compliance"])
async def get_compliance_alerts(
    status: str,
    severity: Optional[str] = Query(None),
    limit: int = Query(10),
    offset: int = Query(0),
    current_user: UserProfile = Depends(get_current_user)
):
    return await compliance_service.get_alerts_for_review(status, severity, limit, offset)

@app.get("/api/v1/compliance/dashboard", tags=["Compliance"])
async def get_compliance_dashboard(
    country_code: Optional[str] = Query(None),
    current_user: UserProfile = Depends(get_current_user)
):
    return await compliance_service.get_dashboard_metrics(country_code)

# --- Consent ---
@app.post("/api/v1/consent/cookies", tags=["Consent"])
async def set_consent_cookies(payload: ConsentPayload):
    return {"status": "success", "message": "Consent preferences updated."}
