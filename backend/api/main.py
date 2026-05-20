# File: backend/api/main.py
# Self-Healing Import Path (Edge Computing Pattern)

import sys
import os
from pathlib import Path

# Get absolute paths
CURRENT_FILE = Path(__file__).resolve()
API_DIR = CURRENT_FILE.parent  # backend/api/
BACKEND_DIR = API_DIR.parent   # backend/
PROJECT_ROOT = BACKEND_DIR.parent  # seamount-io/

# Add to sys.path (multiple strategies for reliability)
paths_to_add = [
    str(PROJECT_ROOT),
    str(BACKEND_DIR),
    str(API_DIR),
]

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

# Verify paths
print("=" * 70)
print("🔵 PYTHON PATH SELF-HEALING")
print("=" * 70)
print(f"📍 CURRENT_FILE: {CURRENT_FILE}")
print(f"📍 API_DIR: {API_DIR}")
print(f"📍 BACKEND_DIR: {BACKEND_DIR}")
print(f"📍 PROJECT_ROOT: {PROJECT_ROOT}")
print(f"📍 sys.path[0:3]: {sys.path[0:3]}")
print("=" * 70)

# Now we can import normally
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
from decimal import Decimal

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

# ===== IMPORT XRP SERVICES =====
try:
    from backend.services.xrp_service import XRPService
    from backend.services.xrp_monitor_service import XRPMonitorService
    from backend.services.xrp_credential_service import XRPCredentialService
    xrp_services_available = True
    logger.info("✅ XRP services imported successfully")
except ImportError as e:
    logger.error(f"❌ XRP services import error: {e}")
    xrp_services_available = False

from backend.api.routes import seed_routes
from backend.api.routes import wallet_backup_routes
from backend.api.routes import onramp, offramp, bank_verification

# ===== IMPORT ROUTERS WITH COMPREHENSIVE ERROR HANDLING =====
try:
    from backend.api.routes import quidax
    routers_available['quidax'] = quidax
    logger.info("✅ Quidax router imported")
except ImportError as e:
    logger.error(f"❌ Quidax router import error: {e}")
    routers_available['quidax'] = None

try:
    from backend.api.routes import bank_verification
    routers_available['bank_verification'] = bank_verification
    logger.info("✅ Bank verification router imported")
except ImportError as e:
    logger.error(f"❌ Bank verification router import error: {e}")
    routers_available['bank_verification'] = None

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
    logger.info("Additional routers imported (webhooks, portfolio, investor, consent)")
except ImportError as e:
    logger.error(f"Additional routers import error: {e}")
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
    from backend.api.routes.meter_xpress import router as meter_xpress_router
    routers_available['meter_xpress'] = meter_xpress_router
    logger.info("✅ Meter Xpress router imported")
except ImportError as e:
    logger.error(f"❌ Meter Xpress router import error: {e}")
    routers_available['meter_xpress'] = None

try:
    from backend.api.routes.swap_routes import router as swap_router
    routers_available['swap'] = swap_router
    logger.info("✅ Swap router imported")
except ImportError as e:
    logger.error(f"❌ Swap router import error: {e}")
    routers_available['swap'] = None

try:
    from backend.api.routes.p2p import router as p2p_router
    routers_available['p2p'] = p2p_router
    logger.info("✅ P2P router imported")
except ImportError as e:
    logger.error(f"❌ P2P router import error: {e}")
    routers_available['p2p'] = None

try:
    from backend.workers.p2p_worker import P2PWorker
    logger.info("✅ P2P worker imported")
except ImportError as e:
    logger.error(f"❌ P2P worker import error: {e}")
    P2PWorker = None

try:
    from backend.api.routes.yield_routes import router as yield_router
    routers_available['yield'] = yield_router
    logger.info("✅ Yield router imported")
except ImportError as e:
    logger.error(f"❌ Yield router import error: {e}")
    routers_available['yield'] = None

try:
    from backend.api.routes import market
    routers_available['market'] = market
    logger.info("✅ Market terminal router imported")
except ImportError as e:
    logger.error(f"❌ Market terminal router import error: {e}")
    routers_available['market'] = None

try:
    from backend.api.routes.xrp_routes import router as xrp_router
    routers_available['xrp'] = xrp_router
    logger.info("✅ XRP payments router imported")
except ImportError as e:
    logger.error(f"❌ XRP payments router import error: {e}")
    routers_available['xrp'] = None

