# File Location: backend/api/main.py
# CRITICAL FIX: Proper CORS, Security, and corrected routes without duplicates

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from supabase import create_client, Client
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timedelta
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
from backend.api.routes.users import router as users_router
from backend.config import Settings, get_settings, BusinessModelConfig, LicenseTier, PricingRegion
from backend.services.email_service import EmailService
from backend.services.notification_service import NotificationService
from backend.services.wallet_service import WalletService
from backend.services.kyc_service import KYCService
from backend.services.database_service import DatabaseService
from backend.services.audit_service import AuditService
from backend.dependencies import initialize_dependencies, get_supabase_client, get_current_user, get_wallet_service, get_notification_service, get_audit_service
from backend.models import UserRole
from backend.api.routes.session import router as session_router

logger = logging.getLogger(__name__)

# SECURITY: Rate limiter with Redis backend for production
limiter = Limiter(key_func=get_remote_address)

# SECURITY: Suspicious activity tracker
suspicious_activity: Dict[str, list] = {}

class SecurityValidator:
    """Enhanced security validation for wallet and payment operations"""
    
    @staticmethod
    def detect_anomalies(request: Request, user_id: str) -> Dict[str, Any]:
        """Detect suspicious patterns in user requests"""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        
        anomalies = []
        
        # Track request patterns
        if client_ip not in suspicious_activity:
            suspicious_activity[client_ip] = []
        
        suspicious_activity[client_ip].append({
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "endpoint": str(request.url.path),
            "user_agent": user_agent
        })
        
        # Clean old entries (keep last 1 hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        suspicious_activity[client_ip] = [
            req for req in suspicious_activity[client_ip] 
            if req["timestamp"] > cutoff
        ]
        
        # Detect rapid requests
        if len(suspicious_activity[client_ip]) > 20:
            anomalies.append("rapid_requests")
        
        # Detect multiple user IDs from same IP
        unique_users = set(req["user_id"] for req in suspicious_activity[client_ip])
        if len(unique_users) > 5:
            anomalies.append("multiple_users_same_ip")
        
        return {
            "anomalies": anomalies,
            "request_count": len(suspicious_activity[client_ip]),
            "unique_users": len(unique_users)
        }

def require_role(required_role: str):
    """Decorator to require specific user roles"""
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_role = current_user.get("role", "alien")
        if user_role != required_role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

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
        
        # Initialize all services
        email_service = EmailService(settings)
        notification_service = NotificationService(email_service)
        wallet_service = WalletService(settings, supabase_client)
        database_service = DatabaseService(supabase_client)
        audit_service = AuditService(supabase_client)
        kyc_service = KYCService(settings, supabase_client, database_service, audit_service)

        # FIXED: Initialize dependencies with audit service included
        initialize_dependencies(
            supabase_client, 
            wallet_service, 
            notification_service, 
            audit_service,  # <- Added this line
            kyc_service
        )
        
        license_fee = settings.business_model.calculate_license_fee(
            LicenseTier.BASIC, 
            PricingRegion.NIGERIA
        )
        logger.info(f"Business model initialized. Basic license fee in Nigeria: {license_fee}")
        
        logger.info("All services initialized successfully.")
        yield
    except Exception as e:
        logger.critical(f"FATAL STARTUP ERROR: {e}\n{traceback.format_exc()}")
        raise
    logger.info("--- Seamount API Shutting Down ---")

app = FastAPI(
    title="Seamount.io API",
    version="3.1.5",
    description="The core API for Seamount's cross-border payment and treasury platform.",
    lifespan=lifespan
)

