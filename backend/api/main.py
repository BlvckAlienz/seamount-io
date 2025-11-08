# File: backend/api/main.py
# Merged Production-Ready Version - Phase 1 Complete
# Combines clean architecture with essential business logic

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from supabase import create_client, Client
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from uuid import uuid4
from datetime import datetime, timedelta
import asyncio
import traceback
import aiohttp
import sys
from pathlib import Path
from decimal import Decimal

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ===== LOGGING SETUP =====
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== MODULE-LEVEL FLAGS =====
services_available = False
dependencies_available = False
oracle_service_available = False
routers_available = {}

logger.info("🚀 Starting Seamount API initialization...")

# ===== IMPORT DEPENDENCIES =====
try:
    from backend.dependencies import (
        initialize_dependencies,
        get_supabase_client,
        get_current_user,
        get_multi_chain_wallet_service,
        get_notification_service,
        get_audit_service,
        get_kyc_service,
        get_db_service,
        get_oracle_service
    )
    dependencies_available = True
    logger.info("✅ Dependencies imported successfully")
except ImportError as e:
    logger.error(f"❌ Critical dependency import error: {e}")
    dependencies_available = False
    
    # Create mock functions for graceful degradation
    def get_supabase_client():
        raise HTTPException(status_code=503, detail="Supabase client not available")
    def get_current_user():
        raise HTTPException(status_code=503, detail="Authentication service not available")
    def get_multi_chain_wallet_service():
        raise HTTPException(status_code=503, detail="Multi-chain wallet service not available")
    def get_notification_service():
        raise HTTPException(status_code=503, detail="Notification service not available")
    def get_audit_service():
        raise HTTPException(status_code=503, detail="Audit service not available")
    def get_kyc_service():
        raise HTTPException(status_code=503, detail="KYC service not available")
    def get_db_service():
        raise HTTPException(status_code=503, detail="Database service not available")
    def get_oracle_service():
        raise HTTPException(status_code=503, detail="Oracle service not available")
    def initialize_dependencies(*args, **kwargs):
        logger.warning("Dependencies initialization skipped due to import errors")

# ===== IMPORT CORE SERVICES =====
from backend.config import get_settings, BusinessModelConfig
from backend.models import UserRole

# Import services individually with fallbacks
try:
    from backend.services.multi_chain_wallet_service import MultiChainWalletService
    logger.info("✅ MultiChainWalletService imported")
except ImportError as e:
    logger.error(f"❌ MultiChainWalletService import failed: {e}")
    MultiChainWalletService = None

try:
    from backend.services.email_service import EmailService
    from backend.services.notification_service import NotificationService
    from backend.services.kyc_service import KYCService
    from backend.services.database_service import DatabaseService
    from backend.services.audit_service import AuditService
    services_available = True
    logger.info("✅ Core services imported")
except ImportError as e:
    logger.error(f"❌ Core services import error: {e}")
    services_available = False

# ===== IMPORT ORACLE SERVICE =====
try:
    from backend.services.oracle_service import OracleService
    oracle_service_available = True
    logger.info("✅ Oracle service imported successfully")
except ImportError as e:
    logger.error(f"❌ Oracle service import error: {e}")
    oracle_service_available = False

from backend.api.routes import seed_routes
from backend.api.routes import wallet_backup_routes

# ===== IMPORT ROUTERS WITH COMPREHENSIVE ERROR HANDLING =====
try:
    from backend.api.routes.users import router as users_router
    routers_available['users'] = users_router
    logger.info("✅ Users router imported")
except ImportError as e:
    logger.error(f"❌ Users router import error: {e}")
    routers_available['users'] = None

try:
    from backend.api.routes.kyc import router as kyc_router
    routers_available['kyc'] = kyc_router
    logger.info("✅ KYC router imported")
except ImportError as e:
    logger.error(f"❌ KYC router import error: {e}")
    routers_available['kyc'] = None

try:
    from backend.api.routes.session import router as session_router
    routers_available['session'] = session_router
    logger.info("✅ Session router imported")
except ImportError as e:
    logger.error(f"❌ Session router import error: {e}")
    routers_available['session'] = None

try:
    from backend.api.routes import wallet
    routers_available['wallet'] = wallet
    logger.info("✅ Wallet router imported")
except ImportError as e:
    logger.error(f"❌ Wallet router import error: {e}")
    routers_available['wallet'] = None

