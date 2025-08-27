# ==============================================================================
# Seamount.io API - Main Application Entrypoint
# Version: 3.0.0 (Restored critical authentication endpoints)
# ==============================================================================

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from uuid import uuid4
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
from dependencies import initialize_dependencies, get_current_user, get_supabase_client, get_notification_service
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
    version="3.0.0",
    description="The core API for Seamount's cross-border payment and treasury platform.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Routers from other files ---
app.include_router(kyc.router, prefix="/api", tags=["KYC"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(portfolio.router, prefix="/api/v1", tags=["Portfolio"])

# --- Public & Core API Endpoints ---
@app.get("/api/v1/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "3.0.0"}

@app.post("/api/v1/session/initialize", response_model=SessionResponse, tags=["Session"])
async def initialize_session(
    request: Request,
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Initializes a new user session, performs IP enrichment, and returns a session ID.
    This endpoint is now correctly restored.
    """
    settings = get_settings()
    ip_address = request.client.host if request.client else "unknown"
    session_data = {
        "id": str(uuid4()), "ip_address": ip_address, "user_agent": user_agent,
        "created_at": datetime.utcnow().isoformat()
    }

    if settings.IPINFO_TOKEN.get_secret_value():
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as http_session:
                async with http_session.get(f"https://ipinfo.io/{ip_address}?token={settings.IPINFO_TOKEN.get_secret_value()}") as response:
                    if response.status == 200:
                        ip_data = await response.json()
                        session_data.update({"country": ip_data.get("country"), "city": ip_data.get("city")})
        except Exception as e:
            logger.warning(f"IPinfo enrichment failed for IP {ip_address}: {e}")
    
    try:
        insert_res = supabase.from_("user_sessions").insert(session_data).execute()
        if not insert_res.data:
            raise Exception("Failed to create session record in database.")
        
        session_id = insert_res.data[0]['id']
        return JSONResponse(content={"session_id": session_id})
    except Exception as e:
        logger.error(f"Session initialization database error: {e}")
        raise HTTPException(status_code=500, detail="Could not initialize session.")

@app.get("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retrieves the full profile for the currently authenticated user.
    This endpoint is now correctly restored.
    """
    return UserProfile(**current_user)

@app.post("/api/v1/leads/business-contact", tags=["Public"])
async def business_contact(payload: BusinessLeadPayload):
    supabase = get_supabase_client()
    notifier = get_notification_service()
    try:
        res = supabase.table('business_leads').insert(payload.model_dump()).execute()
        if not res.data: raise Exception("Failed to save lead.")
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