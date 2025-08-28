# File Location: backend/models.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from enum import Enum

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