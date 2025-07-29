"""
Seamount.io Unified P2P & Cross-Border Payment Engine
Location: /payments/seamount_payment_engine.py
"""

import asyncio
import logging
import os
import json
import functools
import time
import base64
import qrcode
from decimal import Decimal
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
from datetime import datetime, timedelta
from algosdk import account
from supabase import create_client, Client
from cryptography.fernet import Fernet
import aioredis
import aiohttp
from io import BytesIO
from PIL import Image

# Add retry decorator
def retry(max_attempts=3, backoff_factor=2):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        # Last attempt failed, re-raise the exception
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise
                    # Calculate backoff time
                    backoff_time = backoff_factor ** attempt
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {backoff_time}s: {e}")
                    await asyncio.sleep(backoff_time)
        return wrapper
    return decorator

# Placeholder for USDSManager until we have the real implementation
class USDSManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize the USDS manager"""
        self.logger.info("USDS Manager initialized")

    async def get_user_balance(self, address):
        """Get user's USDS balance"""
        # Mock implementation
        return {
            'address': address,
            'usds_balance': Decimal('1000.0'),  # Mock balance
            'updated_at': datetime.utcnow()
        }
    
    async def transfer_usds(self, private_key, to_address, amount, currency, memo):
        """Transfer USDS tokens"""
        # Mock implementation
        return f"tx_{int(time.time())}_{hash(to_address) % 1000000}"
    
    async def mint_usds(self, user_id, address, amount, country_code, collateral_type):
        """Mint new USDS tokens"""
        # Mock implementation
        return {
            'tx_hash': f"tx_{int(time.time())}_{hash(address) % 1000000}",
            'amount': float(amount)
        }
    
    async def burn_usds(self, user_id, address, amount, country_code):
        """Burn USDS tokens"""
        # Mock implementation
        return {
            'tx_hash': f"tx_{int(time.time())}_{hash(address) % 1000000}",
            'amount': float(amount)
        }
    
    async def get_collateral_status(self, country_code):
        """Get collateral status for a country"""
        # Mock implementation
        return {
            'ratio': '200%',
            'tier': 'tier_2',
            'min_required': 175
        }

class CollateralType(Enum):
    USD_BANK_RESERVE = "usd_bank_reserve"
    ALGO = "algo"
    USDC = "usdc"

logger = logging.getLogger(__name__)

# ========================
# ENUMS AND DATA STRUCTURES
# ========================
class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"

class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    KES = "KES"
    NGN = "NGN"
    USDS = "USDS"
    ZAR = "ZAR"
    GHS = "GHS"

class PaymentType(Enum):
    P2P_LOCAL = "p2p_local"
    CROSS_BORDER = "cross_border"
    FIAT_DEPOSIT = "fiat_deposit"
    FIAT_WITHDRAWAL = "fiat_withdrawal"
    QR_PAYMENT = "qr_payment"

@dataclass
class ExchangeRate:
    from_currency: str
    to_currency: str
    rate: Decimal
    timestamp: int
    spread: Decimal = Decimal('0.005')
    source: str = "internal"

@dataclass
class PaymentRequest:
    id: str
    payment_type: PaymentType
    sender_address: str
    receiver_address: str
    amount: Decimal
    from_currency: Currency
    to_currency: Currency
    memo: str = ""
    user_id: Optional[str] = None
    created_at: int = None
    expires_at: int = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = int(time.time())
        if not self.expires_at:
            self.expires_at = self.created_at + 3600  # 1 hour expiration

@dataclass
class PaymentResult:
    request_id: str
    status: PaymentStatus
    payment_type: PaymentType
    tx_id: Optional[str] = None
    final_amount: Optional[Decimal] = None
    fees: Optional[Decimal] = None
    exchange_rate: Optional[Decimal] = None
    error_message: Optional[str] = None
    completed_at: Optional[int] = None

@dataclass
class Dispute:
    transaction_id: str
    user_id: str
    reason: str
    status: str = "pending"
    created_at: datetime = None
    resolved_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

# ========================
# PAYMENT PROCESSOR ADAPTER
# ========================
class PaymentProcessor:
    def __init__(self, public_key: str, secret_key: str, encryption_key: str):
        self.public_key = public_key
        self.secret_key = secret_key
        self.encryption_key = encryption_key

    async def initialize_payment(self, amount: int, currency: str, email: str, phone: Optional[str] = None) -> Dict:
        """Initialize fiat payment (stub implementation)"""
        return {
            "status": "success",
            "tx_ref": f"TXREF_{int(time.time())}",
            "payment_link": "https://payment.link"
        }

    async def verify_payment(self, tx_ref: str) -> Dict:
        """Verify payment (stub implementation)"""
        return {
            "verified": True,
            "amount": 100.0
        }

    async def transfer_to_bank(self, amount: int, currency: str, bank_details: Dict) -> Dict:
        """Initiate bank transfer (stub implementation)"""
        return {
            "status": "success",
            "reference": f"WDREF_{int(time.time())}"
        }

