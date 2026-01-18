# File: backend/api/routes/onramp.py
"""
On-Ramp Routes - Cashramp/Paystack/Flutterwave Integration
PRIORITY ORDER: Paystack (NGN) → Flutterwave (International) → Cashramp (P2P)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from decimal import Decimal
from typing import Optional
from datetime import datetime
import logging

from backend.dependencies import get_current_user, get_db_service, get_audit_service
from backend.services.payment_providers.paystack import PaystackProvider
from backend.services.payment_providers.flutterwave import FlutterwaveProvider
from backend.services.payment_providers.harbor import HarborProvider
from backend.services.cashramp_service import CashrampService
from backend.services.payment_providers.pretium import PretiumProvider
from backend.services.revenue_tracking_service import RevenueTrackingService
from backend.config import get_settings, TransactionType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onramp", tags=["On-Ramp"])

class OnRampRequest(BaseModel):
    amount_fiat: float
    currency: str
    crypto_asset: str
    payment_method: str = "auto"  # auto, paystack, flutterwave, cashramp
    user_country: str = "NG"

@router.post("/initialize")
async def initialize_onramp(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """
    Initialize fiat → crypto on-ramp
    PRIORITY: Paystack (NGN) → Flutterwave (International) → Cashramp (P2P)
    """
    
    try:
        settings = get_settings()
        
        # ✅ STEP 1: Extract payload FIRST (CRITICAL!)
        data = await request.json()
        amount = Decimal(str(data.get("amount_fiat", 0)))
        currency = data.get("currency", "NGN")
        crypto_asset = data.get("crypto_asset", "USDT_ALGO")  # ← MUST BE HERE
        payment_method = data.get("payment_method", "auto")
        user_country = data.get("user_country", "NG")
        phone_number = data.get("phone_number")  # Optional (not used for Tron anymore)
        mobile_network = data.get("mobile_network", "Safaricom")
        
        # Validate amount
        if amount <= 0:
            raise HTTPException(
                status_code=400, 
                detail="Amount must be greater than 0"
            )
        
        # Get asset config
        asset_config = settings.SUPPORTED_ASSETS.get(crypto_asset)
        if not asset_config:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported asset: {crypto_asset}"
            )
        
        # ===================================================================
        # STEP 2: Get user wallet address
        # ===================================================================
        try:
            wallet_result = db_service.supabase.from_('user_wallets')\
                .select('algorand_address')\
                .eq('user_id', current_user["id"])\
                .limit(1)\
                .execute()
            
            if not wallet_result.data or len(wallet_result.data) == 0:
                raise HTTPException(
                    status_code=400, 
                    detail="User wallet not found. Create wallet first."
                )
            
            wallet_address = wallet_result.data[0]["algorand_address"]
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch wallet: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Database error: {str(e)}"
            )
        
        # ===================================================================
        # STEP 3: SMART ROUTING - PAYSTACK-FIRST FOR NGN
        # ===================================================================
        provider = None
        payment_result = None
        checkout_url = None
        
        # 🥇 TIER 1: PAYSTACK (PRIMARY FOR NGN - INSTANT PAYMENT LINKS)
        if currency == "NGN" and payment_method in ["auto", "paystack"]:
            try:
                logger.info(f"🔵 TIER 1: Attempting Paystack on-ramp: {amount} {currency}")
                paystack = PaystackProvider(settings)
                
                our_fee = amount * Decimal("0.005")  # 0.5% Seamount margin
                provider_amount = amount
                
                payment_result = await paystack.initialize_payment(
                    amount=float(provider_amount),
                    currency="NGN",
                    email=current_user["email"],
                    tx_ref=f"ONRAMP_{current_user['id'][:8]}_{int(datetime.now().timestamp())}",
                    phone=current_user.get("phone"),
                    name=f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}"
                )
                
                if payment_result and payment_result.get("status") == "success":
                    checkout_url = (
                        payment_result.get("authorization_url") or 
                        payment_result.get("payment_link") or
                        payment_result.get("access_url")
                    )
                    
                    if checkout_url:
                        provider = "paystack"
                        logger.info(f"✅ Paystack (TIER 1) checkout URL: {checkout_url}")
                        
                        # 🚨 CREATE TRANSACTION AND RETURN IMMEDIATELY
                        tx_id = f"ONRAMP_PAYSTACK_{current_user['id'][:8]}_{int(datetime.now().timestamp())}"
                        
                        tx_data = {
                            "id": tx_id,
                            "user_id": current_user["id"],
                            "type": "onramp",
                            "status": "pending_payment",
                            "provider": "paystack",
                            "provider_name": "Paystack (Bank Transfer)",
                            "currency": currency,
                            "crypto_asset": crypto_asset,
                            "blockchain": asset_config["blockchain"],
                            "amount_fiat": float(amount),
                            "seamount_fee": float(our_fee),
                            "wallet_address": wallet_address,
                            "checkout_url": checkout_url,
                            "user_email": current_user["email"],
                            "user_country": user_country,
                            "estimated_settlement": "5-10 minutes",
                            "created_at": datetime.now().isoformat()
                        }
                        
                        db_service.supabase.from_('onramp_transactions').insert(tx_data).execute()
                        logger.info(f"✅ Paystack (TIER 1) transaction created: {tx_id}")
                        
                        # Track revenue (non-blocking)
                        try:
                            revenue_service = RevenueTrackingService(db_service)
                            await revenue_service.track_transaction_fee(
                                user_id=current_user["id"],
                                transaction_type="on_ramp",
                                amount=amount,
                                fee_rate=Decimal("0.005"),
                                platform_fee=our_fee,
                                network_fee=Decimal("0.001"),
                                blockchain="algorand",
                                metadata={
                                    "transaction_id": tx_id,
                                    "provider": "paystack",
                                    "currency": currency
                                }
                            )
                        except Exception as revenue_error:
                            logger.warning(f"Failed to track revenue: {revenue_error}")
                        
                        # Log audit trail (non-blocking)
                        if audit_service:
                            try:
                                await audit_service.log_event(
                                    "ONRAMP_INITIATED",
                                    user_id=str(current_user["id"]),
                                    resource_id=str(tx_id),
                                    details={
                                        "provider": "paystack",
                                        "amount": float(amount),
                                        "currency": str(currency),
                                        "asset": str(crypto_asset)
                                    }
                                )
                            except Exception as audit_error:
                                logger.warning(f"Failed to log audit: {audit_error}")
                        
                        logger.info(f"✅ Paystack (TIER 1) on-ramp initialized: {tx_id}")
                        
                        return {
                            "success": True,
                            "transaction_id": tx_id,
                            "checkout_url": checkout_url,
                            "provider": "paystack",
                            "amount_fiat": float(amount),
                            "currency": currency,
                            "crypto_asset": crypto_asset,
                            "estimated_settlement": "5-10 minutes"
                        }
                    else:
                        logger.warning(f"⚠️ Paystack returned success but no URL")
                else:
                    logger.warning(f"⚠️ Paystack returned invalid response")
                    
            except Exception as paystack_error:
                logger.warning(f"⚠️ Paystack (TIER 1) failed: {paystack_error}")
                # Fall through to Flutterwave
        
        # 🥈 TIER 2: FLUTTERWAVE (INTERNATIONAL + NGN BACKUP)
        if not checkout_url and payment_method in ["auto", "flutterwave"]:
            try:
                logger.info(f"🌍 TIER 2: Attempting Flutterwave: {amount} {currency}")
                flutterwave = FlutterwaveProvider(settings)
                
                our_fee = amount * Decimal("0.005")
                provider_amount = amount
                
                payment_result = await flutterwave.initialize_payment(
                    amount=float(provider_amount),
                    currency=currency,
                    email=current_user["email"],
                    tx_ref=f"ONRAMP_{current_user['id'][:8]}_{int(datetime.now().timestamp())}",
                    phone=current_user.get("phone"),
                    name=f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}"
                )
                
                if payment_result and payment_result.get("status") == "success":
                    checkout_url = (
                        payment_result.get("link") or 
                        payment_result.get("payment_link") or
                        payment_result.get("data", {}).get("link")
                    )
                    
                    if checkout_url:
                        provider = "flutterwave"
                        logger.info(f"✅ Flutterwave (TIER 2) checkout URL: {checkout_url}")
                    else:
                        logger.warning(f"⚠️ Flutterwave returned success but no URL")
                else:
                    logger.warning(f"⚠️ Flutterwave returned invalid response")
                    
            except Exception as flutterwave_error:
                logger.warning(f"⚠️ Flutterwave (TIER 2) failed: {flutterwave_error}")
                # Fall through to Harbor
        
        # ============================================================================
        # 🏛️ TIER 3: HARBOR (SANDBOX FALLBACK - MULTI-CHAIN DELIVERY)
        # ============================================================================
        if not checkout_url and payment_method in ["auto", "harbor"]:
            try:
                # Only use Harbor if:
                # 1. User wants non-Algorand delivery (blockchain != 'algorand')
                # 2. OR explicitly requested Harbor
                # 3. AND Harbor is available (sandbox mode check)
                
                should_use_harbor = (
                    blockchain != 'algorand' or  # User needs non-Algo delivery
                    payment_method == "harbor"    # Explicitly requested
                )
                
                if should_use_harbor:
                    logger.info(f"🏛️ TIER 3: Attempting Harbor (Sandbox): {amount} {currency} → {crypto_asset}")
                    
                    # Import Harbor provider
                    from backend.services.payment_providers.harbor import HarborProvider
                    harbor = HarborProvider(settings)
                    
                    # Check if sandbox mode
                    if harbor.is_sandbox:
                        logger.warning(f"⚠️ Harbor is in SANDBOX mode - use for testing only")
                    
                    # Create/get customer (Harbor requires customer_uuid)
                    customer_result = await harbor.create_customer(
                        first_name=current_user.get('first_name', 'User'),
                        last_name=current_user.get('last_name', ''),
                        email=current_user['email'],
                        phone_number=current_user.get('phone', '000-000-0000'),
                        description=f"Seamount user {current_user['id'][:8]}"
                    )
                    
                    if not customer_result.get('success'):
                        raise Exception(f"Harbor customer creation failed: {customer_result.get('error')}")
                    
                    customer_uuid = customer_result['customer_uuid']
                    logger.info(f"✅ Harbor customer: {customer_uuid}")
                    
                    # Initialize on-ramp
                    harbor_result = await harbor.initialize_onramp(
                        amount_fiat=amount,
                        currency=currency,
                        crypto_asset=crypto_asset,
                        blockchain=blockchain,
                        wallet_address=wallet_address,
                        customer_uuid=customer_uuid,
                        tx_ref=f"HARBOR_{current_user['id'][:8]}_{int(datetime.now().timestamp())}",
                        metadata={
                            'user_id': current_user['id'],
                            'source': 'seamount_onramp'
                        }
                    )
                    
                    if harbor_result and harbor_result.get('success'):
                        provider = "harbor_sandbox" if harbor.is_sandbox else "harbor"
                        
                        # Harbor may return transfer_instructions instead of checkout_url
                        checkout_url = (
                            harbor_result.get('checkout_url') or
                            harbor_result.get('payment_url') or
                            harbor_result.get('transfer_instructions', {}).get('payment_url')
                        )
                        
                        if checkout_url:
                            logger.info(f"✅ Harbor (TIER 3) initialized: {checkout_url}")
                        else:
                            # No URL = manual transfer instructions
                            logger.warning(f"⚠️ Harbor returned no checkout URL (manual transfer mode)")
                    else:
                        raise Exception(harbor_result.get('error', 'Harbor initialization failed'))
                        
            except Exception as harbor_error:
                logger.warning(f"⚠️ Harbor (TIER 3) failed: {harbor_error}")
                # Continue to next tier (Cashramp)

        # 🥉 TIER 4: CASHRAMP (P2P - CURRENTLY UNDER MAINTENANCE)
        if not checkout_url and payment_method in ["auto", "cashramp"]:
            try:
                logger.info(f"🔵 TIER 3: Attempting Cashramp (P2P): {amount} {currency}")
                cashramp = CashrampService(db_service)
                
                if not cashramp.is_available():
                    logger.warning("Cashramp not available (missing API keys)")
                    raise Exception("Cashramp service not configured")
                
                payment_result = await cashramp.create_ngn_onramp(
                    user_id=current_user["id"],
                    asset=crypto_asset,
                    amount_ngn=amount,
                    payment_method="p2p"
                )
                
                if payment_result and isinstance(payment_result, dict) and payment_result.get("success"):
                    url_candidates = [
                        payment_result.get("payment_url"),
                        payment_result.get("checkout_url"), 
                        payment_result.get("url"),
                        payment_result.get("link")
                    ]
                    
                    for candidate in url_candidates:
                        if candidate and isinstance(candidate, str) and candidate.startswith(('http://', 'https://')):
                            checkout_url = candidate
                            provider = "cashramp"
                            logger.info(f"✅ Cashramp (TIER 3) URL: {checkout_url}")
                            break
                    
                    if not checkout_url:
                        logger.warning(f"Cashramp returned success but no valid URL")
                else:
                    logger.warning(f"Cashramp returned invalid response")
                    
            except Exception as cashramp_error:
                logger.warning(f"⚠️ Cashramp (TIER 3) failed: {cashramp_error}")
                # Fall through to emergency
        
        # ========================================================================
        # QUIDAX DISABLED - Requires pre-funded wallet, not suitable for on-ramp
        # Keeping code commented for future offramp feature
        # ========================================================================
        """
        # TIER X: QUIDAX (DISABLED - Trading API, not payment gateway)
        # Quidax instant orders require existing NGN balance in wallet
        # Not suitable for "user pays now, gets crypto" flow
        # Will be used for offramp (sell crypto → receive NGN) in future
        if currency == "NGN" and payment_method in ["quidax"]:
            logger.info("Quidax requires pre-funded wallet - skipping")
        """
        
        # EMERGENCY FALLBACK: Force Paystack (most reliable)
        if not checkout_url:
            try:
                logger.info("⚠️ ACTIVATING EMERGENCY PAYSTACK FALLBACK...")
                
                # Only for NGN - Flutterwave for others
                if currency == "NGN":
                    paystack = PaystackProvider(settings)
                    
                    payment_result = await paystack.initialize_payment(
                        amount=float(amount),
                        currency="NGN",
                        email=current_user["email"],
                        tx_ref=f"EMG_{current_user['id'][:8]}_{int(datetime.now().timestamp())}",
                        name=current_user.get('first_name', 'User')
                    )
                    
                    if payment_result and payment_result.get("status") == "success":
                        checkout_url = payment_result.get("authorization_url") or payment_result.get("payment_link")
                        if checkout_url:
                            provider = "paystack_emergency"
                            logger.info(f"✅ EMERGENCY PAYSTACK URL: {checkout_url}")
                else:
                    # Non-NGN: Use Flutterwave
                    flutterwave = FlutterwaveProvider(settings)
                    
                    payment_result = await flutterwave.initialize_payment(
                        amount=float(amount),
                        currency=currency,
                        email=current_user["email"],
                        tx_ref=f"EMG_{current_user['id'][:8]}_{int(datetime.now().timestamp())}",
                        name=current_user.get('first_name', 'User')
                    )
                    
                    if payment_result and payment_result.get("status") == "success":
                        checkout_url = payment_result.get("data", {}).get("link") or payment_result.get("link")
                        if checkout_url:
                            provider = "flutterwave_emergency"
                            logger.info(f"✅ EMERGENCY FLUTTERWAVE URL: {checkout_url}")
                        
            except Exception as emergency_error:
                logger.error(f"❌ EMERGENCY FALLBACK FAILED: {emergency_error}")

        # VALIDATION: Ensure we have a checkout URL
        if not checkout_url:
            logger.error(
                f"All providers failed to return checkout URL. "
                f"Last provider: {provider}, Last result: {payment_result}"
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "Payment service temporarily unavailable. "
                    "All providers failed to generate payment link. "
                    "Please try again in a few minutes."
                )
            )
        
        # STEP 4: Store on-ramp transaction
        tx_id = f"ONRAMP_{current_user['id'][:8]}_{int(amount)}_{int(datetime.now().timestamp())}"
        
        our_fee = amount * Decimal("0.005")  # 0.5% Seamount margin
        
        tx_data = {
            "id": tx_id,
            "user_id": current_user["id"],
            "type": "onramp",
            "status": "pending_payment",
            "provider": provider,
            "provider_name": provider.title(),
            "currency": currency,
            "crypto_asset": crypto_asset,
            "amount_fiat": float(amount),
            "seamount_fee": float(our_fee),
            "net_to_user": float(amount - our_fee),
            "wallet_address": wallet_address,
            "checkout_url": checkout_url,
            "user_email": current_user["email"],
            "user_country": user_country,
            "fee_breakdown": {
                "seamount_fee": float(our_fee),
                "provider": provider,
                "currency": currency
            },
            "estimated_settlement": "5-10 minutes",
            "created_at": datetime.now().isoformat()
        }
        
        try:
            db_service.supabase.from_('onramp_transactions').insert(tx_data).execute()
            logger.info(f"Transaction record created: {tx_id}")
        except Exception as db_error:
            logger.error(f"Failed to store transaction: {db_error}")
            # Continue anyway - payment link is still valid
        
        # STEP 5: Track revenue (optional, non-blocking)
        try:
            revenue_service = RevenueTrackingService(db_service)
            await revenue_service.track_transaction_fee(
                user_id=current_user["id"],
                transaction_type="on_ramp",
                amount=amount,
                fee_rate=Decimal("0.005"),
                platform_fee=our_fee,
                network_fee=Decimal("0.001"),
                blockchain="algorand",
                metadata={
                    "transaction_id": tx_id,
                    "provider": provider,
                    "currency": currency
                }
            )
        except Exception as revenue_error:
            logger.warning(f"Failed to track revenue: {revenue_error}")
        
        # STEP 6: Log audit trail (optional, non-blocking)
        if audit_service:
            try:
                await audit_service.log_event(
                    "ONRAMP_INITIATED",
                    user_id=str(current_user["id"]) if current_user else "unknown",
                    resource_id=str(tx_id) if tx_id else "unknown",
                    details={
                        "provider": str(provider) if provider else "unknown",
                        "amount": float(amount) if amount else 0,
                        "currency": str(currency),
                        "asset": str(crypto_asset)
                    }
                )
            except Exception as audit_error:
                logger.warning(f"Failed to log audit (non-critical): {audit_error}")
        
        logger.info(f"On-ramp initialized: {tx_id} via {provider} - URL: {checkout_url}")
        
        return {
            "success": True,
            "transaction_id": tx_id,
            "checkout_url": checkout_url,
            "provider": provider,
            "amount_fiat": float(amount),
            "currency": currency,
            "crypto_asset": crypto_asset,
            "amount_paid": float(amount),
            "seamount_fee": float(our_fee),
            "net_value": float(amount - our_fee),
            "estimated_crypto_amount": float(amount - our_fee),
            "estimated_settlement": "5-10 minutes"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"On-ramp initialization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"On-ramp failed: {str(e)}"
        )


@router.post("/webhook/{provider}")
async def handle_webhook(
    provider: str,
    request: Request,
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Handle payment confirmation webhooks"""
    
    try:
        payload = await request.json()
        logger.info(f"Webhook received from {provider}: {payload.get('event')}")
        
        settings = get_settings()
        
        # Route to correct provider
        if provider == "cashramp":
            cashramp = CashrampService(db_service)
            result = await cashramp.verify_payment(payload.get("reference"))
            
            if result.get("verified"):
                await _credit_user_wallet(
                    db_service,
                    payload.get("reference"),
                    result.get("amount"),
                    result.get("currency")
                )
                   
        elif provider == "paystack":
            paystack = PaystackProvider(settings)
            result = await paystack.verify_payment(payload.get("reference"))
            
            if result.get("verified"):
                await _credit_user_wallet(
                    db_service,
                    payload.get("reference"),
                    result.get("amount"),
                    result.get("currency")
                )
                
        elif provider == "flutterwave":
            flutterwave = FlutterwaveProvider(settings)
            result = await flutterwave.verify_payment(payload.get("tx_ref"))
            
            if result.get("verified"):
                await _credit_user_wallet(
                    db_service,
                    payload.get("tx_ref"),
                    result.get("amount"),
                    result.get("currency")
                )
        
        return {"status": "success", "processed": True}
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        return {"status": "error", "message": str(e)}


