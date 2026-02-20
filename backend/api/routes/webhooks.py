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

@router.post("/paystack")
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

@router.post("/flutterwave")
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

            logger.info(f"✅ KYC approved for user {customer_id}")

            # ✅ NEW: Issue on-chain XRP credential after KYC approval
            try:
                from backend.services.xrp_credential_service import XRPCredentialService
                from datetime import timedelta
                from backend.config import get_settings

                settings = get_settings()
                xrp_cred = XRPCredentialService(settings=settings)

                cred_result = await xrp_cred.issue_credential(
                    subject_address=settings.XRP_HOT_WALLET_ADDRESS,
                    credential_type="KYC_BASIC",
                    expiry_days=365,
                )

                supabase.table("xrp_credentials").insert({
                    "user_id": customer_id,
                    "credential_type": "KYC_BASIC",
                    "on_chain": cred_result.get("success", False),
                    "tx_hash": cred_result.get("tx_hash"),
                    "issuer_address": settings.XRP_ADMIN_WALLET_ADDRESS,
                    "subject_address": settings.XRP_HOT_WALLET_ADDRESS,
                    "expires_at": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                }).execute()

                logger.info(f"✅ On-chain XRP credential issued for user {customer_id} | tx: {cred_result.get('tx_hash')}")

            except Exception as cred_error:
                # ⚠️ Non-fatal: credential failure must NOT block KYC approval
                logger.error(f"⚠️ On-chain credential failed (non-fatal) for {customer_id}: {cred_error}")

        return {"success": True, "message": "Webhook processed"}
        
    except Exception as e:
        logger.error(f"[Regfyl Webhook] Error: {e}")
        return {"success": False, "error": str(e)}
        
    except Exception as e:
        logger.error(f"Regfyl screening webhook failed: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/regfyl/id-verification")
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

@router.post("/regfyl/transaction-monitoring")
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

@router.post("/regfyl/business-screening")
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

