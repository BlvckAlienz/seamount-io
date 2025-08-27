# ==============================================================================
# Seamount.io API - Production Hardened
# Version: 2.7.0 (Implemented self-custody wallet creation handshake)
# ==============================================================================

import logging
import traceback
import asyncio
from contextlib import asynccontextmanager
from fastapi import (
    FastAPI, Depends, HTTPException, Request, status
)
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from supabase import create_client, Client
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timedelta
import aiohttp
from jose import JWTError, jwt

from config import Settings, get_settings
import sys
from pathlib import Path

# Add the backend directory to Python path for clean imports
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Import services, routes, and models
from services.notification_service import NotificationService
from services.email_service import EmailService
from services.wallet_service import WalletService
from api.routes import kyc, webhooks, portfolio
from models import UserProfile

# --- 1. SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)

class BusinessLeadPayload(BaseModel):
    name: str
    business_name: Optional[str] = None
    email: EmailStr
    message: Optional[str] = None

# --- 2. GLOBAL STATE & DEPENDENCIES ---
_supabase_client: Optional[Client] = None
_notification_service: Optional[NotificationService] = None
_wallet_service: Optional[WalletService] = None
jwks_cache: Dict[str, Any] = {}
jwks_cache_expiry: Optional[datetime] = None
security = HTTPBearer()

async def fetch_jwks(settings: Settings) -> Dict[str, Any]:
    global jwks_cache, jwks_cache_expiry
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry:
        return jwks_cache
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(settings.SUPABASE_JWKS_URI) as response:
                response.raise_for_status()
                jwks_data = await response.json()
                jwks_cache, jwks_cache_expiry = jwks_data, datetime.utcnow() + timedelta(hours=1)
                return jwks_data
    except Exception as e:
        logger.critical(f"CRITICAL: Could not fetch JWKS. Error: {e}")
        raise HTTPException(status_code=503, detail="Authentication service unavailable.")

async def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    try:
        token = credentials.credentials
        unverified_header = jwt.get_unverified_header(token)
        jwks = await fetch_jwks(settings)
        rsa_key = next((key for key in jwks["keys"] if key["kid"] == unverified_header["kid"]), None)
        if rsa_key:
            payload = jwt.decode(
                token, rsa_key, algorithms=["RS256"],
                audience="authenticated", issuer=settings.SUPABASE_JWT_ISSUER
            )
            return payload
        raise JWTError("Unable to find appropriate key")
    except JWTError as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

def get_supabase_client() -> Client:
    if not _supabase_client: raise HTTPException(status_code=503, detail="DB client not initialized")
    return _supabase_client

def get_wallet_service() -> WalletService:
    if not _wallet_service: raise HTTPException(status_code=503, detail="Wallet service not initialized")
    return _wallet_service

def get_notification_service() -> NotificationService:
    if not _notification_service: raise HTTPException(status_code=503, detail="Notification service not initialized")
    return _notification_service

async def get_current_user(
    payload: Dict[str, Any] = Depends(verify_supabase_token),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    user_id = payload.get("sub")
    if not user_id: raise HTTPException(status_code=401, detail="Invalid token payload: missing user ID")
    try:
        profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).single().execute()
        if not profile_res.data:
            logger.warning(f"User profile not found for user ID {user_id}. A profile should have been created on sign-up.")
            raise HTTPException(status_code=404, detail="User profile not found")
        return profile_res.data
    except Exception as e:
        logger.error(f"Failed to fetch profile for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving user profile.")

# --- 3. LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _supabase_client, _notification_service, _wallet_service
    logger.info("--- Seamount API Starting Up ---")
    try:
        settings = get_settings()
        _supabase_client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY.get_secret_value())
        email_service = EmailService(settings)
        _notification_service = NotificationService(email_service)
        _wallet_service = WalletService(settings, _supabase_client)
        logger.info("All services initialized successfully.")
        yield
    except Exception as e:
        logger.critical(f"FATAL STARTUP ERROR: {e}\n{traceback.format_exc()}")
        raise
    logger.info("--- Seamount API Shutting Down ---")