# ========================
# CORE PAYMENT ENGINE
# ========================
class SeamountPaymentEngine:
    """Unified P2P and Cross-Border Payment Engine for Seamount.io"""
    
    def __init__(self):
        # Configuration
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost")
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
        
        # Initialize core components
        self.usds_manager = USDSManager({
            'algorand_token': os.getenv("ALGORAND_TOKEN", ""),
            'algorand_node_url': os.getenv("ALGORAND_SERVER", "https://testnet-api.algonode.cloud"),
            'treasury_address': os.getenv("TREASURY_ADDRESS"),
            'treasury_private_key': os.getenv("TREASURY_PRIVATE_KEY"),
            'reserve_address': os.getenv("RESERVE_ADDRESS"),
            'reserve_private_key': os.getenv("RESERVE_PRIVATE_KEY"),
            'supabase_url': self.supabase_url,
            'supabase_key': self.supabase_key,
            'redis_url': self.redis_url
        })
        
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        self.redis = aioredis.from_url(self.redis_url)
        self.payment_processor = PaymentProcessor(
            public_key=os.getenv("FLW_PUBLIC_KEY"),
            secret_key=os.getenv("FLW_SECRET_KEY"),
            encryption_key=os.getenv("FLW_ENCRYPTION_KEY")
        )
        self.fernet = Fernet(self.encryption_key.encode())
        
        # State management
        self.exchange_rates: Dict[str, ExchangeRate] = {}
        self.pending_payments: Dict[str, PaymentRequest] = {}
        self.payment_history: List[PaymentResult] = []
        
        # Fee structure (optimized for low costs)
        self.fee_config = {
            'base_fee_rate': Decimal('0.0005'),  # 0.05%
            'min_fee': Decimal('0.005'),         # $0.005 minimum
            'max_fee': Decimal('5.0'),           # $5 maximum
            'usds_discount': Decimal('0.5'),     # 50% discount for USDS
            'cross_border_premium': Decimal('0.2'),  # 20% premium for cross-border
            'batch_discount': Decimal('0.3'),    # 30% discount for batch
        }
        
        # Initialize exchange rates
        asyncio.create_task(self._initialize_exchange_rates())
        # Start background maintenance
        asyncio.create_task(self.background_maintenance())
    
    async def initialize(self):
        """Initialize the payment engine"""
        await self.usds_manager.initialize()
        logger.info("Seamount Payment Engine initialized")

    # ========================
    # EXCHANGE RATE MANAGEMENT
    # ========================
    async def _initialize_exchange_rates(self):
        """Initialize exchange rates from multiple sources"""
        try:
            # Real-time rates from exchange API
            rates_data = await self._fetch_live_rates()
            
            for rate_info in rates_data:
                rate = ExchangeRate(
                    from_currency=rate_info['from'],
                    to_currency=rate_info['to'],
                    rate=Decimal(str(rate_info['rate'])),
                    timestamp=int(time.time()),
                    source=rate_info.get('source', 'api')
                )
                
                key = f"{rate.from_currency}_{rate.to_currency}"
                self.exchange_rates[key] = rate
                
                # Add reverse rate
                if rate.rate != Decimal('1.0'):
                    reverse_key = f"{rate.to_currency}_{rate.from_currency}"
                    self.exchange_rates[reverse_key] = ExchangeRate(
                        from_currency=rate.to_currency,
                        to_currency=rate.from_currency,
                        rate=Decimal('1') / rate.rate,
                        timestamp=rate.timestamp,
                        source=rate.source
                    )
                    
        except Exception as e:
            logger.error(f"Exchange rate initialization failed: {e}")
            # Fallback to static rates
            await self._load_fallback_rates()
    
    async def _fetch_live_rates(self) -> List[Dict]:
        """Fetch live exchange rates from real APIs"""
        try:
            async with aiohttp.ClientSession() as session:
                # Use multiple data sources for redundancy
                sources = [
                    await self._fetch_fixer_rates(session),
                    await self._fetch_coinbase_rates(session)
                ]
                
                # Merge and validate rates
                merged_rates = {}
                for source_rates in sources:
                    if source_rates:
                        for rate in source_rates:
                            key = f"{rate['from']}_{rate['to']}"
                            if key not in merged_rates:
                                merged_rates[key] = rate
                
                return list(merged_rates.values())
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            return await self._get_fallback_rates()        
        except Exception as e:
            logger.error(f"Live rate fetch failed: {e}")
            return await self._get_fallback_rates()
    
    async def _fetch_fixer_rates(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Fetch rates from Fixer.io API"""
        try:
            api_key = os.getenv("FIXER_API_KEY")
            if not api_key:
                return []
                
            url = f"http://data.fixer.io/api/latest?access_key={api_key}&base=USD"
            async with session.get(url, timeout=5) as response:
                data = await response.json()
                
                if data.get('success'):
                    rates = []
                    for currency, rate in data['rates'].items():
                        if currency in ['EUR', 'GBP', 'KES', 'NGN', 'ZAR', 'GHS']:
                            rates.append({
                                'from': 'USD',
                                'to': currency,
                                'rate': rate,
                                'source': 'fixer'
                            })
                    
                    # Add USDS 1:1 peg
                    rates.append({'from': 'USD', 'to': 'USDS', 'rate': 1.0, 'source': 'internal'})
                    return rates
            return []
        except Exception as e:
            logger.warning(f"Fixer.io API failed: {e}")
            return []
    
    async def _fetch_coinbase_rates(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Fetch rates from Coinbase API"""
        try:
            url = "https://api.coinbase.com/v2/exchange-rates?currency=USD"
            async with session.get(url, timeout=5) as response:
                data = await response.json()
                
                if data.get('data'):
                    rates = []
                    exchange_rates = data['data']['rates']
                    
                    for currency in ['EUR', 'GBP', 'KES', 'NGN', 'ZAR', 'GHS']:
                        if currency in exchange_rates:
                            rates.append({
                                'from': 'USD',
                                'to': currency,
                                'rate': float(exchange_rates[currency]),
                                'source': 'coinbase'
                            })
                    
                    return rates
            return []
        except Exception as e:
            logger.warning(f"Coinbase API failed: {e}")
            return []
    
    async def _get_fallback_rates(self) -> List[Dict]:
        """Get fallback rates when APIs fail"""
        return [
            {'from': 'USD', 'to': 'USDS', 'rate': 1.0, 'source': 'fallback'},
            {'from': 'USD', 'to': 'EUR', 'rate': 0.85, 'source': 'fallback'},
            {'from': 'USD', 'to': 'GBP', 'rate': 0.75, 'source': 'fallback'},
            {'from': 'USD', 'to': 'KES', 'rate': 145.50, 'source': 'fallback'},
            {'from': 'USD', 'to': 'NGN', 'rate': 465.80, 'source': 'fallback'},
            {'from': 'USD', 'to': 'ZAR', 'rate': 18.50, 'source': 'fallback'},
            {'from': 'USD', 'to': 'GHS', 'rate': 12.00, 'source': 'fallback'},
        ]
    
    async def _load_fallback_rates(self):
        """Load fallback exchange rates when API calls fail"""
        fallback_rates = await self._get_fallback_rates()
        for rate_info in fallback_rates:
            key = f"{rate_info['from']}_{rate_info['to']}"
            self.exchange_rates[key] = ExchangeRate(
                from_currency=rate_info['from'],
                to_currency=rate_info['to'],
                rate=Decimal(str(rate_info['rate'])),
                timestamp=int(time.time()),
                source='fallback'
            )

    # ========================
    # SECURITY & ENCRYPTION
    # ========================
    async def _encrypt_private_key(self, private_key: str) -> str:
        """Encrypt private key for storage"""
        try:
            return self.fernet.encrypt(private_key.encode()).decode()
        except Exception as e:
            logger.error(f"Private key encryption failed: {e}")
            raise
    
    async def _decrypt_private_key(self, encrypted_key: str) -> str:
        """Decrypt private key for use"""
        try:            
            return self.fernet.decrypt(encrypted_key.encode()).decode()
        except Exception as e:
            logger.error(f"Private key decryption failed: {e}")
            raise
    
    async def _check_aml(self, address: str) -> bool:
        """Comprehensive AML check"""
        try:
            # Check against Redis blacklist
            if await self.redis.sismember("blacklist:addresses", address):
                logger.warning(f"Address {address} is blacklisted")
                return False
            
            # Check against database blacklist
            blacklisted = self.supabase.table("blacklisted_addresses").select("address").eq("address", address).execute()
            if blacklisted.data:
                logger.warning(f"Address {address} is blacklisted in database")
                return False
            
            # Check transaction velocity
            recent_txns = await self.redis.get(f"velocity:{address}") or "0"
            if int(recent_txns) > 100:  # Max 100 txns per hour
                logger.warning(f"Address {address} exceeds velocity limits")
                return False
            
            return True
        except Exception as e:
            logger.error(f"AML check failed for {address}: {e}")
            return False

    # ========================
    # WALLET MANAGEMENT
    # ========================
    async def create_wallet(self, user_id: str) -> Dict:
        """Create new wallet for user"""
        try:
            address, private_key = account.generate_account()
            encrypted_key = await self._encrypt_private_key(private_key)
            
            await self.supabase.table("users").update({
                "p2p_address": address,
                "encrypted_private_key": encrypted_key,
                "wallet_created_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            
            logger.info(f"Wallet created for user {user_id}: {address}")
            return {"address": address, "status": "created"}
        except Exception as e:
            logger.error(f"Wallet creation failed for user {user_id}: {e}")
            raise

    def get_exchange_rate(self, from_currency: Currency, to_currency: Currency) -> Optional[ExchangeRate]:
        """Get exchange rate between two currencies"""
        key = f"{from_currency.value}_{to_currency.value}"
        if key in self.exchange_rates:
            return self.exchange_rates[key]
        
        # Try reverse lookup with conversion
        reverse_key = f"{to_currency.value}_{from_currency.value}"
        if reverse_key in self.exchange_rates:
            rate = self.exchange_rates[reverse_key]
            return ExchangeRate(
                from_currency=from_currency.value,
                to_currency=to_currency.value,
                rate=Decimal('1') / rate.rate,
                timestamp=rate.timestamp,
                source=f"{rate.source}_inverse"
            )
        return None
        
    # ========================
    # FEE CALCULATION
    # ========================
    async def calculate_fees(self, amount: Decimal, from_currency: Currency,
                           payment_type: PaymentType, is_batch: bool = False) -> Tuple[Decimal, Dict]:
        """Calculate optimized fees for different payment types"""
        try:
            # Base fee calculation
            base_fee = amount * self.fee_config['base_fee_rate']
            base_fee = max(base_fee, self.fee_config['min_fee'])
            base_fee = min(base_fee, self.fee_config['max_fee'])
            
            # Apply modifiers
            final_fee = base_fee
            
            # USDS discount
            if from_currency == Currency.USDS:
                final_fee *= self.fee_config['usds_discount']
            
            # Cross-border premium
            if payment_type == PaymentType.CROSS_BORDER:
                final_fee *= (1 + self.fee_config['cross_border_premium'])
            
            # Batch discount
            if is_batch:
                final_fee *= (1 - self.fee_config['batch_discount'])
            
            # Network congestion adjustment
            network_status = await self._get_network_congestion()
            congestion_multiplier = Decimal('1.2') if network_status > 0.8 else Decimal('1.0')
            final_fee *= congestion_multiplier
            
            breakdown = {
                'base_fee': float(base_fee),
                'currency_discount': float(base_fee - base_fee * self.fee_config.get('usds_discount', 1)) if from_currency == Currency.USDS else 0,
                'cross_border_premium': float(final_fee * self.fee_config['cross_border_premium']) if payment_type == PaymentType.CROSS_BORDER else 0,
                'batch_discount': float(final_fee * self.fee_config['batch_discount']) if is_batch else 0,
                'network_adjustment': float(final_fee * (congestion_multiplier - 1)),
                'total_fee': float(final_fee),
                'effective_rate_percent': float((final_fee / amount) * 100)
            }
            
            return final_fee, breakdown
        except Exception as e:
            logger.error(f"Fee calculation failed: {e}")
            return self.fee_config['min_fee'], {'error': str(e)}
    
    async def _get_network_congestion(self) -> float:
        """Get network congestion level (0.0 - 1.0)"""
        try:
            pending_txns = await self.redis.get("network:pending_txns") or "0"
            return min(float(pending_txns) / 1000, 1.0)
        except:
            return 0.5  # Default moderate congestion

    # ========================
    # PAYMENT OPERATIONS
    # ========================
    async def create_p2p_payment(self, sender_user_id: str, receiver_address: str,
                               amount: Decimal, memo: str = "") -> PaymentRequest:
        """Create P2P local payment"""
        try:
            # Get sender wallet
            sender_data = await self.supabase.table("users").select(
                "p2p_address, kyc_level"
            ).eq("id", sender_user_id).execute()
            
            if not sender_data.data or not sender_data.data[0]["p2p_address"]:
                raise ValueError("Sender wallet not found")
            
            sender_address = sender_data.data[0]["p2p_address"]
            
            # Validate USDS balance
            balance = await self.usds_manager.get_user_balance(sender_address)
            fee, _ = await self.calculate_fees(amount, Currency.USDS, PaymentType.P2P_LOCAL)
            total_needed = amount + fee
            
            if balance['usds_balance'] < total_needed:
                raise ValueError(f"Insufficient balance: {balance['usds_balance']} < {total_needed}")
            
            # Create payment request
            payment_id = f"P2P_{int(time.time())}_{hash((sender_address, receiver_address, float(amount))) % 10000:04d}"
            
            request = PaymentRequest(
                id=payment_id,
                payment_type=PaymentType.P2P_LOCAL,
                sender_address=sender_address,
                receiver_address=receiver_address,
                amount=amount,
                from_currency=Currency.USDS,
                to_currency=Currency.USDS,
                memo=memo,
                user_id=sender_user_id
            )
            
            self.pending_payments[payment_id] = request
            logger.info(f"P2P payment created: {payment_id}")
            
            return request
        except Exception as e:
            logger.error(f"P2P payment creation failed: {e}")
            raise
            
    @retry(max_attempts=3, backoff_factor=2)
    async def execute_p2p_payment(self, payment_id: str) -> PaymentResult:
        """Execute P2P payment"""
        if payment_id not in self.pending_payments:
            return PaymentResult(payment_id, PaymentStatus.FAILED, PaymentType.P2P_LOCAL, 
                               error_message="Payment not found")
        
        request = self.pending_payments[payment_id]
        
        try:
            # Check expiry
            if time.time() > request.expires_at:
                del self.pending_payments[payment_id]
                return PaymentResult(payment_id, PaymentStatus.FAILED, PaymentType.P2P_LOCAL,
                                   error_message="Payment expired")
            
            # AML checks
            if not await self._check_aml(request.sender_address) or not await self._check_aml(request.receiver_address):
                return PaymentResult(payment_id, PaymentStatus.FAILED, PaymentType.P2P_LOCAL,
                                   error_message="AML check failed")
            
            # Get sender private key
            user_data = await self.supabase.table("users").select(
                "encrypted_private_key"
            ).eq("id", request.user_id).execute()
            
            private_key = await self._decrypt_private_key(user_data.data[0]["encrypted_private_key"])
            
            # Calculate fees
            fee, fee_breakdown = await self.calculate_fees(request.amount, Currency.USDS, PaymentType.P2P_LOCAL)
            
            # Execute transfer
            tx_id = await self.usds_manager.transfer_usds(
                private_key,
                request.receiver_address,
                request.amount,
                request.from_currency.value,
                f"P2P: {request.memo}"
            )
            
            # Record transaction
            await self.supabase.table("payment_transactions").insert({
                "payment_id": payment_id,
                "sender_address": request.sender_address,
                "receiver_address": request.receiver_address,
                "amount": float(request.amount),
                "fee": float(fee),
                "tx_id": tx_id,
                "payment_type": PaymentType.P2P_LOCAL.value,
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
            
            # Create result
            result = PaymentResult(
                request_id=payment_id,
                status=PaymentStatus.COMPLETED,
                payment_type=PaymentType.P2P_LOCAL,
                tx_id=tx_id,
                final_amount=request.amount,
                fees=fee,
                completed_at=int(time.time())
            )
            
            # Cleanup
            del self.pending_payments[payment_id]
            self.payment_history.append(result)
            
            # Update metrics
            await self.redis.incr("transactions:p2p:count")
            await self.redis.incrbyfloat("transactions:p2p:volume", float(request.amount))
            
            logger.info(f"P2P payment completed: {payment_id} - TX: {tx_id}")
            return result
        except Exception as e:
            logger.error(f"P2P payment execution failed: {e}")
            return PaymentResult(
                request_id=payment_id,
                status=PaymentStatus.FAILED,
                payment_type=PaymentType.P2P_LOCAL,
                error_message=str(e)
            )

    # ========================
    # CROSS-BORDER PAYMENTS
    # ========================
    async def create_cross_border_payment(self, sender_user_id: str, receiver_address: str,
                                        amount: Decimal, from_currency: Currency,
                                        to_currency: Currency, memo: str = "") -> PaymentRequest:
        """Create cross-border payment"""
        try:
            # Get sender wallet
            sender_data = await self.supabase.table("users").select(
                "p2p_address, kyc_level"
            ).eq("id", sender_user_id).execute()
            
            if not sender_data.data or not sender_data.data[0]["p2p_address"]:
                raise ValueError("Sender wallet not found")
            
            if sender_data.data[0]["kyc_level"] < 2:  # Require higher KYC for cross-border
                raise ValueError("Enhanced KYC verification required for cross-border payments")
            
            sender_address = sender_data.data[0]["p2p_address"]
            
            # Validate exchange rate availability
            rate = self.get_exchange_rate(from_currency, to_currency)
            if not rate:
                raise ValueError(f"Exchange rate unavailable for {from_currency.value} to {to_currency.value}")
            
            # Create payment request
            payment_id = f"XB_{int(time.time())}_{hash((sender_address, receiver_address, float(amount))) % 10000:04d}"
            
            request = PaymentRequest(
                id=payment_id,
                payment_type=PaymentType.CROSS_BORDER,
                sender_address=sender_address,
                receiver_address=receiver_address,
                amount=amount,
                from_currency=from_currency,
                to_currency=to_currency,
                memo=memo,
                user_id=sender_user_id
            )
            
            self.pending_payments[payment_id] = request
            logger.info(f"Cross-border payment created: {payment_id}")
            
            return request
        except Exception as e:
            logger.error(f"Cross-border payment creation failed: {e}")
            raise
    
    async def execute_cross_border_payment(self, payment_id: str) -> PaymentResult:
        """Execute cross-border payment"""
        if payment_id not in self.pending_payments:
            return PaymentResult(payment_id, PaymentStatus.FAILED, PaymentType.CROSS_BORDER,
                               error_message="Payment not found")
        
        request = self.pending_payments[payment_id]
        
        try:
            # Get exchange rate
            rate = self.get_exchange_rate(request.from_currency, request.to_currency)
            if not rate:
                return PaymentResult(payment_id, PaymentStatus.FAILED, PaymentType.CROSS_BORDER,
                                   error_message="Exchange rate unavailable")
            
            # Get sender private key
            user_data = await self.supabase.table("users").select(
                "encrypted_private_key"
            ).eq("id", request.user_id).execute()
            
            private_key = await self._decrypt_private_key(user_data.data[0]["encrypted_private_key"])
            
            # Calculate fees
            fee, fee_breakdown = await self.calculate_fees(request.amount, request.from_currency, PaymentType.CROSS_BORDER)
            
            # Convert to USDS for transfer
            if request.from_currency == Currency.USDS:
                final_amount = request.amount - fee
            else:
                usd_equivalent = request.amount / rate.rate if rate.rate != Decimal('1.0') else request.amount
                final_amount = usd_equivalent - fee
            
            # Execute transfer
            tx_id = await self.usds_manager.transfer_usds(
                private_key,
                request.receiver_address,
                final_amount,
                request.to_currency.value,
                f"Cross-border: {request.from_currency.value}→{request.to_currency.value}: {request.memo}"
            )
            
            # Record transaction
            await self.supabase.table("payment_transactions").insert({
                "payment_id": payment_id,
                "sender_address": request.sender_address,
                "receiver_address": request.receiver_address,
                "amount": float(request.amount),
                "final_amount": float(final_amount),
                "fee": float(fee),
                "exchange_rate": float(rate.rate),
                "from_currency": request.from_currency.value,
                "to_currency": request.to_currency.value,
                "tx_id": tx_id,
                "payment_type": PaymentType.CROSS_BORDER.value,
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
            
            # Create result
            result = PaymentResult(
                request_id=payment_id,
                status=PaymentStatus.COMPLETED,
                payment_type=PaymentType.CROSS_BORDER,
                tx_id=tx_id,
                final_amount=final_amount,
                fees=fee,
                exchange_rate=rate.rate,
                completed_at=int(time.time())
            )
            
            # Cleanup and metrics
            del self.pending_payments[payment_id]
            self.payment_history.append(result)
            
            await self.redis.incr("transactions:cross_border:count")
            await self.redis.incrbyfloat("transactions:cross_border:volume", float(request.amount))
            
            logger.info(f"Cross-border payment completed: {payment_id} - TX: {tx_id}")
            return result
        except Exception as e:
            logger.error(f"Cross-border payment execution failed: {e}")
            return PaymentResult(
                request_id=payment_id,
                status=PaymentStatus.FAILED,
                payment_type=PaymentType.CROSS_BORDER,
                error_message=str(e)
            )

    # ========================
    # FIAT INTEGRATION
    # ========================
    async def deposit_fiat(self, user_id: str, amount_usd: float, email: str, phone: Optional[str] = None) -> Dict:
        """Deposit fiat currency and mint USDS"""
        try:
            # Get user data
            user_data = await self.supabase.table("users").select(
                "p2p_address, kyc_level"
            ).eq("id", user_id).execute()
            
            if not user_data.data or not user_data.data[0]["p2p_address"]:
                raise ValueError("User wallet not found")
            
            if user_data.data[0]["kyc_level"] == 0:
                raise ValueError("KYC verification required")
            
            # Initialize payment
            payment_result = await self.payment_processor.initialize_payment(
                amount=int(amount_usd * 100),  # Convert to cents
                currency="USD",
                email=email,
                phone=phone,
            )
            
            if payment_result["status"] != "success":
                raise ValueError("Payment initialization failed")
            
            # Verify payment
            verification = await self.payment_processor.verify_payment(payment_result["tx_ref"])
            if not verification["verified"]:
                raise ValueError("Payment verification failed")
            
            # Mint USDS
            amount_usds = Decimal(str(verification["amount"]))
            mint_result = await self.usds_manager.mint_usds(
                user_id, 
                user_data.data[0]["p2p_address"],
                amount_usds,
                "ZA",  # Default country code
                CollateralType.USD_BANK_RESERVE
            )
          
            # Record deposit
            await self.supabase.table("fiat_transactions").insert({
                "user_id": user_id,
                "transaction_type": "deposit",
                "amount_usd": float(amount_usds),
                "amount_usds": float(amount_usds),
                "tx_ref": payment_result["tx_ref"],
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(f"Fiat deposit completed for user {user_id}: ${amount_usds}")
            return {
                "status": "success",
                "amount_deposited": float(amount_usds),
                "usds_minted": float(amount_usds),
                "tx_ref": payment_result["tx_ref"]
            }
        except Exception as e:
            logger.error(f"Fiat deposit failed for user {user_id}: {e}")
            raise
    
    async def withdraw_fiat(self, user_id: str, amount_usds: Decimal, bank_details: Dict) -> Dict:
        """Withdraw USDS to fiat currency"""
        try:
            # Get user data
            user_data = await self.supabase.table("users").select(
                "p2p_address, encrypted_private_key, kyc_level"
            ).eq("id", user_id).execute()
            
            if not user_data.data or user_data.data[0]["kyc_level"] < 2:
                raise ValueError("Enhanced KYC required for fiat withdrawal")
            
            # Check USDS balance
            balance = await self.usds_manager.get_user_balance(user_data.data[0]["p2p_address"])
            if balance['usds_balance'] < amount_usds:
                raise ValueError("Insufficient USDS balance")
            
            # Calculate withdrawal fee
            fee, _ = await self.calculate_fees(amount_usds, Currency.USDS, PaymentType.FIAT_WITHDRAWAL)
            net_amount = amount_usds - fee
            
            # Burn USDS
            burn_result = await self.usds_manager.burn_usds(
                user_id,
                user_data.data[0]["p2p_address"],
                amount_usds,
                "ZA"  # Default country code
            )
            
            # Process bank transfer
            transfer_result = await self.payment_processor.transfer_to_bank(
                amount=int(net_amount * 100),  # Convert to cents
                currency="USD",
                bank_details=bank_details
            )
            
            # Record withdrawal
            await self.supabase.table("fiat_transactions").insert({
                "user_id": user_id,
                "transaction_type": "withdrawal",
                "amount_usd": float(net_amount),
                "amount_usds": float(amount_usds),
                "fee": float(fee),
                "bank_reference": transfer_result.get("reference"),
                "status": "processing",
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
            
            return {
                "status": "success",
                "amount_withdrawn": float(net_amount),
                "fee": float(fee),
                "reference": transfer_result.get("reference")
            }
        except Exception as e:
            logger.error(f"Fiat withdrawal failed for user {user_id}: {e}")
            raise

    # ========================
    # DISPUTE HANDLING
    # ========================
    async def create_dispute(self, transaction_id: str, user_id: str, reason: str) -> Dict:
        """Create a payment dispute"""
        try:
            tx = await self.supabase.table("payment_transactions").select("*").eq("id", transaction_id).execute()
            if not tx.data or tx.data[0]["sender_id"] != user_id:
                raise ValueError("Transaction not found or not authorized")
            
            dispute = Dispute(
                transaction_id=transaction_id,
                user_id=user_id,
                reason=reason
            )
            
            await self.supabase.table("disputes").insert(asdict(dispute)).execute()
            await self.redis.incr("disputes:count")
            
            # Update transaction status
            await self.supabase.table("payment_transactions").update({
                "status": PaymentStatus.DISPUTED.value
            }).eq("id", transaction_id).execute()
            
            logger.info(f"Dispute created for transaction {transaction_id} by user {user_id}")
            return asdict(dispute)
        except Exception as e:
            logger.error(f"Dispute creation failed: {e}")
            raise

    # ========================
    # QR PAYMENTS
    # ========================
    def generate_payment_qr(self, address: str, amount: Optional[Decimal] = None, memo: str = "") -> str:
        """Generate QR code for payment request (base64 encoded)"""
        try:
            # Create payment URI
            uri = f"seamount:{address}"
            params = []
            
            if amount:
                params.append(f"amount={amount}")
            if memo:
                params.append(f"memo={memo}")
            
            if params:
                uri += "?" + "&".join(params)
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(uri)
            qr.make(fit=True)
            
            # Convert to base64 string
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return qr_code_base64
        except Exception as e:
            logger.error(f"QR code generation failed: {e}")
            raise

    # ========================
    # PAYMENT STATUS & HISTORY
    # ========================
    async def get_payment_status(self, payment_id: str) -> Optional[PaymentResult]:
        """Get payment status"""
        try:
            # Check pending payments
            if payment_id in self.pending_payments:
                return PaymentResult(
                    request_id=payment_id,
                    status=PaymentStatus.PENDING,
                    payment_type=self.pending_payments[payment_id].payment_type
                )
            
            # Check history
            for result in self.payment_history:
                if result.request_id == payment_id:
                    return result
            
            # Check database
            db_result = await self.supabase.table("payment_transactions").select("*").eq("payment_id", payment_id).execute()
            
            if db_result.data:
                tx = db_result.data[0]
                return PaymentResult(
                    request_id=payment_id,
                    status=PaymentStatus(tx["status"]),
                    payment_type=PaymentType(tx["payment_type"]),
                    tx_id=tx["tx_id"],
                    final_amount=Decimal(str(tx["amount"])),
                    fees=Decimal(str(tx["fee"])),
                    exchange_rate=Decimal(str(tx.get("exchange_rate", 1.0))),
                    completed_at=int(datetime.fromisoformat(tx["timestamp"]).timestamp())
                )
            
            return None
        except Exception as e:
            logger.error(f"Payment status check failed: {e}")
            return None
    
    async def get_user_payment_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get user payment history"""
        try:
            # Get user address
            user_data = await self.supabase.table("users").select("p2p_address").eq("id", user_id).execute()
            if not user_data.data:
                return []
            
            address = user_data.data[0]["p2p_address"]
            
            # Get transactions
            transactions = await self.supabase.table("payment_transactions").select("*").or_(
                f"sender_address.eq.{address},receiver_address.eq.{address}"
            ).order("timestamp", desc=True).limit(limit).execute()
            
            return transactions.data
        except Exception as e:
            logger.error(f"Payment history retrieval failed: {e}")
            return []

    # ========================
    # BACKGROUND MAINTENANCE
    # ========================
    async def background_maintenance(self):
        """Background maintenance tasks"""
        while True:
            try:
                # Cleanup expired payments every 5 minutes
                await self.cleanup_expired_payments()
                
                # Refresh exchange rates every 10 minutes
                if time.time() % 600 < 300:  # Every 10 minutes
                    await self.refresh_exchange_rates()
                
                # Health check logging every 30 minutes
                if time.time() % 1800 < 300:  # Every 30 minutes
                    health = await self.health_check()
                    if health["status"] != "healthy":
                        logger.warning(f"System health degraded: {health}")
                
                await asyncio.sleep(300)  # 5 minutes
            except Exception as e:
                logger.error(f"Background maintenance error: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute

    async def cleanup_expired_payments(self):
        """Clean up expired pending payments"""
        try:
            current_time = time.time()
            expired_payments = [
                payment_id for payment_id, request in self.pending_payments.items()
                if current_time > request.expires_at
            ]
            
            for payment_id in expired_payments:
                del self.pending_payments[payment_id]
                logger.info(f"Cleaned up expired payment: {payment_id}")
            
            return len(expired_payments)
        except Exception as e:
            logger.error(f"Payment cleanup failed: {e}")
            return 0

    async def refresh_exchange_rates(self):
        """Refresh exchange rates from external sources"""
        try:
            await self._initialize_exchange_rates()
            logger.info("Exchange rates refreshed")
            return True
        except Exception as e:
            logger.error(f"Exchange rate refresh failed: {e}")
            return False

    # ========================
    # HEALTH CHECKS & METRICS
    # ========================
    async def health_check(self) -> Dict:
        """Comprehensive system health check"""
        try:
            health = {"status": "healthy", "checks": {}}
            
            # Database connectivity
            try:
                await self.supabase.table("users").select("id").limit(1).execute()
                health["checks"]["database"] = "healthy"
            except Exception as e:
                health["checks"]["database"] = f"unhealthy: {e}"
                health["status"] = "degraded"
            
            # Redis connectivity
            try:
                await self.redis.ping()
                health["checks"]["redis"] = "healthy"
            except Exception as e:
                health["checks"]["redis"] = f"unhealthy: {e}"
                health["status"] = "degraded"
            
            # USDS manager status
            try:
                await self.usds_manager.get_collateral_status("ZA")  # Test call
                health["checks"]["algorand"] = "healthy"
            except Exception as e:
                health["checks"]["algorand"] = f"unhealthy: {e}"
                health["status"] = "degraded"
            
            # Exchange rate freshness
            fresh_rates = sum(1 for rate in self.exchange_rates.values() 
                            if time.time() - rate.timestamp < 300)
            total_rates = len(self.exchange_rates)
            
            if fresh_rates / max(total_rates, 1) > 0.8:
                health["checks"]["exchange_rates"] = "healthy"
            else:
                health["checks"]["exchange_rates"] = f"stale: {fresh_rates}/{total_rates} fresh"
                health["status"] = "degraded"
            
            # System resources
            health["checks"]["pending_payments"] = len(self.pending_payments)
            health["checks"]["payment_history_size"] = len(self.payment_history)
            
            return health
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def get_platform_metrics(self) -> Dict:
        """Get platform performance metrics"""
        try:
            metrics = {
                "p2p_count": int(await self.redis.get("transactions:p2p:count") or 0),
                "cross_border_count": int(await self.redis.get("transactions:cross_border:count") or 0),
                "p2p_volume": float(await self.redis.get("transactions:p2p:volume") or 0),
                "cross_border_volume": float(await self.redis.get("transactions:cross_border:volume") or 0),
                "dispute_count": int(await self.redis.get("disputes:count") or 0),
                "network_congestion": await self._get_network_congestion(),
                "pending_payments": len(self.pending_payments),
                "exchange_rates": len(self.exchange_rates)
            }
            return metrics
        except Exception as e:
            logger.error(f"Metrics retrieval failed: {e}")
            return {}