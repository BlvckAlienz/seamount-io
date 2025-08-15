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
from jose.constants import ALGORITHMS
from passlib.context import CryptContext
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pyotp
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
import asyncio

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
jwks_cache = {}
jwks_cache_expiry = None

class Settings:
    VITE_SUPABASE_URL: str = os.getenv("VITE_SUPABASE_URL", "https://opqnoficlhbylxfpaehp.supabase.co")
    SUPABASE_SERVICE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")  # Optional
    ALGORAND_NODE_URL: str = os.getenv("ALGORAND_NODE_URL", "https://mainnet-algorand.api.purestake.io/ps2")
    ALGORAND_API_KEY: Optional[str] = os.getenv("ALGORAND_API_KEY")
    ALGORAND_CREATOR_MNEMONIC: Optional[str] = os.getenv("ALGORAND_CREATOR_MNEMONIC")
    USDS_ASSET_ID: int = int(os.getenv("USDS_ASSET_ID", 0))
    TREASURY_ADDRESS: Optional[str] = os.getenv("TREASURY_ADDRESS")
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "workplace.truehost.cloud")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "no-reply@seamount.io")
    MAIL_PASSWORD: Optional[str] = os.getenv("MAIL_PASSWORD")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "no-reply@seamount.io")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "True") == "True"
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "False") == "True"
    PORT: int = int(os.getenv("PORT", 8000))
    
    @property
    def JWKS_URL(self) -> str:
        """Construct the JWKS URL from Supabase URL."""
        return f"{self.VITE_SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"

def get_settings() -> Settings:
    try:
        settings = Settings()
        if not settings.VITE_SUPABASE_URL:
            logger.critical("FATAL: VITE_SUPABASE_URL must be set.")
            raise ValueError("Missing critical Supabase environment variable: VITE_SUPABASE_URL")
        logger.info(f"Settings loaded successfully. JWKS URL: {settings.JWKS_URL}")
        return settings
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

# JWKS Authentication Implementation
async def fetch_jwks(jwks_url: str) -> Dict[str, Any]:
    """Fetch JWKS from Supabase with caching and retry logic"""
    global jwks_cache, jwks_cache_expiry
    
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry:
        logger.debug("Using cached JWKS")
        return jwks_cache
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(jwks_url) as response:
                response.raise_for_status()
                jwks_data = await response.json()
                jwks_cache = jwks_data
                jwks_cache_expiry = datetime.utcnow() + timedelta(hours=1)
                logger.info("JWKS fetched and cached successfully")
                return jwks_data
    except aiohttp.ClientResponseError as e:
        logger.error(f"Failed to fetch JWKS: HTTP {e.status} - {e.message}")
        raise HTTPException(status_code=503, detail="JWKS service unavailable")
    except Exception as e:
        logger.error(f"Unexpected JWKS fetch error: {str(e)}")
        raise HTTPException(status_code=503, detail="JWKS fetch failed")

def get_public_key(jwk: Dict[str, Any]) -> Any:
    """Extract RSA public key from JWK"""
    try:
        if jwk['kty'] == 'RSA':
            n = int.from_bytes(base64.urlsafe_b64decode(jwk['n'] + '==='), 'big')
            e = int.from_bytes(base64.urlsafe_b64decode(jwk['e'] + '==='), 'big')
            return rsa.RSAPublicNumbers(e, n).public_key()
        elif jwk['kty'] == 'EC':
            x = int.from_bytes(base64.urlsafe_b64decode(jwk['x'] + '==='), 'big')
            y = int.from_bytes(base64.urlsafe_b64decode(jwk['y'] + '==='), 'big')
            curve = {'P-256': ec.SECP256R1, 'P-384': ec.SECP384R1, 'P-521': ec.SECP521R1}.get(jwk.get('crv'))
            if not curve:
                raise ValueError(f"Unsupported EC curve: {jwk.get('crv')}")
            return ec.EllipticCurvePublicNumbers(x, y, curve()).public_key()
        else:
            raise ValueError(f"Unsupported key type: {jwk['kty']}")
    except Exception as e:
        logger.error(f"Public key extraction error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid JWK format")

