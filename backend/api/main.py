# ==============================================================================
# Seamount.io API - Main Application Entrypoint
# Version: 3.0.3 (Fixed CORS, authentication, and wallet creation flow)
# ==============================================================================

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
import asyncio
import traceback
import aiohttp

# Add the project root to the Python path for clean imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Import core components and services
from config import get_settings
from services.email_service import EmailService
from services.notification_service import NotificationService
from services.wallet_service import WalletService
from services.kyc_providers.complycube import complycube_service
from dependencies import initialize_dependencies, get_current_user, get_supabase_client, get_notification_service, get_wallet_service
from api.routes import kyc, webhooks, portfolio
from models import UserProfile, SessionResponse

logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class BusinessLeadPayload(BaseModel):
    name: str
    business_name: Optional[str] = None
    email: EmailStr
    message: Optional[str] = None

# --- Lifespan Manager (Application Startup & Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- Seamount API Starting Up ---")
    try:
        settings = get_settings()
        supabase_client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY.get_secret_value())
        email_service = EmailService(settings)
        notification_service = NotificationService(email_service)
        wallet_service = WalletService(settings, supabase_client)
        initialize_dependencies(
            supabase_client=supabase_client,
            wallet_service=wallet_service,
            notification_service=notification_service
        )
        logger.info("All services initialized and injected into dependencies.")
        yield
    except Exception as e:
        logger.critical(f"FATAL STARTUP ERROR: {e}\n{traceback.format_exc()}")
        raise
    logger.info("--- Seamount API Shutting Down ---")

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Seamount.io API",
    version="3.0.3",
    description="The core API for Seamount's cross-border payment and treasury platform.",
    lifespan=lifespan
)

# Enhanced CORS configuration - explicitly include www subdomain
settings = get_settings()
allowed_origins = settings.ALLOWED_ORIGINS
if "https://www.seamount.io" not in allowed_origins:
    allowed_origins.append("https://www.seamount.io")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# --- Include Routers from other files ---
