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

from backend.dependencies import get_supabase_client, get_db_service
from backend.config import get_settings, Settings
from backend.services.multi_chain_wallet_service import MultiChainWalletService as WalletService
from backend.services.kyc_providers.regfyl import regfyl_service
from backend.services.database_service import DatabaseService
from backend.services.algorand_service import AlgorandService

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
        
        logger.info(f"âœ… Payment completed: {reference} - {amount} {asset.upper()} credited to user {user_id}")
        
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
        
        logger.warning(f"âŒ Payment failed: {reference}")
        
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
        
        logger.info(f"âœ… Flutterwave payment completed: {reference} - {amount} {asset.upper()} credited")
        
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
        
        logger.warning(f"âŒ Flutterwave payment failed: {reference}")
        
    except Exception as e:
        logger.error(f"Failed to handle Flutterwave failure: {str(e)}")

async def handle_paystack_transfer_success(event_data):
    """Handle successful Paystack transfer (payout)"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        amount = float(data.get("amount", 0)) / 100
        
        supabase = get_supabase_client()
        
        supabase.table("payout_transactions").update({
            "status": "completed",
            "provider_tx_id": data.get("id"),
            "completed_at": datetime.utcnow().isoformat(),
            "routing_metadata": json.dumps({
                "paystack_transfer_code": data.get("transfer_code"),
                "paystack_recipient": data.get("recipient")
            })
        }).eq("reference", reference).execute()
        
        logger.info(f"Paystack transfer completed: {reference} - {amount} NGN")
        
    except Exception as e:
        logger.error(f"Failed to handle transfer success: {str(e)}")

async def handle_paystack_transfer_failed(event_data):
    """Handle failed Paystack transfer (payout)"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        
        supabase = get_supabase_client()
        
        supabase.table("payout_transactions").update({
            "status": "failed",
            "routing_metadata": json.dumps({
                "failure_reason": data.get("failures"),
                "paystack_transfer_code": data.get("transfer_code")
            })
        }).eq("reference", reference).execute()
        
        logger.warning(f"Paystack transfer failed: {reference}")
        
    except Exception as e:
        logger.error(f"Failed to handle transfer failure: {str(e)}")

