# File Location: backend/api/routes/webhooks.py
import hashlib
import hmac
import json
import os
from fastapi import APIRouter, Request, HTTPException, status, Depends
from supabase import Client
import logging
from backend.dependencies import get_supabase_client
from config import get_settings, Settings
from services.wallet_service import WalletService

router = APIRouter()
logger = logging.getLogger(__name__)

# =============================================================================
# PAYSTACK WEBHOOK HANDLER (PRIMARY FOR NGN PAYMENTS)
# =============================================================================

@router.post("/webhooks/paystack")
async def paystack_webhook(request: Request):
    """Handle Paystack webhook events with robust error handling"""
    try:
        # Get the signature from headers
        signature = request.headers.get("x-paystack-signature")
        if not signature:
            raise HTTPException(status_code=400, detail="Missing signature")
        
        # Get request body
        body = await request.body()
        payload = body.decode('utf-8')
        
        # Verify webhook signature
        webhook_secret = os.getenv("PAYSTACK_WEBHOOK_SECRET")
        if not webhook_secret:
            logger.error("PAYSTACK_WEBHOOK_SECRET not configured")
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
        
        # Calculate expected signature
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        # Verify signatures match
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Invalid Paystack webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse event data
        event_data = json.loads(payload)
        event_type = event_data.get("event")
        
        logger.info(f"Received Paystack webhook: {event_type}")
        
        # Route to appropriate handler with retry logic
        handlers = {
            "charge.success": handle_paystack_charge_success,
            "charge.failed": handle_paystack_charge_failed,
            "transfer.success": handle_paystack_transfer_success,
            "transfer.failed": handle_paystack_transfer_failed,
            "transfer.reversed": handle_paystack_transfer_reversed
        }
        
        if event_type in handlers:
            await handlers[event_type](event_data)
        else:
            logger.info(f"Unhandled Paystack event type: {event_type}")
        
        return {"status": "success", "message": "Webhook processed"}
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

async def handle_paystack_charge_success(event_data):
    """Handle successful payment with automatic USDS minting"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        amount = float(data.get("amount", 0)) / 100  # Convert from kobo to naira
        
        from services.database_service import DatabaseService
        db = DatabaseService()
        
        # Update payment record
        await db.update(
            "payment_transactions",
            {"reference": reference},
            {
                "status": "completed",
                "provider_tx_id": data.get("id"),
                "completed_at": "NOW()",
                "routing_metadata": json.dumps({
                    "paystack_gateway_response": data.get("gateway_response"),
                    "paystack_channel": data.get("channel"),
                    "customer_email": data.get("customer", {}).get("email")
                })
            }
        )
        
        # Trigger USDS minting process
        from services.payment_service import EnhancedPaymentService
        payment_service = EnhancedPaymentService()  # Dependency injection needed
        await payment_service._handle_successful_payment(
            transaction_id=reference,
            provider_tx_id=data.get("id"),
            amount=amount,
            metadata={}
        )
        
        logger.info(f"✅ Payment completed: {reference} - NGN {amount}")
        
    except Exception as e:
        logger.error(f"Failed to handle charge success: {str(e)}")

async def handle_paystack_charge_failed(event_data):
    """Handle failed payment"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        
        from services.database_service import DatabaseService
        db = DatabaseService()
        
        await db.update(
            "payment_transactions",
            {"reference": reference},
            {
                "status": "failed",
                "provider_tx_id": data.get("id"),
                "routing_metadata": json.dumps({
                    "failure_reason": data.get("gateway_response"),
                    "paystack_channel": data.get("channel")
                })
            }
        )
        
        logger.warning(f"❌ Payment failed: {reference}")
        
    except Exception as e:
        logger.error(f"Failed to handle charge failure: {str(e)}")

async def handle_paystack_transfer_success(event_data):
    """Handle successful payout/transfer"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        amount = float(data.get("amount", 0)) / 100
        
        from services.database_service import DatabaseService
        db = DatabaseService()
        
        await db.update(
            "payment_transactions",
            {"reference": reference},
            {
                "status": "completed",
                "provider_tx_id": data.get("transfer_code"),
                "completed_at": "NOW()"
            }
        )
        
        logger.info(f"✅ Transfer completed: {reference} - NGN {amount}")
        
    except Exception as e:
        logger.error(f"Failed to handle transfer success: {str(e)}")

async def handle_paystack_transfer_failed(event_data):
    """Handle failed payout/transfer"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        
        from services.database_service import DatabaseService
        db = DatabaseService()
        
        await db.update(
            "payment_transactions",
            {"reference": reference},
            {
                "status": "failed",
                "routing_metadata": json.dumps({
                    "failure_reason": data.get("failure_reason")
                })
            }
        )
        
        logger.warning(f"❌ Transfer failed: {reference}")
        
    except Exception as e:
        logger.error(f"Failed to handle transfer failure: {str(e)}")

