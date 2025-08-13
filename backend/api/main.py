import logging
from contextlib import asynccontextmanager
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

# Global services
database_service = None
audit_service = None
algorand_client = None

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

class KYCDocument(BaseModel):
    id: str
    user_id: str
    document_type: str
    document_data: str
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None

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
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_supabase_client() -> Client:
    settings = get_settings()
    try:
        client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        logger.info("Supabase client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_algorand_client() -> algod.AlgodClient:
    settings = get_settings()
    try:
        algod_client = algod.AlgodClient(
            settings.ALGORAND_API_KEY or "",
            settings.ALGORAND_NODE_URL,
            headers={"X-API-Key": settings.ALGORAND_API_KEY or ""}
        )
        logger.info("Algorand client initialized successfully")
        return algod_client
    except Exception as e:
        logger.error(f"Failed to initialize Algorand client: {str(e)}")
        raise

class DatabaseService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def insert(self, table: str, data: Dict[str, Any], upsert: bool = False):
        try:
            query = self.supabase.from_(table).insert(data)
            if upsert:
                query = query.upsert(data)
            response = query.execute()
            if not response.data:
                raise HTTPException(status_code=400, detail=f"Failed to insert into {table}")
            return response.data
        except Exception as e:
            logger.error(f"Database insert error: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def select(self, table: str, filters: Dict[str, Any] = None):
        try:
            query = self.supabase.from_(table).select("*")
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Database select error: {str(e)}")
            raise

class AuditService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def log_action(self, user_id: str, action: str, details: Dict[str, Any]):
        try:
            self.supabase.from_("compliance_logs").insert({
                "user_id": user_id,
                "action_taken": action,
                "details": details,
                "timestamp": datetime.utcnow().isoformat(),
            }).execute()
            logger.info(f"Logged action: {action} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to log action: {str(e)}")
            raise

class TreasuryService:
    def __init__(self, algorand_client: algod.AlgodClient, supabase: Client, reserve_address: str):
        self.algorand_client = algorand_client
        self.supabase = supabase
        self.reserve_address = reserve_address

    async def monitor_demand(self):
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

    async def adjust_supply(self, amount: float, action: str):
        try:
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

# Lifespan manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global database_service, audit_service, algorand_client
    
    try:
        # Initialize Supabase
        supabase = await get_supabase_client()
        database_service = DatabaseService(supabase)
        audit_service = AuditService(supabase)
        
        # Initialize Algorand (optional)
        try:
            algorand_client = await get_algorand_client()
        except Exception as e:
            logger.warning(f"Algorand client initialization failed: {str(e)}")
            algorand_client = None
        
        logger.info("Services initialized successfully")
        
        # Log startup
        if audit_service:
            await audit_service.log_action("system", "application_started", {
                "timestamp": datetime.utcnow().isoformat(),
                "services": {
                    "database": "connected",
                    "algorand": "connected" if algorand_client else "not_configured"
                }
            })
        
        yield  # App runs here
        
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise
    finally:
        # Shutdown
        try:
            if audit_service:
                await audit_service.log_action("system", "api_shutdown", {
                    "timestamp": datetime.utcnow().isoformat()
                })
            logger.info("API shutdown completed")
        except Exception as e:
            logger.error(f"Shutdown error: {str(e)}")

# Initialize FastAPI with lifespan
app = FastAPI(
    title="Seamount.io API",
    version="1.0.0",
    description="P2P cross-border payment and yield-farming stablecoin network",
    lifespan=lifespan
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.seamount.io", "https://seamount.io", "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        supabase = await get_supabase_client()
        user = supabase.from_("user_profiles").select("*").eq("id", user_id).single().execute()
        if not user.data:
            raise HTTPException(status_code=401, detail="User not found")
        return user.data
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_api_key(api_key: str = Security(api_key_header)):
    settings = get_settings()
    if api_key != settings.JWT_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"}
    )

@app.post("/api/v1/user/register", response_model=dict, tags=["User"])
async def register_user(user: UserProfile):
    global database_service, audit_service
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    if not audit_service:
        audit_service = AuditService(supabase)
    
    try:
        algorand_address, private_key = account.generate_account()
        hashed_password = pwd_context.hash(user.password)
        user_data = user.dict(exclude={"password"})
        user_data.update({
            "id": str(uuid4()),
            "password": hashed_password,
            "created_at": datetime.utcnow().isoformat(),
            "algorand_address": algorand_address,
        })
        await database_service.insert("user_profiles", user_data)
        await audit_service.log_action(user_data["id"], "user_registered", user_data)
        
        settings = get_settings()
        msg = MIMEText(f"Welcome to Seamount.io, {user.first_name}! Your account has been created.")
        msg["Subject"] = "Welcome to Seamount.io"
        msg["From"] = settings.MAIL_FROM
        msg["To"] = user.email
        try:
            with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
                if settings.MAIL_STARTTLS:
                    server.starttls()
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                server.send_message(msg)
            logger.info(f"Welcome email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
        
        logger.info(f"User registered: {user.email}")
        return {"message": "User registered successfully"}
    except Exception as e:
        logger.error(f"User registration error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/token", response_model=Token, tags=["User"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    supabase = await get_supabase_client()
    try:
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
    try:
        return current_user
    except Exception as e:
        logger.error(f"Profile fetch error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/investor-contact", response_model=dict, tags=["Investor"])
async def investor_contact(contact: InvestorContactPayload):
    global database_service, audit_service
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    if not audit_service:
        audit_service = AuditService(supabase)
    
    try:
        await database_service.insert("investor_contacts", contact.dict())
        await audit_service.log_action("anonymous", "investor_contact", contact.dict())
        
        settings = get_settings()
        msg = MIMEText(f"New investor contact: {contact.name}, {contact.email}, {contact.message}")
        msg["Subject"] = "New Investor Contact - Seamount.io"
        msg["From"] = settings.MAIL_FROM
        msg["To"] = settings.MAIL_FROM
        try:
            with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
                if settings.MAIL_STARTTLS:
                    server.starttls()
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                server.send_message(msg)
            logger.info(f"Investor contact email sent for {contact.email}")
        except Exception as e:
            logger.error(f"Failed to send investor contact email for {contact.email}: {str(e)}")
        
        logger.info(f"Investor contact submitted: {contact.email}")
        return {"message": "Contact request sent successfully"}
    except Exception as e:
        logger.error(f"Investor contact error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/kyc/submit", response_model=dict, tags=["KYC"])
async def submit_kyc(kyc: KYCSubmission, current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service, audit_service
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    if not audit_service:
        audit_service = AuditService(supabase)
    
    try:
        kyc_data = kyc.dict()
        kyc_data["id"] = str(uuid4())
        kyc_data["user_id"] = current_user["id"]
        kyc_data["submitted_at"] = datetime.utcnow().isoformat()
        kyc_data["status"] = "pending"
        await database_service.insert("kyc_documents", kyc_data)
        await database_service.insert("kyc_verifications", {
            "user_id": current_user["id"],
            "status": "pending",
            "submitted_at": datetime.utcnow().isoformat(),
        }, upsert=True)
        await audit_service.log_action(current_user["id"], "kyc_submitted", kyc_data)
        logger.info(f"KYC submitted for user: {current_user['id']}")
        return {"message": "KYC documents submitted successfully"}
    except Exception as e:
        logger.error(f"KYC submission error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/kyc/status", response_model=dict, tags=["KYC"])
async def get_kyc_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    
    try:
        kyc_status = await database_service.select("kyc_verifications", {"user_id": current_user["id"]})
        if not kyc_status:
            raise HTTPException(status_code=404, detail="KYC status not found")
        return kyc_status[0]
    except Exception as e:
        logger.error(f"KYC status fetch error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/payments/send", response_model=PaymentResponse, tags=["Payments"])
async def send_payment(payment: PaymentRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service, algorand_client
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    if not algorand_client:
        algorand_client = await get_algorand_client()
    
    try:
        recipient = supabase.from_("user_profiles").select("id, algorand_address").eq("email", payment.recipient_email).single().execute()
        if not recipient.data:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        sender_balance = await database_service.select("wallet_balances", {"user_id": current_user["id"], "currency": payment.currency})
        if not sender_balance or sender_balance[0]["amount"] < payment.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        settings = get_settings()
        tx_params = algorand_client.suggested_params()
        tx = transaction.PaymentTxn(
            sender=current_user["algorand_address"],
            sp=tx_params,
            receiver=recipient.data["algorand_address"],
            amt=int(payment.amount * 1_000_000),  # Assuming 6 decimals for USDS
            note=f"USDS payment: {payment.amount}"
        )
        
        if settings.ALGORAND_CREATOR_MNEMONIC:
            signed_tx = tx.sign(mnemonic.to_private_key(settings.ALGORAND_CREATOR_MNEMONIC))
            tx_id = algorand_client.send_transaction(signed_tx)
        else:
            tx_id = str(uuid4())  # Fallback for development
        
        supabase.from_("transactions").insert({
            "sender_id": current_user["id"],
            "recipient_id": recipient.data["id"],
            "amount": payment.amount,
            "currency": payment.currency,
            "transaction_id": tx_id,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
        }).execute()
        
        await database_service.insert("wallet_balances", {
            "user_id": current_user["id"],
            "currency": payment.currency,
            "amount": sender_balance[0]["amount"] - payment.amount
        }, upsert=True)
        
        recipient_balance = await database_service.select("wallet_balances", {"user_id": recipient.data["id"], "currency": payment.currency})
        recipient_amount = recipient_balance[0]["amount"] if recipient_balance else 0
        await database_service.insert("wallet_balances", {
            "user_id": recipient.data["id"],
            "currency": payment.currency,
            "amount": recipient_amount + payment.amount
        }, upsert=True)
        
        logger.info(f"Payment sent: {tx_id} for {payment.amount} USDS")
        return {
            "transaction_id": tx_id,
            "status": "completed",
            "amount": payment.amount,
            "currency": payment.currency,
            "timestamp": datetime.utcnow(),
        }
    except Exception as e:
        logger.error(f"Payment send error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/usds/mint", tags=["USDS"])
async def mint_usds(mint: MintRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    global algorand_client
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not algorand_client:
        algorand_client = await get_algorand_client()
    
    supabase = await get_supabase_client()
    treasury = TreasuryService(algorand_client, supabase, get_settings().TREASURY_ADDRESS or "")
    try:
        demand = await treasury.monitor_demand()
        if demand["utilization"] < 80:
            raise HTTPException(status_code=400, detail="Utilization below 80%, minting not required")
        await treasury.adjust_supply(mint.amount, "mint")
        logger.info(f"Minted {mint.amount} USDS to {mint.recipient_address}")
        return {"message": f"Successfully minted {mint.amount} USDS"}
    except Exception as e:
        logger.error(f"Mint USDS error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/usds/burn", tags=["USDS"])
async def burn_usds(burn: BurnRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    global algorand_client
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not algorand_client:
        algorand_client = await get_algorand_client()
    
    supabase = await get_supabase_client()
    treasury = TreasuryService(algorand_client, supabase, get_settings().TREASURY_ADDRESS or "")
    try:
        await treasury.adjust_supply(burn.amount, "burn")
        logger.info(f"Burned {burn.amount} USDS from {burn.sender_address}")
        return {"message": f"Successfully burned {burn.amount} USDS"}
    except Exception as e:
        logger.error(f"Burn USDS error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/whitelabel/quote", tags=["Whitelabel Services"])
async def get_payment_quote(payload: WhitelabelQuotePayload, api_key: str = Depends(get_api_key)):
    global database_service, audit_service
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    if not audit_service:
        audit_service = AuditService(supabase)
    
    try:
        rate = await database_service.select("exchange_rates", {
            "from_currency": payload.from_currency.upper(),
            "to_currency": payload.to_currency.upper()
        })
        exchange_rate = Decimal(rate[0]["rate"]) if rate else Decimal("1.0")
        fee = payload.amount * Decimal("0.03")
        converted_amount = payload.amount * exchange_rate
        quote_id = f"quote_{uuid4()}"
        await database_service.insert("payment_requests", {
            "quote_id": quote_id,
            "amount": str(payload.amount),
            "from_currency": payload.from_currency.upper(),
            "to_currency": payload.to_currency.upper(),
            "exchange_rate": str(exchange_rate),
            "fee": str(fee),
            "converted_amount": str(converted_amount),
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=15)).isoformat(),
        })
        
        await audit_service.log_action("whitelabel_api", "quote_generated", {
            "quote_id": quote_id,
            "amount": str(payload.amount),
            "currencies": f"{payload.from_currency}->{payload.to_currency}"
        })
        
        logger.info(f"Quote generated: {quote_id}")
        return {
            "quote_id": quote_id,
            "amount": str(payload.amount),
            "from_currency": payload.from_currency.upper(),
            "to_currency": payload.to_currency.upper(),
            "exchange_rate": str(exchange_rate),
            "fee": str(fee),
            "converted_amount": str(converted_amount),
            "expires_at": (datetime.utcnow() + timedelta(minutes=15)).isoformat(),
        }
    except Exception as e:
        logger.error(f"Quote generation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/user/consent", response_model=dict, tags=["User"])
async def update_consent_preferences(
    consent: ConsentPayload,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    global database_service, audit_service
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    if not audit_service:
        audit_service = AuditService(supabase)
    
    try:
        await database_service.insert("user_consents", {
            "user_id": current_user["id"],
            "preferences": consent.preferences,
            "updated_at": datetime.utcnow().isoformat(),
        }, upsert=True)
        
        await audit_service.log_action(current_user["id"], "consent_updated", consent.preferences)
        
        logger.info(f"Consent updated for user: {current_user['id']}")
        return {"message": "Consent preferences updated successfully"}
    except Exception as e:
        logger.error(f"Consent update error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/user/balance", response_model=dict, tags=["Wallet"])
async def get_wallet_balance(current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    
    try:
        balances = await database_service.select("wallet_balances", {"user_id": current_user["id"]})
        balance_dict = {balance["currency"]: balance["amount"] for balance in balances}
        return {"balances": balance_dict}
    except Exception as e:
        logger.error(f"Balance fetch error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/user/mfa/setup", response_model=MFASetupResponse, tags=["Security"])
async def setup_mfa(current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service, audit_service
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    if not audit_service:
        audit_service = AuditService(supabase)
    
    try:
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        qr_code_url = totp.provisioning_uri(
            name=current_user["email"],
            issuer_name="Seamount.io"
        )
        
        await database_service.insert("user_mfa", {
            "user_id": current_user["id"],
            "secret": secret,
            "enabled": False,
            "created_at": datetime.utcnow().isoformat(),
        }, upsert=True)
        
        await audit_service.log_action(current_user["id"], "mfa_setup_initiated", {})
        
        logger.info(f"MFA setup for user: {current_user['id']}")
        return {"secret": secret, "qr_code_url": qr_code_url}
    except Exception as e:
        logger.error(f"MFA setup error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/user/mfa/verify", response_model=dict, tags=["Security"])
async def verify_mfa(
    mfa_request: MFAVerifyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    global database_service, audit_service
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    if not audit_service:
        audit_service = AuditService(supabase)
    
    try:
        mfa_data = await database_service.select("user_mfa", {"user_id": current_user["id"]})
        if not mfa_data:
            raise HTTPException(status_code=404, detail="MFA not set up")
        
        totp = pyotp.TOTP(mfa_data[0]["secret"])
        if not totp.verify(mfa_request.token):
            raise HTTPException(status_code=400, detail="Invalid MFA token")
        
        await database_service.insert("user_mfa", {
            "user_id": current_user["id"],
            "secret": mfa_data[0]["secret"],
            "enabled": True,
            "verified_at": datetime.utcnow().isoformat(),
        }, upsert=True)
        
        await audit_service.log_action(current_user["id"], "mfa_enabled", {})
        
        logger.info(f"MFA enabled for user: {current_user['id']}")
        return {"message": "MFA enabled successfully"}
    except Exception as e:
        logger.error(f"MFA verification error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/portfolio", response_model=List[PortfolioHolding], tags=["Portfolio"])
async def get_portfolio(current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    
    try:
        holdings = await database_service.select("portfolio_holdings", {"user_id": current_user["id"]})
        return holdings
    except Exception as e:
        logger.error(f"Portfolio fetch error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/health", tags=["System"])
async def health_check():
    try:
        supabase = await get_supabase_client()
        # Basic connection test
        supabase.from_("user_profiles").select("id").limit(1).execute()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "connected",
                "api": "running"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.get("/api/v1/treasury/status", tags=["Treasury"])
async def get_treasury_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    global algorand_client
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not algorand_client:
        algorand_client = await get_algorand_client()
    
    supabase = await get_supabase_client()
    treasury = TreasuryService(algorand_client, supabase, get_settings().TREASURY_ADDRESS or "")
    
    try:
        demand_metrics = await treasury.monitor_demand()
        return {
            "circulating_supply": demand_metrics["circulating_supply"],
            "utilization_rate": demand_metrics["utilization"],
            "status": "healthy" if demand_metrics["utilization"] < 90 else "high_demand",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Treasury status error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
        log_level="info"
    )