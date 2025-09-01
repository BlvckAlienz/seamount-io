# File Location: backend/models.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from enum import Enum
from decimal import Decimal

class UserRole(str, Enum):
    TRIBE = "tribe"
    ALIEN = "alien"

class UserProfile(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    country_code: Optional[str] = None
    kyc_level: int = Field(default=0)
    kyc_status: str = Field(default="none")
    algorand_address: Optional[str] = None
    evm_address: Optional[str] = None
    is_admin: bool = Field(default=False)
    role: UserRole = Field(default=UserRole.ALIEN)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PaymentRequest(BaseModel):
    recipient_email: EmailStr
    amount: float
    currency: str = "USDS"

class PaymentResponse(BaseModel):
    transaction_id: str
    status: str
    amount: float
    currency: str
    timestamp: datetime

class MFASetupResponse(BaseModel):
    secret: str
    qr_code_url: str

class MFAVerifyRequest(BaseModel):
    token: str

class PortfolioHolding(BaseModel):
    id: str
    user_id: str
    asset: str
    amount: float
    value_usd: float

class SessionResponse(BaseModel): 
    session_id: uuid.UUID

class ConsentUpdatePayload(BaseModel): 
    session_id: uuid.UUID
    preferences: Dict[str, bool]

class InvestorContactPayload(BaseModel): 
    name: str
    email: EmailStr
    company: Optional[str] = None
    checkSize: Optional[str] = None
    message: Optional[str] = None

class KYCSubmission(BaseModel): 
    document_type: str
    document_data: str
    
class UserSession(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    ip_address: str
    user_agent: str
    device_type: str
    browser: str
    platform: str
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
class Config:
    from_attributes = True
        
class LicenseTier(str, Enum):
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class LicenseStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active" 
    EXPIRED = "expired"
    SUSPENDED = "suspended"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class LicensePurchaseRequest(BaseModel):
    tier: LicenseTier
    region: str = "nigeria"  # Default to Nigeria
    payment_method: str = "flutterwave"
    company_name: Optional[str] = None
    employee_count: Optional[int] = None

class LicensePurchaseResponse(BaseModel):
    license_id: str
    transaction_id: str
    payment_link: str
    amount: float
    currency: str
    tier: LicenseTier
    expires_at: Optional[datetime] = None

class LicenseInfo(BaseModel):
    id: str
    user_id: str
    tier: LicenseTier
    status: LicenseStatus
    purchase_amount: float
    currency: str
    region: str
    transaction_fee_rate: float
    employee_limit: Optional[int] = None
    features: List[str]
    purchased_at: datetime
    expires_at: Optional[datetime] = None
    last_payment_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TierUpgradeRequest(BaseModel):
    current_tier: LicenseTier
    target_tier: LicenseTier
    payment_method: str = "flutterwave"

class LicenseUsageStats(BaseModel):
    license_id: str
    current_month_volume: Decimal
    current_month_transactions: int
    current_month_fees: Decimal
    total_savings_vs_individual: Decimal
    utilization_percentage: float

class TransactionFeeCalculation(BaseModel):
    amount: Decimal
    tier: LicenseTier
    base_rate: float
    calculated_fee: Decimal
    min_fee_applied: bool
    max_fee_applied: bool
    final_fee: Decimal
    effective_rate: float
    savings_vs_individual: Decimal