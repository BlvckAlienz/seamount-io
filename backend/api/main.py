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
from algosdk import account, mnemonic
from py_algorand_sdk import ApplicationClient
import smtplib
from email.mime.text import MIMEText
from jose import JWTError, jwt
from passlib.context import CryptContext
from tenacity import retry, stop_after_attempt, wait_exponential

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings:
    VITE_SUPABASE_URL: str = os.getenv("VITE_SUPABASE_URL", "https://opqnoficlhbylxfpaehp.supabase.co")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY")
    ALGORAND_API_URL: str = os.getenv("ALGORAND_API_URL", "https://testnet-algorand.api.purestake.io/ps2")
    ALGORAND_API_KEY: str = os.getenv("ALGORAND_API_KEY")
    ALGORAND_MNEMONIC: str = os.getenv("ALGORAND_MNEMONIC")
    USDS_APP_ID: int = int(os.getenv("USDS_APP_ID", 0))
    RESERVE_ADDRESS: str = os.getenv("RESERVE_ADDRESS")
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "workplace.truehost.cloud")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "no-reply@seamount.io")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "no-reply@seamount.io")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "True") == "True"
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "False") == "True"
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        case_sensitive = True

def get_settings() -> Settings:
    required_vars = [
        "VITE_SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "ALGORAND_API_URL",
        "ALGORAND_API_KEY",
        "ALGORAND_MNEMONIC",
        "USDS_APP_ID",
        "RESERVE_ADDRESS",
        "MAIL_SERVER",
        "MAIL_PORT",
        "MAIL_USERNAME",
        "MAIL_PASSWORD",
        "MAIL_FROM",
        "MAIL_STARTTLS",
        "MAIL_SSL_TLS",
        "JWT_SECRET_KEY",
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

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.seamount.io"],
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

# Services
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_supabase_client() -> Client:
    settings = get_settings()
    client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    try:
        await client.auth.get_session()
        logger.info("Supabase client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_algorand_client() -> ApplicationClient:
    settings = get_settings()
    try:
        algod_client = algod.AlgodClient(
            settings.ALGORAND_API_KEY,
            settings.ALGORAND_API_URL,
            headers={"X-API-Key": settings.ALGORAND_API_KEY}
        )
        account_private_key = mnemonic.to_private_key(settings.ALGORAND_MNEMONIC)
        app_client = ApplicationClient(
            client=algod_client,
            app_id=settings.USDS_APP_ID,
            signer=account_private_key
        )
        logger.info("Algorand client initialized successfully")
        return app_client
    except Exception as e:
        logger.error(f"Failed to initialize Algorand client: {str(e)}")
        raise

class DatabaseService:
    def __init__(self, settings: Settings):
        self.supabase = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def insert(self, table: str, data: Dict[str, Any], upsert: bool = False):
        try:
            query = self.supabase.from_(table).insert(data)
            if upsert:
                query = query.upsert(data)
            response = await query.execute()
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
            response = await query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Database select error: {str(e)}")
            raise

class AuditService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def log_action(self, user_id: str, action: str, details: Dict[str, Any]):
        try:
            await self.supabase.from_("compliance_logs").insert({
                "user_id": user_id,
                "action": action,
                "details": details,
                "timestamp": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            logger.error(f"Compliance log error: {str(e)}")

class TreasuryService:
    def __init__(self, algorand_client: ApplicationClient, supabase_client: Client, reserve_address: str):
        self.algorand_client = algorand_client
        self.supabase_client = supabase_client
        self.reserve_address = reserve_address

    async def get_reserve_balance(self) -> float:
        try:
            account_info = await self.algorand_client.client.account_info(self.reserve_address)
            balance = account_info.get("amount", 0) / 1_000_000
            logger.info(f"Reserve balance: {balance} USDS")
            return balance
        except Exception as e:
            logger.error(f"Failed to get reserve balance: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch reserve balance")

    async def monitor_demand(self) -> Dict[str, Any]:
        try:
            response = await self.supabase_client.from_("transactions").select("amount").eq("currency", "USDS").execute()
            total_usage = sum(tx["amount"] for tx in response.data) if response.data else 0
            reserve_balance = await self.get_reserve_balance()
            utilization = (total_usage / reserve_balance) * 100 if reserve_balance > 0 else 0
            logger.info(f"Demand monitoring: Total usage={total_usage}, Utilization={utilization}%")
            return {"total_usage": total_usage, "utilization": utilization}
        except Exception as e:
            logger.error(f"Failed to monitor demand: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to monitor demand")

    async def adjust_supply(self, amount: float, action: str):
        try:
            if action == "mint":
                await self.algorand_client.call("mint", amount=int(amount * 1_000_000), recipient=self.reserve_address)
                logger.info(f"Minted {amount} USDS to {self.reserve_address}")
                await self.supabase_client.from_("backing_reserves").insert({
                    "amount": amount,
                    "action": "mint",
                    "timestamp": datetime.utcnow().isoformat(),
                }).execute()
            elif action == "burn":
                await self.algorand_client.call("burn", amount=int(amount * 1_000_000), sender=self.reserve_address)
                logger.info(f"Burned {amount} USDS from {self.reserve_address}")
                await self.supabase_client.from_("backing_reserves").insert({
                    "amount": amount,
                    "action": "burn",
                    "timestamp": datetime.utcnow().isoformat(),
                }).execute()
            else:
                raise HTTPException(status_code=400, detail="Invalid action")
        except Exception as e:
            logger.error(f"Failed to {action} USDS: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to {action} USDS")

# Auth
async def get_api_key(api_key: str = Security(api_key_header)):
    settings = get_settings()
    if api_key != settings.JWT_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    supabase = await get_supabase_client()
    user = await supabase.from_("user_profiles").select("*").eq("email", email).single().execute()
    if user.data is None:
        raise credentials_exception
    return user.data

@app.post("/api/v1/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    supabase = await get_supabase_client()
    try:
        response = await supabase.auth.sign_in_with_password({
            "email": form_data.username,
            "password": form_data.password,
        })
        if response.session is None:
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        access_token_expires = timedelta(minutes=get_settings().ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=400, detail="Incorrect email or password")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    settings = get_settings()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

# Endpoints
@app.post("/api/v1/investor-contact")
async def investor_contact(payload: InvestorContactPayload):
    settings = get_settings()
    database_service = DatabaseService(settings)
    try:
        await database_service.insert("investor_contacts", {
            "name": payload.name,
            "email": payload.email,
            "company": payload.company,
            "check_size": payload.checkSize,
            "message": payload.message,
            "created_at": datetime.utcnow().isoformat(),
        })
        msg = MIMEText(f"Name: {payload.name}\nEmail: {payload.email}\nCompany: {payload.company}\nCheck Size: {payload.checkSize}\nMessage: {payload.message}")
        msg["Subject"] = "Investor Contact from Seamount.io"
        msg["From"] = settings.MAIL_FROM
        msg["To"] = "support@seamount.io"
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            if settings.MAIL_STARTTLS:
                server.starttls()
            if settings.MAIL_SSL_TLS:
                server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)
        logger.info(f"Investor contact email sent for {payload.email}")
        return {"message": "Contact request sent successfully"}
    except Exception as e:
        logger.error(f"Failed to send investor contact email: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send contact request")

@app.get("/api/v1/user/profile")
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user

@app.post("/api/v1/user/register")
async def register_user(user: UserProfile):
    supabase = await get_supabase_client()
    database_service = DatabaseService(get_settings())
    try:
        response = await supabase.auth.sign_up({
            "email": user.email,
            "password": user.password,
            "options": {
                "data": {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "country_code": user.country_code,
                }
            }
        })
        if response.user is None:
            raise HTTPException(status_code=400, detail="Registration failed")
        await database_service.insert("user_profiles", {
            "id": response.user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "country_code": user.country_code,
            "kyc_level": 0,
            "kyc_status": "pending",
            "is_admin": False,
            "created_at": datetime.utcnow().isoformat(),
            "algorand_address": user.algorand_address,
        })
        settings = get_settings()
        msg = MIMEText(f"Welcome {user.first_name}! Your account has been created successfully.")
        msg["Subject"] = "Welcome to Seamount.io"
        msg["From"] = settings.MAIL_FROM
        msg["To"] = user.email
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            if settings.MAIL_STARTTLS:
                server.starttls()
            if settings.MAIL_SSL_TLS:
                server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)
        logger.info(f"User registered: {user.email}")
        return {"message": "User registered successfully"}
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/kyc/submit")
async def submit_kyc(kyc: KYCSubmission, current_user: Dict[str, Any] = Depends(get_current_user)):
    database_service = DatabaseService(get_settings())
    try:
        if current_user["id"] != kyc.user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        await database_service.insert("kyc_documents", {
            "user_id": kyc.user_id,
            "document_type": kyc.document_type,
            "document_data": kyc.document_data,
            "status": "pending",
            "submitted_at": datetime.utcnow().isoformat(),
        })
        await database_service.insert("kyc_verifications", {
            "user_id": kyc.user_id,
            "status": "pending",
            "submitted_at": datetime.utcnow().isoformat(),
        }, upsert=True)
        await database_service.insert("user_profiles", {
            "id": kyc.user_id,
            "kyc_status": "pending",
            "kyc_level": 1
        }, upsert=True)
        logger.info(f"KYC submitted for user: {kyc.user_id}")
        return {"message": "KYC document submitted successfully"}
    except Exception as e:
        logger.error(f"KYC submission error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/kyc/status", response_model=List[KYCDocument])
async def get_kyc_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    database_service = DatabaseService(get_settings())
    try:
        response = await database_service.select("kyc_documents", {"user_id": current_user["id"]})
        return response
    except Exception as e:
        logger.error(f"KYC status error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/payments/send", response_model=PaymentResponse)
async def send_payment(payment: PaymentRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    supabase = await get_supabase_client()
    algorand_client = await get_algorand_client()
    database_service = DatabaseService(get_settings())
    try:
        if current_user["id"] != payment.sender_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        recipient = await supabase.from_("user_profiles").select("id, algorand_address").eq("email", payment.recipient_email).single().execute()
        if not recipient.data:
            raise HTTPException(status_code=404, detail="Recipient not found")
        balance = await database_service.select("wallet_balances", {"user_id": current_user["id"], "currency": payment.currency})
        if not balance or balance[0]["amount"] < payment.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        tx_params = await algorand_client.client.suggested_params()
        tx = {
            "sender": current_user["algorand_address"],
            "receiver": recipient.data["algorand_address"],
            "amount": int(payment.amount * 1_000_000),
            "note": f"USDS payment: {payment.amount}",
        }
        tx_id = await algorand_client.call("transfer", **tx)
        await supabase.from_("transactions").insert({
            "sender_id": payment.sender_id,
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
            "amount": balance[0]["amount"] - payment.amount
        }, upsert=True)
        await database_service.insert("wallet_balances", {
            "user_id": recipient.data["id"],
            "currency": payment.currency,
            "amount": (await database_service.select("wallet_balances", {"user_id": recipient.data["id"], "currency": payment.currency}) or [{"amount": 0}])[0]["amount"] + payment.amount
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

@app.post("/api/v1/payments/receive", response_model=PaymentResponse)
async def receive_payment(payment: PaymentRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    supabase = await get_supabase_client()
    algorand_client = await get_algorand_client()
    database_service = DatabaseService(get_settings())
    try:
        sender = await supabase.from_("user_profiles").select("id, algorand_address").eq("email", payment.recipient_email).single().execute()
        if not sender.data:
            raise HTTPException(status_code=404, detail="Sender not found")
        sender_balance = await database_service.select("wallet_balances", {"user_id": sender.data["id"], "currency": payment.currency})
        if not sender_balance or sender_balance[0]["amount"] < payment.amount:
            raise HTTPException(status_code=400, detail="Sender has insufficient balance")
        tx_params = await algorand_client.client.suggested_params()
        tx = {
            "sender": sender.data["algorand_address"],
            "receiver": current_user["algorand_address"],
            "amount": int(payment.amount * 1_000_000),
            "note": f"USDS receipt: {payment.amount}",
        }
        tx_id = await algorand_client.call("transfer", **tx)
        await supabase.from_("transactions").insert({
            "sender_id": sender.data["id"],
            "recipient_id": current_user["id"],
            "amount": payment.amount,
            "currency": payment.currency,
            "transaction_id": tx_id,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
        }).execute()
        await database_service.insert("wallet_balances", {
            "user_id": sender.data["id"],
            "currency": payment.currency,
            "amount": sender_balance[0]["amount"] - payment.amount
        }, upsert=True)
        await database_service.insert("wallet_balances", {
            "user_id": current_user["id"],
            "currency": payment.currency,
            "amount": (await database_service.select("wallet_balances", {"user_id": current_user["id"], "currency": payment.currency}) or [{"amount": 0}])[0]["amount"] + payment.amount
        }, upsert=True)
        logger.info(f"Payment received: {tx_id} for {payment.amount} USDS")
        return {
            "transaction_id": tx_id,
            "status": "completed",
            "amount": payment.amount,
            "currency": payment.currency,
            "timestamp": datetime.utcnow(),
        }
    except Exception as e:
        logger.error(f"Payment receive error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/usds/mint")
async def mint_usds(mint: MintRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    algorand_client = await get_algorand_client()
    supabase = await get_supabase_client()
    treasury = TreasuryService(algorand_client, supabase, get_settings().RESERVE_ADDRESS)
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

@app.post("/api/v1/usds/burn")
async def burn_usds(burn: BurnRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    algorand_client = await get_algorand_client()
    supabase = await get_supabase_client()
    treasury = TreasuryService(algorand_client, supabase, get_settings().RESERVE_ADDRESS)
    try:
        await treasury.adjust_supply(burn.amount, "burn")
        logger.info(f"Burned {burn.amount} USDS from {burn.sender_address}")
        return {"message": f"Successfully burned {burn.amount} USDS"}
    except Exception as e:
        logger.error(f"Burn USDS error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/whitelabel/quote", tags=["Whitelabel Services"])
async def get_payment_quote(payload: WhitelabelQuotePayload, api_key: str = Depends(get_api_key)):
    database_service = DatabaseService(get_settings())
    audit_service = AuditService(await get_supabase_client())
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
            "estimated_fee": str(fee),
            "converted_amount": str(converted_amount),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        })
        await audit_service.log_action("system", "quote_generated", payload.dict())
        return {
            "from_currency": payload.from_currency.upper(),
            "to_currency": payload.to_currency.upper(),
            "amount_to_send": str(payload.amount),
            "exchange_rate": str(exchange_rate),
            "estimated_fee": str(fee),
            "estimated_amount_to_receive": str(converted_amount - fee),
            "quote_id": quote_id,
            "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
        }
    except Exception as e:
        logger.error(f"Payment quote error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate quote")

@app.post("/api/v1/consent/cookies", tags=["Consent"])
async def set_consent_cookies(payload: ConsentPayload):
    database_service = DatabaseService(get_settings())
    audit_service = AuditService(await get_supabase_client())
    try:
        await database_service.insert("user_consent", {
            "preferences": payload.preferences,
            "created_at": datetime.utcnow().isoformat(),
        })
        await audit_service.log_action("anonymous", "consent_update", payload.dict())
        return {"status": "success", "message": "Consent preferences updated"}
    except Exception as e:
        logger.error(f"Consent cookies error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update consent")

@app.get("/")
async def root():
    return {"status": "healthy", "service": "Seamount.io API Gateway"}

# Initialize services
try:
    settings = get_settings()
    database_service = DatabaseService(settings)
    audit_service = AuditService(create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY))
except ValueError as e:
    logger.error(f"Startup failed: {str(e)}")
    raise

@app.on_event("startup")
async def startup_event():
    global database_service, audit_service
    database_service.supabase = await get_supabase_client()
    audit_service.supabase = await get_supabase_client()
    logger.info("Application startup complete")