try:
    from backend.api.routes.xrp_yield_routes import router as xrp_yield_router
    routers_available['xrp_yield'] = xrp_yield_router
    logger.info("✅ XRP yield router imported")
except ImportError as e:
    logger.error(f"❌ XRP yield router import error: {e}")
    routers_available['xrp_yield'] = None

try:
    from backend.api.routes.wdk_protocols_routes import router as wdk_protocols_router
    routers_available['wdk_protocols'] = wdk_protocols_router
    logger.info("✅ WDK Protocols router imported (swap, lend, fiat, prices)")
except ImportError as e:
    logger.error(f"❌ WDK Protocols router import error: {e}")
    routers_available['wdk_protocols'] = None

try:
    from backend.api.routes.circle_bridge_routes import router as circle_bridge_router
    from backend.api.routes.circle_swap_routes   import router as circle_swap_router
    routers_available['circle_bridge'] = circle_bridge_router
    routers_available['circle_swap']   = circle_swap_router
    logger.info("✅ Circle App Kit routers imported")
except ImportError as e:
    logger.error(f"❌ Circle App Kit routes import error: {e}")
    routers_available['circle_bridge'] = None
    routers_available['circle_swap']   = None

try:
    from backend.api.routes.moonpay import router as moonpay_router
    routers_available['moonpay'] = moonpay_router
    logger.info("✅ MoonPay router imported")
except ImportError as e:
    logger.error(f"❌ MoonPay router import error: {e}")
    routers_available['moonpay'] = None

try:
    from backend.api.routes.learn import router as learn_router
    routers_available['learn'] = learn_router
    logger.info("✅ Financial Literacy router imported (quests, wellbeing, guild)")