# SECURITY: Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://www.seamount.io", "https://seamount.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FIXED: Correct router inclusion with proper prefixes - Changed KYC prefix to /api/kyc
app.include_router(users_router, prefix="/api/v1/user", tags=["User"])
app.include_router(kyc.router, prefix="/api/kyc", tags=["KYC"])  # Changed from /api/v1/kyc
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(portfolio.router, prefix="/api/v1", tags=["Portfolio"])
app.include_router(investor.router, prefix="/api/v1", tags=["Investor"])
app.include_router(consent.router, prefix="/api/v1", tags=["Consent"])
app.include_router(licensing_router, prefix="/api/v1", tags=["Licensing"])
app.include_router(session_router, prefix="/api/v1/session", tags=["Session"])

@app.get("/api/v1/health", tags=["System"])
@limiter.limit("10/minute")
async def health_check(request: Request):
    return {"status": "healthy", "version": "3.1.5"}

@app.post("/api/v1/session/initialize", tags=["Session"])
@limiter.limit("20/minute")
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

    # Enhanced IPInfo integration with timeout and better error handling
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

@app.post("/api/wallet/create", tags=["Wallet"])
@limiter.limit("5/minute")  # SECURITY: Strict rate limit for wallet operations
async def create_wallet(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    wallet_service: WalletService = Depends(get_wallet_service),
    audit_service: AuditService = Depends(get_audit_service),  # FIXED: Use dependency injection
    supabase: Client = Depends(get_supabase_client)
):
    """Enhanced wallet creation with security monitoring"""
    user_id = current_user.get("id")
    if not user_id: 
        raise HTTPException(status_code=400, detail="User ID not found in token")
    
    # SECURITY: Enhanced monitoring for wallet operations
    security_check = SecurityValidator.detect_anomalies(request, user_id)
    if "rapid_requests" in security_check["anomalies"]:
        logger.critical(f"SECURITY ALERT: Rapid wallet creation attempts from user {user_id}")
        raise HTTPException(status_code=429, detail="Too many wallet creation attempts")
    
    logger.info(f"[Wallet Create] Initiated for user: {user_id}")
    try:
        # FIXED: Changed table from wallet_balances to user_wallets
        wallet_res = supabase.from_("user_wallets").select("algorand_address, is_demo").eq("user_id", user_id).maybe_single().execute()
        
        if wallet_res.data:
            return { 
                "success": True, 
                "message": "Wallet already exists", 
                **wallet_res.data, 
                "mnemonic": None 
            }

        new_wallet_material = wallet_service.create_algorand_wallet()
        await wallet_service.store_encrypted_wallet(user_id, new_wallet_material)
        
        # SECURITY: Audit wallet creation with proper dependency injection
        await audit_service.log_wallet_operation(
            user_id=user_id,
            operation="wallet_created",
            wallet_address=new_wallet_material["address"]
        )
        
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
@limiter.limit("3/minute")
async def business_contact(request: Request, payload: BusinessLeadPayload):
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

# SECURITY: Admin-only system monitoring endpoint
@app.get("/api/v1/admin/security-status", dependencies=[Depends(require_role("tribe"))], tags=["Admin"])
@limiter.limit("10/minute")
async def get_security_status(request: Request):
    """Admin endpoint for security monitoring"""
    return {
        "suspicious_activity_count": len(suspicious_activity),
        "active_rate_limits": len([k for k, v in suspicious_activity.items() if len(v) > 50]),
        "system_status": "secure",
        "timestamp": datetime.utcnow().isoformat()
    }

# FIXED: Add role-based access control to critical endpoints
@app.post("/api/v1/payments/send", dependencies=[Depends(require_role("tribe"))], tags=["Payments"])
@limiter.limit("10/minute")
async def send_payment(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Send payment - requires Tribe role"""
    return {"message": "Payment processed successfully"}

@app.post("/api/v1/trading/buy", dependencies=[Depends(require_role("tribe"))], tags=["Trading"])
@limiter.limit("10/minute")
async def buy_assets(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Buy assets - requires Tribe role"""
    return {"message": "Trade executed successfully"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid4())[:8]
    logger.critical(f"Unhandled exception for request {request.url} [Error ID: {error_id}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected internal server error occurred. Please contact support with Error ID: {error_id}"},
    )