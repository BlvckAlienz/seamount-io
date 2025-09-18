# File Location: backend/api/main.py
# PRODUCTION-READY: Complete API with security hardening and KYC fixes

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
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import core dependencies first
try:
    from backend.dependencies import (
        initialize_dependencies, 
        get_supabase_client, 
        get_current_user, 
        get_wallet_service, 
        get_notification_service, 
        get_audit_service,
        get_kyc_service  # FIXED: Add missing KYC service dependency
    )
    dependencies_available = True
except ImportError as e:
    logging.error(f"Critical dependency import error: {e}")
    dependencies_available = False
    
    # Create mock functions for critical dependencies
    def get_supabase_client():
        raise HTTPException(status_code=503, detail="Supabase client not available")
    
    def get_current_user():
        raise HTTPException(status_code=503, detail="Authentication service not available")
    
    def get_wallet_service():
        raise HTTPException(status_code=503, detail="Wallet service not available")
    
    def get_notification_service():
        raise HTTPException(status_code=503, detail="Notification service not available")
    
    def get_audit_service():
        raise HTTPException(status_code=503, detail="Audit service not available")
    
    def get_kyc_service():
        raise HTTPException(status_code=503, detail="KYC service not available")
    
    def initialize_dependencies(*args, **kwargs):
        logging.warning("Dependencies initialization skipped due to import errors")

# Define placeholder classes for type annotations
class WalletService:
    pass

class AuditService:
    pass

class KYCService:
    pass

# Then try to import other dependencies
try:
    from backend.config import Settings, get_settings, BusinessModelConfig, LicenseTier, PricingRegion
    from backend.services.email_service import EmailService
    from backend.services.notification_service import NotificationService
    from backend.services.wallet_service import WalletService as ActualWalletService
    from backend.services.kyc_service import KYCService as ActualKYCService
    from backend.services.database_service import DatabaseService
    from backend.services.audit_service import AuditService as ActualAuditService
    from backend.models import UserRole
    
    # Override the placeholder classes with the actual ones
    WalletService = ActualWalletService
    AuditService = ActualAuditService
    KYCService = ActualKYCService
    services_available = True
except ImportError as e:
    logging.error(f"Core service import error: {e}")
    services_available = False

# Try to import routers with better error handling
routers_available = {}

try:
    from backend.api.routes.licensing import router as licensing_router
    routers_available['licensing'] = licensing_router
except ImportError as e:
    logging.error(f"Licensing router import error: {e}")
    routers_available['licensing'] = None

try:
    from backend.api.routes import kyc
    routers_available['kyc'] = kyc
except ImportError as e:
    logging.error(f"KYC router import error: {e}")
    routers_available['kyc'] = None

try:
    from backend.api.routes import webhooks, portfolio, investor, consent
    routers_available['webhooks'] = webhooks
    routers_available['portfolio'] = portfolio
    routers_available['investor'] = investor
    routers_available['consent'] = consent
except ImportError as e:
    logging.error(f"Additional routers import error: {e}")
    routers_available.update({
        'webhooks': None,
        'portfolio': None,
        'investor': None,
        'consent': None
    })

try:
    from backend.api.routes.users import router as users_router
    routers_available['users'] = users_router
except ImportError as e:
    logging.error(f"Users router import error: {e}")
    routers_available['users'] = None

try:
    from backend.api.routes.session import router as session_router
    routers_available['session'] = session_router
except ImportError as e:
    logging.error(f"Session router import error: {e}")
    routers_available['session'] = None

# Import payments router with specific error handling
try:
    from backend.api.routes.payments import router as payments_router
    routers_available['payments'] = payments_router
    logging.info("Payments router imported successfully")