async def get_current_user(token: str = Security(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token"))):
    settings = get_settings()
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get('kid')
        if not kid:
            raise JWTError("Missing 'kid' in token header")
        
        jwks = await fetch_jwks(settings.JWKS_URL)
        matching_key = next((key for key in jwks.get('keys', []) if key['kid'] == kid), None)
        if not matching_key:
            raise JWTError("No matching JWK found for kid")
        
        public_key = get_public_key(matching_key)
        
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[matching_key.get('alg', 'RS256')],
            audience="authenticated",
            options={"verify_signature": True, "verify_aud": True, "verify_exp": True}
        )
        
        user_id = payload.get("sub")
        user_email = payload.get("email")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")
        
        supabase = await get_supabase_client()
        profile = supabase.from_("user_profiles").select("*").eq("id", user_id).single().execute()
        
        if profile.data:
            return profile.data
        
        logger.info(f"Auto-creating profile for new user: {user_id}")
        new_profile = {
            "id": user_id,
            "email": user_email,
            "kyc_level": 0,
            "kyc_status": "pending",
            "is_admin": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        create_res = supabase.from_("user_profiles").insert(new_profile).execute()
        
        if not create_res.data:
            raise HTTPException(status_code=500, detail="Failed to create user profile")
        
        return create_res.data[0]
        
    except JWTError as e:
        logger.warning(f"JWT validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# Services
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_supabase_client() -> Client:
    settings = get_settings()
    try:
        client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY or "")
        logger.info("Supabase client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_algorand_client() -> Optional[algod.AlgodClient]:
    settings = get_settings()
    if not all([settings.ALGORAND_NODE_URL, settings.ALGORAND_API_KEY]):
        logger.warning("Algorand client not configured - skipping initialization")
        return None
    try:
        headers = {"X-API-Key": settings.ALGORAND_API_KEY}
        client = algod.AlgodClient("", settings.ALGORAND_NODE_URL, headers=headers)
        status = client.status()
        logger.info(f"Algorand client initialized - current round: {status.get('last-round')}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Algorand client: {str(e)}")
        raise

class DatabaseService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    def select(self, table: str, query: Dict[str, Any]) -> List[Dict]:
        try:
            res = self.supabase.from_(table).select("*").match(query).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"DB select error [{table}]: {str(e)}")
            raise

    def insert(self, table: str, data: Dict, upsert: bool = False) -> Dict:
        try:
            if upsert:
                res = self.supabase.from_(table).upsert(data).execute()
            else:
                res = self.supabase.from_(table).insert(data).execute()
            return res.data[0] if res.data else {}
        except Exception as e:
            logger.error(f"DB insert error [{table}]: {str(e)}")
            raise

class AuditService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def log_action(self, user_id: str, action: str, details: Dict):
        try:
            log_entry = {
                "user_id": user_id,
                "action": action,
                "details": json.dumps(details),
                "timestamp": datetime.utcnow().isoformat()
            }
            self.supabase.from_("audit_logs").insert(log_entry).execute()
        except Exception as e:
            logger.error(f"Audit log error: {str(e)}")

class TreasuryService:
    def __init__(self, algorand_client: Optional[algod.AlgodClient], supabase: Client, treasury_address: str):
        self.algorand_client = algorand_client
        self.supabase = supabase
        self.treasury_address = treasury_address

    def monitor_demand(self) -> Dict:
        if not self.algorand_client:
            return {"status": "unavailable", "message": "Algorand not configured"}
        try:
            account_info = self.algorand_client.account_info(self.treasury_address)
            circulating_supply = account_info.get('amount', 0)
            utilization = (circulating_supply / 1000000000) * 100 if circulating_supply else 0
            return {
                "circulating_supply": circulating_supply,
                "utilization": utilization,
                "status": "healthy" if utilization < 80 else "high"
            }
        except Exception as e:
            logger.error(f"Treasury monitor error: {str(e)}")
            raise HTTPException(status_code=503, detail="Treasury monitor failed")

# Dependency Injection Helpers
async def get_db() -> DatabaseService:
    global database_service
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    return database_service

async def get_audit() -> AuditService:
    global audit_service
    supabase = await get_supabase_client()
    if not audit_service:
        audit_service = AuditService(supabase)
    return audit_service

async def get_algo() -> Optional[algod.AlgodClient]:
    global algorand_client
    if not algorand_client:
        algorand_client = await get_algorand_client()
    return algorand_client

def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)):
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin privileges required")