@router.post("/pretium")
async def pretium_webhook(
    request: Request,
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

# ============================================================================
# QUIDAX WEBHOOK HANDLER
# ============================================================================

@router.post("/quidax")  # ✅ CORRECT - router already has /webhooks prefix
async def quidax_webhook(request: Request):
    """
    Handle Quidax webhook events
    
    Events:
    - instant_order.done: Order completed
    - instant_order.cancelled: Order cancelled
    - deposit.successful: Deposit confirmed
    - withdraw.successful: Withdrawal completed
    - withdraw.rejected: Withdrawal rejected
    """
    try:
        # Get signature from headers
        signature = request.headers.get("quidax-signature")
        if not signature:
            logger.warning("❌ Missing Quidax webhook signature")
            raise HTTPException(status_code=400, detail="Missing signature")
        
        # Get raw body
        body = await request.body()
        payload_str = body.decode('utf-8')
        
        # Verify signature
        from backend.services.quidax_service import QuidaxService
        quidax = QuidaxService(get_supabase_client())
        
        if signature:
            # ✅ More explicit control
            ALLOW_TEST_WEBHOOKS = os.getenv("ALLOW_TEST_WEBHOOKS", "false").lower() == "true"

            is_valid = quidax.verify_webhook_signature(payload_str, signature)

            if not is_valid and not ALLOW_TEST_WEBHOOKS:
                logger.error("❌ Invalid Quidax webhook signature - REJECTING")
                raise HTTPException(status_code=401, detail="Invalid signature")
            elif not is_valid:
                logger.warning("⚠️ Invalid signature but ALLOW_TEST_WEBHOOKS=true")
        else:
            logger.warning("⚠️ No signature header - webhook accepted without verification")
        
        # Parse event data
        event_data = json.loads(payload_str)
        event_type = event_data.get("event")
        
        logger.info(f"📨 Quidax webhook received: {event_type}")
        
        # Log webhook event
        supabase = get_supabase_client()
        webhook_log = {
            "event_type": event_type,
            "event_id": event_data.get("id"),
            "raw_payload": event_data,
            "signature": signature,
            "received_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("quidax_webhook_events").insert(webhook_log).execute()
        
        # Route to appropriate handler
        handlers = {
            "instant_order.done": handle_quidax_order_completed,
            "instant_order.cancelled": handle_quidax_order_cancelled,
            "deposit.successful": handle_quidax_deposit_successful,
            "withdraw.successful": handle_quidax_withdraw_successful,
            "withdraw.rejected": handle_quidax_withdraw_rejected,
            "wallet.updated": handle_quidax_wallet_updated
        }
        
        if event_type in handlers:
            await handlers[event_type](event_data, supabase)
        else:
            logger.info(f"ℹ️ Unhandled Quidax event: {event_type}")
        
        return {"status": "success", "message": "Webhook processed"}
        
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON in Quidax webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"❌ Quidax webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


async def handle_quidax_order_completed(event_data: dict, supabase: Client):
    """
    Handle completed instant order
    
    Flow:
    1. Verify order status from Quidax API
    2. Update onramp_transaction to 'completed'
    3. Initiate auto-withdrawal to user's WDK wallet
    """
    try:
        data = event_data.get("data", {})
        order_id = data.get("id")
        order_type = data.get("type")  # 'buy' or 'sell'
        
        logger.info(f"🔍 Processing Quidax order: {order_id}")
        
        # 🚨 DEFENSIVE: Use .limit(1) instead of .single() to avoid exceptions
        tx_result = supabase.table("onramp_transactions")\
            .select("*")\
            .eq("quidax_order_id", order_id)\
            .limit(1)\
            .execute()
        
        # ✅ CHECK: Does transaction exist?
        if not tx_result.data or len(tx_result.data) == 0:
            logger.warning(f"⚠️ No transaction found for Quidax order {order_id} - possibly test webhook or external order")
            
            # 📊 Update webhook record using EXISTING columns
            try:
                supabase.table("quidax_webhook_events").update({
                    "processed": True,  # ✅ Mark as handled
                    "processing_error": "No matching transaction - test webhook or external order",
                    "processed_at": datetime.utcnow().isoformat()
                }).eq("event_id", event_data.get("id")).execute()
            except Exception as update_err:
                logger.warning(f"Could not update webhook record: {update_err}")
            
            return  # Exit gracefully
        
        # ✅ GET TRANSACTION DATA (only once, no duplicate logic)
        tx = tx_result.data[0]
        user_id = tx["user_id"]
        crypto_amount = float(tx["net_to_user"])
        crypto_currency = tx["crypto_asset"]
        
        logger.info(f"✅ Found transaction for user {user_id[:8]}... - {crypto_amount} {crypto_currency}")
        
        # Verify order status from Quidax API (always re-query)
        from backend.services.quidax_service import QuidaxService
        quidax = QuidaxService(supabase)
        
        order_status = await quidax.get_order_status(order_id)
        
        if not order_status.get("success") or order_status.get("status") != "done":
            logger.warning(f"⚠️ Order {order_id} verification failed: {order_status.get('status')}")
            return
        
        logger.info(f"✅ Quidax order {order_id} verified as complete")
        
        # Update transaction status
        supabase.table("onramp_transactions").update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "webhook_received_at": datetime.utcnow().isoformat(),
            "metadata": json.dumps({
                **json.loads(tx.get("metadata", "{}")),
                "quidax_completed_event": data
            })
        }).eq("quidax_order_id", order_id).execute()
        
        logger.info(f"✅ Transaction {order_id} marked as completed")
        
        # 📊 Mark webhook as successfully processed
        try:
            supabase.table("quidax_webhook_events").update({
                "processed": True,
                "processed_at": datetime.utcnow().isoformat()
            }).eq("event_id", event_data.get("id")).execute()
        except Exception as update_err:
            logger.warning(f"Could not update webhook record: {update_err}")
        
        # 🚨 AUTO-WITHDRAWAL LOGIC
        # Get user's WDK wallet address for this crypto
        wallet_result = supabase.table("multi_chain_addresses")\
            .select("address")\
            .eq("user_id", user_id)\
            .eq("chain", _map_crypto_to_chain(crypto_currency))\
            .limit(1)\
            .execute()
        
        if wallet_result.data and len(wallet_result.data) > 0 and wallet_result.data[0].get("address"):
            destination_address = wallet_result.data[0]["address"]
            
            # Initiate withdrawal to user's wallet
            logger.info(f"🔄 Auto-withdrawing {crypto_amount} {crypto_currency} to {destination_address[:8]}...")
            
            withdrawal_result = await quidax.withdraw_crypto(
                user_id=user_id,
                currency=crypto_currency.lower(),
                amount=float(crypto_amount),
                destination_address=destination_address,
                network="trc20" if crypto_currency.upper() == "USDT" else None
            )
            
            if withdrawal_result.get("success"):
                logger.info(f"✅ Auto-withdrawal initiated: {withdrawal_result.get('withdrawal_id')}")
            else:
                logger.error(f"❌ Auto-withdrawal failed: {withdrawal_result.get('error')}")
        else:
            logger.warning(f"⚠️ No WDK wallet found for user {user_id[:8]}... - manual withdrawal required")
        
    except Exception as e:
        logger.error(f"❌ Failed to handle Quidax order completion: {e}")
        
        # 📊 Log the failure in webhook record
        try:
            # ✅ Get current retry count first
            webhook_record = supabase.table("quidax_webhook_events")\
                .select("retry_count")\
                .eq("event_id", event_data.get("id"))\
                .limit(1)\
                .execute()
            
            current_retries = 0
            if webhook_record.data and len(webhook_record.data) > 0:
                current_retries = webhook_record.data[0].get("retry_count", 0)
            
            # ✅ Update with incremented count
            supabase.table("quidax_webhook_events").update({
                "processed": False,
                "processing_error": str(e),
                "retry_count": current_retries + 1
            }).eq("event_id", event_data.get("id")).execute()
        except Exception as update_err:
            logger.warning(f"Could not log webhook error: {update_err}")


