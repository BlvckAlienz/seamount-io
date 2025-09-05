# File Location: backend/api/main.py
# CRITICAL FIX: Proper CORS and missing routes

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
import sys
from pathlib import Path

# Add the project root to the Python path for clean imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Import all routes and services
from backend.api.routes.licensing import router as licensing_router
from backend.api.routes import kyc, webhooks, portfolio, investor, consent
from backend.api.routes.users import router as users_router  # FIXED: Added missing users router
from backend.config import get_settings, BusinessModelConfig, LicenseTier, PricingRegion
from backend.services.email_service import EmailService
from backend.services.notification_service import NotificationService
from backend.services.wallet_service import WalletService
from backend.dependencies import initialize_dependencies, get_supabase_client, get_current_user, get_wallet_service, get_notification_service
from backend.models import UserProfile, SessionResponse, ProfileUpdateRequest
logger = logging.getLogger(__name__)

class BusinessLeadPayload(BaseModel):
    name: str
    business_name: Optional[str] = None
    email: EmailStr
    message: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- Seamount API Starting Up ---")
    try:
        settings = get_settings()
        supabase_client = create_client(
            settings.VITE_SUPABASE_URL, 
            settings.SUPABASE_SERVICE_KEY.get_secret_value()
        )
        email_service = EmailService(settings)
        notification_service = NotificationService(email_service)
        wallet_service = WalletService(settings, supabase_client)

        initialize_dependencies(supabase_client, wallet_service, notification_service)
        
        license_fee = settings.business_model.calculate_license_fee(
            LicenseTier.BASIC, 
            PricingRegion.NIGERIA
        )
        logger.info(f"Business model initialized. Basic license fee in Nigeria: {license_fee}")
        
        logger.info("All services initialized and injected into the dependency module.")
        yield
    except Exception as e:
        logger.critical(f"FATAL STARTUP ERROR: {e}\n{traceback.format_exc()}")
        raise
    logger.info("--- Seamount API Shutting Down ---")

app = FastAPI(
    title="Seamount.io API",
    version="3.1.4",
    description="The core API for Seamount's cross-border payment and treasury platform.",
    lifespan=lifespan
)

# FIXED: Update CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://www.seamount.io", "https://seamount.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FIXED: Update router inclusion with proper prefix
app.include_router(users_router, prefix="/api/v1/user", tags=["User"])
app.include_router(kyc.router, prefix="/api/v1", tags=["KYC"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(portfolio.router, prefix="/api/v1", tags=["Portfolio"])
app.include_router(investor.router, prefix="/api/v1", tags=["Investor"])
app.include_router(consent.router, prefix="/api/v1", tags=["Consent"])
app.include_router(licensing_router, prefix="/api/v1", tags=["Licensing"])

# REMOVED: Duplicate endpoints that were causing conflicts
# @app.get("/api/v1/user/profile", response_model=UserProfile)
# @app.put("/api/v1/user/profile")

@app.get("/api/v1/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "3.1.4"}
    
# Add these endpoints to main.py
@app.get("/api/v1/user/profile", response_model=UserProfile)
async def get_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    return current_user

@app.put("/api/v1/user/profile")
async def update_user_profile(
    update_data: ProfileUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    # Update logic here
    pass

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

    # FIXED: Enhanced IPInfo integration with timeout and better error handling
    if settings.IPINFO_TOKEN and ip_address != "unknown":
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2.0)) as http_session:
                async with http_session.get(
                    f"https://ipinfo.io/{ip_address}?token={settings.IPINFO_TOKEN.get_secret_value()}"
                ) as response:
                    if response.status == 200:
                        ip_data = await response.json()
                        session_data.update({
                            "country": ip_data.get("country", "US"),
                            "city": ip_data.get("city", "Unknown"),
                            "region": ip_data.get("region", "Unknown"),
                            "org": ip_data.get("org", "Unknown ISP"),
                            "timezone": ip_data.get("timezone", "UTC"),
                            "is_vpn": ip_data.get("privacy", {}).get("vpn", False)
                        })
                        logger.info(f"IPInfo enrichment successful for {ip_address}")
        except asyncio.TimeoutError:
            logger.warning(f"IPInfo timeout for IP {ip_address}")
        except Exception as e:
            logger.warning(f"IPInfo enrichment failed for IP {ip_address}: {e}")
    
    try:
        insert_res = supabase.from_("user_sessions").insert(session_data).execute()
        return JSONResponse(content={"session_id": session_data["id"]})
    except Exception as e:
        logger.error(f"Session initialization database error: {e}")
        return JSONResponse(content={"session_id": session_data["id"]})
    
    try:
        insert_res = supabase.from_("user_sessions").insert(session_data).execute()
        if not insert_res.data:
            logger.error(f"Failed to persist session to DB: {insert_res.error}")
        return JSONResponse(content={"session_id": session_data["id"]})
    except Exception as e:
        logger.error(f"Session initialization database error: {e}", exc_info=True)
        return JSONResponse(content={"session_id": session_data["id"]})

@app.post("/api/wallet/create", tags=["Wallet"])
async def create_wallet(
    current_user: Dict[str, Any] = Depends(get_current_user),
    wallet_service: WalletService = Depends(get_wallet_service),
    supabase: Client = Depends(get_supabase_client)
):
    user_id = current_user.get("id")
    if not user_id: 
        raise HTTPException(status_code=400, detail="User ID not found in token")
    
    logger.info(f"[Wallet Create] Initiated for user: {user_id}")
    try:
        wallet_res = supabase.from_("wallet_balances").select("wallet_address, is_demo").eq("user_id", user_id).maybe_single().execute()
        if wallet_res.data:
            return { 
                "success": True, 
                "message": "Wallet already exists", 
                **wallet_res.data, 
                "mnemonic": None 
            }

        new_wallet_material = wallet_service.create_algorand_wallet()
        await wallet_service.store_encrypted_wallet(user_id, new_wallet_material)
        
        return {
            "success": True,
            "address": new_wallet_material["address"],
            "mnemonic": new_wallet_material["mnemonic"],
            "message": "Wallet created successfully. Secure your mnemonic phrase immediately."
        }
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.critical(f"[Wallet Create] FAILED for user {user_id} [Error ID: {error_id}]: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"A critical server error occurred. Error ID: {error_id}")

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
        
        asyncio.create_task(notifier.email_service.send_email(
            subject, 
            ["support@seamount.io"], 
            body
        ))
        
        return {"message": "Your request has been submitted successfully."}
    except Exception as e:
        logger.error(f"Business contact submission failed: {e}")
        raise HTTPException(status_code=500, detail="Could not process your request.")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid4())[:8]
    logger.critical(f"Unhandled exception for request {request.url} [Error ID: {error_id}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected internal server error occurred. Please contact support with Error ID: {error_id}"},
    )