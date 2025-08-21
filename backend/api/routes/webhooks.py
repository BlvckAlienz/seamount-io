from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib
import json
from ...services.kyc_providers.complycube import complycube_service

router = APIRouter()

@router.post("/webhooks/complycube")
async def handle_complycube_webhook(request: Request):
    try:
        # Verify webhook signature (important for security)
        signature = request.headers.get('X-ComplyCube-Signature')
        body = await request.body()
        
        # Verify signature here (implementation depends on your ComplyCube settings)
        # ...
        
        # Process the webhook data
        data = await request.json()
        event_type = data.get('type')
        applicant_id = data.get('data', {}).get('clientId')
        
        if event_type == 'check.completed':
            # Update user KYC status based on verification result
            check_result = data.get('data', {}).get('result', {})
            review_status = check_result.get('reviewStatus')
            
            kyc_status = 'pending'
            if review_status == 'approved':
                kyc_status = 'approved'
            elif review_status == 'rejected':
                kyc_status = 'rejected'
            
            # Update user profile
            complycube_service.update_user_kyc_status(applicant_id, kyc_status)
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")