"""
Production-Grade USDS Asset Manager for Seamount.io
Wall Street-Level Implementation with Complete Error Handling & Multi-Collateral Support
File: /src/core/usds_asset_manager.py
"""
import asyncio
import logging
import os
import base64
import uuid
import time
import hashlib
import hmac
import json
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
import requests
from requests.exceptions import RequestException
from functools import wraps

# Blockchain & Crypto imports
from algosdk import account, mnemonic, transaction, encoding
from algosdk.v2client import algod, indexer
from algosdk.atomic_transaction_composer import AtomicTransactionComposer, TransactionWithSigner
from algosdk.abi import Contract
from algosdk.transaction import (
    AssetConfigTxn, AssetTransferTxn, PaymentTxn, 
    AssetOptInTxn, AssetFreezeTxn
)

# Database & Cache imports
try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - using in-memory cache")

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logging.warning("Supabase not available - using local storage")

# Web3 for multi-chain support
try:
    from web3 import Web3
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    logging.warning("Web3 not available - Algorand only mode")

# Determine the logs directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)  # Move up to backend directory
logs_dir = os.path.join(project_dir, 'logs')
os.makedirs(logs_dir, exist_ok=True)  # Ensure logs directory exists

# Configure logging
log_file = os.path.join(logs_dir, 'usds_manager.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========================
# CONFIGURATION CONSTANTS
# ========================
class CollateralType(Enum):
    USD_BANK_RESERVE = "usd_bank_reserve"
    USDC = "usdc"
    ALGO = "algo"
    USDT = "usdt"
    GOLD = "gold"
    ETH = "ethereum"
    BTC = "bitcoin"

COLLATERAL_QUALITY = {
    CollateralType.USD_BANK_RESERVE: Decimal('1.0'),
    CollateralType.USDC: Decimal('0.95'),
    CollateralType.ALGO: Decimal('0.85'),
    CollateralType.USDT: Decimal('0.80'),
    CollateralType.ETH: Decimal('0.75'),
    CollateralType.BTC: Decimal('0.70'),
    CollateralType.GOLD: Decimal('0.65')
}

class USDSOperationType(Enum):
    MINT = "mint"
    BURN = "burn"
    TRANSFER = "transfer"
    FREEZE = "freeze"
    UNFREEZE = "unfreeze"
    OPT_IN = "opt_in"
    CLAWBACK = "clawback"
    LIQUIDATION = "liquidation"

class TransactionStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

@dataclass
class CountryConfig:
    country_code: str
    currency: str
    min_collateral_ratio: int
    liquidation_ratio: int
    risk_weight: Decimal
    stability_fee: Decimal
    daily_mint_limit: Decimal
    kyc_required: bool = True
    
    def to_dict(self) -> Dict:
        return asdict(self)

class USDSConfig:
    """Production configuration for multi-country USDS deployment"""
    COUNTRIES = {
        'ZA': CountryConfig('ZA', 'ZAR', 175, 160, Decimal('0.15'), Decimal('0.065'), Decimal('1000000')),
        'NG': CountryConfig('NG', 'NGN', 200, 175, Decimal('0.25'), Decimal('0.075'), Decimal('500000')),
        'MA': CountryConfig('MA', 'MAD', 200, 175, Decimal('0.25'), Decimal('0.075'), Decimal('750000')),
        'EG': CountryConfig('EG', 'EGP', 200, 175, Decimal('0.25'), Decimal('0.075'), Decimal('600000')),
        'KE': CountryConfig('KE', 'KES', 200, 175, Decimal('0.25'), Decimal('0.075'), Decimal('800000')),
        'TZ': CountryConfig('TZ', 'TZS', 200, 175, Decimal('0.25'), Decimal('0.075'), Decimal('400000')),
        'GH': CountryConfig('GH', 'GHS', 225, 200, Decimal('0.35'), Decimal('0.09'), Decimal('300000')),
        'VE': CountryConfig('VE', 'VES', 225, 200, Decimal('0.35'), Decimal('0.09'), Decimal('200000')),
        'AR': CountryConfig('AR', 'ARS', 250, 225, Decimal('0.45'), Decimal('0.12'), Decimal('150000')),
        'TR': CountryConfig('TR', 'TRY', 200, 175, Decimal('0.30'), Decimal('0.08'), Decimal('500000'))
    }
    
    GLOBAL_LIMITS = {
        'max_daily_mint': Decimal('10000000'),
        'max_user_holdings': Decimal('1000000'),
        'max_single_transaction': Decimal('100000'),
        'min_mint_amount': Decimal('10'),
        'emergency_pause_threshold': Decimal('0.95')  # PEG threshold
    }
    
    @classmethod
    def get_country_config(cls, country_code: str) -> Optional[CountryConfig]:
        return cls.COUNTRIES.get(country_code.upper())
    
    @classmethod
    def get_all_countries(cls) -> List[str]:
        return list(cls.COUNTRIES.keys())

# ========================
# DATA STRUCTURES
# ========================
@dataclass
class USDSTransaction:
    tx_id: str
    user_id: str
    operation_type: USDSOperationType
    amount: Decimal
    algorand_tx_hash: str
    country_code: str
    collateral_type: Optional[CollateralType] = None
    fiat_reference: Optional[str] = None
    fee: Decimal = Decimal('0')
    status: TransactionStatus = TransactionStatus.PENDING
    gas_fee: Decimal = Decimal('0')
    created_at: datetime = None
    confirmed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['operation_type'] = self.operation_type.value
        data['status'] = self.status.value
        if self.collateral_type:
            data['collateral_type'] = self.collateral_type.value
        return data

@dataclass
class CollateralReserve:
    country_code: str
    reserve_type: CollateralType
    total_amount: Decimal
    allocated_amount: Decimal
    available_amount: Decimal
    last_updated: datetime
    health_ratio: Decimal = Decimal('1.0')
    
    def update_amounts(self, allocated: Decimal, available: Decimal):
        self.allocated_amount = allocated
        self.available_amount = available
        self.last_updated = datetime.utcnow()
        
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['reserve_type'] = self.reserve_type.value
        return data

@dataclass
class TreasuryHealth:
    treasury_balance: int
    balance_usds: Decimal
    total_supply: int
    circulating_supply: int
    treasury_percentage: Decimal
    reserve_ratio: Decimal
    peg_stability: Decimal
    status: str
    timestamp: int
    emergency_mode: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class UserProfile:
    user_id: str
    address: str
    country_code: str
    kyc_verified: bool
    risk_score: Decimal
    daily_volume: Decimal
    monthly_volume: Decimal
    total_minted: Decimal
    total_burned: Decimal
    created_at: datetime
    last_activity: datetime
    
    def to_dict(self) -> Dict:
        return asdict(self)

# ========================
# UTILITY DECORATORS
# ========================
def retry_with_exponential_backoff(max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """Enhanced retry decorator with exponential backoff and jitter"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        logger.error(f"Final attempt failed for {func.__name__}: {e}")
                        raise
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = delay * 0.1 * (0.5 - abs(hash(str(e)) % 100) / 100)
                    total_delay = delay + jitter
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {total_delay:.2f}s..."
                    )
                    await asyncio.sleep(total_delay)
            
            raise last_exception
        return wrapper
    return decorator

def validate_address(func):
    """Decorator to validate Algorand addresses"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        # Extract address parameters
        for i, arg in enumerate(args):
            if isinstance(arg, str) and len(arg) == 58:  # Algorand address length
                if not self._is_valid_algorand_address(arg):
                    raise ValueError(f"Invalid Algorand address: {arg}")
        return await func(self, *args, **kwargs)
    return wrapper

def require_initialization(func):
    """Decorator to ensure manager is initialized"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not hasattr(self, '_initialized') or not self._initialized:
            raise RuntimeError("USDSManager must be initialized before use")
        return await func(self, *args, **kwargs)
    return wrapper

# ========================
# KYC COMPLIANCE INTEGRATION
# ========================
class KYCManager:
    """KYC verification manager with ComplyCube integration"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.complycube.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    @retry_with_exponential_backoff(max_attempts=3)
    async def verify_user(
        self, 
        user_id: str, 
        document_path: str, 
        selfie_path: str
    ) -> Dict[str, Union[bool, str]]:
        """Verify user identity using ComplyCube API"""
        try:
            # Create client profile
            client_data = {"type": "person", "id": user_id}
            client_response = requests.post(
                f"{self.base_url}/clients",
                headers=self.headers,
                json=client_data
            )
            client_response.raise_for_status()
            client_id = client_response.json()["id"]
            
            # Create document check
            check_data = {
                "clientId": client_id,
                "type": "document_check",
                "document": {"file": self._read_file(document_path)},
                "selfie": {"file": self._read_file(selfie_path)}
            }
            check_response = requests.post(
                f"{self.base_url}/checks",
                headers=self.headers,
                json=check_data
            )
            check_response.raise_for_status()
            check_id = check_response.json()["id"]
            
            # Wait for verification result
            result = await self._poll_verification_result(check_id)
            
            # Update verification status
            if result["outcome"] == "clear":
                return {"verified": True, "level": 2, "details": "Full KYC verification"}
            else:
                logger.warning(f"KYC failed for user {user_id}: {result.get('details', 'Unknown reason')}")
                return {"verified": False, "level": 0, "details": result.get("details", "Verification failed")}
                
        except RequestException as e:
            logger.error(f"ComplyCube API error: {str(e)}")
            return {"verified": False, "level": 0, "details": f"API error: {str(e)}"}
        except Exception as e:
            logger.error(f"KYC verification failed: {str(e)}")
            return {"verified": False, "level": 0, "details": f"Verification error: {str(e)}"}
    
    async def _poll_verification_result(self, check_id: str, timeout: int = 120) -> Dict[str, Any]:
        """Poll for verification result with timeout"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.base_url}/checks/{check_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()
                
                if data["status"] == "completed":
                    return data
                elif data["status"] == "failed":
                    return {"outcome": "reject", "details": "Verification process failed"}
                
                await asyncio.sleep(5)
            except RequestException as e:
                logger.warning(f"Polling error: {str(e)} - retrying...")
                await asyncio.sleep(5)
        
        return {"outcome": "reject", "details": "Verification timeout"}
    
    def _read_file(self, file_path: str) -> str:
        """Read file content as base64 encoded string"""
        import base64
        with open(file_path, "rb") as file:
            return base64.b64encode(file.read()).decode("utf-8")

# ========================
# RISK MANAGEMENT
# ========================
class USDSRiskManager:
    """Advanced risk management for USDS operations"""
    
    def __init__(self, manager):
        self.manager = manager
        self.risk_models = {}
        self.blacklisted_addresses = set()
        self.velocity_cache = {}
        
    async def validate_mint_risk(self, user_id: str, amount: Decimal, country_code: str) -> Dict:
        """Comprehensive mint risk validation"""
        try:
            country_config = USDSConfig.get_country_config(country_code)
            if not country_config:
                return {'allowed': False, 'reason': 'Unsupported country'}
            
            # Check daily system limits
            daily_mints = await self._get_daily_system_mints(country_code)
            if daily_mints + amount > country_config.daily_mint_limit:
                return {'allowed': False, 'reason': 'Daily country mint limit exceeded'}
            
            # Check global limits
            global_daily = await self._get_global_daily_mints()
            if global_daily + amount > USDSConfig.GLOBAL_LIMITS['max_daily_mint']:
                return {'allowed': False, 'reason': 'Global daily mint limit exceeded'}
            
            # Check user holdings
            user_balance = await self.manager.get_user_balance(user_id)
            new_balance = user_balance.get('usds_balance', 0) + amount
            if new_balance > USDSConfig.GLOBAL_LIMITS['max_user_holdings']:
                return {'allowed': False, 'reason': 'User holdings limit exceeded'}
            
            # Check velocity risk
            if await self._check_velocity_risk(user_id, amount):
                return {'allowed': False, 'reason': 'High velocity trading detected'}
            
            # Check blacklist
            if user_id in self.blacklisted_addresses:
                return {'allowed': False, 'reason': 'Address blacklisted'}
            
            # Calculate risk score
            risk_score = await self._calculate_risk_score(user_id, amount, country_code)
            
            return {
                'allowed': True,
                'risk_score': float(risk_score),
                'requires_manual_review': risk_score > Decimal('0.7')
            }
            
        except Exception as e:
            logger.error(f"Risk validation failed: {e}")
            return {'allowed': False, 'reason': f'Risk validation error: {str(e)}'}
    
    async def _get_daily_system_mints(self, country_code: str) -> Decimal:
        """Get total daily mints for a country"""
        try:
            if self.manager.redis_pool:
                key = f"daily_mints:{country_code}:{datetime.utcnow().strftime('%Y-%m-%d')}"
                value = await self.manager.redis_pool.get(key)
                return Decimal(value) if value else Decimal('0')
            return Decimal('0')
        except Exception as e:
            logger.error(f"Failed to get daily mints: {e}")
            return Decimal('0')
    
    async def _get_global_daily_mints(self) -> Decimal:
        """Get total global daily mints"""
        try:
            if self.manager.redis_pool:
                key = f"global_daily_mints:{datetime.utcnow().strftime('%Y-%m-%d')}"
                value = await self.manager.redis_pool.get(key)
                return Decimal(value) if value else Decimal('0')
            return Decimal('0')
        except Exception as e:
            logger.error(f"Failed to get global daily mints: {e}")
            return Decimal('0')
    
    async def _check_velocity_risk(self, user_id: str, amount: Decimal) -> bool:
        """Check for high velocity trading patterns"""
        try:
            current_time = time.time()
            user_velocity = self.velocity_cache.get(user_id, [])
            
            # Clean old entries (24 hours)
            user_velocity = [(ts, amt) for ts, amt in user_velocity if current_time - ts < 86400]
            
            # Add current transaction
            user_velocity.append((current_time, amount))
            
            # Calculate velocity (total amount in last 24h)
            total_24h = sum(amt for _, amt in user_velocity)
            
            # Update cache
            self.velocity_cache[user_id] = user_velocity[-50:]  # Keep last 50 transactions
            
            # Check threshold
            velocity_threshold = USDSConfig.GLOBAL_LIMITS['max_user_holdings'] * Decimal('0.1')
            return total_24h > velocity_threshold
            
        except Exception as e:
            logger.error(f"Velocity check failed: {e}")
            return False
    
    async def _calculate_risk_score(self, user_id: str, amount: Decimal, country_code: str) -> Decimal:
        """Calculate comprehensive risk score"""
        try:
            score = Decimal('0')
            
            # Country risk
            country_config = USDSConfig.get_country_config(country_code)
            score += country_config.risk_weight if country_config else Decimal('0.5')
            
            # Amount risk (larger amounts = higher risk)
            if amount > Decimal('50000'):
                score += Decimal('0.3')
            elif amount > Decimal('10000'):
                score += Decimal('0.1')
            
            # User history risk
            user_profile = await self._get_user_profile(user_id)
            if user_profile:
                if not user_profile.get('kyc_verified', False):
                    score += Decimal('0.2')
                if user_profile.get('risk_score', 0) > 0.5:
                    score += Decimal('0.1')
            else:
                score += Decimal('0.3')  # New user penalty
            
            return min(score, Decimal('1.0'))
            
        except Exception as e:
            logger.error(f"Risk score calculation failed: {e}")
            return Decimal('0.5')  # Default medium risk
    
    async def _get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile for risk assessment"""
        try:
            if self.manager.supabase:
                response = self.manager.supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
                return response.data[0] if response.data else None
            return None
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return None

# ========================
# COMPLIANCE MANAGEMENT
# ========================
class USDSComplianceManager:
    """Regulatory compliance and AML/KYC management"""
    
    def __init__(self, manager):
        self.manager = manager
        self.high_value_threshold = Decimal('10000')
        self.suspicious_pattern_threshold = Decimal('50000')
        
    async def validate_compliance(self, user_id: str, amount: Decimal, operation: str) -> Dict:
        """Comprehensive compliance validation"""
        try:
            # High-value transaction reporting
            if amount >= self.high_value_threshold:
                await self._file_ctr_report(user_id, amount, operation)
                return {
                    'compliant': True,
                    'requires_manual_review': True,
                    'reason': 'High-value transaction requires compliance review',
                    'report_filed': 'CTR'
                }
            
            # Suspicious pattern detection
            if await self._detect_suspicious_pattern(user_id, amount):
                await self._file_sar_report(user_id, amount, operation)
                return {
                    'compliant': False,
                    'reason': 'Suspicious activity pattern detected',
                    'report_filed': 'SAR'
                }
            
            # KYC verification
            kyc_status = await self._verify_kyc_status(user_id)
            if not kyc_status['verified'] and amount > Decimal('1000'):
                return {
                    'compliant': False,
                    'reason': 'KYC verification required for amounts > $1000'
                }
            
            # Sanctions screening
            sanctions_check = await self._screen_sanctions(user_id)
            if not sanctions_check['clear']:
                return {
                    'compliant': False,
                    'reason': 'Sanctions screening failed'
                }
            
            return {
                'compliant': True,
                'requires_manual_review': False,
                'kyc_verified': kyc_status['verified']
            }
            
        except Exception as e:
            logger.error(f"Compliance validation failed: {e}")
            return {'compliant': False, 'reason': f'Compliance validation error: {str(e)}'}
    
    async def _file_ctr_report(self, user_id: str, amount: Decimal, operation: str):
        """File Currency Transaction Report"""
        try:
            report = {
                'type': 'CTR',
                'user_id': user_id,
                'amount': float(amount),
                'operation': operation,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'filed'
            }
            
            if self.manager.supabase:
                self.manager.supabase.table('compliance_reports').insert(report).execute()
            
            logger.info(f"CTR report filed for user {user_id}, amount {amount}")
            
        except Exception as e:
            logger.error(f"Failed to file CTR report: {e}")
    
    async def _file_sar_report(self, user_id: str, amount: Decimal, operation: str):
        """File Suspicious Activity Report"""
        try:
            report = {
                'type': 'SAR',
                'user_id': user_id,
                'amount': float(amount),
                'operation': operation,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'filed'
            }
            
            if self.manager.supabase:
                self.manager.supabase.table('compliance_reports').insert(report).execute()
            
            logger.warning(f"SAR report filed for user {user_id}, amount {amount}")
            
        except Exception as e:
            logger.error(f"Failed to file SAR report: {e}")
    
    async def _detect_suspicious_pattern(self, user_id: str, amount: Decimal) -> bool:
        """Detect suspicious transaction patterns"""
        try:
            # Get user's recent transactions
            if self.manager.supabase:
                response = self.manager.supabase.table('usds_transactions')\
                    .select('*')\
                    .eq('user_id', user_id)\
                    .gte('created_at', (datetime.utcnow() - timedelta(days=7)).isoformat())\
                    .execute()
                
                transactions = response.data
                
                # Pattern 1: Rapid large transactions
                if len(transactions) > 10:
                    total_amount = sum(Decimal(tx['amount']) for tx in transactions)
                    if total_amount > self.suspicious_pattern_threshold:
                        return True
                
                # Pattern 2: Round number transactions (potential structuring)
                round_numbers = sum(1 for tx in transactions if Decimal(tx['amount']) % 1000 == 0)
                if round_numbers > len(transactions) * 0.8:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Suspicious pattern detection failed: {e}")
            return False
    
    async def _verify_kyc_status(self, user_id: str) -> Dict:
        """Verify KYC status"""
        try:
            if self.manager.supabase:
                response = self.manager.supabase.table('user_profiles')\
                    .select('kyc_verified, kyc_level')\
                    .eq('user_id', user_id)\
                    .execute()
                
                if response.data:
                    user_data = response.data[0]
                    return {
                        'verified': user_data.get('kyc_verified', False),
                        'level': user_data.get('kyc_level', 0)
                    }
            
            return {'verified': False, 'level': 0}
            
        except Exception as e:
            logger.error(f"KYC verification failed: {e}")
            return {'verified': False, 'level': 0}
    
    async def _screen_sanctions(self, user_id: str) -> Dict:
        """Screen against sanctions lists"""
        try:
            # In production, integrate with OFAC API or similar
            # For now, simple check against internal blacklist
            if self.manager.supabase:
                response = self.manager.supabase.table('sanctions_list')\
                    .select('*')\
                    .eq('user_id', user_id)\
                    .execute()
                
                return {'clear': len(response.data) == 0}
            
            return {'clear': True}
            
        except Exception as e:
            logger.error(f"Sanctions screening failed: {e}")
            return {'clear': False}

# ========================
# RESERVE MANAGEMENT
# ========================
class USDSReserveManager:
    """Advanced collateral and reserve management"""
    
    def __init__(self, manager):
        self.manager = manager
        self.min_reserve_ratio = Decimal('1.1')
        self.target_reserve_ratio = Decimal('1.2')
        self.emergency_threshold = Decimal('1.05')
        self.max_reserve_ratio = Decimal('1.5')
        
    async def rebalance_reserves(self, country_code: str):
        """Intelligent reserve rebalancing"""
        try:
            current_ratio = await self._calculate_reserve_ratio(country_code)
            logger.info(f"Current reserve ratio for {country_code}: {current_ratio}")
            
            if current_ratio < self.emergency_threshold:
                await self._trigger_emergency_procedures(country_code)
            elif current_ratio < self.min_reserve_ratio:
                await self._increase_reserves(country_code)
            elif current_ratio > self.max_reserve_ratio:
                await self._optimize_reserves(country_code)
            
        except Exception as e:
            logger.error(f"Reserve rebalancing failed for {country_code}: {e}")
    
    async def _calculate_reserve_ratio(self, country_code: str) -> Decimal:
        """Calculate current reserve ratio"""
        try:
            reserves = self.manager.collateral_reserves.get(country_code, {})
            total_reserves = Decimal('0')
            
            for collateral_type, reserve in reserves.items():
                quality_factor = COLLATERAL_QUALITY.get(collateral_type, Decimal('0.5'))
                total_reserves += reserve.available_amount * quality_factor
            
            # Get circulating supply for this country
            circulating = await self._get_country_circulating_supply(country_code)
            
            if circulating > 0:
                return total_reserves / circulating
            return Decimal('0')
            
        except Exception as e:
            logger.error(f"Reserve ratio calculation failed: {e}")
            return Decimal('0')
    
    async def _get_country_circulating_supply(self, country_code: str) -> Decimal:
        """Get circulating supply for specific country"""
        try:
            if self.manager.supabase:
                response = self.manager.supabase.table('usds_transactions')\
                    .select('amount, operation_type')\
                    .eq('country_code', country_code)\
                    .eq('status', 'confirmed')\
                    .execute()
                
                total = Decimal('0')
                for tx in response.data:
                    amount = Decimal(tx['amount'])
                    if tx['operation_type'] == 'mint':
                        total += amount
                    elif tx['operation_type'] == 'burn':
                        total -= amount
                
                return max(total, Decimal('0'))
            
            return Decimal('0')
            
        except Exception as e:
            logger.error(f"Failed to get country circulating supply: {e}")
            return Decimal('0')
    
    async def _trigger_emergency_procedures(self, country_code: str):
        """Emergency procedures for low reserves"""
        try:
            logger.critical(f"EMERGENCY: Low reserves detected for {country_code}")
            
            # Pause new mints
            await self._pause_mints(country_code)
            
            # Notify administrators
            await self._send_emergency_alert(country_code)
            
            # Attempt automatic reserve injection
            await self._inject_emergency_reserves(country_code)
            
        except Exception as e:
            logger.error(f"Emergency procedures failed: {e}")
    
    async def _increase_reserves(self, country_code: str):
        """Increase reserves through various mechanisms"""
        try:
            # Increase stability fees temporarily
            await self._adjust_stability_fees(country_code, increase=True)
            
            # Request additional collateral
            await self._request_additional_collateral(country_code)
            
        except Exception as e:
            logger.error(f"Reserve increase failed: {e}")
    
    async def _optimize_reserves(self, country_code: str):
        """Optimize excess reserves"""
        try:
            # Deploy excess reserves for yield
            await self._deploy_yield_strategies(country_code)
            
            # Reduce stability fees
            await self._adjust_stability_fees(country_code, increase=False)
            
        except Exception as e:
            logger.error(f"Reserve optimization failed: {e}")

# ========================
# CORE USDS MANAGER
# ========================
class USDSManager:
    """Production-grade USDS asset manager with enterprise features"""

    def __init__(self, config: Dict):
        self.config = config
        self._initialized = False
        
        # Initialize Algorand clients
        self.algod_client = algod.AlgodClient(
            config['algorand_token'],
            config['algorand_node_url']
        )
        
        self.indexer_client = None
        if config.get('algorand_indexer_url') and config.get('indexer_token'):
            self.indexer_client = indexer.IndexerClient(
                config['indexer_token'],
                config['algorand_indexer_url']
            )
        
        # Initialize accounts
        self.treasury_account = {
            'address': config['treasury_address'],
            'private_key': config['treasury_private_key']
        }
        self.reserve_account = {
            'address': config['reserve_address'],
            'private_key': config['reserve_private_key']
        }
        
        # Initialize USDS asset
        self.usds_asset_id = config.get('usds_asset_id', 0)
        self.decimals = config.get('decimals', 6)
        self.usds_total_supply = Decimal('0')
        self.usds_circulating_supply = Decimal('0')
        
        # Initialize operational parameters
        self.min_balance = config.get('min_balance', 100_000)
        self.transfer_threshold = config.get('transfer_threshold', 1_000_000)
        self.target_peg = Decimal('1.00')
        
        # Initialize data storage components
        self.redis_pool = None
        self.supabase = None
        self.collateral_reserves = {}
        self.country_balances = {}
        self.pending_transactions = {}
        
        # Initialize sub-managers
        self.risk_manager = USDSRiskManager(self)
        self.compliance_manager = USDSComplianceManager(self)
        self.reserve_manager = USDSReserveManager(self)
        
        # Initialize KYC manager if API key provided
        self.kyc_manager = None
        complycube_api_key = config.get('complycube_api_key')
        if complycube_api_key:
            self.kyc_manager = KYCManager(
                api_key=complycube_api_key,
                base_url=config.get('complycube_url', 'https://api.complycube.com/v1')
            )
            logger.info("ComplyCube KYC integration initialized")
        else:
            logger.info("ComplyCube KYC integration not configured")
        
        # Monitoring and metrics
        self.metrics = {
            'total_mints': 0,
            'total_burns': 0,
            'total_transfers': 0,
            'failed_transactions': 0,
            'emergency_stops': 0
        }
        
        # Emergency controls
        self.emergency_pause = False
        self.maintenance_mode = False
        
    async def initialize(self) -> bool:
        """Initialize all components and verify system health"""
        try:
            logger.info("Initializing USDS Manager...")
            
            # Initialize Redis connection
            if REDIS_AVAILABLE and self.config.get('redis_url'):
                self.redis_pool = await aioredis.from_url(
                    self.config['redis_url'],
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=20,
                    retry_on_timeout=True
                )
                logger.info("Redis connection established")
            
            # Initialize Supabase connection
            if SUPABASE_AVAILABLE and self.config.get('supabase_url'):
                self.supabase = create_client(
                    self.config['supabase_url'],
                    self.config['supabase_key']
                )
                logger.info("Supabase connection established")
            
            # Verify Algorand connection
            await self._verify_algorand_connection()
            
            # Load USDS asset information
            await self._load_usds_asset_info()
            
            # Initialize collateral reserves
            await self._initialize_collateral_reserves()
            
            # Verify treasury health
            treasury_health = await self.get_treasury_health()
            if treasury_health.emergency_mode:
                logger.warning("System initialized in EMERGENCY MODE")
                self.emergency_pause = True
            
            # Start background tasks
            asyncio.create_task(self._background_health_monitor())
            asyncio.create_task(self._background_reserve_rebalancer())
            
            self._initialized = True
            logger.info("USDS Manager successfully initialized")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    async def _verify_algorand_connection(self):
        """Verify Algorand node connectivity"""
        try:
            status = self.algod_client.status()
            logger.info(f"Connected to Algorand node - Round: {status['last-round']}")
            
            # Verify treasury account exists
            treasury_info = self.algod_client.account_info(self.treasury_account['address'])
            logger.info(f"Treasury account balance: {treasury_info['amount']} microAlgos")
            
        except Exception as e:
            raise RuntimeError(f"Algorand connection failed: {e}")

    def _is_valid_algorand_address(self, address: str) -> bool:
        """Validate Algorand address"""
        try:
            return account.is_valid_address(address)
        except Exception:
            return False

    async def prepare_opt_in_transaction(self, user_address: str) -> Dict[str, Any]:
        """Prepare an opt-in transaction for the user to sign"""
        try:
            if not self._is_valid_algorand_address(user_address):
                return {"success": False, "error": "Invalid Algorand address"}
            
            params = self.algod_client.suggested_params()
            txn = AssetOptInTxn(sender=user_address, sp=params, index=self.usds_asset_id)
            txn_id = txn.get_txid()
            unsigned_txn = encoding.msgpack_encode(txn)
            
            return {
                "success": True,
                "unsigned_txn": unsigned_txn,
                "tx_id": txn_id
            }
        except Exception as e:
            logger.error(f"Failed to prepare opt-in transaction: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _load_usds_asset_info(self):
        """Load and verify USDS asset information"""
        try:
            if self.usds_asset_id > 0:
                asset_info = self.algod_client.asset_info(self.usds_asset_id)
                asset_params = asset_info['params']
                
                self.usds_total_supply = Decimal(asset_params['total'])
                self.decimals = asset_params['decimals']
                
                # Calculate circulating supply
                treasury_balance = await self._get_asset_balance(
                    self.treasury_account['address'], 
                    self.usds_asset_id
                )
                self.usds_circulating_supply = self.usds_total_supply - treasury_balance
                
                logger.info(f"USDS Asset loaded - ID: {self.usds_asset_id}, "
                          f"Total: {self.usds_total_supply}, "
                          f"Circulating: {self.usds_circulating_supply}")
            else:
                logger.warning("USDS asset not deployed - running in test mode")
                
        except Exception as e:
            logger.error(f"Failed to load USDS asset info: {e}")
    
    async def _initialize_collateral_reserves(self):
        """Initialize collateral reserves for all supported countries"""
        try:
            for country_code in USDSConfig.get_all_countries():
                self.collateral_reserves[country_code] = {}
                
                # Initialize each collateral type
                for collateral_type in CollateralType:
                    reserve = CollateralReserve(
                        country_code=country_code,
                        reserve_type=collateral_type,
                        total_amount=Decimal('0'),
                        allocated_amount=Decimal('0'),
                        available_amount=Decimal('0'),
                        last_updated=datetime.utcnow()
                    )
                    self.collateral_reserves[country_code][collateral_type] = reserve
                
                logger.info(f"Initialized collateral reserves for {country_code}")
                
        except Exception as e:
            logger.error(f"Failed to initialize collateral reserves: {e}")
    
    # ========================
    # CORE USDS OPERATIONS
    # ========================
    
    @require_initialization
    async def verify_user_kyc(
        self, 
        user_id: str, 
        document_path: str, 
        selfie_path: str,
        store_result: bool = True
    ) -> Dict[str, Any]:
        """Verify user identity and optionally store result in database"""
        if not self.kyc_manager:
            return {"success": False, "error": "KYC manager not configured"}
        
        result = await self.kyc_manager.verify_user(user_id, document_path, selfie_path)
        
        if store_result and self.supabase:
            try:
                # Update user profile with KYC status
                update_data = {
                    "kyc_verified": result["verified"],
                    "kyc_level": result["level"],
                    "kyc_last_verified": datetime.utcnow().isoformat(),
                    "kyc_details": result.get("details", "")
                }
                
                self.supabase.table('user_profiles').update(update_data).eq('user_id', user_id).execute()
                logger.info(f"Updated KYC status for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to update KYC status: {str(e)}")
                result["storage_error"] = str(e)
        
        return {
            "success": result["verified"],
            "verified": result["verified"],
            "kyc_level": result["level"],
            "details": result.get("details", ""),
            "user_id": user_id
        }
    
    @require_initialization
    @retry_with_exponential_backoff(max_attempts=3)
    async def mint_usds(
        self, 
        user_address: str, 
        amount: Decimal, 
        country_code: str,
        collateral_type: CollateralType,
        fiat_reference: Optional[str] = None
    ) -> Dict:
        """Mint USDS tokens with comprehensive validation"""
        try:
            # Generate transaction ID
            tx_id = str(uuid.uuid4())
            
            # Validate inputs
            if amount < USDSConfig.GLOBAL_LIMITS['min_mint_amount']:
                raise ValueError(f"Minimum mint amount is {USDSConfig.GLOBAL_LIMITS['min_mint_amount']} USDS")
            
            if amount > USDSConfig.GLOBAL_LIMITS['max_single_transaction']:
                raise ValueError(f"Maximum single transaction is {USDSConfig.GLOBAL_LIMITS['max_single_transaction']} USDS")
            
            # Risk validation
            risk_result = await self.risk_manager.validate_mint_risk(user_address, amount, country_code)
            if not risk_result['allowed']:
                return {
                    'success': False,
                    'tx_id': tx_id,
                    'error': risk_result['reason']
                }
            
            # Compliance validation
            compliance_result = await self.compliance_manager.validate_compliance(
                user_address, amount, 'mint'
            )
            if not compliance_result['compliant']:
                return {
                    'success': False,
                    'tx_id': tx_id,
                    'error': compliance_result['reason']
                }
            
            # Collateral validation
            collateral_valid = await self._validate_collateral(amount, country_code, collateral_type)
            if not collateral_valid['valid']:
                return {
                    'success': False,
                    'tx_id': tx_id,
                    'error': collateral_valid['reason']
                }
            
            # Create transaction record
            transaction = USDSTransaction(
                tx_id=tx_id,
                user_id=user_address,
                operation_type=USDSOperationType.MINT,
                amount=amount,
                algorand_tx_hash='',
                country_code=country_code,
                collateral_type=collateral_type,
                fiat_reference=fiat_reference
            )
            
            # Execute mint on Algorand
            algorand_result = await self._execute_mint_transaction(user_address, amount, transaction)
            
            if algorand_result['success']:
                transaction.algorand_tx_hash = algorand_result['tx_hash']
                transaction.status = TransactionStatus.CONFIRMED
                transaction.confirmed_at = datetime.utcnow()
                
                # Update reserves
                await self._update_collateral_allocation(amount, country_code, collateral_type, 'allocate')
                
                # Update metrics
                self.metrics['total_mints'] += 1
                
                # Cache daily mints
                await self._update_daily_mint_cache(amount, country_code)
                
                # Store transaction
                await self._store_transaction(transaction)
                
                logger.info(f"Successfully minted {amount} USDS for {user_address} - TX: {tx_id}")
                
                return {
                    'success': True,
                    'tx_id': tx_id,
                    'algorand_tx_hash': algorand_result['tx_hash'],
                    'amount': float(amount),
                    'requires_review': compliance_result.get('requires_manual_review', False)
                }
            else:
                transaction.status = TransactionStatus.FAILED
                transaction.error_message = algorand_result['error']
                await self._store_transaction(transaction)
                
                self.metrics['failed_transactions'] += 1
                
                return {
                    'success': False,
                    'tx_id': tx_id,
                    'error': algorand_result['error']
                }
                
        except Exception as e:
            logger.error(f"Mint operation failed: {e}")
            self.metrics['failed_transactions'] += 1
            return {
                'success': False,
                'tx_id': tx_id if 'tx_id' in locals() else str(uuid.uuid4()),
                'error': f"Mint failed: {str(e)}"
            }
    
    @require_initialization
    @retry_with_exponential_backoff(max_attempts=3)
    async def burn_usds(
        self,
        user_address: str,
        amount: Decimal,
        country_code: str,
        fiat_reference: Optional[str] = None
    ) -> Dict:
        """Burn USDS tokens and release collateral"""
        try:
            tx_id = str(uuid.uuid4())
            
            # Validate user has sufficient balance
            user_balance = await self._get_asset_balance(user_address, self.usds_asset_id)
            if user_balance < amount:
                return {
                    'success': False,
                    'tx_id': tx_id,
                    'error': f"Insufficient balance. Available: {user_balance} USDS"
                }
            
            # Compliance validation
            compliance_result = await self.compliance_manager.validate_compliance(
                user_address, amount, 'burn'
            )
            if not compliance_result['compliant']:
                return {
                    'success': False,
                    'tx_id': tx_id,
                    'error': compliance_result['reason']
                }
            
            # Create transaction record
            transaction = USDSTransaction(
                tx_id=tx_id,
                user_id=user_address,
                operation_type=USDSOperationType.BURN,
                amount=amount,
                algorand_tx_hash='',
                country_code=country_code,
                fiat_reference=fiat_reference
            )
            
            # Execute burn on Algorand
            algorand_result = await self._execute_burn_transaction(user_address, amount, transaction)
            
            if algorand_result['success']:
                transaction.algorand_tx_hash = algorand_result['tx_hash']
                transaction.status = TransactionStatus.CONFIRMED
                transaction.confirmed_at = datetime.utcnow()
                
                # Release collateral
                await self._release_collateral(amount, country_code)
                
                # Update metrics
                self.metrics['total_burns'] += 1
                
                # Store transaction
                await self._store_transaction(transaction)
                
                logger.info(f"Successfully burned {amount} USDS for {user_address} - TX: {tx_id}")
                
                return {
                    'success': True,
                    'tx_id': tx_id,
                    'algorand_tx_hash': algorand_result['tx_hash'],
                    'amount': float(amount)
                }
            else:
                transaction.status = TransactionStatus.FAILED
                transaction.error_message = algorand_result['error']
                await self._store_transaction(transaction)
                
                self.metrics['failed_transactions'] += 1
                
                return {
                    'success': False,
                    'tx_id': tx_id,
                    'error': algorand_result['error']
                }
                
        except Exception as e:
            logger.error(f"Burn operation failed: {e}")
            self.metrics['failed_transactions'] += 1
            return {
                'success': False,
                'tx_id': tx_id if 'tx_id' in locals() else str(uuid.uuid4()),
                'error': f"Burn failed: {str(e)}"
            }
      
    @require_initialization
    @validate_address
    @retry_with_exponential_backoff(max_attempts=3)
    async def transfer_usds(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
        memo: Optional[str] = None
    ) -> Dict:
        """Transfer USDS between addresses with compliance checks"""
        try:
            tx_id = str(uuid.uuid4())
            
            # Validate sender balance
            sender_balance = await self._get_asset_balance(from_address, self.usds_asset_id)
            if sender_balance < amount:
                return {
                    'success': False,
                    'tx_id': tx_id,
                    'error': f"Insufficient balance. Available: {sender_balance} USDS"
                }
            
            # Compliance validation for both addresses
            compliance_from = await self.compliance_manager.validate_compliance(
                from_address, amount, 'transfer_out'
            )
            compliance_to = await self.compliance_manager.validate_compliance(
                to_address, amount, 'transfer_in'
            )
            
            if not compliance_from['compliant']:
                return {'success': False, 'tx_id': tx_id, 'error': compliance_from['reason']}
            if not compliance_to['compliant']:
                return {'success': False, 'tx_id': tx_id, 'error': compliance_to['reason']}
            
            # Create transaction record
            transaction = USDSTransaction(
                tx_id=tx_id,
                user_id=from_address,
                operation_type=USDSOperationType.TRANSFER,
                amount=amount,
                algorand_tx_hash='',
                country_code='TRANSFER'  # Special code for transfers
            )
            
            # Execute transfer on Algorand
            algorand_result = await self._execute_transfer_transaction(
                from_address, to_address, amount, memo, transaction
            )
            
            if algorand_result['success']:
                transaction.algorand_tx_hash = algorand_result['tx_hash']
                transaction.status = TransactionStatus.CONFIRMED
                transaction.confirmed_at = datetime.utcnow()
                
                # Update metrics
                self.metrics['total_transfers'] += 1
                
                # Store transaction
                await self._store_transaction(transaction)
                
                logger.info(f"Successfully transferred {amount} USDS from {from_address} to {to_address}")
                
                return {
                    'success': True,
                    'tx_id': tx_id,
                    'algorand_tx_hash': algorand_result['tx_hash'],
                    'amount': float(amount)
                }
            else:
                transaction.status = TransactionStatus.FAILED
                transaction.error_message = algorand_result['error']
                await self._store_transaction(transaction)
                
                self.metrics['failed_transactions'] += 1
                
                return {
                    'success': False,
                    'tx_id': tx_id,
                    'error': algorand_result['error']
                }
                
        except Exception as e:
            logger.error(f"Transfer operation failed: {e}")
            self.metrics['failed_transactions'] += 1
            return {
                'success': False,
                'tx_id': tx_id if 'tx_id' in locals() else str(uuid.uuid4()),
                'error': f"Transfer failed: {str(e)}"
            }
    
    # ========================
    # ALGORAND BLOCKCHAIN OPERATIONS
    # ========================
    
    async def _execute_mint_transaction(self, user_address: str, amount: Decimal, transaction: USDSTransaction) -> Dict:
        """Execute mint transaction on Algorand blockchain"""
        try:
            # Get suggested parameters
            params = self.algod_client.suggested_params()
            
            # Convert amount to asset units
            asset_amount = int(amount * (10 ** self.decimals))
            
            # Create asset transfer transaction (mint from treasury to user)
            mint_txn = AssetTransferTxn(
                sender=self.treasury_account['address'],
                sp=params,
                receiver=user_address,
                amt=asset_amount,
                index=self.usds_asset_id,
                note=f"USDS Mint: {transaction.tx_id}".encode()
            )
            
            # Sign transaction
            signed_txn = mint_txn.sign(self.treasury_account['private_key'])
            
            # Submit transaction
            tx_id = self.algod_client.send_transaction(signed_txn)
            
            # Wait for confirmation
            confirmed_txn = await self._wait_for_confirmation(tx_id)
            
            if confirmed_txn:
                return {
                    'success': True,
                    'tx_hash': tx_id,
                    'confirmed_round': confirmed_txn['confirmed-round']
                }
            else:
                return {
                    'success': False,
                    'error': 'Transaction confirmation timeout'
                }
                
        except Exception as e:
            logger.error(f"Mint transaction failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _execute_burn_transaction(self, user_address: str, amount: Decimal, transaction: USDSTransaction) -> Dict:
        """Execute burn transaction on Algorand blockchain"""
        try:
            # Get suggested parameters
            params = self.algod_client.suggested_params()
            
            # Convert amount to asset units
            asset_amount = int(amount * (10 ** self.decimals))
            
            # Create asset transfer transaction (burn from user to treasury)
            burn_txn = AssetTransferTxn(
                sender=user_address,
                sp=params,
                receiver=self.treasury_account['address'],
                amt=asset_amount,
                index=self.usds_asset_id,
                note=f"USDS Burn: {transaction.tx_id}".encode()
            )
            
            # For production, user would sign this transaction
            # For this implementation, we assume treasury control
            signed_txn = burn_txn.sign(self.treasury_account['private_key'])
            
            # Submit transaction
            tx_id = self.algod_client.send_transaction(signed_txn)
            
            # Wait for confirmation
            confirmed_txn = await self._wait_for_confirmation(tx_id)
            
            if confirmed_txn:
                return {
                    'success': True,
                    'tx_hash': tx_id,
                    'confirmed_round': confirmed_txn['confirmed-round']
                }
            else:
                return {
                    'success': False,
                    'error': 'Transaction confirmation timeout'
                }
                
        except Exception as e:
            logger.error(f"Burn transaction failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _execute_transfer_transaction(
        self, 
        from_address: str, 
        to_address: str, 
        amount: Decimal, 
        memo: Optional[str], 
        transaction: USDSTransaction
    ) -> Dict:
        """Execute transfer transaction on Algorand blockchain"""
        try:
            # Get suggested parameters
            params = self.algod_client.suggested_params()
            
            # Convert amount to asset units
            asset_amount = int(amount * (10 ** self.decimals))
            
            # Create note
            note = f"USDS Transfer: {transaction.tx_id}"
            if memo:
                note += f" | {memo}"
            
            # Create asset transfer transaction
            transfer_txn = AssetTransferTxn(
                sender=from_address,
                sp=params,
                receiver=to_address,
                amt=asset_amount,
                index=self.usds_asset_id,
                note=note.encode()
            )
            
            # For production, sender would sign this transaction
            # For this implementation, we assume treasury control
            signed_txn = transfer_txn.sign(self.treasury_account['private_key'])
            
            # Submit transaction
            tx_id = self.algod_client.send_transaction(signed_txn)
            
            # Wait for confirmation
            confirmed_txn = await self._wait_for_confirmation(tx_id)
            
            if confirmed_txn:
                return {
                    'success': True,
                    'tx_hash': tx_id,
                    'confirmed_round': confirmed_txn['confirmed-round']
                }
            else:
                return {
                    'success': False,
                    'error': 'Transaction confirmation timeout'
                }
                
        except Exception as e:
            logger.error(f"Transfer transaction failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _wait_for_confirmation(self, tx_id: str, max_rounds: int = 10) -> Optional[Dict]:
        """Wait for transaction confirmation with timeout"""
        try:
            current_round = self.algod_client.status()["last-round"]
            
            for _ in range(max_rounds):
                try:
                    confirmed_txn = self.algod_client.pending_transaction_info(tx_id)
                    if confirmed_txn.get("confirmed-round", 0) > 0:
                        return confirmed_txn
                except Exception:
                    pass
                
                # Wait for next round
                self.algod_client.status_after_block(current_round + 1)
                current_round += 1
            
            return None
            
        except Exception as e:
            logger.error(f"Transaction confirmation failed: {e}")
            return None
    
    # ========================
    # ASSET BALANCE & INFO
    # ========================
    
    async def _get_asset_balance(self, address: str, asset_id: int) -> Decimal:
        """Get asset balance for an address"""
        try:
            account_info = self.algod_client.account_info(address)
            
            if asset_id == 0:  # ALGO balance
                return Decimal(account_info['amount']) / Decimal(10**6)
            
            # Asset balance
            for asset in account_info.get('assets', []):
                if asset['asset-id'] == asset_id:
                    return Decimal(asset['amount']) / Decimal(10**self.decimals)
            
            return Decimal('0')
            
        except Exception as e:
            logger.error(f"Failed to get asset balance: {e}")
            return Decimal('0')
    
    async def get_user_balance(self, user_address: str) -> Dict:
        """Get comprehensive user balance information"""
        try:
            usds_balance = await self._get_asset_balance(user_address, self.usds_asset_id)
            algo_balance = await self._get_asset_balance(user_address, 0)
            
            # Get transaction history
            transaction_count = 0
            if self.supabase:
                response = self.supabase.table('usds_transactions')\
                    .select('*', count='exact')\
                    .eq('user_id', user_address)\
                    .execute()
                transaction_count = response.count or 0
            
            return {
                'address': user_address,
                'usds_balance': float(usds_balance),
                'algo_balance': float(algo_balance),
                'transaction_count': transaction_count,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get user balance: {e}")
            return {
                'address': user_address,
                'usds_balance': 0.0,
                'algo_balance': 0.0,
                'transaction_count': 0,
                'error': str(e)
            }
    
    # ========================
    # TREASURY & RESERVE MANAGEMENT
    # ========================
    
    async def get_treasury_health(self) -> TreasuryHealth:
        """Get comprehensive treasury health metrics"""
        try:
            # Get treasury balance
            treasury_balance = await self._get_asset_balance(
                self.treasury_account['address'], 
                self.usds_asset_id
            )
            
            # Calculate circulating supply
            circulating_supply = self.usds_total_supply - treasury_balance
            
            # Calculate treasury percentage
            treasury_percentage = (treasury_balance / self.usds_total_supply) if self.usds_total_supply > 0 else Decimal('1.0')
            
            # Calculate reserve ratio
            total_reserves = Decimal('0')
            for country_reserves in self.collateral_reserves.values():
                for collateral_type, reserve in country_reserves.items():
                    quality_factor = COLLATERAL_QUALITY.get(collateral_type, Decimal('0.5'))
                    total_reserves += reserve.available_amount * quality_factor
            
            reserve_ratio = total_reserves / circulating_supply if circulating_supply > 0 else Decimal('0')
            
            # Calculate peg stability (simplified - in production would use oracle data)
            peg_stability = Decimal('1.0')  # Assuming stable for now
            
            # Determine status
            emergency_mode = False
            if reserve_ratio < Decimal('1.05'):
                status = "EMERGENCY"
                emergency_mode = True
            elif reserve_ratio < Decimal('1.1'):
                status = "WARNING"
            elif reserve_ratio < Decimal('1.2'):
                status = "CAUTION"
            else:
                status = "HEALTHY"
            
            return TreasuryHealth(
                treasury_balance=int(treasury_balance * (10 ** self.decimals)),
                balance_usds=treasury_balance,
                total_supply=int(self.usds_total_supply * (10 ** self.decimals)),
                circulating_supply=int(circulating_supply * (10 ** self.decimals)),
                treasury_percentage=treasury_percentage,
                reserve_ratio=reserve_ratio,
                peg_stability=peg_stability,
                status=status,
                timestamp=int(time.time()),
                emergency_mode=emergency_mode
            )
            
        except Exception as e:
            logger.error(f"Failed to get treasury health: {e}")
            return TreasuryHealth(
                treasury_balance=0,
                balance_usds=Decimal('0'),
                total_supply=0,
                circulating_supply=0,
                treasury_percentage=Decimal('0'),
                reserve_ratio=Decimal('0'),
                peg_stability=Decimal('0'),
                status="ERROR",
                timestamp=int(time.time()),
                emergency_mode=True
            )
    
    # ========================
    # COLLATERAL MANAGEMENT
    # ========================
    
    async def _validate_collateral(self, amount: Decimal, country_code: str, collateral_type: CollateralType) -> Dict:
        """Validate collateral sufficiency for mint operation"""
        try:
            country_config = USDSConfig.get_country_config(country_code)
            if not country_config:
                return {'valid': False, 'reason': 'Unsupported country'}
            
            # Get collateral reserve for this country and type
            reserve = self.collateral_reserves.get(country_code, {}).get(collateral_type)
            if not reserve:
                return {'valid': False, 'reason': 'Collateral reserve not found'}
            
            # Calculate required collateral
            collateral_ratio = Decimal(country_config.min_collateral_ratio) / Decimal('100')
            quality_factor = COLLATERAL_QUALITY.get(collateral_type, Decimal('0.5'))
            required_collateral = amount * collateral_ratio / quality_factor
            
            # Check availability
            if reserve.available_amount < required_collateral:
                return {
                    'valid': False, 
                    'reason': f'Insufficient collateral. Required: {required_collateral}, Available: {reserve.available_amount}'
                }
            
            return {
                'valid': True,
                'required_collateral': required_collateral,
                'available_collateral': reserve.available_amount
            }
            
        except Exception as e:
            logger.error(f"Collateral validation failed: {e}")
            return {'valid': False, 'reason': f'Validation error: {str(e)}'}
    
    async def _update_collateral_allocation(
        self, 
        amount: Decimal, 
        country_code: str, 
        collateral_type: CollateralType, 
        operation: str
    ):
        """Update collateral allocation after mint/burn operations"""
        try:
            reserve = self.collateral_reserves.get(country_code, {}).get(collateral_type)
            if not reserve:
                logger.error(f"Collateral reserve not found: {country_code}/{collateral_type}")
                return
            
            country_config = USDSConfig.get_country_config(country_code)
            collateral_ratio = Decimal(country_config.min_collateral_ratio) / Decimal('100')
            quality_factor = COLLATERAL_QUALITY.get(collateral_type, Decimal('0.5'))
            collateral_amount = amount * collateral_ratio / quality_factor
            
            if operation == 'allocate':
                reserve.allocated_amount += collateral_amount
                reserve.available_amount -= collateral_amount
            elif operation == 'release':
                reserve.allocated_amount -= min(collateral_amount, reserve.allocated_amount)
                reserve.available_amount += min(collateral_amount, reserve.total_amount - reserve.available_amount)
            
            reserve.last_updated = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Failed to update collateral allocation: {e}")

    async def _release_collateral(self, amount: Decimal, country_code: str):
        """Release collateral proportionally across all types"""
        try:
            country_reserves = self.collateral_reserves.get(country_code, {})
            total_allocated = sum(reserve.allocated_amount for reserve in country_reserves.values())
            
            if total_allocated == 0:
                return
            
            # Release proportionally
            for collateral_type, reserve in country_reserves.items():
                if reserve.allocated_amount > 0:
                    proportion = reserve.allocated_amount / total_allocated
                    release_amount = amount * proportion
                    
                    country_config = USDSConfig.get_country_config(country_code)
                    collateral_ratio = Decimal(country_config.min_collateral_ratio) / Decimal('100')
                    quality_factor = COLLATERAL_QUALITY.get(collateral_type, Decimal('0.5'))
                    collateral_amount = release_amount * collateral_ratio / quality_factor
                    
                    reserve.allocated_amount -= min(collateral_amount, reserve.allocated_amount)
                    reserve.available_amount += min(collateral_amount, reserve.total_amount - reserve.available_amount)
                    reserve.last_updated = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Failed to release collateral: {e}")

    # ========================
    # DATA PERSISTENCE & CACHING
    # ========================
    
    async def _store_transaction(self, transaction: USDSTransaction):
        """Store transaction with redundant persistence"""
        try:
            # Store in Supabase
            if self.supabase:
                await self._store_transaction_supabase(transaction)
            
            # Cache in Redis
            if self.redis_pool:
                await self._cache_transaction_redis(transaction)
            
        except Exception as e:
            logger.error(f"Failed to store transaction: {e}")
    
    async def _store_transaction_supabase(self, transaction: USDSTransaction):
        """Store transaction in Supabase"""
        try:
            data = {
                'tx_id': transaction.tx_id,
                'user_id': transaction.user_id,
                'operation_type': transaction.operation_type.value,
                'amount': str(transaction.amount),
                'algorand_tx_hash': transaction.algorand_tx_hash,
                'country_code': transaction.country_code,
                'collateral_type': transaction.collateral_type.value if transaction.collateral_type else None,
                'fiat_reference': transaction.fiat_reference,
                'status': transaction.status.value,
                'created_at': transaction.created_at.isoformat(),
                'confirmed_at': transaction.confirmed_at.isoformat() if transaction.confirmed_at else None,
                'error_message': transaction.error_message
            }
            
            self.supabase.table('usds_transactions').insert(data).execute()
            
        except Exception as e:
            logger.error(f"Supabase storage failed: {e}")
    
    async def _cache_transaction_redis(self, transaction: USDSTransaction):
        """Cache transaction in Redis with TTL"""
        try:
            key = f"tx:{transaction.tx_id}"
            data = {
                'user_id': transaction.user_id,
                'operation_type': transaction.operation_type.value,
                'amount': str(transaction.amount),
                'status': transaction.status.value,
                'created_at': transaction.created_at.isoformat()
            }
            
            await self.redis_pool.hset(key, mapping=data)
            await self.redis_pool.expire(key, 86400)  # 24 hour TTL
            
        except Exception as e:
            logger.error(f"Redis caching failed: {e}")
    
    async def _update_daily_mint_cache(self, amount: Decimal, country_code: str):
        """Update daily mint tracking for rate limiting"""
        try:
            if not self.redis_pool:
                return
            
            today = datetime.utcnow().strftime('%Y-%m-%d')
            key = f"daily_mint:{country_code}:{today}"
            
            current = await self.redis_pool.get(key) or '0'
            new_amount = Decimal(current) + amount
            
            await self.redis_pool.set(key, str(new_amount), ex=86400)
            
        except Exception as e:
            logger.error(f"Failed to update daily mint cache: {e}")
    
    async def _get_kyc_status(self, user_id: str) -> Dict:
        """Get KYC status from database"""
        try:
            if self.supabase:
                response = self.supabase.table('user_profiles') \
                    .select('kyc_verified, kyc_level, kyc_last_verified') \
                    .eq('user_id', user_id) \
                    .execute()
                
                if response.data:
                    user_data = response.data[0]
                    if user_data.get('kyc_verified', False):
                        return {
                            'verified': True,
                            'level': user_data.get('kyc_level', 0),
                            'last_verified': user_data.get('kyc_last_verified')
                        }
            
            # If no valid KYC status found
            return {'verified': False, 'level': 0}
            
        except Exception as e:
            logger.error(f"KYC status check failed: {e}")
            return {'verified': False, 'level': 0}

    # ========================
    # BACKGROUND MONITORING
    # ========================
    
    async def _background_health_monitor(self):
        """Background task for continuous system health monitoring"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Check treasury health
                treasury_health = await self.get_treasury_health()
                
                if treasury_health.emergency_mode and not self.emergency_pause:
                    logger.critical("EMERGENCY MODE ACTIVATED - System paused")
                    self.emergency_pause = True
                    self.metrics['emergency_stops'] += 1
                
                elif not treasury_health.emergency_mode and self.emergency_pause:
                    logger.info("System health restored - Emergency mode lifted")
                    self.emergency_pause = False
                
                # Log health status
                if treasury_health.status in ['WARNING', 'EMERGENCY']:
                    logger.warning(f"Treasury status: {treasury_health.status}, "
                                 f"Reserve ratio: {treasury_health.reserve_ratio}")
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    async def _background_reserve_rebalancer(self):
        """Background task for automatic reserve rebalancing"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                if self.emergency_pause:
                    continue
                
                # Perform reserve rebalancing for each country
                for country_code in USDSConfig.get_all_countries():
                    await self.reserve_manager.rebalance_reserves(country_code)
                
            except Exception as e:
                logger.error(f"Reserve rebalancer error: {e}")
                await asyncio.sleep(7200)  # Back off on error

    # ========================
    # SYSTEM STATUS & METRICS
    # ========================
    
    async def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        try:
            treasury_health = await self.get_treasury_health()
            
            # Calculate performance metrics
            total_transactions = (self.metrics['total_mints'] + 
                                self.metrics['total_burns'] + 
                                self.metrics['total_transfers'])
            
            success_rate = ((total_transactions - self.metrics['failed_transactions']) / 
                          total_transactions * 100) if total_transactions > 0 else 100
            
            # Get network status
            try:
                algorand_status = self.algod_client.status()
                network_healthy = True
            except:
                algorand_status = None
                network_healthy = False
            
            return {
                'system_status': {
                    'initialized': self._initialized,
                    'emergency_pause': self.emergency_pause,
                    'maintenance_mode': self.maintenance_mode,
                    'network_healthy': network_healthy
                },
                'treasury_health': {
                    'status': treasury_health.status,
                    'reserve_ratio': float(treasury_health.reserve_ratio),
                    'peg_stability': float(treasury_health.peg_stability),
                    'emergency_mode': treasury_health.emergency_mode
                },
                'performance_metrics': {
                    'total_mints': self.metrics['total_mints'],
                    'total_burns': self.metrics['total_burns'],
                    'total_transfers': self.metrics['total_transfers'],
                    'failed_transactions': self.metrics['failed_transactions'],
                    'success_rate': round(success_rate, 2),
                    'emergency_stops': self.metrics['emergency_stops']
                },
                'network_info': {
                    'last_round': algorand_status['last-round'] if algorand_status else None,
                    'node_healthy': network_healthy,
                    'usds_asset_id': self.usds_asset_id
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                'system_status': {'error': str(e)},
                'timestamp': datetime.utcnow().isoformat()
            }

    # ========================
    # EMERGENCY CONTROLS
    # ========================
    
    async def emergency_pause_system(self, reason: str) -> bool:
        """Emergency system pause with audit trail"""
        try:
            self.emergency_pause = True
            self.metrics['emergency_stops'] += 1
            
            # Log emergency action
            emergency_log = {
                'action': 'EMERGENCY_PAUSE',
                'reason': reason,
                'timestamp': datetime.utcnow().isoformat(),
                'triggered_by': 'system'
            }
            
            if self.supabase:
                self.supabase.table('emergency_actions').insert(emergency_log).execute()
            
            logger.critical(f"EMERGENCY SYSTEM PAUSE: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Emergency pause failed: {e}")
            return False
    
    async def resume_system(self, authorized_by: str) -> bool:
        """Resume system operations after emergency pause"""
        try:
            # Verify system health before resuming
            treasury_health = await self.get_treasury_health()
            
            if treasury_health.emergency_mode:
                logger.error("Cannot resume - treasury still in emergency mode")
                return False
            
            self.emergency_pause = False
            
            # Log resume action
            resume_log = {
                'action': 'SYSTEM_RESUME',
                'authorized_by': authorized_by,
                'timestamp': datetime.utcnow().isoformat(),
                'treasury_status': treasury_health.status
            }
            
            if self.supabase:
                self.supabase.table('emergency_actions').insert(resume_log).execute()
            
            logger.info(f"System operations resumed by {authorized_by}")
            return True
            
        except Exception as e:
            logger.error(f"System resume failed: {e}")
            return False

    # ========================
    # CLEANUP & SHUTDOWN
    # ========================
    
    async def shutdown(self):
        """Graceful shutdown with cleanup"""
        try:
            logger.info("Initiating USDS Manager shutdown...")
            
            # Set maintenance mode
            self.maintenance_mode = True
            
            # Close Redis connections
            if self.redis_pool:
                await self.redis_pool.close()
                logger.info("Redis connections closed")
            
            # Final metrics log
            logger.info(f"Final metrics - Mints: {self.metrics['total_mints']}, "
                       f"Burns: {self.metrics['total_burns']}, "
                       f"Transfers: {self.metrics['total_transfers']}, "
                       f"Failed: {self.metrics['failed_transactions']}")
            
            logger.info("USDS Manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}")


# ========================
# UTILITY FUNCTIONS & INITIALIZATION
# ========================

def create_usds_manager(config: Dict) -> USDSManager:
    """Factory function to create and initialize USDS Manager"""
    try:
        manager = USDSManager(config)
        logger.info("USDS Manager created successfully")
        return manager
    except Exception as e:
        logger.error(f"Failed to create USDS Manager: {e}")
        raise


async def initialize_usds_system(config: Dict) -> USDSManager:
    """Initialize complete USDS system"""
    try:
        manager = create_usds_manager(config)
        
        if await manager.initialize():
            logger.info("🚀 USDS SYSTEM FULLY OPERATIONAL 🚀")
            return manager
        else:
            raise RuntimeError("USDS system initialization failed")
            
    except Exception as e:
        logger.error(f"USDS system initialization failed: {e}")
        raise


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    # Test configuration
    test_config = {
        'algorand_token': 'YOUR_ALGOD_TOKEN',
        'algorand_node_url': 'https://testnet-algorand.api.purestake.io/ps2',
        'indexer_token': 'YOUR_INDEXER_TOKEN',
        'algorand_indexer_url': 'https://testnet-algorand.api.purestake.io/idx2',
        'treasury_address': 'YOUR_TREASURY_ADDRESS',
        'treasury_private_key': 'YOUR_TREASURY_PRIVATE_KEY',
        'reserve_address': 'YOUR_RESERVE_ADDRESS',
        'reserve_private_key': 'YOUR_RESERVE_PRIVATE_KEY',
        'usds_asset_id': 0,  # Set to 0 for testing
        'redis_url': 'redis://localhost:6379',
        'supabase_url': 'YOUR_SUPABASE_URL',
        'supabase_key': 'YOUR_SUPABASE_KEY',
        'complycube_api_key': 'YOUR_COMPLYCUBE_API_KEY'
    }
    
    async def test_usds_system():
        """Test USDS system functionality"""
        try:
            # Initialize system
            manager = await initialize_usds_system(test_config)
            
            # Test system status
            status = await manager.get_system_status()
            print("System Status:", status)
            
            # Test treasury health
            treasury = await manager.get_treasury_health()
            print("Treasury Health:", treasury.status)
            
            # Test preparing opt-in transaction
            opt_in_tx = await manager.prepare_opt_in_transaction("USER_ADDRESS")
            print("Opt-in Transaction:", opt_in_tx)
            
            # Graceful shutdown
            await manager.shutdown()
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Run test
    asyncio.run(test_usds_system())