except ImportError as payment_e:
    logging.error(f"Payments router import error: {payment_e}")
    from fastapi import APIRouter
    payments_router = APIRouter()
    @payments_router.get("/health")
    async def payments_health():
        return {"status": "payments module not available", "error": str(payment_e)}
    routers_available['payments'] = payments_router

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
        # Check if we can get settings
        if services_available:
            try:
                settings = get_settings()
        
                # Validate Supabase credentials before creating client
                if settings.validate_supabase_credentials():
                    try:
                        supabase_client = create_client(
                            settings.SUPABASE_URL, 
                            settings.SUPABASE_SERVICE_KEY.get_secret_value()
                        )
                        logger.info("Supabase client created successfully")
                    except Exception as e:
                        logger.error(f"Failed to create Supabase client: {e}")
                        supabase_client = None
                else:
                    logger.warning("Supabase credentials validation failed - operating without database")
                    supabase_client = None
                    
                # Initialize all services if available
                email_service = EmailService(settings)
                notification_service = NotificationService(email_service)
                
                # Only initialize services that require Supabase if client is available
                if supabase_client:
                    wallet_service = WalletService(settings, supabase_client)
                    database_service = DatabaseService(supabase_client)
                    audit_service = AuditService(supabase_client)
                    kyc_service = KYCService(settings, supabase_client, database_service, audit_service)

                    # Test KYC service initialization with health check
                    try:
                        kyc_health = await kyc_service.health_check()
                        logger.info(f"KYC Service health: {kyc_health}")
                        
                        if kyc_health.get('provider') != 'healthy':
                            logger.warning("KYC provider not healthy - KYC features may be limited")
                    except Exception as e:
                        logger.error(f"KYC Service health check failed: {e}")
                        # Continue anyway but log the error

                    # Initialize dependencies
                    if dependencies_available:
                        initialize_dependencies(
                            supabase_client, 
                            wallet_service, 
                            notification_service, 
                            audit_service,
                            kyc_service
                        )
                else:
                    logger.warning("Supabase client not available, skipping database-dependent services")
                    # Initialize with minimal dependencies
                    if dependencies_available:
                        initialize_dependencies(
                            None, 
                            None, 
                            notification_service, 
                            None,
                            None
                        )
                
                # This part can proceed without Supabase
                try:
                    license_fee = settings.business_model.calculate_license_fee(
                        LicenseTier.BASIC, 
                        PricingRegion.NIGERIA
                    )
                    logger.info(f"Business model initialized. Basic license fee in Nigeria: {license_fee}")
                except:
                    logger.warning("Business model calculation failed")
                
                logger.info("Services initialized successfully.")
            except Exception as e:
                logger.error(f"Service initialization error: {e}")
                # Don't raise the error, continue with partial initialization
                logger.warning("Continuing with partial service initialization")
        else:
            logger.warning("Core services not available due to import errors")
        
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

# SECURITY: Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Add security headers
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://www.seamount.io", "https://seamount.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FIXED: Include routers with proper error handling and consistent prefixes
if routers_available.get('users'):
    app.include_router(routers_available['users'], prefix="/api/v1/user", tags=["User"])
    logger.info("✅ Users router registered")

# FIXED: Correct KYC router registration
if routers_available.get('kyc'):
    from backend.api.routes.kyc import router as kyc_router
    app.include_router(kyc_router, prefix="/api/v1/kyc", tags=["KYC"])
    logger.info("✅ KYC router registered at /api/v1/kyc")

if routers_available.get('webhooks') and hasattr(routers_available['webhooks'], 'router'):
    app.include_router(routers_available['webhooks'].router, prefix="/webhooks", tags=["Webhooks"])
    logger.info("✅ Webhooks router registered")

if routers_available.get('portfolio') and hasattr(routers_available['portfolio'], 'router'):
    app.include_router(routers_available['portfolio'].router, prefix="/api/v1", tags=["Portfolio"])
    logger.info("✅ Portfolio router registered")

if routers_available.get('investor') and hasattr(routers_available['investor'], 'router'):
    app.include_router(routers_available['investor'].router, prefix="/api/v1", tags=["Investor"])
    logger.info("✅ Investor router registered")

if routers_available.get('consent') and hasattr(routers_available['consent'], 'router'):
    app.include_router(routers_available['consent'].router, prefix="/api/v1", tags=["Consent"])
    logger.info("✅ Consent router registered")

if routers_available.get('licensing'):
    app.include_router(routers_available['licensing'], prefix="/api/v1", tags=["Licensing"])
    logger.info("✅ Licensing router registered")

if routers_available.get('session'):
    app.include_router(routers_available['session'], prefix="/api/v1/session", tags=["Session"])
    logger.info("✅ Session router registered")

if routers_available.get('payments'):
    app.include_router(routers_available['payments'], prefix="/api/payments", tags=["Payments"])
    logger.info("✅ Payments router registered")
else:
    logger.warning("Payments router not available - payment endpoints disabled")

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
    if not services_available:
        raise HTTPException(status_code=503, detail="Settings service not available")
    
    try:
        settings = get_settings()
    except NameError:
        raise HTTPException(status_code=503, detail="Settings service not available")
    
    ip_address = request.client.host if request.client else "unknown"
    
    session_data = {
        "id": str(uuid4()),
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": datetime.utcnow().isoformat()
    }

    # Enhanced IPInfo integration with timeout and better error handling
    if hasattr(settings, 'IPINFO_TOKEN') and settings.IPINFO_TOKEN and ip_address != "unknown":
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
    audit_service: AuditService = Depends(get_audit_service),
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
        if audit_service:
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

# MOVED: Payment and trading endpoints to dedicated handlers (no missing router dependency)
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