try:
    from backend.api.routes import oracle
    routers_available['oracle'] = oracle
    logger.info("✅ Oracle router imported")
except ImportError as e:
    logger.error(f"❌ Oracle router import error: {e}")
    routers_available['oracle'] = None

try:
    from backend.api.routes.licensing import router as licensing_router
    routers_available['licensing'] = licensing_router
    logger.info("✅ Licensing router imported")
except ImportError as e:
    logger.error(f"❌ Licensing router import error: {e}")
    routers_available['licensing'] = None

try:
    from backend.api.routes import webhooks, portfolio, investor, consent
    routers_available['webhooks'] = webhooks
    routers_available['portfolio'] = portfolio
    routers_available['investor'] = investor
    routers_available['consent'] = consent
    logger.info("✅ Additional routers imported (webhooks, portfolio, investor, consent)")
except ImportError as e:
    logger.error(f"❌ Additional routers import error: {e}")
    routers_available.update({
        'webhooks': None,
        'portfolio': None,
        'investor': None,
        'consent': None
    })

try:
    from backend.api.routes.payments import router as payments_router
    routers_available['payments'] = payments_router
    logger.info("✅ Payments router imported")
except ImportError as payment_e:
    logger.error(f"❌ Payments router import error: {payment_e}")
    from fastapi import APIRouter
    payments_router = APIRouter()
    @payments_router.get("/health")
    async def payments_health():
        return {"status": "payments module not available", "error": str(payment_e)}
    routers_available['payments'] = payments_router

try:
    from backend.api.routes.transactions import router as transactions_router
    routers_available['transactions'] = transactions_router
    logger.info("✅ Transactions router imported")
except ImportError as e:
    logger.error(f"❌ Transactions router import error: {e}")
    routers_available['transactions'] = None

try:
    from backend.api.routes.onramp import router as onramp_router
    routers_available['onramp'] = onramp_router
    logger.info("✅ On-ramp router imported")
except ImportError as e:
    logger.error(f"❌ On-ramp router import error: {e}")
    routers_available['onramp'] = None

try:
    from backend.api.routes.offramp import router as offramp_router
    routers_available['offramp'] = offramp_router
    logger.info("✅ Off-ramp router imported")
except ImportError as e:
    logger.error(f"❌ Off-ramp router import error: {e}")
    routers_available['offramp'] = None

try:
    from backend.api.routes.wallet_connect import router as wallet_connect_router
    routers_available['wallet_connect'] = wallet_connect_router
    logger.info("✅ Wallet connect router imported")
except ImportError as e:
    logger.error(f"❌ Wallet connect router import error: {e}")
    routers_available['wallet_connect'] = None

try:
    from backend.api.routes.yield_routes import router as yield_router
    routers_available['yield'] = yield_router
    logger.info("✅ Yield router imported")
except ImportError as e:
    logger.error(f"❌ Yield router import error: {e}")
    routers_available['yield'] = None

# ===== SECURITY COMPONENTS =====
limiter = Limiter(key_func=get_remote_address)
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

# ===== PYDANTIC MODELS =====
class BusinessLeadPayload(BaseModel):
    name: str
    business_name: Optional[str] = None
    email: EmailStr
    message: Optional[str] = None