# --- 4. FASTAPI APP & ROUTING ---
app = FastAPI(title="Seamount.io API", version="2.7.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().ALLOWED_ORIGINS,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)
app.include_router(kyc.router, prefix="/api", tags=["KYC"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(portfolio.router, prefix="/api/v1", tags=["Portfolio"])

# --- 5. API ENDPOINTS ---
@app.get("/api/v1/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "2.7.0"}

@app.post("/api/v1/leads/business-contact", tags=["Public"])
async def business_contact(
    payload: BusinessLeadPayload,
    supabase: Client = Depends(get_supabase_client),
    notifier: NotificationService = Depends(get_notification_service)
):
    try:
        res = supabase.table('business_leads').insert(payload.model_dump()).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to save contact information")
        subject = f"New Seamount Business Lead: {payload.business_name or payload.name}"
        body = f"<p><b>Name:</b> {payload.name}</p><p><b>Company:</b> {payload.business_name or 'N/A'}</p><p><b>Email:</b> {payload.email}</p><p><b>Message:</b> {payload.message or 'N/A'}</p>"
        asyncio.create_task(notifier.email_service.send_email(subject, ["sales@seamount.io"], body))
        return {"message": "Your request has been submitted successfully."}
    except Exception as e:
        logger.error(f"Business contact submission failed: {e}")
        raise HTTPException(status_code=500, detail="Could not process your request.")

@app.get("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    return UserProfile(**current_user)

@app.post("/api/wallet/create", tags=["Wallet"])
async def create_wallet(
    current_user: Dict[str, Any] = Depends(get_current_user),
    wallet_service: WalletService = Depends(get_wallet_service),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Creates a self-custodial wallet for the user.
    On first creation, it returns the mnemonic phrase for user backup.
    If a wallet already exists, it confirms its existence without exposing keys.
    """
    user_id = current_user["id"]
    logger.info(f"Wallet creation request for user: {user_id}")
    
    # Step 1: Check if a wallet already exists to prevent overwrites.
    # Note: We query 'wallet_balances' as per the schema.
    wallet_res = supabase.from_("wallet_balances").select("wallet_address").eq("user_id", user_id).maybe_single().execute()
    
    if wallet_res.data:
        logger.info(f"Wallet already exists for user {user_id}. Confirming address.")
        return {
            "success": True,
            "message": "Wallet already exists.",
            "address": wallet_res.data["wallet_address"],
            "mnemonic": None  # CRITICAL: Do not expose mnemonic for existing wallets.
        }

    # Step 2: If no wallet exists, proceed with the creation handshake.
    try:
        logger.info(f"No existing wallet found. Starting generation for user {user_id}.")
        
        # Generate the full key material (address, private key, mnemonic).
        new_wallet_material = wallet_service.create_algorand_wallet()

        # Store the encrypted wallet (this function does NOT store the mnemonic).
        await wallet_service.store_encrypted_wallet(user_id, new_wallet_material)

        # Return the mnemonic and address to the frontend ONCE for user backup.
        logger.warning(f"SECURITY: Returning mnemonic phrase to user {user_id} for one-time backup.")
        return {
            "success": True,
            "message": "Wallet created successfully. Secure your mnemonic phrase immediately.",
            "address": new_wallet_material["address"],
            "mnemonic": new_wallet_material["mnemonic"]
        }
    except Exception as e:
        logger.critical(f"Wallet creation process failed for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="A critical error occurred while creating your wallet. Please try again later.")

# --- 6. ERROR HANDLING MIDDLEWARE ---
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Unhandled exception in request {request.url} [{error_id}]: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"An unexpected internal server error occurred. Please contact support with Error ID: {error_id}"}
        )