async def handle_paystack_transfer_reversed(event_data):
    """Handle reversed Paystack transfer (payout)"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        
        supabase = get_supabase_client()
        
        supabase.table("payout_transactions").update({
            "status": "reversed",
            "routing_metadata": json.dumps({
                "reversal_reason": "Transfer reversed by Paystack"
            })
        }).eq("reference", reference).execute()
        
        logger.warning(f"Paystack transfer reversed: {reference}")
        
    except Exception as e:
        logger.error(f"Failed to handle transfer reversal: {str(e)}")

# ============================================================================
# REGFYL WEBHOOK HANDLERS (FIXED TABLE NAMES)
# ============================================================================

@router.post("/regfyl/screening")
async def regfyl_screening_webhook(
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """Handle Regfyl screening callbacks"""
    try:
        data = await request.json()
        logger.info(f"[Regfyl Webhook] Received: {data}")
        
        customer_id = data.get('customerID')
        check_type = data.get('checkType', 'PEP')
        status = data.get('status', 'Not yet reviewed')
        reference = data.get('reference', '')
        
        # Update user based on check results
        if check_type == 'PEP' and status == 'Reviewed - No further action required':
            supabase.table('user_profiles').update({
                'kyc_status': 'approved',
                'kyc_level': 3,
                'role': 'tribe',
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', customer_id).execute()
            
        return {"success": True, "message": "Webhook processed"}
        
    except Exception as e:
        logger.error(f"[Regfyl Webhook] Error: {e}")
        return {"success": False, "error": str(e)}
        
        # Update user compliance status using EXISTING compliance_checks table
        supabase = get_supabase_client()
        
        compliance_data = {
            "user_id": customer_id,
            "check_type": "regfyl_screening",
            "provider": "regfyl",
            "status": callback_result['status'],
            "reference_id": callback_result['reference'],
            "risk_level": callback_result['risk_level'],
            "metadata": json.dumps({
                "action_required": callback_result['action_required'],
                "callback_data": payload
            }),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Use UPSERT with compliance_checks table
        supabase.table("compliance_checks").upsert(compliance_data).execute()
        
        logger.info(f"Regfyl screening callback processed for user {customer_id}: {callback_result['status']}")
        
        return {"status": "success", "message": "Screening callback processed"}
        
    except Exception as e:
        logger.error(f"Regfyl screening webhook failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.post("/webhooks/regfyl/id-verification")
async def regfyl_id_verification_webhook(request: Request):
    """Handle Regfyl ID verification callbacks"""
    try:
        payload = await request.json()
        
        # Verify webhook signature
        signature = request.headers.get("x-Signature")
        if signature:
            body = await request.body()
            expected_signature = regfyl_service._generate_signature(body.decode('utf-8'))
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("Invalid Regfyl ID verification webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse callback data
        callback_result = regfyl_service.parse_callback(payload)
        customer_id = callback_result['customer_id']
        
        if not customer_id:
            logger.error("No customer_id in Regfyl ID verification callback")
            return {"status": "error", "message": "Missing customer_id"}
        
        supabase = get_supabase_client()
        
        # Update both compliance_checks and user KYC status based on ID verification result
        compliance_data = {
            "user_id": customer_id,
            "check_type": "regfyl_id_verification",
            "provider": "regfyl",
            "status": callback_result['status'],
            "reference_id": callback_result['reference'],
            "risk_level": callback_result['risk_level'],
            "metadata": json.dumps({
                "action_required": callback_result['action_required'],
                "callback_data": payload
            }),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Store in compliance_checks table
        supabase.table("compliance_checks").upsert(compliance_data).execute()
        
        # Update user profile based on verification result
        if callback_result['status'] in ['Reviewed - Cleared', 'Cleared']:
            # ID verification passed - update to tier 2
            supabase.table("user_profiles").update({
                "kyc_status": "id_verified",
                "kyc_tier": 2,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", customer_id).execute()
            
        elif callback_result['action_required']:
            # ID verification requires action
            supabase.table("user_profiles").update({
                "kyc_status": "manual_review",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", customer_id).execute()
        
        logger.info(f"Regfyl ID verification callback processed for user {customer_id}: {callback_result['status']}")
        
        return {"status": "success", "message": "ID verification callback processed"}
        
    except Exception as e:
        logger.error(f"Regfyl ID verification webhook failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.post("/webhooks/regfyl/transaction-monitoring")
async def regfyl_transaction_monitoring_webhook(request: Request):
    """Handle Regfyl transaction monitoring callbacks"""
    try:
        payload = await request.json()
        
        # Verify webhook signature
        signature = request.headers.get("x-Signature")
        if signature:
            body = await request.body()
            expected_signature = regfyl_service._generate_signature(body.decode('utf-8'))
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("Invalid Regfyl transaction monitoring webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse callback data
        callback_result = regfyl_service.parse_callback(payload)
        customer_id = callback_result['customer_id']
        transaction_reference = payload.get('transactionReference')
        
        if not customer_id or not transaction_reference:
            logger.error("Missing required data in Regfyl transaction monitoring callback")
            return {"status": "error", "message": "Missing required data"}
        
        supabase = get_supabase_client()
        
        # Store transaction monitoring result in compliance_logs table
        compliance_data = {
            "user_id": customer_id,
            "transaction_id": transaction_reference,
            "compliance_type": "regfyl_transaction_monitoring",
            "provider": "regfyl",
            "status": callback_result['status'],
            "reference_id": callback_result['reference'],
            "risk_level": callback_result['risk_level'],
            "metadata": json.dumps({
                "action_required": callback_result['action_required'],
                "callback_data": payload
            }),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store in compliance_logs table
        supabase.table("compliance_logs").upsert(compliance_data).execute()
        
        # If high risk or action required, flag the transaction
        if callback_result['action_required'] or callback_result['risk_level'] == 'HIGH':
            # Update transaction status in existing transactions table
            supabase.table("transactions").update({
                "status": "flagged",
                "metadata": json.dumps({
                    "compliance_flag": "regfyl_manual_review",
                    "compliance_notes": f"Regfyl flagged: {callback_result['status']}"
                }),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("transaction_id", transaction_reference).execute()
            
            logger.warning(f"Transaction {transaction_reference} flagged by Regfyl for manual review")
        
        logger.info(f"Regfyl transaction monitoring callback processed: {transaction_reference}")
        
        return {"status": "success", "message": "Transaction monitoring callback processed"}
        
    except Exception as e:
        logger.error(f"Regfyl transaction monitoring webhook failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.post("/webhooks/regfyl/business-screening")
async def regfyl_business_screening_webhook(request: Request):
    """Handle Regfyl business screening callbacks"""
    try:
        payload = await request.json()
        
        # Verify webhook signature
        signature = request.headers.get("x-Signature")
        if signature:
            body = await request.body()
            expected_signature = regfyl_service._generate_signature(body.decode('utf-8'))
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("Invalid Regfyl business screening webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse callback data
        callback_result = regfyl_service.parse_callback(payload)
        customer_id = callback_result['customer_id']
        
        if not customer_id:
            logger.error("No customer_id in Regfyl business screening callback")
            return {"status": "error", "message": "Missing customer_id"}
        
        supabase = get_supabase_client()
        
        # Store business screening result in compliance_logs table
        compliance_data = {
            "user_id": customer_id,
            "compliance_type": "regfyl_business_screening",
            "provider": "regfyl",
            "status": callback_result['status'],
            "reference_id": callback_result['reference'],
            "risk_level": callback_result['risk_level'],
            "metadata": json.dumps({
                "action_required": callback_result['action_required'],
                "callback_data": payload,
                "business_screening": True
            }),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store in compliance_logs table
        supabase.table("compliance_logs").upsert(compliance_data).execute()
        
        logger.info(f"Regfyl business screening callback processed for business {customer_id}: {callback_result['status']}")
        
        return {"status": "success", "message": "Business screening callback processed"}
        
    except Exception as e:
        logger.error(f"Regfyl business screening webhook failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

# ============================================================================
# PRETIUM WEBHOOK HANDLER (Tron USDT Transactions)
# ============================================================================

@router.post("/webhooks/pretium")
async def pretium_webhook(
    request: Request,
    db_service = Depends(get_db_service)
):
    """
    Handle Pretium transaction status callbacks
    
    Pretium sends status updates for:
    - On-ramp: Fiat received → USDT credited
    - Off-ramp: USDT received → Fiat disbursed
    """
    
    try:
        payload = await request.json()
        logger.info(f"📨 Pretium webhook received: {payload.get('event')}")
        
        # Extract transaction data
        transaction_code = payload.get("transaction_code")
        status = payload.get("status")  # PENDING, COMPLETE, FAILED
        currency = payload.get("currency")
        
        if not transaction_code:
            logger.error("❌ Missing transaction_code in Pretium webhook")
            return {"status": "error", "message": "Missing transaction_code"}
        
        # Find transaction in database
        # Try onramp first
        tx_result = db_service.supabase.from_('onramp_transactions')\
            .select('*')\
            .eq('pretium_txn_code', transaction_code)\
            .limit(1)\
            .execute()
        
        tx_type = "onramp"
        
        if not tx_result.data or len(tx_result.data) == 0:
            # Try offramp
            tx_result = db_service.supabase.from_('offramp_transactions')\
                .select('*')\
                .eq('pretium_txn_code', transaction_code)\
                .limit(1)\
                .execute()
            tx_type = "offramp"
        
        if not tx_result.data or len(tx_result.data) == 0:
            logger.error(f"❌ Transaction not found for Pretium code: {transaction_code}")
            return {"status": "error", "message": "Transaction not found"}
        
        tx_data = tx_result.data[0]
        user_id = tx_data["user_id"]
        crypto_amount = tx_data.get("crypto_amount") or tx_data.get("net_crypto_amount")
        
        # Process based on status
        if status == "COMPLETE":
            logger.info(f"✅ Pretium transaction completed: {transaction_code}")
            
            if tx_type == "onramp":
                # Credit user's Tron wallet balance
                await _credit_tron_balance(
                    db_service,
                    user_id,
                    crypto_amount,
                    transaction_code
                )
                
                # Update onramp transaction
                db_service.supabase.from_('onramp_transactions').update({
                    'status': 'completed',
                    'completed_at': datetime.now().isoformat(),
                    'metadata': {
                        **tx_data.get('metadata', {}),
                        'pretium_status': status,
                        'pretium_webhook': payload
                    }
                }).eq('pretium_txn_code', transaction_code).execute()
                
            else:  # offramp
                # Update offramp transaction
                db_service.supabase.from_('offramp_transactions').update({
                    'status': 'completed',
                    'completed_at': datetime.now().isoformat(),
                    'metadata': {
                        **tx_data.get('metadata', {}),
                        'pretium_status': status,
                        'pretium_webhook': payload
                    }
                }).eq('pretium_txn_code', transaction_code).execute()
        
        elif status == "FAILED":
            logger.warning(f"⚠️ Pretium transaction failed: {transaction_code}")
            
            if tx_type == "offramp":
                # Refund user's balance
                await _refund_tron_balance(
                    db_service,
                    user_id,
                    crypto_amount,
                    transaction_code
                )
            
            # Update transaction status
            table = 'onramp_transactions' if tx_type == 'onramp' else 'offramp_transactions'
            db_service.supabase.from_(table).update({
                'status': 'failed',
                'metadata': {
                    **tx_data.get('metadata', {}),
                    'pretium_status': status,
                    'pretium_webhook': payload
                }
            }).eq('pretium_txn_code', transaction_code).execute()
        
        return {"status": "success", "message": "Webhook processed"}
        
    except Exception as e:
        logger.error(f"💥 Pretium webhook processing failed: {e}")
        return {"status": "error", "message": str(e)}


async def _credit_tron_balance(
    db_service,
    user_id: str,
    amount: float,
    transaction_code: str
):
    """Credit user's USDT_TRON balance after successful on-ramp"""
    
    try:
        # Get current balance
        balance_result = db_service.supabase.from_('wallet_balances')\
            .select('usdt_tron_balance')\
            .eq('user_id', user_id)\
            .limit(1)\
            .execute()
        
        if not balance_result.data or len(balance_result.data) == 0:
            logger.error(f"❌ No wallet found for user {user_id}")
            return
        
        current_balance = float(balance_result.data[0].get('usdt_tron_balance', 0))
        new_balance = current_balance + float(amount)
        
        # Update balance
        db_service.supabase.from_('wallet_balances').update({
            'usdt_tron_balance': new_balance,
            'updated_at': datetime.now().isoformat()
        }).eq('user_id', user_id).execute()
        
        logger.info(f"✅ Credited {amount} USDT_TRON to user {user_id[:8]}... (Pretium tx: {transaction_code})")
        
    except Exception as e:
        logger.error(f"❌ Failed to credit Tron balance: {e}")


