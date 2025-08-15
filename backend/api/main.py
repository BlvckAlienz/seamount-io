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
    SUPABASE_SERVICE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")  # Optional now
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
    # JWT_SECRET removed - we'll use JWKS instead
    PORT: int = int(os.getenv("PORT", 8000))
    
    @property
    def SUPABASE_JWT_SECRET(self) -> Optional[str]:
        """Legacy fallback for development only"""
        return os.getenv("JWT_SECRET")
    
    @property
    def JWKS_URL(self) -> str:
        """Construct JWKS URL from Supabase URL"""
        return f"{self.VITE_SUPABASE_URL.rstrip('/')}/rest/v1/auth/jwks"

def get_settings() -> Settings:
    """Initialize settings without requiring specific env vars"""
    try:
        settings = Settings()
        # Only require VITE_SUPABASE_URL
        if not settings.VITE_SUPABASE_URL:
            logger.error("VITE_SUPABASE_URL is required")
            raise ValueError("VITE_SUPABASE_URL is required")
        
        logger.info(f"Settings loaded successfully. JWKS URL: {settings.JWKS_URL}")
        return settings
    except Exception as e:
        logger.error(f"Failed to load settings: {str(e)}")
        raise

# JWKS Authentication Implementation
async def fetch_jwks(jwks_url: str) -> Dict[str, Any]:
    """Fetch JWKS from Supabase with caching and retry logic"""
    global jwks_cache, jwks_cache_expiry
    
    # Check cache first (cache for 1 hour)
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry:
        logger.debug("Using cached JWKS")
        return jwks_cache
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(jwks_url) as response:
                if response.status == 200:
                    jwks_data = await response.json()
                    # Cache for 1 hour
                    jwks_cache = jwks_data
                    jwks_cache_expiry = datetime.utcnow() + timedelta(hours=1)
                    logger.info("JWKS fetched and cached successfully")
                    return jwks_data
                else:
                    logger.error(f"Failed to fetch JWKS: HTTP {response.status}")
                    # Fall back to cached data if available
                    if jwks_cache:
                        logger.warning("Using stale JWKS cache due to fetch failure")
                        return jwks_cache
                    raise HTTPException(status_code=503, detail="JWKS service unavailable")
    except Exception as e:
        logger.error(f"JWKS fetch error: {str(e)}")
        # Fall back to cached data if available
        if jwks_cache:
            logger.warning("Using stale JWKS cache due to network error")
            return jwks_cache
        raise HTTPException(status_code=503, detail="Authentication service unavailable")

def jwk_to_pem(jwk: Dict[str, Any]) -> str:
    """Convert JWK to PEM format for token verification"""
    try:
        if jwk.get('kty') == 'RSA':
            # RSA key
            n = base64.urlsafe_b64decode(jwk['n'] + '==')
            e = base64.urlsafe_b64decode(jwk['e'] + '==')
            
            # Convert to integers
            n_int = int.from_bytes(n, 'big')
            e_int = int.from_bytes(e, 'big')
            
            # Create RSA public key
            public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key()
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            return pem.decode('utf-8')
        
        elif jwk.get('kty') == 'EC':
            # Elliptic Curve key (ES256)
            x = base64.urlsafe_b64decode(jwk['x'] + '==')
            y = base64.urlsafe_b64decode(jwk['y'] + '==')
            
            # Convert to integers
            x_int = int.from_bytes(x, 'big')
            y_int = int.from_bytes(y, 'big')
            
            # Create EC public key (P-256 curve for ES256)
            public_key = ec.EllipticCurvePublicNumbers(
                x_int, y_int, ec.SECP256R1()
            ).public_key()
            
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            return pem.decode('utf-8')
        
        else:
            raise ValueError(f"Unsupported key type: {jwk.get('kty')}")
            
    except Exception as e:
        logger.error(f"JWK to PEM conversion error: {str(e)}")
        raise