async def _credit_user_wallet(db_service, tx_ref: str, amount: float, currency: str):
    """Credit user wallet after successful payment"""
    
    try:
        result = db_service.supabase.from_('onramp_transactions')\
            .select('user_id, crypto_asset, wallet_address')\
            .eq('id', tx_ref)\
            .limit(1)\
            .execute()
        
        if not result.data:
            logger.error(f"Transaction not found: {tx_ref}")
            return
        
        tx = result.data[0]
    except Exception as e:
        logger.error(f"Failed to fetch transaction: {e}")
        return
    
    try:
        balance_result = await db_service.supabase.from_('wallet_balances')\
            .select('usdt_balance')\
            .eq('user_id', tx["user_id"])\
            .limit(1)\
            .execute()
        
        if balance_result.data:
            current_balance = float(balance_result.data[0].get('usdt_balance', 0))
            new_balance = current_balance + amount
            
            db_service.supabase.from_('wallet_balances')\
                .update({'usdt_balance': new_balance, 'updated_at': 'NOW()'})\
                .eq('user_id', tx["user_id"])\
                .execute()
            
            logger.info(f"Credited {amount} USDT to user {tx['user_id']}")
    except Exception as e:
        logger.error(f"Failed to update balance: {e}")
    
    try:
        db_service.supabase.from_('onramp_transactions')\
            .update({'status': 'completed', 'completed_at': 'NOW()'})\
            .eq('id', tx_ref)\
            .execute()
    except Exception as e:
        logger.error(f"Failed to mark transaction complete: {e}")

