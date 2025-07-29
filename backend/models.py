# File Location: backend/models.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
import uuid

class UserProfile(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    country_code: Optional[str] = None
    kyc_level: int = Field(default=0)
    kyc_status: str = Field(default="none")
    algorand_address: Optional[str] = None
    is_admin: bool = Field(default=False) # Critical field for admin routes
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True