async def handle_paystack_transfer_reversed(event_data):
    """Handle reversed transfer"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        
        from services.database_service import DatabaseService
        db = DatabaseService()
        
        await db.update(
            "payment_transactions",
            {"reference": reference},
            {
                "status": "reversed",
                "routing_metadata": json.dumps({
                    "reversal_reason": "Transfer reversed by provider"
                })
            }
        )
        
        logger.warning(f"🔄 Transfer reversed: {reference}")
        
    except Exception as e:
        logger.error(f"Failed to handle transfer reversal: {str(e)}")

# =============================================================================
# COMPLYCUBE WEBHOOK HANDLER (EXISTING KYC LOGIC PRESERVED)
# =============================================================================

@router.post("/complycube")
async def handle_complycube_webhook(
    request: Request,
    supabase: Client = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings)
):
    """Handle ComplyCube KYC webhook events"""
    # Verify webhook signature
    signature = request.headers.get("X-ComplyCube-Signature")
    body = await request.body()
    
    if not verify_signature(body, signature, settings.COMPLYCUBE_WEBHOOK_SECRET.get_secret_value()):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    event = await request.json()
    
    if event["type"] == "check.completed" and event["data"]["status"] == "complete":
        applicant_id = event["data"]["applicantId"]
        
        # Find user with this applicant ID
        user_res = supabase.from_("user_profiles").select("*").eq("complycube_applicant_id", applicant_id).execute()
        
        if user_res.data:
            user_id = user_res.data[0]["id"]
            
            # Update user role to 'tribe'
            supabase.from_("user_profiles").update({
                "role": "tribe",
                "kyc_status": "approved",
                "kyc_level": 3
            }).eq("id", user_id).execute()
            
            # Create wallet for user
            wallet_service = WalletService(settings, supabase)
            await wallet_service.provision_user_wallet(user_id)
            
            logger.info(f"User {user_id} KYC completed and wallet created")
    
    return {"status": "success"}

# =============================================================================
# FLUTTERWAVE WEBHOOK HANDLER (FALLBACK PROVIDER)
# =============================================================================

@router.post("/webhooks/flutterwave")
async def flutterwave_webhook(request: Request):
    """Handle Flutterwave webhook events (fallback provider)"""
    try:
        # Verify webhook signature
        signature = request.headers.get("verif-hash")
        webhook_secret = os.getenv("FLUTTERWAVE_WEBHOOK_SECRET")
        
        if signature != webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        payload = await request.json()
        event_type = payload.get("event")
        
        logger.info(f"Received Flutterwave webhook: {event_type}")
        
        if event_type == "charge.completed" and payload["data"]["status"] == "successful":
            await handle_flutterwave_success(payload["data"])
        elif payload["data"]["status"] == "failed":
            await handle_flutterwave_failure(payload["data"])
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Flutterwave webhook failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

async def handle_flutterwave_success(data):
    """Handle successful Flutterwave payment"""
    try:
        reference = data.get("tx_ref")
        amount = float(data.get("amount", 0))
        
        from services.database_service import DatabaseService
        db = DatabaseService()
        
        await db.update(
            "payment_transactions",
            {"reference": reference},
            {
                "status": "completed",
                "provider_tx_id": data.get("id"),
                "completed_at": "NOW()",
                "routing_metadata": json.dumps({
                    "flutterwave_processor": data.get("processor_response"),
                    "flutterwave_narration": data.get("narration")
                })
            }
        )
        
        logger.info(f"✅ Flutterwave payment completed: {reference}")
        
    except Exception as e:
        logger.error(f"Failed to handle Flutterwave success: {str(e)}")

async def handle_flutterwave_failure(data):
    """Handle failed Flutterwave payment"""
    try:
        reference = data.get("tx_ref")
        
        from services.database_service import DatabaseService
        db = DatabaseService()
        
        await db.update(
            "payment_transactions",
            {"reference": reference},
            {
                "status": "failed",
                "routing_metadata": json.dumps({
                    "failure_reason": data.get("processor_response")
                })
            }
        )
        
        logger.warning(f"❌ Flutterwave payment failed: {reference}")
        
    except Exception as e:
        logger.error(f"Failed to handle Flutterwave failure: {str(e)}")

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature for security"""
    if not signature or not secret:
        return False
        
    try:
        expected_signature = hmac.new(
            secret.encode(), 
            payload, 
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False