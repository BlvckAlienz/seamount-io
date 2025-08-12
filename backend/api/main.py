import logging
from fastapi import FastAPI, Depends, HTTPException, Request, Security, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field, EmailStr
from supabase import create_client, Client
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timedelta
import os
import aiohttp
from algosdk.v2client import algod
from algosdk import account, mnemonic
import smtplib
from email.mime.text import MIMEText

# --- Core Config & Models ---
class Settings:
    VITE_SUPABASE_URL: str = os.getenv("VITE_SUPABASE_URL", "https://opqnoficlhbylxfpaehp.supabase.co")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY")  # Must be set in Render
    ALGORAND_API_URL: str = os.getenv("ALGORAND_API_URL", "https://testnet-algorand.api.purestake.io/ps2")
    ALGORAND_API_KEY: str = os.getenv("ALGORAND_API_KEY")  # Must be set in Render
    EMAIL_HOST: str = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USER: str = os.getenv("EMAIL_USER")
    EMAIL_PASS: str = os.getenv("EMAIL_PASS")

    class Config:
        case_sensitive = True

def get_settings() -> Settings:
    settings = Settings()
    if not all([settings.SUPABASE_SERVICE_KEY, settings.ALGORAND_API_KEY, settings.EMAIL_USER, settings.EMAIL_PASS]):
        raise ValueError("Missing required environment variables")
    return settings

class UserProfile(BaseModel):
    id: str
    email: str
    kyc_level: int
    kyc_status: str
    is_admin: bool
    algorand_address: Optional[str] = None

class InvestorContactPayload(BaseModel):
    name: str
    email: EmailStr
    company: str
    checkSize: str
    message: str

class WhitelabelQuotePayload(BaseModel):
    amount: Decimal
    from_currency: str
    to_currency: str

class ConsentPayload(BaseModel):
    preferences: Dict[str, bool]