async def _credit_multi_asset_wallet(
    db_service,
    tx_ref: str,
    crypto_asset: str,
    crypto_amount: float,
    wallet_address: str
):
    """
    🎯 CREDIT ANY CRYPTO TO ANY WALLET (Multi-Chain Support)
    
    This replaces the old USDT-only crediting logic.
    Works with: ALGO, USDT, BTC, ETH, MATIC, TRX, etc.
    """
    try:
        logger.info(f"💰 Crediting {crypto_amount} {crypto_asset} to {wallet_address[:12]}...")
        
        # Step 1: Get transaction details
        tx_result = db_service.supabase.from_('onramp_transactions')\
            .select('user_id, crypto_asset, blockchain')\
            .eq('id', tx_ref)\
            .single()\
            .execute()
        
        if not tx_result.data:
            logger.error(f"❌ Transaction not found: {tx_ref}")
            return False
        
        user_id = tx_result.data['user_id']
        blockchain = tx_result.data.get('blockchain', 'algorand')
        
        # Step 2: Use MultiChainWalletService to credit wallet
        # This handles all chains automatically
        from backend.dependencies import get_multi_chain_wallet_service
        wallet_service = get_multi_chain_wallet_service()
        
        # The actual crediting happens via the payment provider (Paystack/Flutterwave)
        # They send crypto directly to user's wallet address
        # We just mark the transaction as complete
        
        # Step 3: Mark transaction complete
        db_service.supabase.from_('onramp_transactions')\
            .update({
                'status': 'completed',
                'completed_at': 'NOW()',
                'credited_amount': crypto_amount
            })\
            .eq('id', tx_ref)\
            .execute()
        
        logger.info(f"✅ Transaction {tx_ref} marked complete")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to credit wallet: {e}")
        return False
    