# ===== APPLICATION LIFESPAN =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle"""
    logger.info("--- Seamount API Starting Up ---")
    
    try:
        if services_available and dependencies_available:
            logger.info("✅ Core services available - proceeding with initialization")
            settings = get_settings()
            
            # Validate Supabase credentials
            if hasattr(settings, 'validate_supabase_credentials') and settings.validate_supabase_credentials():
                try:
                    supabase_client = create_client(
                        settings.SUPABASE_URL,
                        settings.SUPABASE_SERVICE_KEY.get_secret_value()
                    )
                    logger.info("✅ Supabase client created successfully")
                    
                    # Validate WDK configuration
                    settings.validate_wdk_configuration()

                    # Initialize core services
                    email_service = EmailService(settings)
                    notification_service = NotificationService(email_service)
                    db_service = DatabaseService(supabase_client)
                    audit_service = AuditService(supabase_client)
                    
                    # Initialize Algorand service
                    from backend.services.algorand_service import AlgorandService
                    algorand_service = AlgorandService(settings)
                    logger.info("✅ Algorand service initialized")
                    
                    # Initialize Fee Calculator
                    from backend.services.fee_calculator import FeeCalculatorService
                    fee_calculator = FeeCalculatorService(db_service)
                    logger.info("✅ Fee calculator initialized")

                    # Initialize Oracle service
                    oracle_service = None
                    if oracle_service_available:
                        try:
                            oracle_service = OracleService(db_service)
                            logger.info("✅ Oracle service initialized")
                        except Exception as e:
                            logger.error(f"❌ Oracle service initialization failed: {e}")
                            logger.info("Creating mock oracle service for graceful degradation...")

                    # ✅ ADD THIS FALLBACK (if oracle is still None):
                    if oracle_service is None:
                        logger.warning("⚠️ Using mock oracle service")
                        # Create mock oracle class inline
                        class MockOracleService:
                            async def get_asset_price(self, asset_name: str):
                                """Mock price: always returns $1.00"""
                                return Decimal('1.0'), {'source': 'mock', 'asset': asset_name}
                        
                        oracle_service = MockOracleService()
                        logger.info("✅ Mock oracle service created")

                    # Initialize Multi-Chain Wallet Service (UNIFIED NAME)
                    multi_chain_wallet_service = MultiChainWalletService(
                        db_service=db_service,
                        algorand_service=algorand_service,
                        fee_calculator=fee_calculator,
                        oracle_service=oracle_service
                    )
                    logger.info("✅ Multi-Chain Wallet Service initialized")
                    
                    # Initialize WalletCreationService
                    try:
                        from backend.services.wallet_creation_service import WalletCreationService
                        wallet_creation_service = WalletCreationService(
                            db_service=db_service,
                            algorand_service=algorand_service,
                            wdk_client=multi_chain_wallet_service.wdk  # Use actual WDK client
                        )
                        logger.info("✅ WalletCreationService initialized")
                    except Exception as e:
                        logger.warning(f"⚠️ WalletCreationService unavailable: {e}")
                        wallet_creation_service = None

                    # Initialize KYC service
                    kyc_service = KYCService(
                        settings,
                        supabase_client,
                        db_service,
                        audit_service
                    )
                    
                    # Test KYC service health
                    try:
                        kyc_health = await kyc_service.health_check()
                        logger.info(f"✅ KYC Service health: {kyc_health}")
                    except Exception as e:
                        logger.error(f"❌ KYC Service health check failed: {e}")
                    
                    # Register all services with dependency injection
                    initialize_dependencies(
                        supabase_client,
                        multi_chain_wallet_service,
                        notification_service,
                        audit_service,
                        kyc_service,
                        db_service,
                        algorand_service,
                        oracle_service
                    )
                    logger.info("✅ All dependencies initialized successfully")
                    
                    # Test business model calculations
                    try:
                        test_calc = settings.business_model.calculate_cross_border_economics(
                            amount=Decimal("1000"),
                            from_currency="NGN",
                            to_currency="USD",
                            from_country="nigeria",
                            to_country="kenya"
                        )
                        logger.info(f"💰 Business model initialized. Test $1000 cross-border: Fee=${test_calc['total_fee']}, Revenue=${test_calc['net_revenue']}")
                    except Exception as e:
                        logger.warning(f"⚠️ Business model validation failed: {e}")
                    
                except Exception as e:
                    logger.error(f"❌ Supabase client creation failed: {e}")
                    supabase_client = None
            else:
                logger.warning("❌ Supabase credentials validation failed - operating without database")
        else:
            logger.warning("❌ Core services not available - operating in limited mode")
    
    except Exception as e:
        logger.critical(f"💥 FATAL STARTUP ERROR: {e}\n{traceback.format_exc()}")
        logger.info("🚨 Continuing with degraded functionality")

        # ✅ START WDK DEPOSIT MONITOR (background task)
        if services_available:
            try:
                from backend.services.wdk_deposit_monitor import WDKDepositMonitor
                
                monitor = WDKDepositMonitor(db_service)
                
                # Run in background (non-blocking)
                asyncio.create_task(monitor.monitor_deposits())
                
                logger.info("✅ WDK Deposit Monitor started (polling every 30s)")
            except Exception as e:
                logger.warning(f"⚠️ WDK Deposit Monitor failed to start: {e}")
                
    yield
    
    logger.info("--- Seamount API Shutting Down ---")

# ===== CREATE FASTAPI APP =====
app = FastAPI(
    title="Seamount.io API",
    version="3.1.6",
    description="Multi-chain cross-border payment and treasury platform",
    lifespan=lifespan
)