# --- Service Classes ---
class DatabaseService:
    def __init__(self, settings: Settings):
        self.supabase = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    async def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        for attempt in range(3):
            try:
                response = self.supabase.table(table).insert(data).execute()
                return response.data[0]
            except Exception as e:
                logger.error(f"DB insert attempt {attempt+1}/3 on {table}: {str(e)}")
                if attempt == 2:
                    raise HTTPException(status_code=500, detail=f"DB insert failed: {str(e)}")
                await asyncio.sleep(2 ** attempt)

    async def select(self, table: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        for attempt in range(3):
            try:
                response = self.supabase.table(table).select("*").match(query).execute()
                return response.data
            except Exception as e:
                logger.error(f"DB select attempt {attempt+1}/3 on {table}: {str(e)}")
                if attempt == 2:
                    raise HTTPException(status_code=500, detail=f"DB select failed: {str(e)}")
                await asyncio.sleep(2 ** attempt)

    async def update(self, table: str, query: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        for attempt in range(3):
            try:
                response = self.supabase.table(table).update(data).match(query).execute()
                return response.data[0] if response.data else {}
            except Exception as e:
                logger.error(f"DB update attempt {attempt+1}/3 on {table}: {str(e)}")
                if attempt == 2:
                    raise HTTPException(status_code=500, detail=f"DB update failed: {str(e)}")
                await asyncio.sleep(2 ** attempt)

class AuditService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.db = DatabaseService(get_settings())

    async def log_action(self, user_id: str, action: str, details: Dict[str, Any]):
        try:
            await self.db.insert("compliance_logs", {
                "user_id": user_id,
                "action": action,
                "details": details,
                "created_at": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Audit log error: {str(e)}")

class EmailService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_email(self, to: str, subject: str, body: str):
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.settings.EMAIL_USER
        msg["To"] = to
        for attempt in range(3):
            try:
                with smtplib.SMTP(self.settings.EMAIL_HOST, self.settings.EMAIL_PORT) as server:
                    server.starttls()
                    server.login(self.settings.EMAIL_USER, self.settings.EMAIL_PASS)
                    server.send_message(msg)
                return
            except Exception as e:
                logger.error(f"Email send attempt {attempt+1}/3: {str(e)}")
                if attempt == 2:
                    raise HTTPException(status_code=500, detail="Failed to send email")
                await asyncio.sleep(2 ** attempt)

class NotificationService:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service

    async def notify_investor_contact(self, payload: InvestorContactPayload):
        await self.email_service.send_email(
            to="support@seamount.io",
            subject="New Investor Contact",
            body=f"Name: {payload.name}\nEmail: {payload.email}\nCompany: {payload.company}\nCheck Size: {payload.checkSize}\nMessage: {payload.message}"
        )

class KYCService:
    def __init__(self, settings: Settings, supabase_client: Client, database_service: DatabaseService, audit_service: AuditService):
        self.settings = settings
        self.supabase = supabase_client
        self.db = database_service
        self.audit_service = audit_service

    async def update_kyc_status(self, user_id: str, status: str, level: int):
        try:
            await self.db.update("user_profiles", {"id": user_id}, {
                "kyc_status": status,
                "kyc_level": level,
                "updated_at": datetime.utcnow().isoformat()
            })
            await self.db.insert("kyc_verifications", {
                "user_id": user_id,
                "status": status,
                "level": level,
                "updated_at": datetime.utcnow().isoformat()
            })
            await self.audit_service.log_action(user_id, "kyc_update", {"status": status, "level": level})
        except Exception as e:
            logger.error(f"KYC update error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update KYC")

class WalletService:
    def __init__(self, settings: Settings, supabase_client: Client):
        self.settings = settings
        self.supabase = supabase_client
        self.db = DatabaseService(settings)

    async def provision_user_wallet(self, user_id: str) -> Dict[str, str]:
        try:
            private_key, address = account.generate_account()
            await self.db.insert("wallet_balances", {
                "user_id": user_id,
                "algorand_address": address,
                "balance": "0.0",
                "created_at": datetime.utcnow().isoformat()
            })
            await self.db.update("user_profiles", {"id": user_id}, {
                "algorand_address": address,
                "updated_at": datetime.utcnow().isoformat()
            })
            return {"algorand_address": address}
        except Exception as e:
            logger.error(f"Wallet provision error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to provision wallet")

class AlgorandService:
    def __init__(self, settings: Settings):
        self.settings = settings
        headers = {"X-API-Key": settings.ALGORAND_API_KEY}
        self.client = algod.AlgodClient(settings.ALGORAND_API_KEY, settings.ALGORAND_API_URL, headers)

    async def get_usds_balance(self, address: str) -> Decimal:
        for attempt in range(3):
            try:
                account_info = await self.client.account_info(address)
                for asset in account_info.get("assets", []):
                    if asset["asset-id"] == 123456:  # Replace with your USDS ASA ID
                        return Decimal(str(asset["amount"])) / Decimal("1000000")  # Adjust for 6 decimals
                return Decimal("0.0")
            except Exception as e:
                logger.error(f"Algorand balance attempt {attempt+1}/3: {str(e)}")
                if attempt == 2:
                    raise HTTPException(status_code=500, detail="Failed to fetch balance")
                await asyncio.sleep(2 ** attempt)

class TreasuryService:
    def __init__(self, settings: Settings, database_service: DatabaseService, algorand_service: AlgorandService):
        self.settings = settings
        self.db = database_service
        self.algorand_service = algorand_service

    async def monitor_backing_ratio(self):
        try:
            reserves = await self.db.select("backing_reserves", {})
            total_supply = Decimal("0.0")
            for reserve in reserves:
                total_supply += Decimal(str(reserve.get("amount", "0.0")))
            # Fetch circulating supply from Algorand (mocked for now)
            circulating_supply = Decimal("1000000.0")  # Replace with real Algorand query
            utilization = circulating_supply / total_supply if total_supply > 0 else Decimal("0.0")
            if utilization > Decimal("0.8"):
                logger.info("Utilization above 80%, triggering supply expansion")
                # Implement minting logic here
            await self.db.insert("compliance_logs", {
                "action": "backing_ratio_check",
                "details": {"utilization": str(utilization)},
                "created_at": datetime.utcnow().isoformat()
            })
            return {"utilization": str(utilization)}
        except Exception as e:
            logger.error(f"Treasury monitor error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to monitor treasury")

class OnboardingService:
    def __init__(self, settings: Settings, supabase_client: Client, wallet_service: WalletService, kyc_service: KYCService):
        self.settings = settings
        self.supabase = supabase_client
        self.wallet_service = wallet_service
        self.kyc_service = kyc_service

    async def start_onboarding(self, user_id: str):
        try:
            await self.kyc_service.update_kyc_status(user_id, "pending", 0)
            await self.wallet_service.provision_user_wallet(user_id)
            return {"status": "onboarding_started"}
        except Exception as e:
            logger.error(f"Onboarding error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to start onboarding")

class PaymentService:
    def __init__(self, settings: Settings, database_service: DatabaseService, wallet_service: WalletService, algorand_service: AlgorandService, treasury_service: TreasuryService):
        self.settings = settings
        self.db = database_service
        self.wallet_service = wallet_service
        self.algorand_service = algorand_service
        self.treasury_service = treasury_service

    async def process_payment(self, user_id: str, amount: Decimal, to_address: str):
        try:
            await self.db.insert("payment_requests", {
                "user_id": user_id,
                "amount": str(amount),
                "to_address": to_address,
                "status": "completed",
                "created_at": datetime.utcnow().isoformat()
            })
            await self.db.insert("transactions", {
                "user_id": user_id,
                "amount": str(amount),
                "to_address": to_address,
                "type": "payment",
                "status": "completed",
                "created_at": datetime.utcnow().isoformat()
            })
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Payment error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to process payment")

class TradingService:
    def __init__(self, settings: Settings, database_service: DatabaseService, oracle_service: Any, wallet_service: WalletService, algorand_service: AlgorandService):
        self.settings = settings
        self.db = database_service
        self.oracle_service = oracle_service
        self.wallet_service = wallet_service
        self.algorand_service = algorand_service

    async def execute_trade(self, user_id: str, asset: str, amount: Decimal):
        try:
            price = await self.oracle_service.get_price(asset)
            await self.db.insert("portfolio_holdings", {
                "user_id": user_id,
                "asset": asset,
                "amount": str(amount),
                "price": str(price),
                "created_at": datetime.utcnow().isoformat()
            })
            return {"status": "success", "price": str(price)}
        except Exception as e:
            logger.error(f"Trade error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to execute trade")

class OracleService:
    def __init__(self, settings: Settings, database_service: DatabaseService):
        self.settings = settings
        self.db = database_service

    async def get_price(self, asset: str) -> Decimal:
        for attempt in range(3):
            try:
                rates = await self.db.select("exchange_rates", {"asset": asset})
                if rates:
                    return Decimal(str(rates[0]["price"]))
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://api.example.com/price/{asset}") as resp:
                        data = await resp.json()
                        price = Decimal(str(data["price"]))
                        await self.db.insert("exchange_rates", {
                            "asset": asset,
                            "price": str(price),
                            "updated_at": datetime.utcnow().isoformat()
                        })
                        return price
            except Exception as e:
                logger.error(f"Oracle price attempt {attempt+1}/3: {str(e)}")
                if attempt == 2:
                    raise HTTPException(status_code=500, detail="Failed to fetch price")
                await asyncio.sleep(2 ** attempt)

class ComplianceService:
    def __init__(self, settings: Settings, database_service: DatabaseService, kyc_service: KYCService, audit_service: AuditService):
        self.settings = settings
        self.db = database_service
        self.kyc_service = kyc_service
        self.audit_service = audit_service

    async def get_alerts_for_review(self, status: str, severity: Optional[str], limit: int, offset: int):
        try:
            query = {"status": status}
            if severity:
                query["severity"] = severity
            alerts = await self.db.select("compliance_logs", query)
            return {"alerts": alerts[offset:offset+limit], "total": len(alerts)}
        except Exception as e:
            logger.error(f"Compliance alerts error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch alerts")

    async def get_dashboard_metrics(self, country_code: Optional[str]):
        try:
            query = {} if not country_code else {"country_code": country_code}
            users = await self.db.select("user_profiles", query)
            return {"metrics": {"total_users": len(users)}}
        except Exception as e:
            logger.error(f"Compliance dashboard error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch metrics")

class SwapService:
    def __init__(self, settings: Settings, database_service: DatabaseService, oracle_service: OracleService):
        self.settings = settings
        self.db = database_service
        self.oracle_service = oracle_service

    async def execute_swap(self, user_id: str, from_asset: str, to_asset: str, amount: Decimal):
        try:
            from_price = await self.oracle_service.get_price(from_asset)
            to_price = await self.oracle_service.get_price(to_asset)
            to_amount = (amount * from_price) / to_price
            await self.db.insert("transactions", {
                "user_id": user_id,
                "from_asset": from_asset,
                "to_asset": to_asset,
                "amount": str(amount),
                "to_amount": str(to_amount),
                "type": "swap",
                "status": "completed",
                "created_at": datetime.utcnow().isoformat()
            })
            return {"status": "success", "to_amount": str(to_amount)}
        except Exception as e:
            logger.error(f"Swap error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to execute swap")

# --- Auth Dependency ---
async def get_current_user(request: Request) -> UserProfile:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    token = auth_header.split(" ")[1]
    try:
        user_data = supabase_client.auth.get_user(token)
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_records = await DatabaseService(get_settings()).select("user_profiles", {"id": user_data.user.id})
        if not user_records:
            raise HTTPException(status_code=404, detail="User profile not found")
        user = user_records[0]
        return UserProfile(
            id=user["id"],
            email=user["email"],
            kyc_level=user.get("kyc_level", 0),
            kyc_status=user.get("kyc_status", "pending"),
            is_admin=user.get("is_admin", False),
            algorand_address=user.get("algorand_address")
        )
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(status_code=401, detail="Token validation failed")

# --- API Key Dependency ---
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != get_settings().ALGORAND_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# --- Initialization ---
settings: Settings = get_settings()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)
supabase_client: Client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

# --- Service Instances ---
database_service = DatabaseService(settings)
audit_service = AuditService(supabase_client)
email_service = EmailService(settings)
notification_service = NotificationService(email_service)
kyc_service = KYCService(settings, supabase_client, database_service, audit_service)
wallet_service = WalletService(settings, supabase_client)
algorand_service = AlgorandService(settings)
treasury_service = TreasuryService(settings, database_service, algorand_service)
onboarding_service = OnboardingService(settings, supabase_client, wallet_service, kyc_service)
compliance_service = ComplianceService(settings, database_service, kyc_service, audit_service)
oracle_service = OracleService(settings, database_service)
swap_service = SwapService(settings, database_service, oracle_service)
payment_service = PaymentService(settings, database_service, wallet_service, algorand_service, treasury_service)
trading_service = TradingService(settings, database_service, oracle_service, wallet_service, algorand_service)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://seamount.io",
        "https://www.seamount.io",
        "http://localhost:3000",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
@app.get("/api/v1/user/profile", tags=["User"])
async def get_user_profile(current_user: UserProfile = Depends(get_current_user)):
    logger.info(f"Fetching profile for user: {current_user.id}")
    try:
        await audit_service.log_action(current_user.id, "profile_view", {})
        return {
            "id": current_user.id,
            "email": current_user.email,
            "kyc_level": current_user.kyc_level,
            "kyc_status": current_user.kyc_status,
            "is_admin": current_user.is_admin,
            "algorand_address": current_user.algorand_address
        }
    except Exception as e:
        logger.error(f"Profile fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch profile")

@app.post("/api/v1/investor-contact", tags=["Investor"])
async def investor_contact(payload: InvestorContactPayload):
    logger.info(f"Received investor contact: {payload}")
    try:
        await database_service.insert("investor_contacts", {
            "name": payload.name,
            "email": payload.email,
            "company": payload.company,
            "check_size": payload.checkSize,
            "message": payload.message,
            "created_at": datetime.utcnow().isoformat()
        })
        await notification_service.notify_investor_contact(payload)
        await audit_service.log_action("anonymous", "investor_contact", payload.dict())
        return {"status": "success", "message": "Contact received"}
    except Exception as e:
        logger.error(f"Investor contact error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process contact")

@app.get("/api/v1/portfolio/summary", tags=["Portfolio"])
async def get_portfolio_summary(current_user: UserProfile = Depends(get_current_user)):
    logger.info(f"Fetching portfolio summary for user: {current_user.id}")
    try:
        holdings = await database_service.select("portfolio_holdings", {"user_id": current_user.id})
        total_value = sum(Decimal(str(holding.get("amount", "0.0"))) * Decimal(str(holding.get("price", "0.0"))) for holding in holdings)
        yield_value = Decimal("0.0")  # Implement yield farming logic
        await audit_service.log_action(current_user.id, "portfolio_view", {"total_value": str(total_value)})
        return {"total_value": str(total_value), "assets": holdings, "yield": str(yield_value)}
    except Exception as e:
        logger.error(f"Portfolio summary error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch portfolio")

@app.get("/api/v1/wallet/balance", tags=["Wallet"])
async def get_wallet_balance(current_user: UserProfile = Depends(get_current_user)):
    if not current_user.algorand_address:
        logger.error(f"No wallet for user: {current_user.id}")
        raise HTTPException(status_code=400, detail="Wallet not provisioned")
    try:
        balance = await algorand_service.get_usds_balance(current_user.algorand_address)
        await database_service.update("wallet_balances", {"user_id": current_user.id}, {
            "balance": str(balance),
            "updated_at": datetime.utcnow().isoformat()
        })
        await audit_service.log_action(current_user.id, "balance_view", {"balance": str(balance)})
        return {"balance": str(balance)}
    except Exception as e:
        logger.error(f"Wallet balance error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch balance")

@app.post("/api/v1/user/provision-wallets", tags=["User"])
async def provision_wallets(current_user: UserProfile = Depends(get_current_user)):
    try:
        result = await wallet_service.provision_user_wallet(str(current_user.id))
        await audit_service.log_action(current_user.id, "wallet_provision", {"address": result["algorand_address"]})
        return result
    except Exception as e:
        logger.error(f"Wallet provision error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to provision wallet")

@app.get("/api/v1/compliance/alerts", tags=["Compliance"])
async def get_compliance_alerts(
    status: str,
    severity: Optional[str] = Query(None),
    limit: int = Query(10),
    offset: int = Query(0),
    current_user: UserProfile = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        alerts = await compliance_service.get_alerts_for_review(status, severity, limit, offset)
        await audit_service.log_action(current_user.id, "alerts_view", {"status": status, "limit": limit, "offset": offset})
        return alerts
    except Exception as e:
        logger.error(f"Compliance alerts error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")

@app.get("/api/v1/compliance/dashboard", tags=["Compliance"])
async def get_compliance_dashboard(
    country_code: Optional[str] = Query(None),
    current_user: UserProfile = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        metrics = await compliance_service.get_dashboard_metrics(country_code)
        await audit_service.log_action(current_user.id, "dashboard_view", {"country_code": country_code})
        return metrics
    except Exception as e:
        logger.error(f"Compliance dashboard error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")

@app.post("/api/v1/whitelabel/quote", tags=["Whitelabel Services"])
async def get_payment_quote(payload: WhitelabelQuotePayload, api_key: str = Depends(get_api_key)):
    try:
        fee = payload.amount * Decimal("0.03")  # 3% fee
        quote_id = f"quote_{uuid4()}"
        await database_service.insert("payment_requests", {
            "quote_id": quote_id,
            "amount": str(payload.amount),
            "from_currency": payload.from_currency.upper(),
            "to_currency": payload.to_currency.upper(),
            "estimated_fee": str(fee),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        })
        await audit_service.log_action("system", "quote_generated", payload.dict())
        return {
            "from_currency": payload.from_currency.upper(),
            "to_currency": payload.to_currency.upper(),
            "amount_to_send": str(payload.amount),
            "estimated_fee": str(fee),
            "estimated_amount_to_receive": str(payload.amount - fee),
            "quote_id": quote_id,
            "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }
    except Exception as e:
        logger.error(f"Payment quote error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate quote")

@app.post("/api/v1/consent/cookies", tags=["Consent"])
async def set_consent_cookies(payload: ConsentPayload):
    try:
        await database_service.insert("user_consent", {
            "preferences": payload.preferences,
            "created_at": datetime.utcnow().isoformat()
        })
        await audit_service.log_action("anonymous", "consent_update", payload.dict())
        return {"status": "success", "message": "Consent preferences updated"}
    except Exception as e:
        logger.error(f"Consent cookies error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update consent")

@app.get("/")
async def root():
    return {"status": "healthy", "service": "Seamount.io API Gateway"}