# App setup
app = FastAPI(
    title="Seamount API",
    description="Seamount backend API for stablecoin operations",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.post("/api/v1/investor/contact", response_model=dict, tags=["Investor"])
async def investor_contact(
    contact: InvestorContactPayload,
    db: DatabaseService = Depends(get_db),
    audit: AuditService = Depends(get_audit)
):
    try:
        contact_data = contact.dict(exclude_unset=True)
        contact_data["id"] = str(uuid4())
        contact_data["created_at"] = datetime.utcnow().isoformat()
        db.insert("investor_contacts", contact_data)
        
        settings = get_settings()
        if not all([settings.MAIL_USERNAME, settings.MAIL_PASSWORD]):
            logger.warning("Email service not fully configured - skipping send")
        else:
            msg = MIMEText(contact.message or "")
            msg['Subject'] = f"Investor Contact: {contact.name}"
            msg['From'] = settings.MAIL_FROM
            msg['To'] = "investors@seamount.io"
        
            with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
                if settings.MAIL_STARTTLS:
                    server.starttls()
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                server.send_message(msg)
        
        await audit.log_action(None, "investor_contact", contact_data)
        return {"message": "Contact request submitted successfully"}
    except Exception as e:
        logger.error(f"Investor contact error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/quote/whitelabel", response_model=dict, tags=["Quote"])
async def get_whitelabel_quote(quote: WhitelabelQuotePayload):
    try:
        base_rate = 1.0
        fee_rate = 0.002
        fee_amount = float(quote.amount) * fee_rate
        net_amount = float(quote.amount) - fee_amount
        
        return {
            "from_amount": float(quote.amount),
            "from_currency": quote.from_currency,
            "to_amount": net_amount,
            "to_currency": quote.to_currency,
            "exchange_rate": base_rate,
            "fee": fee_amount,
            "quote_id": str(uuid4()),
            "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        }
    except Exception as e:
        logger.error(f"Quote generation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/user/consent", response_model=dict, tags=["User"])
async def update_consent(
    consent: ConsentPayload,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
    audit: AuditService = Depends(get_audit)
):
    try:
        consent_data = {
            "user_id": current_user["id"],
            "preferences": json.dumps(consent.preferences),
            "updated_at": datetime.utcnow().isoformat()
        }
        db.insert("user_consent", consent_data, upsert=True)
        await audit.log_action(current_user["id"], "consent_updated", consent_data)
        return {"message": "Consent preferences updated"}
    except Exception as e:
        logger.error(f"Consent update error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/user/mfa/setup", response_model=MFASetupResponse, tags=["Security"])
async def setup_mfa(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
    audit: AuditService = Depends(get_audit)
):
    try:
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        qr_code_url = totp.provisioning_uri(name=current_user["email"], issuer_name="Seamount.io")
        mfa_data = {
            "user_id": current_user["id"],
            "secret": secret,
            "enabled": False,
            "created_at": datetime.utcnow().isoformat()
        }
        db.insert("user_mfa", mfa_data, upsert=True)
        await audit.log_action(current_user["id"], "mfa_setup_initiated", {})
        logger.info(f"MFA setup initiated for user: {current_user['id']}")
        return MFASetupResponse(secret=secret, qr_code_url=qr_code_url)
    except Exception as e:
        logger.error(f"MFA setup error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/user/mfa/verify", response_model=dict, tags=["Security"])
async def verify_mfa(
    mfa_request: MFAVerifyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
    audit: AuditService = Depends(get_audit)
):
    try:
        mfa_data = db.select("user_mfa", {"user_id": current_user["id"]})
        if not mfa_data:
            raise HTTPException(status_code=404, detail="MFA not set up")
        
        totp = pyotp.TOTP(mfa_data[0]["secret"])
        if not totp.verify(mfa_request.token):
            raise HTTPException(status_code=400, detail="Invalid MFA token")
        
        db.insert("user_mfa", {
            "user_id": current_user["id"],
            "secret": mfa_data[0]["secret"],
            "enabled": True,
            "verified_at": datetime.utcnow().isoformat()
        }, upsert=True)
        
        await audit.log_action(current_user["id"], "mfa_enabled", {})
        logger.info(f"MFA enabled for user: {current_user['id']}")
        return {"message": "MFA enabled successfully"}
    except Exception as e:
        logger.error(f"MFA verification error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/portfolio", response_model=List[PortfolioHolding], tags=["Portfolio"])
async def get_portfolio(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    try:
        holdings = db.select("portfolio_holdings", {"user_id": current_user["id"]})
        return holdings
    except Exception as e:
        logger.error(f"Portfolio fetch error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/health", tags=["System"])
async def health_check():
    try:
        supabase = await get_supabase_client()
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
async def get_treasury_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
    algo: Optional[algod.AlgodClient] = Depends(get_algo),
    db: DatabaseService = Depends(get_db)
):
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        treasury = TreasuryService(algo, db.supabase, get_settings().TREASURY_ADDRESS or "")
        demand_metrics = treasury.monitor_demand()
        return {
            "circulating_supply": demand_metrics["circulating_supply"],
            "utilization_rate": demand_metrics["utilization"],
            "status": "healthy" if demand_metrics["utilization"] < 90 else "high_demand",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Treasury status error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/admin/users", response_model=List[dict], tags=["Admin"], dependencies=[Depends(require_admin)])
async def get_all_users(db: DatabaseService = Depends(get_db)):
    try:
        users = db.select("user_profiles", {})
        return users
    except Exception as e:
        logger.error(f"Admin users fetch error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/admin/kyc/approve/{user_id}", response_model=dict, tags=["Admin"], dependencies=[Depends(require_admin)])
async def approve_kyc(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
    audit: AuditService = Depends(get_audit)
):
    try:
        db.insert("user_profiles", {
            "id": user_id,
            "kyc_status": "approved",
            "kyc_level": 2
        }, upsert=True)
        
        db.insert("kyc_documents", {
            "user_id": user_id,
            "status": "approved",
            "reviewed_at": datetime.utcnow().isoformat()
        }, upsert=True)
        
        await audit.log_action(current_user["id"], "kyc_approved", {"approved_user_id": user_id})
        return {"message": "KYC approved successfully"}
    except Exception as e:
        logger.error(f"KYC approval error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/dev/jwks-test", tags=["Development"])
async def test_jwks():
    try:
        settings = get_settings()
        jwks = await fetch_jwks(settings.JWKS_URL)
        return {
            "status": "success",
            "jwks_url": settings.JWKS_URL,
            "keys_count": len(jwks.get("keys", [])),
            "algorithms": [key.get("alg") for key in jwks.get("keys", [])]
        }
    except Exception as e:
        logger.error(f"JWKS test error: {str(e)}")
        raise HTTPException(status_code=503, detail=f"JWKS test failed: {str(e)}")

@app.post("/api/v1/stablecoin/mint", response_model=dict, tags=["Stablecoin"], dependencies=[Depends(require_admin)])
async def mint_usds(
    mint_request: MintRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
    audit: AuditService = Depends(get_audit),
    algo: Optional[algod.AlgodClient] = Depends(get_algo)
):
    if not algo or not get_settings().ALGORAND_CREATOR_MNEMONIC:
        raise HTTPException(status_code=503, detail="Algorand service not configured for minting.")
    try:
        mint_data = {
            "id": str(uuid4()),
            "amount": str(mint_request.amount),
            "recipient_address": mint_request.recipient_address,
            "status": "pending",
            "minted_by": current_user["id"]
        }
        db.insert("mint_transactions", mint_data)
        await audit.log_action(current_user["id"], "usds_minted", mint_data)
        return {"message": "Mint transaction created", "mint_id": mint_data["id"]}
    except Exception as e:
        logger.error(f"Mint error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/stablecoin/burn", response_model=dict, tags=["Stablecoin"], dependencies=[Depends(require_admin)])
async def burn_usds(
    burn_request: BurnRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
    audit: AuditService = Depends(get_audit),
    algo: Optional[algod.AlgodClient] = Depends(get_algo)
):
    if not algo or not get_settings().ALGORAND_CREATOR_MNEMONIC:
        raise HTTPException(status_code=503, detail="Algorand service not configured for burning.")
    try:
        burn_data = {
            "id": str(uuid4()),
            "amount": str(burn_request.amount),
            "sender_address": burn_request.sender_address,
            "status": "pending",
            "burned_by": current_user["id"]
        }
        db.insert("burn_transactions", burn_data)
        await audit.log_action(current_user["id"], "usds_burned", burn_data)
        return {"message": "Burn transaction created", "burn_id": burn_data["id"]}
    except Exception as e:
        logger.error(f"Burn error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/treasury/stats", response_model=dict, tags=["Treasury"])
async def get_treasury_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    algo: Optional[algod.AlgodClient] = Depends(get_algo),
    db: DatabaseService = Depends(get_db)
):
    if not get_settings().TREASURY_ADDRESS:
        raise HTTPException(status_code=501, detail="Treasury not configured")
    try:
        service = TreasuryService(algo, db.supabase, get_settings().TREASURY_ADDRESS)
        return service.monitor_demand()
    except Exception as e:
        logger.error(f"Treasury stats error: {str(e)}")
        raise HTTPException(status_code=503, detail="Treasury stats failed")

@app.post("/api/v1/payment", response_model=PaymentResponse, tags=["Payment"])
async def process_payment(
    payment: PaymentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
    audit: AuditService = Depends(get_audit),
    algo: Optional[algod.AlgodClient] = Depends(get_algo)
):
    try:
        recipient = db.select("user_profiles", {"email": payment.recipient_email})
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        tx_id = str(uuid4())
        tx_data = {
            "id": tx_id,
            "sender_id": current_user["id"],
            "recipient_id": recipient[0]["id"],
            "amount": payment.amount,
            "currency": payment.currency,
            "status": "pending",
            "timestamp": datetime.utcnow().isoformat()
        }
        db.insert("transactions", tx_data)
        await audit.log_action(current_user["id"], "payment_initiated", tx_data)
        
        if algo and recipient[0].get("algorand_address"):
            # Placeholder for Algorand transaction
            tx_data["status"] = "completed"
            db.insert("transactions", tx_data, upsert=True)
        
        return PaymentResponse(
            transaction_id=tx_id,
            status=tx_data["status"],
            amount=payment.amount,
            currency=payment.currency,
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Payment error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    logger.info("Starting Seamount.io API server...")
    logger.info(f"JWKS URL: {settings.JWKS_URL}")
    logger.info(f"Supabase URL: {settings.VITE_SUPABASE_URL}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
        log_level="info"
    )