async def handle_quidax_order_cancelled(event_data: dict, supabase: Client):
    """Handle cancelled instant order"""
    try:
        data = event_data.get("data", {})
        order_id = data.get("id")
        
        supabase.table("onramp_transactions").update({
            "status": "cancelled",
            "metadata": json.dumps({
                "cancellation_reason": data.get("cancel_reason", "User cancelled"),
                "quidax_cancelled_event": data
            })
        }).eq("quidax_order_id", order_id).execute()
        
        logger.info(f"⚠️ Quidax order {order_id} cancelled")
        
    except Exception as e:
        logger.error(f"❌ Failed to handle Quidax order cancellation: {e}")


async def handle_quidax_deposit_successful(event_data: dict, supabase: Client):
    """Handle successful crypto deposit to Quidax wallet"""
    try:
        data = event_data.get("data", {})
        
        logger.info(f"💰 Quidax deposit successful: {data.get('currency')} - {data.get('amount')}")
        
        # Store deposit record
        # This would be used if we're holding crypto in Quidax long-term
        # For now, just log it
        
    except Exception as e:
        logger.error(f"❌ Failed to handle Quidax deposit: {e}")


async def handle_quidax_withdraw_successful(event_data: dict, supabase: Client):
    """
    Handle successful withdrawal
    
    This confirms crypto was sent to user's external wallet
    """
    try:
        data = event_data.get("data", {})
        withdrawal_id = data.get("id")
        
        # Find the corresponding onramp transaction
        # Update it to show withdrawal completed
        
        logger.info(f"✅ Quidax withdrawal {withdrawal_id} completed")
        
    except Exception as e:
        logger.error(f"❌ Failed to handle Quidax withdrawal success: {e}")


async def handle_quidax_withdraw_rejected(event_data: dict, supabase: Client):
    """Handle rejected withdrawal"""
    try:
        data = event_data.get("data", {})
        withdrawal_id = data.get("id")
        
        logger.warning(f"⚠️ Quidax withdrawal {withdrawal_id} rejected: {data.get('reject_reason')}")
        
        # TODO: Notify user about rejection
        # May need to credit their Seamount balance instead
        
    except Exception as e:
        logger.error(f"❌ Failed to handle Quidax withdrawal rejection: {e}")


async def handle_quidax_wallet_updated(event_data: dict, supabase: Client):
    """Handle wallet balance update"""
    try:
        data = event_data.get("data", {})
        
        logger.info(f"💼 Quidax wallet updated: {data.get('currency')} - {data.get('balance')}")
        
        # Could sync Quidax balances to our database here if needed
        
    except Exception as e:
        logger.error(f"❌ Failed to handle Quidax wallet update: {e}")


def _map_crypto_to_chain(crypto: str) -> str:
    """Map crypto symbol to blockchain name"""
    mapping = {
        "USDT": "tron",
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "ALGO": "algorand",
        "MATIC": "polygon"
    }
    return mapping.get(crypto.upper(), "tron")

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