async def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """Verify JWT token using JWKS with fallback to legacy method"""
    settings = get_settings()
    
    try:
        # Decode header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        alg = unverified_header.get('alg', 'HS256')
        
        logger.debug(f"Token algorithm: {alg}, kid: {kid}")
        
        # Try JWKS verification first (modern method)
        if kid and alg in ['RS256', 'ES256']:
            try:
                jwks = await fetch_jwks(settings.JWKS_URL)
                
                # Find the matching key
                matching_key = None
                for key in jwks.get('keys', []):
                    if key.get('kid') == kid:
                        matching_key = key
                        break
                
                if matching_key:
                    # Convert JWK to PEM and verify
                    public_key_pem = jwk_to_pem(matching_key)
                    payload = jwt.decode(
                        token, 
                        public_key_pem, 
                        algorithms=[alg],
                        audience=settings.VITE_SUPABASE_URL.split('//')[1].split('.')[0]  # Extract project ref
                    )
                    logger.debug("JWT verified using JWKS")
                    return payload
                else:
                    logger.warning(f"No matching key found for kid: {kid}")
            except Exception as e:
                logger.warning(f"JWKS verification failed: {str(e)}")
        
        # Fallback to legacy HS256 method (development/backward compatibility)
        if settings.SUPABASE_JWT_SECRET and alg == 'HS256':
            try:
                payload = jwt.decode(
                    token, 
                    settings.SUPABASE_JWT_SECRET, 
                    algorithms=['HS256']
                )
                logger.debug("JWT verified using legacy HS256 secret")
                return payload
            except Exception as e:
                logger.warning(f"Legacy JWT verification failed: {str(e)}")
        
        # If we reach here, verification failed
        raise HTTPException(status_code=401, detail="Invalid or unverifiable token")
        
    except JWTError as e:
        logger.error(f"JWT verification error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token format")
    except Exception as e:
        logger.error(f"Unexpected JWT verification error: {str(e)}")
        raise HTTPException(status_code=401, detail="Token verification failed")

