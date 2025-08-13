import logging
from fastapi import FastAPI, Depends, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr
from supabase import create_client, Client
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timedelta
import os
import aiohttp
from algosdk.v2client import algod
from algosdk import account, mnemonic, transaction
import smtplib
from email.mime.text import MIMEText
from jose import JWTError, jwt
from passlib.context import CryptContext
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pyotp

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Settings:
    VITE_SUPABASE_URL: str = os.getenv("VITE_SUPABASE_URL", "https://opqnoficlhbylxfpaehp.supabase.co")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY")
    ALGORAND_NODE_URL: str = os.getenv("ALGORAND_NODE_URL", "https://mainnet-algorand.api.purestake.io/ps2")
    ALGORAND_API_KEY: str = os.getenv("ALGORAND_API_KEY")
    ALGORAND_CREATOR_MNEMONIC: str = os.getenv("ALGORAND_CREATOR_MNEMONIC")
    USDS_ASSET_ID: int = int(os.getenv("USDS_ASSET_ID", 0))
    TREASURY_ADDRESS: str = os.getenv("TREASURY_ADDRESS")
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "workplace.truehost.cloud")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "no-reply@seamount.io")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "no-reply@seamount.io")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "True") == "True"
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "False") == "True"
    JWT_SECRET: str = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    PORT: int = int(os.getenv("PORT", 8000))

    class Config:
        case_sensitive = True