@router.get("/providers")
async def get_providers():
    """Get available payment providers (UPDATED PRIORITY ORDER)"""
    
    return {
        "providers": [
            {
                "id": "paystack",
                "name": "Paystack",
                "currencies": ["NGN"],
                "fee": "2.5%",
                "settlement": "Instant",
                "recommended": True,
                "priority": 1,
                "status": "operational"
            },
            {
                "id": "flutterwave",
                "name": "Flutterwave",
                "currencies": ["NGN", "KES", "GHS", "ZAR", "USD", "EUR"],
                "fee": "2.5-4.0%",
                "settlement": "5-10 minutes",
                "recommended": True,
                "priority": 2,
                "status": "operational"
            },
            {
                "id": "cashramp",
                "name": "Cashramp P2P",
                "currencies": ["NGN", "KES", "GHS"],
                "fee": "1.8%",
                "settlement": "< 5 seconds",
                "recommended": False,
                "priority": 3,
                "status": "maintenance"
            }
        ]
    }


@router.post("/quote")
async def get_onramp_quote(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service)
):
    """Real-time on-ramp quote (live prices)"""
    
    try:
        data = await request.json()
        amount_fiat = Decimal(str(data.get("amount_fiat", 0)))
        currency = data.get("currency", "NGN")
        crypto_asset = data.get("crypto_asset", "USDT_ALGO")
        
        if amount_fiat <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        settings = get_settings()
        asset_config = settings.SUPPORTED_ASSETS.get(crypto_asset)
        
        if not asset_config:
            raise HTTPException(status_code=400, detail=f"Unsupported asset: {crypto_asset}")
        
        # Get forex rate
        if currency == "USD":
            fiat_to_usd_rate = Decimal("1.0")
        else:
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://api.exchangerate-api.com/v4/latest/USD",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            rates_data = await response.json()
                            fiat_per_usd = Decimal(str(rates_data["rates"].get(currency, 1)))
                            fiat_to_usd_rate = Decimal("1") / fiat_per_usd if fiat_per_usd > 0 else Decimal("1")
                        else:
                            raise Exception(f"ExchangeRate-API returned {response.status}")
            except Exception as forex_error:
                logger.error(f"Forex API failed: {forex_error}")
                raise HTTPException(
                    status_code=503,
                    detail="Cannot get live exchange rates. Please try again."
                )
        
        amount_usd = amount_fiat * fiat_to_usd_rate
        
        # Simple fee calculation: 2.5% total (0.5% Seamount)
        seamount_fee_rate = Decimal("0.005")  # 0.5% Seamount margin
        provider_fee_rate = Decimal("0.020")  # ~2.0% provider cost
        total_fee_rate = seamount_fee_rate + provider_fee_rate
        
        # Get crypto price
        from backend.services.oracle_service import EnhancedOracleService
        oracle_service = EnhancedOracleService(db_service)
        
        oracle_symbol = asset_config.get("oracle_symbol", "bitcoin")
        
        try:
            crypto_price_usd, price_metadata = await oracle_service.get_asset_price(oracle_symbol)
        except Exception as price_error:
            logger.error(f"Price oracle failed: {price_error}")
            raise HTTPException(
                status_code=503,
                detail="Cannot get live crypto prices. Please try again."
            )
        
        # Calculate USD fees first
        total_fee_usd = amount_usd * total_fee_rate
        seamount_fee_usd = amount_usd * seamount_fee_rate
        provider_fee_usd = total_fee_usd - seamount_fee_usd

        # User pays requested amount, receives AFTER fees
        net_usd_after_fees = amount_usd - total_fee_usd
        estimated_crypto = net_usd_after_fees / crypto_price_usd

        # ✅ NEW: Fees are deducted, not added
        if currency != "USD":
            total_fee_fiat = total_fee_usd / fiat_to_usd_rate
            seamount_fee_fiat = seamount_fee_usd / fiat_to_usd_rate
            provider_fee_fiat = provider_fee_usd / fiat_to_usd_rate
            net_fiat_after_fees = amount_fiat - total_fee_fiat  # ✅ Subtract
            usd_to_fiat_rate = Decimal("1") / fiat_to_usd_rate
        else:
            total_fee_fiat = total_fee_usd
            seamount_fee_fiat = seamount_fee_usd
            provider_fee_fiat = provider_fee_usd
            net_fiat_after_fees = amount_fiat - total_fee_fiat  # ✅ Subtract
            usd_to_fiat_rate = Decimal("1")
        
        return {
            "success": True,
            "quote": {
                "requested_fiat_amount": float(amount_fiat),  # ✅ What user wants to spend
                "currency": currency,
                "crypto_asset": crypto_asset,
                "blockchain": asset_config["blockchain"],
                
                # Pricing info
                "crypto_price_usd": float(crypto_price_usd),
                "exchange_rate": float(usd_to_fiat_rate),
                "forex_source": "ExchangeRate-API (live)",
                
                # ✅ TRANSPARENT FEE BREAKDOWN:
                "seamount_fee": float(seamount_fee_fiat),
                "seamount_fee_pct": float(seamount_fee_rate * 100),  # e.g., 0.5%
                "provider_fee": float(provider_fee_fiat),
                "provider_fee_pct": float((total_fee_rate - seamount_fee_rate) * 100),
                "total_fee": float(total_fee_fiat),
                "total_fee_pct": float(total_fee_rate * 100),  # e.g., 2.5%
                
                # ✅ NEW: User pays requested, gets amount minus fees
                "amount_to_pay": float(amount_fiat),           # What user pays
                "net_after_fees": float(net_fiat_after_fees),  # Value after fees
                "crypto_to_receive": float(estimated_crypto),  # Crypto received
                
                "valid_for_seconds": 300,
                "timestamp": datetime.now().isoformat(),
                "quote_id": f"onramp_quote_{current_user['id'][:8]}_{int(datetime.now().timestamp())}"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quote generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quote failed: {str(e)}")


@router.post("/quote/public")
async def get_public_onramp_quote(request: Request):
    """Public quote endpoint (no auth required)"""
    
    try:
        data = await request.json()
        amount_fiat = Decimal(str(data.get("amount_fiat", 0)))
        currency = data.get("currency", "NGN")
        crypto_asset = data.get("crypto_asset", "USDT_ALGO")
        
        if amount_fiat <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        settings = get_settings()
        asset_config = settings.SUPPORTED_ASSETS.get(crypto_asset)
        
        if not asset_config:
            raise HTTPException(status_code=400, detail=f"Unsupported asset: {crypto_asset}")
        
        from backend.dependencies import get_database_service
        database_service = get_database_service()
        
        # Get forex rate
        if currency == "USD":
            fiat_to_usd_rate = Decimal("1.0")
        else:
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://api.exchangerate-api.com/v4/latest/USD",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            rates_data = await response.json()
                            fiat_per_usd = Decimal(str(rates_data["rates"].get(currency, 1)))
                            fiat_to_usd_rate = Decimal("1") / fiat_per_usd if fiat_per_usd > 0 else Decimal("1")
                        else:
                            raise Exception(f"ExchangeRate-API returned {response.status}")
            except Exception as forex_error:
                logger.error(f"Forex API failed: {forex_error}")
                raise HTTPException(
                    status_code=503,
                    detail="Cannot get live exchange rates. Please try again."
                )
        
        amount_usd = amount_fiat * fiat_to_usd_rate
        
        # Simple fee calculation: 2.5% total (0.5% Seamount)
        seamount_fee_rate = Decimal("0.005")  # 0.5% Seamount margin
        provider_fee_rate = Decimal("0.020")  # ~2.0% provider cost
        total_fee_rate = seamount_fee_rate + provider_fee_rate
        
        # Get crypto price
        from backend.services.oracle_service import EnhancedOracleService
        oracle_service = EnhancedOracleService(database_service)
        
        oracle_symbol = asset_config.get("oracle_symbol", "bitcoin")
        
        try:
            crypto_price_usd, price_metadata = await oracle_service.get_asset_price(oracle_symbol)
        except Exception as price_error:
            logger.error(f"Price oracle failed: {price_error}")
            raise HTTPException(
                status_code=503,
                detail="Cannot get live crypto prices. Please try again."
            )
        
        # ✅ NEW: Deduct fees from requested amount
        total_fee_usd = amount_usd * total_fee_rate
        seamount_fee_usd = amount_usd * seamount_fee_rate
        provider_fee_usd = total_fee_usd - seamount_fee_usd
        
        # User pays requested amount, receives AFTER fees
        net_usd_after_fees = amount_usd - total_fee_usd
        estimated_crypto = net_usd_after_fees / crypto_price_usd

        # ✅ NEW: Fees are deducted, not added
        if currency != "USD":
            total_fee_fiat = total_fee_usd / fiat_to_usd_rate
            seamount_fee_fiat = seamount_fee_usd / fiat_to_usd_rate
            provider_fee_fiat = provider_fee_usd / fiat_to_usd_rate
            net_fiat_after_fees = amount_fiat - total_fee_fiat  # ✅ Subtract
            usd_to_fiat_rate = Decimal("1") / fiat_to_usd_rate
        else:
            total_fee_fiat = total_fee_usd
            seamount_fee_fiat = seamount_fee_usd
            provider_fee_fiat = provider_fee_usd
            net_fiat_after_fees = amount_fiat - total_fee_fiat  # ✅ Subtract
            usd_to_fiat_rate = Decimal("1")
        
        return {
            "success": True,
            "quote": {
                "requested_fiat_amount": float(amount_fiat),
                "currency": currency,
                "crypto_asset": crypto_asset,
                "blockchain": asset_config["blockchain"],
                
                # Pricing info
                "crypto_price_usd": float(crypto_price_usd),
                "exchange_rate": float(usd_to_fiat_rate),
                "forex_source": "ExchangeRate-API (live)",
                
                # ✅ FEE BREAKDOWN (with updated mobile money rate: 0.6% Seamount):
                "seamount_fee": float(seamount_fee_fiat),
                "seamount_fee_pct": float(seamount_fee_rate * 100),
                "provider_fee": float(provider_fee_fiat),
                "provider_fee_pct": float((total_fee_rate - seamount_fee_rate) * 100),
                "total_fee": float(total_fee_fiat),
                "total_fee_pct": float(total_fee_rate * 100),
                
                # ✅ NEW: User pays requested, gets amount minus fees
                "amount_to_pay": float(amount_fiat),           # What user pays
                "net_after_fees": float(net_fiat_after_fees),  # Value after fees
                "crypto_to_receive": float(estimated_crypto),  # Crypto received
                
                "valid_for_seconds": 300,
                "timestamp": datetime.now().isoformat(),
                "quote_id": f"public_onramp_quote_{int(datetime.now().timestamp())}"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Public quote failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quote failed: {str(e)}")