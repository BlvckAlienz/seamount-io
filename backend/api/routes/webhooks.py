# File Location: backend/api/routes/webhooks.py
import hashlib
import hmac
import json
import os
from fastapi import APIRouter, Request, HTTPException, status, Depends
from supabase import Client
import logging
from decimal import Decimal
from datetime import datetime

from backend.dependencies import get_supabase_client
from backend.config import get_settings, Settings
from backend.services.wallet_service import WalletService

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
    """Handle successful payment with asset-specific credit"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        amount = float(data.get("amount", 0)) / 100  # Convert from kobo to naira
        
        # Get transaction details to determine which asset was purchased
        supabase = get_supabase_client()
        transaction_result = supabase.table("payment_transactions").select("*").eq("reference", reference).single().execute()
        
        if not transaction_result.data:
            logger.error(f"Transaction not found for reference: {reference}")
            return
            
        transaction = transaction_result.data
        user_id = transaction["user_id"]
        
        # Determine which asset to credit based on transaction metadata
        asset = transaction.get("asset", "usdt")  # Default to USDT if not specified
        wallet_service = WalletService(get_settings(), supabase)
        
        # Get current balance
        balances = await wallet_service.get_wallet_balances(user_id)
        current_balance = balances.get(asset, Decimal("0"))
        
        # Calculate new balance
        new_balance = current_balance + Decimal(str(amount))
        
        # Update the specific asset balance
        success = await wallet_service.update_asset_balance(user_id, asset, new_balance)
        
        if not success:
            logger.error(f"Failed to update {asset} balance for user {user_id}")
            return
            
        # Update payment record
        update_data = {
            "status": "completed",
            "provider_tx_id": data.get("id"),
            "completed_at": datetime.utcnow().isoformat(),
            "routing_metadata": json.dumps({
                "paystack_gateway_response": data.get("gateway_response"),
                "paystack_channel": data.get("channel"),
                "customer_email": data.get("customer", {}).get("email"),
                "asset_credited": asset,
                "amount_credited": float(amount)
            })
        }
        
        supabase.table("payment_transactions").update(update_data).eq("reference", reference).execute()
        
        logger.info(f"✅ Payment completed: {reference} - {amount} {asset.upper()} credited to user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to handle charge success: {str(e)}")

async def handle_paystack_charge_failed(event_data):
    """Handle failed payment"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        
        supabase = get_supabase_client()
        
        supabase.table("payment_transactions").update({
            "status": "failed",
            "provider_tx_id": data.get("id"),
            "routing_metadata": json.dumps({
                "failure_reason": data.get("gateway_response"),
                "paystack_channel": data.get("channel")
            })
        }).eq("reference", reference).execute()
        
        logger.warning(f"❌ Payment failed: {reference}")
        
    except Exception as e:
        logger.error(f"Failed to handle charge failure: {str(e)}")

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
    """Handle successful Flutterwave payment with asset-specific credit"""
    try:
        reference = data.get("tx_ref")
        amount = float(data.get("amount", 0))
        
        # Get transaction details to determine which asset was purchased
        supabase = get_supabase_client()
        transaction_result = supabase.table("payment_transactions").select("*").eq("reference", reference).single().execute()
        
        if not transaction_result.data:
            logger.error(f"Transaction not found for reference: {reference}")
            return
            
        transaction = transaction_result.data
        user_id = transaction["user_id"]
        
        # Determine which asset to credit based on transaction metadata
        asset = transaction.get("asset", "usdt")  # Default to USDT if not specified
        wallet_service = WalletService(get_settings(), supabase)
        
        # Get current balance
        balances = await wallet_service.get_wallet_balances(user_id)
        current_balance = balances.get(asset, Decimal("0"))
        
        # Calculate new balance
        new_balance = current_balance + Decimal(str(amount))
        
        # Update the specific asset balance
        success = await wallet_service.update_asset_balance(user_id, asset, new_balance)
        
        if not success:
            logger.error(f"Failed to update {asset} balance for user {user_id}")
            return
        
        # Update transaction record
        supabase.table("payment_transactions").update({
            "status": "completed",
            "provider_tx_id": data.get("id"),
            "completed_at": datetime.utcnow().isoformat(),
            "routing_metadata": json.dumps({
                "flutterwave_processor": data.get("processor_response"),
                "flutterwave_narration": data.get("narration"),
                "asset_credited": asset,
                "amount_credited": float(amount)
            })
        }).eq("reference", reference).execute()
        
        logger.info(f"✅ Flutterwave payment completed: {reference} - {amount} {asset.upper()} credited")
        
    except Exception as e:
        logger.error(f"Failed to handle Flutterwave success: {str(e)}")

async def handle_flutterwave_failure(data):
    """Handle failed Flutterwave payment"""
    try:
        reference = data.get("tx_ref")
        
        supabase = get_supabase_client()
        
        supabase.table("payment_transactions").update({
            "status": "failed",
            "routing_metadata": json.dumps({
                "failure_reason": data.get("processor_response")
            })
        }).eq("reference", reference).execute()
        
        logger.warning(f"❌ Flutterwave payment failed: {reference}")
        
    except Exception as e:
        logger.error(f"Failed to handle Flutterwave failure: {str(e)}")