except ImportError as e:
    logger.error(f"❌ Financial Literacy router import error: {e}")
    routers_available['learn'] = None

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

                    # âœ… REPLACE OLD BACKGROUND TASK WITH SMART PRICE LOGGER
                    if oracle_service:
                        try:
                            from backend.services.price_logger_service import PriceLoggerService
                            from backend.services.quota_service import QuotaService
                            
                            # Initialize quota service
                            quota_service = QuotaService(db_service)
                            
                            # Initialize intelligent price logger
                            price_logger = PriceLoggerService(oracle_service, quota_service)
                            
                            # Start logging
                            await price_logger.start()
                            
                            # Store reference for cleanup
                            app.state.price_logger = price_logger
                            
                            logger.info("✅ Intelligent price logger started with tiered refresh rates:")
                            logger.info("📊 Crypto: 30s | Precious: 5min | Industrial: 15min | Critical: 1hr | Forex: 10min")
                            
                        except Exception as e:
                            logger.error(f"❌ Price logger failed to start: {e}")

                    # Initialize Multi-Chain Wallet Service (UNIFIED NAME)
                    multi_chain_wallet_service = MultiChainWalletService(
                        db_service=db_service,
                        algorand_service=algorand_service,
                        fee_calculator=fee_calculator,
                        oracle_service=oracle_service
                    )
                    logger.info("✅ Multi-Chain Wallet Service initialized")
                    
                    # Initialize XRP Service
                    xrp_service = None
                    if xrp_services_available:
                        try:
                            xrp_service = XRPService(settings=settings)
                            logger.info("✅ XRP service initialized")

                            # Run trust line setup check (safe to call repeatedly — idempotent)
                            # Only needs to run once ever, but won't break if called again
                            asyncio.create_task(xrp_service.setup_hot_wallet_trust_lines())

                        except Exception as e:
                            logger.error(f"❌ XRP service initialization failed: {e}")
                            xrp_service = None

                    # Initialize WalletCreationService (now with XRP)
                    try:
                        from backend.services.wallet_creation_service import WalletCreationService
                        wallet_creation_service = WalletCreationService(
                            db_service=db_service,
                            algorand_service=algorand_service,
                            wdk_client=multi_chain_wallet_service.wdk,
                            xrp_service=xrp_service,   # ✅ NEW
                        )
                        logger.info("✅ WalletCreationService initialized (7 chains)")
                    except Exception as e:
                        logger.warning(f"⚠️ WalletCreationService unavailable: {e}")
                        wallet_creation_service = None

                    # ── Start P2P Worker ──────────────────────────────────
                    if P2PWorker:
                        try:
                            p2p_worker = P2PWorker(
                                supabase=supabase_client,
                                multi_chain_wallet_service=multi_chain_wallet_service
                            )
                            await p2p_worker.start()
                            app.state.p2p_worker = p2p_worker
                            logger.info("✅ P2P worker started")
                        except Exception as e:
                            logger.error(f"❌ P2P worker failed to start: {e}")

                    # Start XRP Deposit Monitor (WebSocket — background task)
                    if xrp_service and xrp_services_available:
                        try:
                            async def on_xrp_deposit(event: dict):
                                """Route incoming deposits to correct user via destination tag."""
                                tag = event.get('destination_tag')
                                symbol = event.get('symbol')
                                amount = event.get('amount')
                                tx_hash = event.get('tx_hash')

                                if not tag:
                                    logger.warning(f"⚠️ XRP deposit with no destination tag: {tx_hash}")
                                    return

                                try:
                                    # Look up user by destination tag
                                    result = supabase_client.table("xrp_destination_tags") \
                                        .select("user_id") \
                                        .eq("destination_tag", tag) \
                                        .execute()

                                    if not result.data:
                                        logger.warning(f"⚠️ Unknown destination tag {tag} | tx: {tx_hash}")
                                        return

                                    user_id = result.data[0]['user_id']

                                    # Credit user balance (atomic DB function)
                                    supabase_client.rpc("update_xrp_balance", {
                                        "p_user_id": user_id,
                                        "p_symbol": symbol,
                                        "p_delta": float(amount),
                                    }).execute()

                                    # Log transaction
                                    supabase_client.table("xrp_transactions").insert({
                                        "user_id": user_id,
                                        "tx_hash": tx_hash,
                                        "tx_type": "deposit",
                                        "symbol": symbol,
                                        "amount": float(amount),
                                        "destination_tag": tag,
                                        "from_address": event.get('from_address'),
                                        "ledger_index": event.get('ledger_index'),
                                        "status": "confirmed",
                                        "created_at": datetime.utcnow().isoformat(),
                                    }).execute()

                                    logger.info(f"✅ Deposit credited: {amount} {symbol} → user {user_id[:8]}... | tx: {tx_hash}")

                                except Exception as credit_err:
                                    logger.error(f"❌ Failed to credit deposit tag={tag} tx={tx_hash}: {credit_err}")

                            xrp_monitor = XRPMonitorService(
                                hot_wallet_address=settings.XRP_HOT_WALLET_ADDRESS,
                                settings=settings,
                                on_deposit=on_xrp_deposit,
                            )
                            asyncio.create_task(xrp_monitor.start())
                            app.state.xrp_monitor = xrp_monitor
                            logger.info("✅ XRP deposit monitor started (WebSocket)")

                        except Exception as e:
                            logger.error(f"❌ XRP monitor failed to start: {e}")

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
                    
                    # ============================================================================
                    # START FEE COLLECTION SCHEDULER (Background Task)
                    # ============================================================================
                    try:
                        from backend.services.fee_collection_scheduler import FeeCollectionScheduler
                        
                        scheduler = FeeCollectionScheduler(interval_minutes=15)   # instead of target_hour/target_minute
                        await scheduler.start()
                        app.state.fee_scheduler = scheduler

                        # Schedule daily yield distribution at 3:30 AM UTC
                        async def run_daily_yield():
                            while True:
                                try:
                                    await asyncio.sleep(24 * 3600)  # 24h
                                    from backend.services.xrp_yield_service import XRPYieldService
                                    from backend.services.xrp_service import XRPService
                                    from backend.services.xrp_defi_service import XRPDeFiService
                                    from backend.services.xrp_payment_service import XRPPaymentService
                                    _xrp = XRPService(settings=settings)
                                    _defi = XRPDeFiService(xrp_service=_xrp, settings=settings)
                                    _pay = XRPPaymentService(supabase_client=supabase_client, xrp_service=_xrp, settings=settings)
                                    _yield = XRPYieldService(supabase_client=supabase_client, xrp_defi_service=_defi, xrp_payment_service=_pay, settings=settings)
                                    for pool in ["RLUSD/XRP", "USDC/XRP"]:
                                        await _yield.distribute_yield(pool=pool)
                                except Exception as ye:
                                    logger.error(f"❌ Daily yield distribution failed: {ye}")

                        asyncio.create_task(run_daily_yield())
                        logger.info("✅ Daily yield distribution task scheduled (24h interval)")


                        logger.info("✅ Fee collection scheduler started (runs daily at 3:00 AM)")
                        
                    except Exception as sched_err:
                        logger.error(f"❌ Fee collection scheduler failed to start: {sched_err}")

                    # Test business model calculations
                    try:
                        test_calc = settings.business_model.calculate_cross_border_economics(
                            amount=Decimal("1000"),
                            from_currency="NGN",
                            to_currency="USD",
                            from_country="nigeria",
                            to_country="kenya"
                        )
                        logger.info(f"✅ Business model initialized. Test $1000 cross-border: Fee=${test_calc['total_fee']}, Revenue=${test_calc['net_revenue']}")
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
        # START WDK DEPOSIT MONITOR (background task)
        if services_available:
            try:
                from backend.services.wdk_deposit_monitor import WDKDepositMonitor
                
                monitor = WDKDepositMonitor(db_service)
                
                # Run in background (non-blocking)
                asyncio.create_task(monitor.monitor_deposits())
                
                logger.info("âœ… WDK Deposit Monitor started (polling every 30s)")
            except Exception as e:
                logger.warning(f"âš ï¸ WDK Deposit Monitor failed to start: {e}")
                
        
    # Store services for cleanup
    app.state.quota_service = quota_service if 'quota_service' in locals() else None

    # ── Self-keepalive: prevents Render from suspending after 90 days ──
    async def self_keepalive():
        """Pings own /ping endpoint every 13 minutes as last-resort warmup."""
        _settings = get_settings()
        _base = _settings.API_BASE_URL.rstrip('/')
        await asyncio.sleep(60)  # Wait 60s for server to fully start first
        while True:
            try:
                async with aiohttp.ClientSession() as _session:
                    async with _session.get(
                        f"{_base}/ping",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        logger.debug(f"✅ Self-keepalive: {resp.status}")
            except Exception as _e:
                logger.warning(f"⚠️ Self-keepalive failed (non-fatal): {_e}")
            await asyncio.sleep(13 * 60)  # 13 minutes

    asyncio.create_task(self_keepalive())
    logger.info("✅ Self-keepalive task started (13min interval)")

    yield

    # ============================================================================
    # SHUTDOWN
    # ============================================================================

    # Stop price logger
    if hasattr(app.state, 'price_logger'):
        try:
            await app.state.price_logger.stop()
            logger.info("✅ Price logger stopped")
        except Exception as e:
            logger.error(f"❌ Failed to stop price logger: {e}")

    # Stop P2P worker
    if hasattr(app.state, 'p2p_worker'):
        try:
            await app.state.p2p_worker.stop()
            logger.info("✅ P2P worker stopped")
        except Exception as e:
            logger.error(f"❌ Failed to stop P2P worker: {e}")

    # Stop XRP monitor
    if hasattr(app.state, 'xrp_monitor'):
        try:
            await app.state.xrp_monitor.stop()
            logger.info("✅ XRP deposit monitor stopped")
        except Exception as e:
            logger.error(f"❌ Failed to stop XRP monitor: {e}")

    # Stop fee collection scheduler
    if hasattr(app.state, 'fee_scheduler'):
        try:
            await app.state.fee_scheduler.stop()
            logger.info("✅ Fee collection scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Failed to stop scheduler: {e}")

    logger.info("--- Seamount API Shutting Down ---")

# ===== CREATE FASTAPI APP =====
app = FastAPI(
    title="Seamount.io API",
    version="3.1.6",
    description="Multi-chain cross-border payment and treasury platform",
    lifespan=lifespan
)

# ===== LIGHTWEIGHT KEEPALIVE ENDPOINT =====
# 📍 No rate limit, no auth, no service deps — pure process-alive check
# Used by cron-job.org every 14 minutes to prevent Render cold starts
@app.api_route("/ping", methods=["GET", "HEAD"], tags=["System"])
async def ping():
    return {"ok": True}

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
    allow_origins=["https://seamount.io", "https://www.seamount.io", "http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Circle App Kit routers ──
if routers_available.get('circle_bridge'):
    app.include_router(routers_available['circle_bridge'], prefix="/api/v1", tags=["Circle Bridge"])
    logger.info("✅ Circle bridge router registered")
if routers_available.get('circle_swap'):
    app.include_router(routers_available['circle_swap'], prefix="/api/v1", tags=["Circle Swap"])
    logger.info("✅ Circle swap router registered")
    
# Seed Retrieval Routes - ADD HERE
try:
    from backend.api.routes.seed_routes import router as seed_routes_router
    app.include_router(seed_routes_router)
    logger.info("Seed retrieval routes registered at /api/v1/seeds")
except ImportError as e:
    logger.error(f"Seed routes import error: {e}")

# ADD this clean registration (only once)
if routers_available.get('wallet_creation'):
    app.include_router(routers_available['wallet_creation'], prefix="/api/v1", tags=["Wallet Creation"])
    logger.info("Wallet creation routes registered at /api/v1/wallet-creation")

# ===== REGISTER ROUTERS =====
app.include_router(seed_routes.router)

# ðŸ“ Prediction Markets Routes
try:
    from backend.api.routes.predictions import router as predictions_router
    app.include_router(predictions_router, prefix="/api/v1", tags=["Prediction Markets"])
    logger.info("Prediction Markets router registered at /api/v1/predictions")
except ImportError as e:
    logger.error(f"Prediction Markets router import error: {e}")

# Wallet backup tracking
try:
    from backend.api.routes.wallet_backup_routes import router as wallet_backup_router
    
    # Add prefix here (router file has NO prefix)
    app.include_router(
        wallet_backup_router, 
        prefix="/api/v1/wallet-backup",
        tags=["wallet-backup"]
    )
    
    logger.info("Wallet backup routes registered at /api/v1/wallet-backup")
    
    # Log registered endpoints
    for route in wallet_backup_router.routes:
        full_path = f"/api/v1/wallet-backup{route.path}"
        logger.info(f"   â†’ {route.methods} {full_path}")
except ImportError as e:
    logger.error(f"Wallet backup routes import error: {e}")

if routers_available.get('users'):
    app.include_router(routers_available['users'], prefix="/api/v1/user", tags=["User"])
    logger.info("Users router registered at /api/v1/user")

# Register wallet creation routes
try:
    from backend.api.routes.wallet_creation_routes import router as wallet_creation_router
    app.include_router(wallet_creation_router)
    logger.info("Wallet creation routes registered at /api/v1/wallet-creation")
except ImportError as e:
    logger.error(f"Failed to import wallet creation routes: {e}")

if routers_available.get('kyc'):
    app.include_router(routers_available['kyc'], prefix="/api/v1/kyc", tags=["KYC"])
    logger.info("KYC router registered at /api/v1/kyc")

if routers_available.get('session'):
    app.include_router(routers_available['session'], prefix="/api/v1/session", tags=["Session"])
    logger.info("Session router registered at /api/v1/session")

if routers_available.get('wallet'):
    app.include_router(routers_available['wallet'].router, prefix="/api/v1", tags=["Multi-Chain Wallet"])
    logger.info("Multi-chain wallet router registered at /api/v1/wallet")

if routers_available.get('oracle'):
    app.include_router(routers_available['oracle'].router, prefix="/api", tags=["Oracle"])
    logger.info("Oracle router registered at /api/oracle")

if routers_available.get('licensing'):
    app.include_router(routers_available['licensing'], prefix="/api/v1", tags=["Licensing"])
    logger.info("Licensing router registered at /api/v1")

if routers_available.get('webhooks') and hasattr(routers_available['webhooks'], 'router'):
    app.include_router(routers_available['webhooks'].router, prefix="/api/v1/webhooks", tags=["Webhooks"])  # ✅ FIXED
    logger.info("Webhooks router registered at /api/v1/webhooks")  # ✅ FIXED

if routers_available.get('portfolio') and hasattr(routers_available['portfolio'], 'router'):
    app.include_router(routers_available['portfolio'].router, prefix="/api/v1", tags=["portfolio"])
    logger.info("portfolio router registered at /api/v1")

if routers_available.get('investor') and hasattr(routers_available['investor'], 'router'):
    app.include_router(routers_available['investor'].router, prefix="/api/v1", tags=["Investor"])
    logger.info("Investor router registered at /api/v1")

if routers_available.get('consent') and hasattr(routers_available['consent'], 'router'):
    app.include_router(routers_available['consent'].router, prefix="/api/v1", tags=["Consent"])
    logger.info("Consent router registered at /api/v1")

if routers_available.get('payments'):
    app.include_router(routers_available['payments'], prefix="/api/payments", tags=["Payments"])
    logger.info("Payments router registered at /api/payments")

if routers_available.get('transactions'):
    app.include_router(routers_available['transactions'], prefix="/api/v1", tags=["Transactions"])
    logger.info("Transactions router registered at /api/v1")

if routers_available.get('onramp'):
    app.include_router(routers_available['onramp'], prefix="/api/v1", tags=["On-Ramp"])
    logger.info("On-ramp router registered at /api/v1")

if routers_available.get('offramp'):
    app.include_router(routers_available['offramp'], prefix="/api/v1", tags=["Off-Ramp"])
    logger.info("Off-ramp router registered at /api/v1")

if routers_available.get('meter_xpress'):
    app.include_router(routers_available['meter_xpress'], prefix="/api/v1", tags=["Meter Xpress"])
    logger.info("✅ Meter Xpress router registered at /api/v1/meter-xpress")

if routers_available.get('quidax'):
    app.include_router(routers_available['quidax'].router, prefix="/api/v1", tags=["Quidax"])                                            
    logger.info("Quidax router registered at /api/v1/quidax")

if routers_available.get('bank_verification'):
    app.include_router(routers_available['bank_verification'].router, prefix="/api/v1", tags=["Bank Verification"])
    logger.info("Bank verification router registered at /api/v1/bank")

if routers_available.get('swap'):
    app.include_router(routers_available['swap'], prefix="/api/v1", tags=["Swap"])
    logger.info("Swap router registered at /api/v1/swap")

if routers_available.get('p2p'):
    app.include_router(routers_available['p2p'])
    logger.info("✅ P2P router registered at /api/p2p")

if routers_available.get('yield'):
    app.include_router(routers_available['yield'], prefix="/api/v1", tags=["Yield"])
    logger.info("Yield router registered at /api/v1")

if routers_available.get('market'):
    # Register main market router (/api/v1/market/...)
    app.include_router(routers_available['market'].router, prefix="/api/v1")
    logger.info("Market terminal router registered at /api/v1/market")

if routers_available.get('xrp'):
    app.include_router(routers_available['xrp'])
    logger.info("✅ XRP payments router registered at /api/v1/xrp")

if routers_available.get('xrp_yield'):
    app.include_router(routers_available['xrp_yield'])
    logger.info("✅ XRP yield router registered at /api/v1/xrp/yield")

if routers_available.get('wdk_protocols'):
    app.include_router(routers_available['wdk_protocols'], prefix="/api/v1", tags=["WDK Protocols"])
    logger.info("✅ WDK Protocols router registered at /api/v1/wdk")

if routers_available.get('moonpay'):
    app.include_router(routers_available['moonpay'], prefix="/api/v1", tags=["MoonPay"])
    logger.info("✅ MoonPay router registered at /api/v1/moonpay")
        
    # Register quota router (/api/v1/quota/...)
    if hasattr(routers_available['market'], 'quota_router'):
        app.include_router(routers_available['market'].quota_router, prefix="/api/v1")
        logger.info("Quota health router registered at /api/v1/quota")

# 🏦 Tokenization Routes (Seamount Protocol)
try:
    from backend.api.routes.tokenization import router as tokenization_router
    app.include_router(tokenization_router, tags=["Tokenization"])
    logger.info("✅ Tokenization router registered at /api/v1/tokenization")
except ImportError as e:
    logger.error(f"❌ Tokenization router import error: {e}")
    routers_available['tokenization'] = None

# 🔐 Collateral Routes (Seamount Protocol)
try:
    from backend.api.routes.collateral import router as collateral_router
    app.include_router(collateral_router, tags=["Collateral"])
    logger.info("✅ Collateral router registered at /api/v1/collateral")
except ImportError as e:
    logger.error(f"❌ Collateral router import error: {e}")
    routers_available['collateral'] = None

# Tax Intelligence Routes
try:
    from backend.api.routes.tax_routes import router as tax_router
    routers_available['tax'] = tax_router
    logger.info("✅ Tax Intelligence router imported")
except ImportError as e:
    logger.error(f"❌ Tax Intelligence router import error: {e}")
    routers_available['tax'] = None

# 📊 Compliance OS Routes
try:
    from backend.api.routes import subscriptions, compliance
    app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["Subscriptions"])
    app.include_router(compliance.router, prefix="/api/v1/compliance", tags=["Compliance"])
    logger.info("✅ Compliance OS routers registered")
except ImportError as e:
    logger.error(f"❌ Compliance routes import error: {e}")

# Register Tax Intelligence Routes
if routers_available.get('tax'):
    app.include_router(routers_available['tax'])
    logger.info("✅ Tax Intelligence router registered with its own prefix")

# 🎯 Tax Intelligence Routes (V1 + V2)
try:
    from backend.api.routes.tax_routes import router as tax_router
    routers_available['tax'] = tax_router
    logger.info("✅ Tax Intelligence router imported (V1 + V2)")
    
    # Register the main tax router (includes both V1 and V2)
    app.include_router(tax_router)
    logger.info("✅ Tax Intelligence router registered with automatic prefixes")
    
except ImportError as e:
    logger.error(f"❌ Tax Intelligence router import error: {e}")
    routers_available['tax'] = None

# 🎓 Financial Literacy Routes (Quests, Wellbeing Coach, Signal Guild)
if routers_available.get('learn'):
    app.include_router(routers_available['learn'])
    logger.info("✅ Financial Literacy router registered at /api/v1/learn")

# ===== ADMIN ROUTES =====
try:
    from backend.api.routes.admin import router as admin_router
    app.include_router(admin_router, prefix="/api/v1", tags=["Admin"])
    logger.info("âœ… Admin routes registered at /api/v1/admin")
except ImportError as e:
    logger.error(f"âŒ Admin routes import error: {e}")

# ===== CORE API ENDPOINTS =====

@app.api_route("/api/v1/health", methods=["GET", "HEAD"], tags=["System"])
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
async def business_contact(
    request: Request, 
    payload: BusinessLeadPayload,
    background_tasks: BackgroundTasks
):
    """
    ðŸ“§ Submit business lead inquiry
    âœ… Saves to database
    âœ… Sends email to business@seamount.io (non-blocking)
    âœ… Returns toast-ready response
    """
    try:
        supabase = get_supabase_client()
        
        # 1ï¸âƒ£ VALIDATE INPUT
        if not payload.name or not payload.email:
            raise HTTPException(
                status_code=400,
                detail="Name and email are required"
            )
        
        # 2ï¸âƒ£ SAVE TO DATABASE
        lead_data = {
            "name": payload.name,
            "email": payload.email,
            "business_name": payload.business_name,
            "message": payload.message
            # created_at and updated_at are handled by database defaults
        }
        
        logger.info(f"[Business Lead] ðŸ’¾ Attempting to save: {payload.name} <{payload.email}>")
        
        db_result = supabase.table('business_leads').insert(lead_data).execute()
        
        if not db_result.data:
            logger.error("[Business Lead] âŒ Database insert failed - no data returned")
            raise HTTPException(
                status_code=500, 
                detail="Failed to save your inquiry. Please try again."
            )
        
        saved_lead = db_result.data[0]
        logger.info(f"[Business Lead] âœ… Saved successfully - ID: {saved_lead['id']}")
        
        # 3ï¸âƒ£ SEND EMAIL IN BACKGROUND (Non-blocking)
        async def send_lead_notification():
            """Background task to send email notification"""
            try:
                from backend.services.email_service import EmailService
                email_service = EmailService(get_settings_cached())
                
                subject = f"ðŸš€ New Business Lead: {payload.business_name or payload.name}"
                
                # Build professional HTML email
                html_body = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{ 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                            line-height: 1.6; 
                            color: #1f2937;
                            margin: 0;
                            padding: 0;
                        }}
                        .container {{ 
                            max-width: 600px; 
                            margin: 0 auto; 
                            background: #ffffff;
                        }}
                        .header {{ 
                            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                            color: white; 
                            padding: 30px 20px;
                            text-align: center;
                        }}
                        .header h1 {{
                            margin: 0;
                            font-size: 24px;
                            font-weight: 700;
                        }}
                        .header p {{
                            margin: 10px 0 0 0;
                            opacity: 0.9;
                            font-size: 14px;
                        }}
                        .content {{ 
                            padding: 30px 20px;
                            background: #f9fafb;
                        }}
                        table {{ 
                            width: 100%; 
                            border-collapse: collapse;
                            background: white;
                            border-radius: 8px;
                            overflow: hidden;
                            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                        }}
                        td {{ 
                            padding: 16px 20px;
                            border-bottom: 1px solid #e5e7eb;
                        }}
                        tr:last-child td {{
                            border-bottom: none;
                        }}
                        .label {{ 
                            font-weight: 600;
                            width: 140px;
                            color: #6b7280;
                            font-size: 14px;
                        }}
                        .value {{ 
                            color: #111827;
                            font-size: 15px;
                        }}
                        .value a {{
                            color: #6366f1;
                            text-decoration: none;
                        }}
                        .value a:hover {{
                            text-decoration: underline;
                        }}
                        .action-box {{
                            margin-top: 20px;
                            padding: 20px;
                            background: #fef3c7;
                            border-left: 4px solid #f59e0b;
                            border-radius: 4px;
                        }}
                        .action-box strong {{
                            color: #92400e;
                            font-size: 15px;
                        }}
                        .footer {{
                            padding: 20px;
                            text-align: center;
                            color: #6b7280;
                            font-size: 13px;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>ðŸ“§ New Business Inquiry</h1>
                            <p>Seamount.io Lead Management</p>
                        </div>
                        <div class="content">
                            <table>
                                <tr>
                                    <td class="label">ðŸ‘¤ Name:</td>
                                    <td class="value">{payload.name}</td>
                                </tr>
                                <tr>
                                    <td class="label">âœ‰ï¸ Email:</td>
                                    <td class="value">
                                        <a href="mailto:{payload.email}">{payload.email}</a>
                                    </td>
                                </tr>
                                <tr>
                                    <td class="label">ðŸ¢ Company:</td>
                                    <td class="value">{payload.business_name or '<em>Not provided</em>'}</td>
                                </tr>
                                <tr>
                                    <td class="label">ðŸ’¬ Message:</td>
                                    <td class="value">{payload.message or '<em>No message provided</em>'}</td>
                                </tr>
                                <tr>
                                    <td class="label">ðŸ• Received:</td>
                                    <td class="value">{datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}</td>
                                </tr>
                            </table>
                            <div class="action-box">
                                <strong>âš¡ Action Required:</strong><br>
                                Please respond within 24 hours to maintain our service commitment.
                            </div>
                        </div>
                        <div class="footer">
                            <p>Lead ID: {saved_lead['id']}</p>
                            <p>This is an automated notification from Seamount.io</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                # Send email
                email_sent = await email_service.send_email(
                    subject=subject,
                    to_emails=["business@seamount.io"],
                    html_content=html_body
                )
                
                if email_sent:
                    logger.info(f"[Business Lead] âœ… Email sent to business@seamount.io")
                else:
                    logger.warning(f"[Business Lead] âš ï¸ Email send returned False (check email service)")
                
            except Exception as email_error:
                # Non-critical: Don't fail the user's request if email fails
                logger.error(f"[Business Lead] âš ï¸ Email notification failed (non-critical): {email_error}")
                logger.error(f"[Business Lead] Stack trace: {traceback.format_exc()}")
        
        # Queue email to send in background (won't block response)
        background_tasks.add_task(send_lead_notification)
        
        # 4ï¸âƒ£ RETURN SUCCESS RESPONSE (User sees this immediately)
        return {
            "success": True,
            "message": "Thank you for your interest! A member of our team will be in touch within 24 hours.",
            "lead_id": saved_lead['id']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"[Business Lead] âŒ Unexpected error [{error_id}]: {str(e)}")
        logger.error(f"[Business Lead] Stack trace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Could not process your request. Please contact support with Error ID: {error_id}"
        )

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

@app.get("/api/debug/all-routes", tags=["Debug"])
async def debug_all_routes():
    """Debug endpoint to see ALL registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, "name", "N/A")
            })
    
    routes_sorted = sorted(routes, key=lambda x: x["path"])
    
    # Filter for wallet-backup routes specifically
    wallet_backup = [r for r in routes_sorted if "wallet-backup" in r["path"] or "wallet_backup" in r["path"]]
    
    return {
        "total_routes": len(routes_sorted),
        "wallet_backup_found": len(wallet_backup),
        "wallet_backup_routes": wallet_backup,
        "all_routes": routes_sorted
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
    """
    Background task to process KYC webhook events.
    Currently handled directly in webhooks.py regfyl_screening_webhook.
    This stub kept for legacy compatibility and future webhook routing.
    """
    try:
        event_type = payload.get("type") or payload.get("checkType")
        customer_id = payload.get("customerID") or payload.get("resource", {}).get("id")
        logger.info(f"process_kyc_webhook: type={event_type} customer={customer_id}")
        # Full logic lives in: backend/api/routes/webhooks.py → regfyl_screening_webhook()
    except Exception as e:
        logger.error(f"process_kyc_webhook error: {e}")

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