def get_settings() -> Settings:
    required_vars = [
        "SUPABASE_SERVICE_KEY",
        "JWT_SECRET",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    try:
        return Settings()
    except Exception as e:
        logger.error(f"Failed to load settings: {str(e)}")
        raise

app = FastAPI(
    title="Seamount.io API",
    version="1.0.0",
    description="P2P cross-border payment and yield-farming stablecoin network"
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.seamount.io", "https://seamount.io", "http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class UserProfile(BaseModel):
    id: str
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    country_code: Optional[str] = None
    kyc_level: int = 0
    kyc_status: str = "pending"
    is_admin: bool = False
    algorand_address: Optional[str] = None

class InvestorContactPayload(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    checkSize: Optional[str] = None
    message: Optional[str] = None

class WhitelabelQuotePayload(BaseModel):
    amount: Decimal
    from_currency: str
    to_currency: str

class ConsentPayload(BaseModel):
    preferences: Dict[str, bool]

class KYCSubmission(BaseModel):
    user_id: str
    document_type: str
    document_data: str
    submitted_at: Optional[datetime] = None

class PaymentRequest(BaseModel):
    sender_id: str
    recipient_email: EmailStr
    amount: float
    currency: str = "USDS"

class PaymentResponse(BaseModel):
    transaction_id: str
    status: str
    amount: float
    currency: str
    timestamp: datetime

class MintRequest(BaseModel):
    amount: float
    recipient_address: str

class BurnRequest(BaseModel):
    amount: float
    sender_address: str

class Token(BaseModel):
    access_token: str
    token_type: str

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
    currency: str
    acquired_at: datetime
    value_usd: float

# Services
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,))
)
def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    settings = get_settings()
    try:
        client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        logger.info("Supabase client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise

def get_algorand_client() -> Optional[algod.AlgodClient]:
    """Initialize Algorand client - returns None if not configured"""
    settings = get_settings()
    
    if not settings.ALGORAND_API_KEY or not settings.ALGORAND_CREATOR_MNEMONIC:
        logger.warning("Algorand not configured - skipping Algorand client initialization")
        return None
        
    try:
        algod_client = algod.AlgodClient(
            settings.ALGORAND_API_KEY,
            settings.ALGORAND_NODE_URL,
            headers={"X-API-Key": settings.ALGORAND_API_KEY}
        )
        # Test connection
        algod_client.status()
        logger.info("Algorand client initialized successfully")
        return algod_client
    except Exception as e:
        logger.warning(f"Failed to initialize Algorand client: {str(e)}")
        return None

class DatabaseService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def insert(self, table: str, data: Dict[str, Any], upsert: bool = False):
        try:
            if upsert:
                response = self.supabase.from_(table).upsert(data).execute()
            else:
                response = self.supabase.from_(table).insert(data).execute()
            if not response.data:
                raise HTTPException(status_code=400, detail=f"Failed to insert into {table}")
            return response.data
        except Exception as e:
            logger.error(f"Database insert error for table {table}: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def select(self, table: str, filters: Dict[str, Any] = None):
        try:
            query = self.supabase.from_(table).select("*")
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Database select error for table {table}: {str(e)}")
            raise

class AuditService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    def log_action(self, user_id: str, action: str, details: Dict[str, Any]):
        """Log action with graceful degradation if audit fails"""
        try:
            self.supabase.from_("compliance_logs").insert({
                "user_id": user_id,
                "action": action,
                "details": details,
                "timestamp": datetime.utcnow().isoformat(),
            }).execute()
            logger.debug(f"Logged action: {action} for user {user_id}")
        except Exception as e:
            # Don't fail the entire request if audit logging fails
            logger.warning(f"Failed to log action '{action}' for user {user_id}: {str(e)}")

class TreasuryService:
    def __init__(self, algorand_client: Optional[algod.AlgodClient], supabase: Client, reserve_address: str):
        self.algorand_client = algorand_client
        self.supabase = supabase
        self.reserve_address = reserve_address

    def monitor_demand(self):
        try:
            total_supply = self.supabase.from_("backing_reserves").select("amount").eq("action", "mint").execute()
            total_burned = self.supabase.from_("backing_reserves").select("amount").eq("action", "burn").execute()
            total_supply = sum(float(record["amount"]) for record in total_supply.data) if total_supply.data else 0
            total_burned = sum(float(record["amount"]) for record in total_burned.data) if total_burned.data else 0
            circulating_supply = total_supply - total_burned
            transactions = self.supabase.from_("transactions").select("amount").eq("currency", "USDS").execute()
            utilization = sum(float(tx["amount"]) for tx in transactions.data) / circulating_supply if circulating_supply > 0 else 0
            return {"circulating_supply": circulating_supply, "utilization": utilization * 100}
        except Exception as e:
            logger.error(f"Demand monitoring error: {str(e)}")
            raise

    def adjust_supply(self, amount: float, action: str):
        try:
            if not self.algorand_client:
                logger.warning(f"Algorand not configured - skipping {action} of {amount} USDS")
                return
                
            settings = get_settings()
            if action == "mint":
                txn = transaction.AssetTransferTxn(
                    sender=self.reserve_address,
                    sp=self.algorand_client.suggested_params(),
                    receiver=self.reserve_address,
                    amt=0,  # Minting logic placeholder
                    index=settings.USDS_ASSET_ID
                )
                # Sign and send txn
            elif action == "burn":
                # Burn logic placeholder
                pass
            
            self.supabase.from_("backing_reserves").insert({
                "amount": str(amount),
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
            }).execute()
            logger.info(f"Supply adjusted: {action} {amount} USDS")
        except Exception as e:
            logger.error(f"Supply adjustment error: {str(e)}")
            raise

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        supabase = get_supabase_client()
        user = supabase.from_("user_profiles").select("*").eq("id", user_id).single().execute()
        if not user.data:
            raise HTTPException(status_code=401, detail="User not found")
        return user.data
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")

def get_api_key(api_key: str = Security(api_key_header)):
    settings = get_settings()
    if api_key != settings.JWT_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Global services
database_service: Optional[DatabaseService] = None
audit_service: Optional[AuditService] = None
algorand_client: Optional[algod.AlgodClient] = None

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.post("/api/v1/user/register", response_model=dict, tags=["User"])
async def register_user(user: UserProfile):
    try:
        if algorand_client:
            algorand_address, private_key = account.generate_account()
        else:
            algorand_address = None
            
        hashed_password = pwd_context.hash(user.password)
        user_data = user.dict(exclude={"password"})
        user_data.update({
            "id": str(uuid4()),
            "password": hashed_password,
            "created_at": datetime.utcnow().isoformat(),
            "algorand_address": algorand_address,
        })
        database_service.insert("user_profiles", user_data)
        audit_service.log_action(user_data["id"], "user_registered", user_data)
        
        # Send welcome email
        settings = get_settings()
        if settings.MAIL_PASSWORD:
            try:
                msg = MIMEText(f"Welcome to Seamount.io, {user.first_name}! Your account has been created.")
                msg["Subject"] = "Welcome to Seamount.io"
                msg["From"] = settings.MAIL_FROM
                msg["To"] = user.email
                with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
                    if settings.MAIL_STARTTLS:
                        server.starttls()
                    server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                    server.send_message(msg)
                logger.info(f"Welcome email sent to {user.email}")
            except Exception as e:
                logger.warning(f"Failed to send welcome email to {user.email}: {str(e)}")
        
        logger.info(f"User registered: {user.email}")
        return {"message": "User registered successfully"}
    except Exception as e:
        logger.error(f"User registration error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/token", response_model=Token, tags=["User"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        supabase = get_supabase_client()
        user = supabase.from_("user_profiles").select("*").eq("email", form_data.username).single().execute()
        if not user.data or not pwd_context.verify(form_data.password, user.data["password"]):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        settings = get_settings()
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = jwt.encode(
            {"sub": user.data["id"], "exp": datetime.utcnow() + access_token_expires},
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/user/profile", response_model=dict, tags=["User"])
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user

@app.post("/api/v1/investor-contact", response_model=dict, tags=["Investor"])
async def investor_contact(contact: InvestorContactPayload):
    try:
        database_service.insert("investor_contacts", contact.dict())
        audit_service.log_action("anonymous", "investor_contact", contact.dict())
        
        # Send notification email
        settings = get_settings()
        if settings.MAIL_PASSWORD:
            try:
                msg = MIMEText(f"New investor contact: {contact.name}, {contact.email}, {contact.message}")
                msg["Subject"] = "New Investor Contact - Seamount.io"
                msg["From"] = settings.MAIL_FROM
                msg["To"] = settings.MAIL_FROM
                with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
                    if settings.MAIL_STARTTLS:
                        server.starttls()
                    server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                    server.send_message(msg)
                logger.info(f"Investor contact email sent for {contact.email}")
            except Exception as e:
                logger.warning(f"Failed to send investor contact email for {contact.email}: {str(e)}")
        
        logger.info(f"Investor contact submitted: {contact.email}")
        return {"message": "Contact request sent successfully"}
    except Exception as e:
        logger.error(f"Investor contact error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health", tags=["Health"])
async def health_check():
    try:
        # Test database connection
        supabase = get_supabase_client()
        
        services = {"database": "connected"}
        
        # Test Algorand connection if configured
        if algorand_client:
            try:
                algorand_client.status()
                services["algorand"] = "connected"
            except Exception as e:
                logger.warning(f"Algorand health check failed: {str(e)}")
                services["algorand"] = "disconnected"
        else:
            services["algorand"] = "not_configured"
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": services
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

# Continuation from the existing code - add these parts to complete the application

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Seamount.io API v1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "register": "/api/v1/user/register",
            "login": "/api/v1/token",
            "profile": "/api/v1/user/profile",
            "investor_contact": "/api/v1/investor-contact"
        }
    }

@app.post("/api/v1/payment/send", response_model=PaymentResponse, tags=["Payment"])
async def send_payment(
    payment: PaymentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Send USDS payment to another user"""
    try:
        if not algorand_client:
            raise HTTPException(status_code=503, detail="Payment service unavailable")
        
        # Verify sender has sufficient balance
        sender_balance = database_service.select("user_balances", {"user_id": payment.sender_id, "currency": payment.currency})
        if not sender_balance or float(sender_balance[0]["balance"]) < payment.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        # Find recipient by email
        recipient = database_service.select("user_profiles", {"email": payment.recipient_email})
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        transaction_id = str(uuid4())
        transaction_data = {
            "id": transaction_id,
            "sender_id": payment.sender_id,
            "recipient_id": recipient[0]["id"],
            "amount": str(payment.amount),
            "currency": payment.currency,
            "status": "completed",
            "created_at": datetime.utcnow().isoformat()
        }
        
        database_service.insert("transactions", transaction_data)
        audit_service.log_action(payment.sender_id, "payment_sent", transaction_data)
        
        return PaymentResponse(
            transaction_id=transaction_id,
            status="completed",
            amount=payment.amount,
            currency=payment.currency,
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Payment error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/usds/mint", response_model=dict, tags=["USDS"])
async def mint_usds(
    mint_request: MintRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Mint USDS tokens (admin only)"""
    try:
        if not current_user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if not algorand_client:
            raise HTTPException(status_code=503, detail="Minting service unavailable")
        
        # Treasury service logic
        treasury_service = TreasuryService(algorand_client, get_supabase_client(), get_settings().TREASURY_ADDRESS)
        treasury_service.adjust_supply(mint_request.amount, "mint")
        
        audit_service.log_action(current_user["id"], "usds_minted", {
            "amount": mint_request.amount,
            "recipient": mint_request.recipient_address
        })
        
        return {"message": f"Minted {mint_request.amount} USDS successfully"}
    except Exception as e:
        logger.error(f"Minting error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/usds/burn", response_model=dict, tags=["USDS"])
async def burn_usds(
    burn_request: BurnRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Burn USDS tokens"""
    try:
        if not algorand_client:
            raise HTTPException(status_code=503, detail="Burning service unavailable")
        
        treasury_service = TreasuryService(algorand_client, get_supabase_client(), get_settings().TREASURY_ADDRESS)
        treasury_service.adjust_supply(burn_request.amount, "burn")
        
        audit_service.log_action(current_user["id"], "usds_burned", {
            "amount": burn_request.amount,
            "sender": burn_request.sender_address
        })
        
        return {"message": f"Burned {burn_request.amount} USDS successfully"}
    except Exception as e:
        logger.error(f"Burning error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/treasury/status", response_model=dict, tags=["Treasury"])
async def get_treasury_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get treasury and demand monitoring status"""
    try:
        treasury_service = TreasuryService(algorand_client, get_supabase_client(), get_settings().TREASURY_ADDRESS)
        status = treasury_service.monitor_demand()
        return status
    except Exception as e:
        logger.error(f"Treasury status error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/kyc/submit", response_model=dict, tags=["KYC"])
async def submit_kyc(
    kyc: KYCSubmission,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Submit KYC documentation"""
    try:
        kyc_data = kyc.dict()
        kyc_data["submitted_at"] = datetime.utcnow().isoformat()
        kyc_data["id"] = str(uuid4())
        
        database_service.insert("kyc_submissions", kyc_data)
        audit_service.log_action(kyc.user_id, "kyc_submitted", kyc_data)
        
        return {"message": "KYC submitted successfully", "status": "under_review"}
    except Exception as e:
        logger.error(f"KYC submission error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/mfa/setup", response_model=MFASetupResponse, tags=["Security"])
async def setup_mfa(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Setup MFA for user account"""
    try:
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        qr_code_url = totp.provisioning_uri(
            current_user["email"],
            issuer_name="Seamount.io"
        )
        
        # Store secret in database
        database_service.insert("user_mfa", {
            "user_id": current_user["id"],
            "secret": secret,
            "enabled": False,
            "created_at": datetime.utcnow().isoformat()
        }, upsert=True)
        
        return MFASetupResponse(secret=secret, qr_code_url=qr_code_url)
    except Exception as e:
        logger.error(f"MFA setup error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/mfa/verify", response_model=dict, tags=["Security"])
async def verify_mfa(
    mfa_request: MFAVerifyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Verify MFA token and enable MFA"""
    try:
        mfa_data = database_service.select("user_mfa", {"user_id": current_user["id"]})
        if not mfa_data:
            raise HTTPException(status_code=400, detail="MFA not set up")
        
        totp = pyotp.TOTP(mfa_data[0]["secret"])
        if not totp.verify(mfa_request.token):
            raise HTTPException(status_code=400, detail="Invalid MFA token")
        
        # Enable MFA
        database_service.insert("user_mfa", {
            "user_id": current_user["id"],
            "enabled": True,
            "verified_at": datetime.utcnow().isoformat()
        }, upsert=True)
        
        return {"message": "MFA enabled successfully"}
    except Exception as e:
        logger.error(f"MFA verification error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.startup_event
async def startup_event():
    """Initialize services on startup"""
    global database_service, audit_service, algorand_client
    
    try:
        # Initialize Supabase
        supabase = get_supabase_client()
        database_service = DatabaseService(supabase)
        audit_service = AuditService(supabase)
        
        # Initialize Algorand (optional)
        algorand_client = get_algorand_client()
        
        logger.info("Services initialized successfully")
        
        # Log startup
        audit_service.log_action("system", "api_startup", {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "connected",
                "algorand": "connected" if algorand_client else "not_configured"
            }
        })
        
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

@app.shutdown_event
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        if audit_service:
            audit_service.log_action("system", "api_shutdown", {
                "timestamp": datetime.utcnow().isoformat()
            })
        logger.info("API shutdown completed")
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")

# Error handlers
@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"}
    )

# Main execution
if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=False,
        log_level="info"
    )