# Models (unchanged)
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
        # Use anon key if service key not available
        api_key = settings.SUPABASE_SERVICE_KEY or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wcW5vZmljbGhieWx4ZnBhZWhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjM2NjI0MzIsImV4cCI6MjAzOTIzODQzMn0.lrJT_7vQOJTWJHQPBT_ODxW3OcZSAodThYsVlGLEqoc"
        client = create_client(settings.VITE_SUPABASE_URL, api_key)
        logger.info("Supabase client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_algorand_client() -> Optional[algod.AlgodClient]:
    settings = get_settings()
    if not settings.ALGORAND_API_KEY:
        logger.info("Algorand client not configured (missing API key)")
        return None
    
    try:
        algod_client = algod.AlgodClient(
            settings.ALGORAND_API_KEY,
            settings.ALGORAND_NODE_URL,
            headers={"X-API-Key": settings.ALGORAND_API_KEY}
        )
        logger.info("Algorand client initialized successfully")
        return algod_client
    except Exception as e:
        logger.error(f"Failed to initialize Algorand client: {str(e)}")
        return None

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
        """
        Write to compliance_logs without ever taking the app down if logging fails.
        Columns used: user_id, action_taken, details, created_at
        """
        try:
            self.supabase.from_("compliance_logs").insert({
                "user_id": user_id,
                "action_taken": action,
                "details": details,
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
            logger.info(f"Logged action: {action} for user {user_id}")
        except Exception as e:
            # Log and swallow to avoid crashing startup/shutdown
            logger.error(f"Failed to log action: {str(e)}")

class TreasuryService:
    def __init__(self, algorand_client: Optional[algod.AlgodClient], supabase: Client, reserve_address: str):
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
            if self.algorand_client and action == "mint":
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
        algorand_client = await get_algorand_client()
        
        # Pre-warm JWKS cache
        settings = get_settings()
        try:
            await fetch_jwks(settings.JWKS_URL)
            logger.info("JWKS cache pre-warmed")
        except Exception as e:
            logger.warning(f"JWKS pre-warming failed: {str(e)}")
        
        logger.info("Services initialized successfully")
        
        # Log startup
        if audit_service:
            await audit_service.log_action("system", "application_started", {
                "timestamp": datetime.utcnow().isoformat(),
                "services": {
                    "database": "connected",
                    "algorand": "connected" if algorand_client else "not_configured",
                    "jwks": "ready"
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
    """Get current user from Supabase JWT token using JWKS verification"""
    try:
        # Verify token using JWKS
        payload = await verify_supabase_jwt(token)
        user_id: str = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")
        
        # Get user from database
        supabase = await get_supabase_client()
        user = supabase.from_("user_profiles").select("*").eq("id", user_id).single().execute()
        
        if not user.data:
            # User might exist in auth but not in profiles - create profile
            auth_user = payload
            user_data = {
                "id": user_id,
                "email": auth_user.get("email"),
                "created_at": datetime.utcnow().isoformat(),
                "kyc_level": 0,
                "kyc_status": "pending",
                "is_admin": False
            }
            
            try:
                await database_service.insert("user_profiles", user_data)
                return user_data
            except Exception as e:
                logger.error(f"Failed to create user profile: {str(e)}")
                raise HTTPException(status_code=401, detail="User profile not found")
        
        return user.data
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"User authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")

async def get_api_key(api_key: str = Security(api_key_header)):
    """Simple API key validation - you may want to use a proper API key system"""
    settings = get_settings()
    # Use a default API key or remove this endpoint if not needed
    expected_key = settings.SUPABASE_JWT_SECRET or "seamount-dev-key"
    if api_key != expected_key:
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

# API Routes (keeping existing routes but removing JWT dependency)
@app.post("/api/v1/user/register", response_model=dict, tags=["User"])
async def register_user(user: UserProfile):
    """Register new user - note: this creates a profile but Supabase handles auth"""
    global database_service, audit_service
    supabase = await get_supabase_client()
    if not database_service:
        database_service = DatabaseService(supabase)
    if not audit_service:
        audit_service = AuditService(supabase)
    
    try:
        # Generate Algorand address
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
        
        # Send welcome email
        settings = get_settings()
        if settings.MAIL_PASSWORD:  # Only send if mail is configured
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
        return {"message": "User registered successfully", "algorand_address": algorand_address}
        
    except Exception as e:
        logger.error(f"User registration error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/token", response_model=Token, tags=["User"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Legacy login endpoint - in production, use Supabase Auth directly"""
    logger.warning("Legacy login endpoint used - consider using Supabase Auth directly")
    supabase = await get_supabase_client()
    
    try:
        user = supabase.from_("user_profiles").select("*").eq("email", form_data.username).single().execute()
        if not user.data or not pwd_context.verify(form_data.password, user.data["password"]):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        # For legacy compatibility, create a simple token
        # In production, this should redirect to Supabase Auth
        settings = get_settings()
        access_token_expires = timedelta(minutes=30)
        
        # Use a fallback secret for dev environments
        secret = settings.SUPABASE_JWT_SECRET or "dev-fallback-secret-change-in-production"
        access_token = jwt.encode(
            {"sub": user.data["id"], "exp": datetime.utcnow() + access_token_expires},
            secret,
            algorithm="HS256"
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

# Keep all other endpoints as they were, just removing the JWT_SECRET requirement

@app.get("/api/v1/health", tags=["System"])
async def health_check():
    try:
        supabase = await get_supabase_client()
        # Basic connection test
        supabase.from_("user_profiles").select("id").limit(1).execute()
        
        # Test JWKS endpoint
        settings = get_settings()
        jwks_status = "ready"
        try:
            await fetch_jwks(settings.JWKS_URL)
        except Exception:
            jwks_status = "degraded"
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "connected",
                "algorand": "connected" if algorand_client else "not_configured",
                "jwks": jwks_status
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.post("/api/v1/user/update-kyc", response_model=dict, tags=["User"])
async def update_kyc(kyc: KYCSubmission, current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service, audit_service
    try:
        kyc_data = kyc.dict()
        kyc_data["id"] = str(uuid4())
        kyc_data["status"] = "pending"
        kyc_data["submitted_at"] = datetime.utcnow().isoformat()
        
        await database_service.insert("kyc_documents", kyc_data)
        await audit_service.log_action(current_user["id"], "kyc_submitted", kyc_data)
        
        logger.info(f"KYC submitted for user: {current_user['id']}")
        return {"message": "KYC submitted successfully", "document_id": kyc_data["id"]}
        
    except Exception as e:
        logger.error(f"KYC submission error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/user/kyc-status", response_model=dict, tags=["User"])
async def get_kyc_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        supabase = await get_supabase_client()
        documents = supabase.from_("kyc_documents").select("*").eq("user_id", current_user["id"]).execute()
        
        return {
            "kyc_level": current_user.get("kyc_level", 0),
            "kyc_status": current_user.get("kyc_status", "pending"),
            "documents": documents.data or []
        }
        
    except Exception as e:
        logger.error(f"KYC status fetch error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/payments/send", response_model=PaymentResponse, tags=["Payments"])
async def send_payment(payment: PaymentRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service, audit_service
    try:
        # Get recipient user
        supabase = await get_supabase_client()
        recipient = supabase.from_("user_profiles").select("*").eq("email", payment.recipient_email).single().execute()
        
        if not recipient.data:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        transaction_data = {
            "id": str(uuid4()),
            "sender_id": current_user["id"],
            "recipient_id": recipient.data["id"],
            "amount": str(payment.amount),
            "currency": payment.currency,
            "status": "completed",
            "created_at": datetime.utcnow().isoformat(),
            "transaction_type": "transfer"
        }
        
        await database_service.insert("transactions", transaction_data)
        await audit_service.log_action(current_user["id"], "payment_sent", transaction_data)
        
        logger.info(f"Payment sent: {transaction_data['id']}")
        return PaymentResponse(
            transaction_id=transaction_data["id"],
            status=transaction_data["status"],
            amount=payment.amount,
            currency=payment.currency,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Payment send error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/payments/history", response_model=List[dict], tags=["Payments"])
async def get_payment_history(current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        supabase = await get_supabase_client()
        
        # Get sent payments
        sent_payments = supabase.from_("transactions").select("*").eq("sender_id", current_user["id"]).execute()
        
        # Get received payments
        received_payments = supabase.from_("transactions").select("*").eq("recipient_id", current_user["id"]).execute()
        
        all_payments = (sent_payments.data or []) + (received_payments.data or [])
        
        # Sort by created_at descending
        all_payments.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return all_payments
        
    except Exception as e:
        logger.error(f"Payment history fetch error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/stablecoin/mint", response_model=dict, tags=["Stablecoin"])
async def mint_usds(mint_request: MintRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service, audit_service
    try:
        # Check if user is admin or has proper permissions
        if not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        settings = get_settings()
        if not algorand_client or not settings.ALGORAND_CREATOR_MNEMONIC:
            raise HTTPException(status_code=503, detail="Algorand service not configured")
        
        # Create mint transaction record
        mint_data = {
            "id": str(uuid4()),
            "amount": str(mint_request.amount),
            "recipient_address": mint_request.recipient_address,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "minted_by": current_user["id"]
        }
        
        await database_service.insert("mint_transactions", mint_data)
        await audit_service.log_action(current_user["id"], "usds_minted", mint_data)
        
        logger.info(f"USDS mint initiated: {mint_data['id']}")
        return {"message": "Mint transaction created", "mint_id": mint_data["id"], "status": "pending"}
        
    except Exception as e:
        logger.error(f"USDS mint error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/stablecoin/burn", response_model=dict, tags=["Stablecoin"])
async def burn_usds(burn_request: BurnRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service, audit_service
    try:
        # Create burn transaction record
        burn_data = {
            "id": str(uuid4()),
            "amount": str(burn_request.amount),
            "sender_address": burn_request.sender_address,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "burned_by": current_user["id"]
        }
        
        await database_service.insert("burn_transactions", burn_data)
        await audit_service.log_action(current_user["id"], "usds_burned", burn_data)
        
        logger.info(f"USDS burn initiated: {burn_data['id']}")
        return {"message": "Burn transaction created", "burn_id": burn_data["id"], "status": "pending"}
        
    except Exception as e:
        logger.error(f"USDS burn error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/treasury/stats", response_model=dict, tags=["Treasury"])
async def get_treasury_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        settings = get_settings()
        if not settings.TREASURY_ADDRESS:
            return {"error": "Treasury not configured"}
        
        treasury_service = TreasuryService(algorand_client, await get_supabase_client(), settings.TREASURY_ADDRESS)
        stats = await treasury_service.monitor_demand()
        
        return stats
        
    except Exception as e:
        logger.error(f"Treasury stats error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/user/mfa/setup", response_model=MFASetupResponse, tags=["Security"])
async def setup_mfa(current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service, audit_service
    try:
        # Generate TOTP secret
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        
        # Generate QR code URL
        qr_url = totp.provisioning_uri(
            current_user["email"],
            issuer_name="Seamount.io"
        )
        
        # Store secret in database
        mfa_data = {
            "user_id": current_user["id"],
            "secret": secret,
            "enabled": False,
            "created_at": datetime.utcnow().isoformat()
        }
        
        await database_service.insert("user_mfa", mfa_data, upsert=True)
        await audit_service.log_action(current_user["id"], "mfa_setup_initiated", {"method": "totp"})
        
        return MFASetupResponse(secret=secret, qr_code_url=qr_url)
        
    except Exception as e:
        logger.error(f"MFA setup error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/user/mfa/verify", response_model=dict, tags=["Security"])
async def verify_mfa(mfa_request: MFAVerifyRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service, audit_service
    try:
        supabase = await get_supabase_client()
        
        # Get user's MFA secret
        mfa_data = supabase.from_("user_mfa").select("*").eq("user_id", current_user["id"]).single().execute()
        
        if not mfa_data.data:
            raise HTTPException(status_code=404, detail="MFA not set up")
        
        # Verify token
        totp = pyotp.TOTP(mfa_data.data["secret"])
        if not totp.verify(mfa_request.token):
            raise HTTPException(status_code=401, detail="Invalid MFA token")
        
        # Enable MFA if not already enabled
        if not mfa_data.data["enabled"]:
            supabase.from_("user_mfa").update({"enabled": True}).eq("user_id", current_user["id"]).execute()
            await audit_service.log_action(current_user["id"], "mfa_enabled", {"method": "totp"})
        else:
            await audit_service.log_action(current_user["id"], "mfa_verified", {"method": "totp"})
        
        return {"message": "MFA verified successfully"}
        
    except Exception as e:
        logger.error(f"MFA verification error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/user/portfolio", response_model=List[PortfolioHolding], tags=["Portfolio"])
async def get_portfolio(current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        supabase = await get_supabase_client()
        holdings = supabase.from_("user_portfolios").select("*").eq("user_id", current_user["id"]).execute()
        
        return holdings.data or []
        
    except Exception as e:
        logger.error(f"Portfolio fetch error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/contact/investor", response_model=dict, tags=["Contact"])
async def investor_contact(contact: InvestorContactPayload):
    global database_service, audit_service
    try:
        contact_data = contact.dict()
        contact_data["id"] = str(uuid4())
        contact_data["created_at"] = datetime.utcnow().isoformat()
        contact_data["status"] = "new"
        
        await database_service.insert("investor_contacts", contact_data)
        
        # Send notification email to team
        settings = get_settings()
        if settings.MAIL_PASSWORD:
            msg = MIMEText(f"New investor contact: {contact.name} ({contact.email})\nCheck size: {contact.checkSize}\nMessage: {contact.message}")
            msg["Subject"] = "New Investor Contact - Seamount.io"
            msg["From"] = settings.MAIL_FROM
            msg["To"] = "investors@seamount.io"  # Configure this
            
            try:
                with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
                    if settings.MAIL_STARTTLS:
                        server.starttls()
                    server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                    server.send_message(msg)
            except Exception as e:
                logger.error(f"Failed to send investor notification: {str(e)}")
        
        logger.info(f"Investor contact received: {contact.email}")
        return {"message": "Contact submitted successfully"}
        
    except Exception as e:
        logger.error(f"Investor contact error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/whitelabel/quote", response_model=dict, tags=["Whitelabel"])
async def get_whitelabel_quote(quote: WhitelabelQuotePayload):
    try:
        # Simple quote calculation - in production, integrate with real pricing APIs
        base_rate = 1.0 if quote.from_currency == "USD" and quote.to_currency == "USDS" else 0.999
        fee_rate = 0.001  # 0.1% fee
        
        gross_amount = float(quote.amount) * base_rate
        fee_amount = gross_amount * fee_rate
        net_amount = gross_amount - fee_amount
        
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
async def update_consent(consent: ConsentPayload, current_user: Dict[str, Any] = Depends(get_current_user)):
    global database_service, audit_service
    try:
        consent_data = {
            "user_id": current_user["id"],
            "preferences": json.dumps(consent.preferences),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await database_service.insert("user_consent", consent_data, upsert=True)
        await audit_service.log_action(current_user["id"], "consent_updated", consent_data)
        
        return {"message": "Consent preferences updated"}
        
    except Exception as e:
        logger.error(f"Consent update error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Admin endpoints
@app.get("/api/v1/admin/users", response_model=List[dict], tags=["Admin"])
async def get_all_users(current_user: Dict[str, Any] = Depends(get_current_user)):
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    try:
        supabase = await get_supabase_client()
        users = supabase.from_("user_profiles").select("*").execute()
        return users.data or []
        
    except Exception as e:
        logger.error(f"Admin users fetch error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/admin/kyc/approve/{user_id}", response_model=dict, tags=["Admin"])
async def approve_kyc(user_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    global audit_service
    try:
        supabase = await get_supabase_client()
        
        # Update user profile
        supabase.from_("user_profiles").update({
            "kyc_status": "approved",
            "kyc_level": 2
        }).eq("id", user_id).execute()
        
        # Update KYC documents
        supabase.from_("kyc_documents").update({
            "status": "approved",
            "reviewed_at": datetime.utcnow().isoformat()
        }).eq("user_id", user_id).execute()
        
        await audit_service.log_action(current_user["id"], "kyc_approved", {"approved_user_id": user_id})
        
        return {"message": "KYC approved successfully"}
        
    except Exception as e:
        logger.error(f"KYC approval error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Development/testing endpoints
@app.get("/api/v1/dev/jwks-test", tags=["Development"])
async def test_jwks():
    """Test JWKS endpoint connectivity"""
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
        reload=False,  # Disable reload in production
        log_level="info"
    )