async def _refund_tron_balance(
    db_service,
    user_id: str,
    amount: float,
    transaction_code: str
):
    """Refund user's USDT_TRON balance after failed off-ramp"""
    
    try:
        # Get current balance
        balance_result = db_service.supabase.from_('wallet_balances')\
            .select('usdt_tron_balance')\
            .eq('user_id', user_id)\
            .limit(1)\
            .execute()
        
        if not balance_result.data or len(balance_result.data) == 0:
            logger.error(f"❌ No wallet found for user {user_id}")
            return
        
        current_balance = float(balance_result.data[0].get('usdt_tron_balance', 0))
        new_balance = current_balance + float(amount)
        
        # Refund balance
        db_service.supabase.from_('wallet_balances').update({
            'usdt_tron_balance': new_balance,
            'updated_at': datetime.now().isoformat()
        }).eq('user_id', user_id).execute()
        
        logger.info(f"✅ Refunded {amount} USDT_TRON to user {user_id[:8]}... (Pretium tx: {transaction_code})")
        
    except Exception as e:
        logger.error(f"❌ Failed to refund Tron balance: {e}")

# ADD THIS HELPER METHOD after the other webhook handlers:

async def handle_paystack_transfer_success(event_data):
    """Handle successful Paystack transfer (payout)"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        amount = float(data.get("amount", 0)) / 100  # Convert from kobo
        
        supabase = get_supabase_client()
        
        # Update payout transaction status
        supabase.table("payout_transactions").update({
            "status": "completed",
            "provider_tx_id": data.get("id"),
            "completed_at": datetime.utcnow().isoformat(),
            "routing_metadata": json.dumps({
                "paystack_transfer_code": data.get("transfer_code"),
                "paystack_recipient": data.get("recipient")
            })
        }).eq("reference", reference).execute()
        
        logger.info(f"Paystack transfer completed: {reference} - {amount} NGN")
        
    except Exception as e:
        logger.error(f"Failed to handle transfer success: {str(e)}")

async def handle_paystack_transfer_failed(event_data):
    """Handle failed Paystack transfer (payout)"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        
        supabase = get_supabase_client()
        
        supabase.table("payout_transactions").update({
            "status": "failed",
            "routing_metadata": json.dumps({
                "failure_reason": data.get("failures"),
                "paystack_transfer_code": data.get("transfer_code")
            })
        }).eq("reference", reference).execute()
        
        logger.warning(f"Paystack transfer failed: {reference}")
        
    except Exception as e:
        logger.error(f"Failed to handle transfer failure: {str(e)}")

async def handle_paystack_transfer_reversed(event_data):
    """Handle reversed Paystack transfer (payout)"""
    try:
        data = event_data.get("data", {})
        reference = data.get("reference")
        
        supabase = get_supabase_client()
        
        supabase.table("payout_transactions").update({
            "status": "reversed",
            "routing_metadata": json.dumps({
                "reversal_reason": "Transfer reversed by Paystack"
            })
        }).eq("reference", reference).execute()
        
        logger.warning(f"Paystack transfer reversed: {reference}")
        
    except Exception as e:
        logger.error(f"Failed to handle transfer reversal: {str(e)}")