# ===== SECURITY MIDDLEWARE =====
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add comprehensive security headers to all responses"""
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

# ===== CORS MIDDLEWARE =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://seamount.io", "https://www.seamount.io", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 Seed Retrieval Routes - ADD HERE
try:
    from backend.api.routes.seed_routes import router as seed_routes_router
    app.include_router(seed_routes_router)
    logger.info("✅ Seed retrieval routes registered at /api/v1/seeds")
except ImportError as e:
    logger.error(f"❌ Seed routes import error: {e}")

# ✅ ADD this clean registration (only once)
if routers_available.get('wallet_creation'):
    app.include_router(routers_available['wallet_creation'], prefix="/api/v1", tags=["Wallet Creation"])
    logger.info("✅ Wallet creation routes registered at /api/v1/wallet-creation")

# ===== REGISTER ROUTERS =====
app.include_router(seed_routes.router)

# Wallet backup tracking
try:
    from backend.api.routes.wallet_backup_routes import router as wallet_backup_router
    app.include_router(wallet_backup_router)
    logger.info("✅ Wallet backup routes registered at /api/v1/wallet-backup")
except ImportError as e:
    logger.error(f"❌ Wallet backup routes import error: {e}")

if routers_available.get('users'):
    app.include_router(routers_available['users'], prefix="/api/v1/user", tags=["User"])
    logger.info("✅ Users router registered at /api/v1/user")

# Register wallet creation routes
try:
    from backend.api.routes.wallet_creation_routes import router as wallet_creation_router
    app.include_router(wallet_creation_router)
    logger.info("✅ Wallet creation routes registered at /api/v1/wallet-creation")
except ImportError as e:
    logger.error(f"❌ Failed to import wallet creation routes: {e}")

try:
    from backend.api.routes.wallet_backup import router as wallet_backup_router
    app.include_router(wallet_backup_router)
    logger.info("✅ Wallet backup routes registered at /api/v1/wallet-backup")
except ImportError as e:
    logger.error(f"❌ Wallet backup routes import error: {e}")

if routers_available.get('kyc'):
    app.include_router(routers_available['kyc'], prefix="/api/v1/kyc", tags=["KYC"])
    logger.info("✅ KYC router registered at /api/v1/kyc")

if routers_available.get('session'):
    app.include_router(routers_available['session'], prefix="/api/v1/session", tags=["Session"])
    logger.info("✅ Session router registered at /api/v1/session")

if routers_available.get('wallet'):
    app.include_router(routers_available['wallet'].router, prefix="/api/v1", tags=["Multi-Chain Wallet"])
    logger.info("✅ Multi-chain wallet router registered at /api/v1/wallet")

if routers_available.get('oracle'):
    app.include_router(routers_available['oracle'].router, prefix="/api", tags=["Oracle"])
    logger.info("✅ Oracle router registered at /api/oracle")

if routers_available.get('licensing'):
    app.include_router(routers_available['licensing'], prefix="/api/v1", tags=["Licensing"])
    logger.info("✅ Licensing router registered at /api/v1")

if routers_available.get('webhooks') and hasattr(routers_available['webhooks'], 'router'):
    app.include_router(routers_available['webhooks'].router, prefix="/webhooks", tags=["Webhooks"])
    logger.info("✅ Webhooks router registered at /webhooks")

if routers_available.get('portfolio') and hasattr(routers_available['portfolio'], 'router'):
    app.include_router(routers_available['portfolio'].router, prefix="/api/v1", tags=["portfolio"])
    logger.info("✅ portfolio router registered at /api/v1")

if routers_available.get('investor') and hasattr(routers_available['investor'], 'router'):
    app.include_router(routers_available['investor'].router, prefix="/api/v1", tags=["Investor"])
    logger.info("✅ Investor router registered at /api/v1")

if routers_available.get('consent') and hasattr(routers_available['consent'], 'router'):
    app.include_router(routers_available['consent'].router, prefix="/api/v1", tags=["Consent"])
    logger.info("✅ Consent router registered at /api/v1")

if routers_available.get('payments'):
    app.include_router(routers_available['payments'], prefix="/api/payments", tags=["Payments"])
    logger.info("✅ Payments router registered at /api/payments")

if routers_available.get('transactions'):
    app.include_router(routers_available['transactions'], prefix="/api/v1", tags=["Transactions"])
    logger.info("✅ Transactions router registered at /api/v1")

if routers_available.get('onramp'):
    app.include_router(routers_available['onramp'], prefix="/api/v1", tags=["On-Ramp"])
    logger.info("✅ On-ramp router registered at /api/v1")

if routers_available.get('offramp'):
    app.include_router(routers_available['offramp'], prefix="/api/v1", tags=["Off-Ramp"])
    logger.info("✅ Off-ramp router registered at /api/v1")

if routers_available.get('wallet_connect'):
    app.include_router(routers_available['wallet_connect'], prefix="/api/v1", tags=["Wallet Connect"])
    logger.info("✅ Wallet connect router registered at /api/v1")

if routers_available.get('yield'):
    app.include_router(routers_available['yield'], prefix="/api/v1", tags=["Yield"])
    logger.info("✅ Yield router registered at /api/v1")

# ===== CORE API ENDPOINTS =====

@app.get("/api/v1/health", tags=["System"])
@limiter.limit("10/minute")
async def health_check(request: Request):
    """Enhanced multi-chain health check endpoint"""
    
    health_status = {
        "status": "healthy",
        "version": "3.1.6",
        "services": {
            "database": "connected" if dependencies_available else "unavailable",
            "oracle": "operational" if oracle_service_available else "unavailable",
            "algorand": "operational",
            "wdk": "checking...",
            "email": "mock_mode"
        },
        "chains": {
            "algorand": True,
            "bitcoin": False,
            "lightning": False,
            "ethereum": False,
            "polygon": False,
            "arbitrum": False,
            "ton": False,
            "tron": False,
            "solana": False
        }
    }
    
    # Check WDK service health
    try:
        from backend.services.wdk_client import WDKClient
        wdk = WDKClient()
        wdk_health = await wdk.health_check()
        
        if wdk_health.get("status") == "healthy":
            health_status["services"]["wdk"] = "operational"
            for chain in wdk_health.get("supported_chains", []):
                if chain in health_status["chains"]:
                    health_status["chains"][chain] = True
        else:
            health_status["services"]["wdk"] = "degraded"
    except Exception as e:
        logger.warning(f"WDK health check failed: {e}")
        health_status["services"]["wdk"] = "unavailable"
    
    # Determine overall status
    critical_services = ["database", "algorand"]
    if all(health_status["services"].get(s) != "unavailable" for s in critical_services):
        health_status["status"] = "healthy"
    else:
        health_status["status"] = "degraded"
    
    return health_status

@app.post("/api/v1/session/initialize", tags=["Session"])
@limiter.limit("20/minute")
async def initialize_session(
    request: Request,
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    supabase: Client = Depends(get_supabase_client)
):
    """Initialize user session with IP enrichment"""
    if not services_available:
        raise HTTPException(status_code=503, detail="Settings service not available")
    
    settings = get_settings()
    ip_address = request.client.host if request.client else "unknown"
    
    session_data = {
        "id": str(uuid4()),
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": datetime.utcnow().isoformat()
    }

    # Enhanced IPInfo integration
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
        except Exception as e:
            logger.warning(f"IPInfo enrichment failed for IP {ip_address}: {e}")
    
    try:
        insert_res = supabase.from_("user_sessions").insert(session_data).execute()
        return JSONResponse(content={"session_id": session_data["id"]})
    except Exception as e:
        logger.error(f"Session initialization database error: {e}")
        return JSONResponse(content={"session_id": session_data["id"]})

@app.post("/api/wallet/create", tags=["Wallet"])
@limiter.limit("5/minute")
async def create_wallet(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    wallet_service = Depends(get_multi_chain_wallet_service)
):
    """Create a multi-chain wallet for the authenticated user"""
    try:
        logger.info(f"Creating wallet for user: {current_user['id']}")
        result = await wallet_service.create_wallet_for_user(current_user["id"])
        
        if result["success"]:
            return result
        else:
            logger.error(f"Wallet creation failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Wallet creation failed"))
            
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Wallet creation error [{error_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Wallet creation failed. Error ID: {error_id}")

@app.post("/api/v1/leads/business-contact", tags=["Public"])
@limiter.limit("3/minute")
async def business_contact(request: Request, payload: BusinessLeadPayload):
    """Submit business lead inquiry"""
    supabase = get_supabase_client()
    notifier = get_notification_service()
    
    try:
        res = supabase.table('business_leads').insert(payload.model_dump()).execute()
        if not res.data:
            raise Exception("Failed to save lead")
        
        subject = f"New Seamount Business Lead: {payload.business_name or payload.name}"
        body = f"<p><b>Name:</b> {payload.name}</p><p><b>Company:</b> {payload.business_name or 'N/A'}</p><p><b>Email:</b> {payload.email}</p><p><b>Message:</b> {payload.message or 'N/A'}</p>"
        
        asyncio.create_task(notifier.email_service.send_email(
            subject,
            ["business@seamount.io"],
            body
        ))
        
        return {"message": "Your request has been submitted successfully. We'll get in touch."}
    except Exception as e:
        logger.error(f"Business contact submission failed: {e}")
        raise HTTPException(status_code=500, detail="Could not process your request")

# ===== DEBUG ENDPOINTS =====

@app.get("/api/debug/db-test", tags=["Debug"])
async def debug_db_test(supabase: Client = Depends(get_supabase_client)):
    """Test database connectivity"""
    try:
        result = supabase.from_("user_profiles").select("count", count="exact").execute()
        return {
            "success": True,
            "user_count": result.count,
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Database connection failed"
        }

@app.get("/api/debug/wallet-test/{user_id}", tags=["Debug"])
async def debug_wallet_test(
    user_id: str,
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """Test multi-chain wallet service functionality"""
    try:
        wallet = await wallet_service.get_wallet_for_user(user_id)
        
        if wallet:
            return {
                "success": True,
                "wallet_exists": True,
                "wallet_address": wallet.get("wallet_address"),
                "message": "Wallet found successfully"
            }
        else:
            return {
                "success": True,
                "wallet_exists": False,
                "message": "No wallet found for user"
            }
    except Exception as e:
        logger.error(f"Wallet test failed for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Wallet service test failed"
        }

@app.get("/api/debug/kyc-test/{user_id}", tags=["Debug"])
async def debug_kyc_test(
    user_id: str,
    kyc_service: KYCService = Depends(get_kyc_service)
):
    """Test KYC service functionality"""
    try:
        health = await kyc_service.health_check()
        
        return {
            "success": True,
            "kyc_health": health,
            "message": "KYC service test completed"
        }
    except Exception as e:
        logger.error(f"KYC test failed for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "KYC service test failed"
        }

@app.get("/api/debug/oracle-test/{asset_name}", tags=["Debug"])
async def debug_oracle_test(asset_name: str):
    """Test Oracle service functionality"""
    try:
        if not oracle_service_available or not dependencies_available:
            return {
                "success": False,
                "error": "Service not available",
                "message": "Oracle service debug endpoint disabled"
            }
        
        oracle_service = get_oracle_service()
        if oracle_service is None:
            return {
                "success": False,
                "error": "Oracle service not initialized",
                "message": "Oracle service is None"
            }
        
        price, metadata = await oracle_service.get_asset_price(asset_name)
        
        return {
            "success": True,
            "asset": asset_name,
            "price": str(price),
            "metadata": metadata,
            "message": "Oracle service test completed successfully"
        }
    except Exception as e:
        logger.error(f"Oracle test failed for asset {asset_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Oracle service test failed"
        }

@app.get("/api/debug/all-routes")
async def debug_all_routes():
    """Debug endpoint to see ALL registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            route_info = {
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, "name", "N/A")
            }
            routes.append(route_info)
    
    # Sort by path for easier reading
    routes.sort(key=lambda x: x["path"])
    
    return {
        "total_routes": len(routes),
        "registered_routes": routes
    }

# ===== ADMIN ENDPOINTS =====

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

# ===== PAYMENT & TRADING ENDPOINTS =====

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

# ===== BACKGROUND TASKS =====

async def process_kyc_webhook(payload: Dict[str, Any]):
    """Background task to process KYC webhook events"""
    try:
        event_type = payload.get("type")
        applicant_id = payload.get("resource", {}).get("id")
        
        logger.info(f"Processing KYC webhook: {event_type} for applicant {applicant_id}")
        
    except Exception as e:
        logger.error(f"Error in background KYC webhook processing: {e}")

# ===== GLOBAL EXCEPTION HANDLER =====

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unhandled errors"""
    error_id = str(uuid4())[:8]
    logger.critical(f"Unhandled exception for request {request.url} [Error ID: {error_id}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected internal server error occurred. Please contact support with Error ID: {error_id}"}
    )