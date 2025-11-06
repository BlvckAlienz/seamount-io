# File Location: backend/models.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import uuid
from enum import Enum
from decimal import Decimal

class UserRole(str, Enum):
    TRIBE = "tribe"
    ALIEN = "alien"

class KYCStatus(str, Enum):
    NOT_STARTED = "not_started"
    PENDING = "pending"  # ADD THIS LINE
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"

class AccessLevel(str, Enum):
    RESTRICTED = "restricted"
    LIMITED = "limited"
    VERIFIED = "verified"
    FULL = "full"

class UserProfile(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    country_code: Optional[str] = None
    country: Optional[str] = Field(default="USA")
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    kyc_level: int = Field(default=0)
    kyc_status: KYCStatus = Field(default=KYCStatus.NOT_STARTED)
    access_level: AccessLevel = Field(default=AccessLevel.LIMITED)
    kyc_initiated_at: Optional[datetime] = None
    kyc_completed_at: Optional[datetime] = None
    kyc_rejection_reason: Optional[str] = None
    is_pep: bool = Field(default=False)
    sanctions_check_passed: Optional[bool] = None
    risk_level: str = Field(default="unknown")
    algorand_address: Optional[str] = None
    evm_address: Optional[str] = None
    is_admin: bool = Field(default=False)
    role: UserRole = Field(default=UserRole.ALIEN)
    verification_skipped: bool = Field(default=False)
    created_at: datetime
    updated_at: datetime
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v.strip() if v else None
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower().strip()
    
    class Config:
        from_attributes = True

class KYCVerificationLog(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    applicant_id: Optional[str] = None
    verification_type: str
    status: str
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProfileUpdateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    phone: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field("USA", max_length=3)
    address_line1: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError('Name must be at least 1 character long')
        return v.strip()

class ProfileCheckResponse(BaseModel):
    profile_complete: bool
    missing_fields: List[str]
    errors: List[str]
    can_start_kyc: bool
    kyc_status: str

class KYCStartResponse(BaseModel):
    token: str
    applicantId: str
    status: str = "success"
    message: str = "KYC verification initiated successfully"

class KYCSkipResponse(BaseModel):
    success: bool = True
    message: str
    access_level: AccessLevel
    kyc_status: KYCStatus

class PaymentRequest(BaseModel):
    recipient_email: EmailStr
    amount: float
    currency: str = "USD"

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

class portfolioHolding(BaseModel):
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

# Additional validation models for comprehensive error handling
class ValidationError(BaseModel):
    field: str
    message: str
    code: str

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[ValidationError]] = None

class WalletCreationStatus(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    chain: str
    status: str = "pending"  # pending, creating, success, failed, retrying
    address: Optional[str] = None
    encrypted_key: Optional[str] = None
    attempt_count: int = 0
    last_attempt_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class WalletCreationQueue(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    chain: str
    priority: int = 5
    scheduled_for: datetime
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 10
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True