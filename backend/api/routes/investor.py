from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from supabase import Client
from dependencies import get_supabase_client  # Correct import
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class InvestorContactRequest(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    checkSize: Optional[str] = None
    message: Optional[str] = None

@router.post("/investor-contact")
async def submit_investor_contact(
    request: InvestorContactRequest,
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_user)
):
    try:
        logger.info(f"Received investor contact from {request.email}")
        
        # Prepare data for insertion
        contact_data = {
            "name": request.name,
            "email": request.email,
            "company": request.company,
            "check_size": request.checkSize,
            "message": request.message,
            "created_at": datetime.utcnow().isoformat(),
            "user_id": current_user.get('id')
        }
        
        # Insert into database
        result = supabase.table("investor_contacts").insert(contact_data).execute()
        
        if not result.data:
            logger.error("Failed to insert investor contact data")
            raise HTTPException(status_code=500, detail="Failed to save contact information")
        
        logger.info(f"Successfully saved investor contact from {request.email}")
        
        # Here you would typically send an email notification
        # For now, we'll just log it
        logger.info(f"Investor contact notification would be sent for: {request.name} <{request.email}>")
        
        return {
            "success": True,
            "message": "Thank you for your interest. We'll be in touch soon.",
            "data": result.data[0] if result.data else None
        }
        
    except Exception as e:
        logger.error(f"Error processing investor contact: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process your request")