app.include_router(kyc.router, prefix="/api", tags=["KYC"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(portfolio.router, prefix="/api/v1", tags=["Portfolio"])

# --- Public & Core API Endpoints ---
@app.get("/api/v1/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "3.0.3"}

@app.post("/api/v1/session/initialize", response_model=SessionResponse, tags=["Session"])
async def initialize_session(
    request: Request,
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    supabase: Client = Depends(get_supabase_client)
):
    settings = get_settings()
    ip_address = request.client.host if request.client else "unknown"
    session_data = {
        "id": str(uuid4()), 
        "ip_address": ip_address, 
        "user_agent": user_agent,
        "created_at": datetime.utcnow().isoformat()
    }

    # Only call IPinfo if token is available and not empty
    ipinfo_token = settings.IPINFO_TOKEN.get_secret_value()
    if ipinfo_token and ipinfo_token.strip():
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as http_session:
                async with http_session.get(f"https://ipinfo.io/{ip_address}?token={ipinfo_token}") as response:
                    if response.status == 200:
                        ip_data = await response.json()
                        session_data.update({
                            "country": ip_data.get("country"), 
                            "city": ip_data.get("city")
                        })
        except Exception as e:
            logger.warning(f"IPinfo enrichment failed for IP {ip_address}: {e}")
    
    try:
        insert_res = supabase.from_("user_sessions").insert(session_data).execute()
        if not insert_res.data:
            logger.error(f"Session insert failed: {insert_res}")
            # Still return a session ID even if DB insert fails to not break the flow
            return JSONResponse(content={"session_id": str(uuid4())})
        
        session_id = insert_res.data[0]['id']
        return JSONResponse(content={"session_id": session_id})
    except Exception as e:
        logger.error(f"Session initialization database error: {e}", exc_info=True)
        # Return a session ID even if DB insert fails to not break the flow
        return JSONResponse(content={"session_id": str(uuid4())})

@app.get("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    return UserProfile(**current_user)

@app.post("/api/wallet/create", tags=["Wallet"])
async def create_wallet(
    current_user: Dict[str, Any] = Depends(get_current_user),
    wallet_service: WalletService = Depends(get_wallet_service),
    supabase: Client = Depends(get_supabase_client)
):
    """Create a new wallet for the authenticated user"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found in token")
        
        logger.info(f"Creating wallet for user: {user_id}")
        
        # Check if user already has a wallet in wallet_balances table
        wallet_res = supabase.from_("wallet_balances").select("*").eq("user_id", user_id).execute()
        
        if wallet_res.data:
            logger.info(f"User {user_id} already has a wallet")
            return {
                "success": True,
                "message": "Wallet already exists",
                "address": wallet_res.data[0]["wallet_address"],
                "is_demo": wallet_res.data[0].get("is_demo", False)
            }
        
        # Create a new wallet
        wallet_data = wallet_service.create_algorand_wallet()
        
        # Store the encrypted wallet
        stored_wallet = await wallet_service.store_encrypted_wallet(user_id, wallet_data)
        
        return {
            "success": True,
            "address": wallet_data["address"],
            "mnemonic": wallet_data["mnemonic"],  # Return only once to user
            "message": "Wallet created successfully. Please securely store your mnemonic phrase."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Wallet creation failed for user {user_id} [{error_id}]: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create wallet. Error ID: {error_id}")

@app.post("/api/kyc/start-verification", tags=["KYC"])
async def start_kyc_verification(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Start KYC verification process with ComplyCube"""
    try:
        logger.info(f"Starting KYC verification for user: {current_user['id']}")
        
        # Check if user already has an applicant ID
        if current_user.get('complycube_applicant_id'):
            logger.info(f"User {current_user['id']} already has applicant ID: {current_user['complycube_applicant_id']}")
            # Generate token for existing applicant
            token = complycube_service.create_verification_token(current_user['complycube_applicant_id'])
        else:
            # Create new applicant
            user_data = {
                'email': current_user['email'],
                'first_name': current_user.get('first_name', ''),
                'last_name': current_user.get('last_name', '')
            }
            
            applicant = complycube_service.create_applicant(user_data)
            
            # Update user profile with applicant ID
            update_data = {
                'complycube_applicant_id': applicant.id,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            result = supabase.from_("user_profiles") \
                .update(update_data) \
                .eq('id', current_user['id']) \
                .execute()
                
            if not result.data:
                logger.error(f"Failed to update user profile with applicant ID: {applicant.id}")
                raise HTTPException(status_code=500, detail="Failed to update user profile")
            
            # Generate verification token
            token = complycube_service.create_verification_token(applicant.id)
        
        return {
            "success": True,
            "token": token,
            "message": "KYC verification started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"KYC start error [{error_id}]: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error starting KYC. Error ID: {error_id}")

@app.post("/api/v1/leads/business-contact", tags=["Public"])
async def business_contact(payload: BusinessLeadPayload):
    supabase = get_supabase_client()
    notifier = get_notification_service()
    try:
        res = supabase.table('business_leads').insert(payload.model_dump()).execute()
        if not res.data: 
            raise Exception("Failed to save lead.")
        subject = f"New Seamount Business Lead: {payload.business_name or payload.name}"
        body = f"<p><b>Name:</b> {payload.name}</p><p><b>Company:</b> {payload.business_name or 'N/A'}</p><p><b>Email:</b> {payload.email}</p><p><b>Message:</b> {payload.message or 'N/A'}</p>"
        asyncio.create_task(notifier.email_service.send_email(subject, ["sales@seamount.io"], body))
        return {"message": "Your request has been submitted successfully."}
    except Exception as e:
        logger.error(f"Business contact submission failed: {e}")
        raise HTTPException(status_code=500, detail="Could not process your request.")

# --- Global Exception Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid4())[:8]
    logger.critical(f"Unhandled exception for request {request.url} [Error ID: {error_id}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected internal server error occurred. Please contact support with Error ID: {error_id}"},
    )