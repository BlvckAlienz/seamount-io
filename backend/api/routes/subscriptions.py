# File Location: backend/api/routes/subscriptions.py
# 🚨 MISSION CRITICAL: Paystack subscription management

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any, List
import logging
from datetime import datetime, timezone
import uuid
import hmac
import hashlib

from backend.dependencies import get_supabase_client, get_current_user
from backend.services.payment_providers.paystack import PaystackProvider
from backend.config import Settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/plans")
async def get_subscription_plans(supabase=Depends(get_supabase_client)):
    """✅ Get all active subscription plans"""
    try:
        result = supabase.from_("subscription_plans")\
            .select("*")\
            .eq("is_active", True)\
            .order("amount")\
            .execute()
        
        return {
            "success": True,
            "plans": result.data or []
        }
    except Exception as e:
        logger.error(f"[Plans Fetch] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-subscription")
async def get_user_subscription(
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """✅ Get current user's active subscription"""
    try:
        user_id = current_user['id']
        
        # 🚨 FIX: Check multiple valid subscription statuses
        # Paystack statuses: active, trialing, non-renewing (still valid until end date)
        valid_statuses = ["active", "trialing", "non-renewing"]
        
        # Get all subscriptions ordered by creation date
        result = supabase.from_("user_subscriptions")\
            .select("*, subscription_plans(*)")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        
        # Find first subscription with valid status
        active_subscription = None
        for sub in (result.data or []):
            logger.info(f"📋 User {user_id} subscription: {sub.get('id')} | Status: {sub.get('status')} | Plan: {sub.get('plan_code')}")
            if sub.get('status') in valid_statuses:
                active_subscription = sub
                logger.info(f"✅ Active subscription found: {sub.get('id')} with status '{sub.get('status')}'")
                break
        
        if not active_subscription and result.data:
            logger.warning(f"⚠️ User {user_id} has subscriptions but none are active. Statuses: {[s.get('status') for s in result.data]}")
        
        return {
            "success": True,
            "subscription": active_subscription,
            "has_active_subscription": active_subscription is not None
        }
    except Exception as e:
        logger.error(f"[Subscription Fetch] Error for user {current_user.get('id')}: {e}")
        # 🚨 CRITICAL: On error, return success=False so frontend can handle gracefully
        return {
            "success": False,
            "subscription": None,
            "has_active_subscription": False,
            "error": str(e)
        }

@router.post("/initialize")
async def initialize_subscription(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    🚨 STEP 1: Initialize Paystack subscription
    Returns payment link for user to complete payment
    """
    try:
        data = await request.json()
        plan_code = data.get('plan_code')
        
        if not plan_code:
            raise HTTPException(status_code=400, detail="Plan code required")
        
        user_id = current_user['id']
        email = current_user.get('email')
        
        # Get plan details
        plan_result = supabase.from_("subscription_plans")\
            .select("*")\
            .eq("plan_code", plan_code)\
            .single()\
            .execute()
        
        if not plan_result.data:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        plan = plan_result.data
        
        # Initialize Paystack subscription
        settings = Settings()
        paystack = PaystackProvider(settings)
        
        # Create subscription in Paystack
        paystack_response = await paystack.initialize_payment(
            amount=float(plan['amount']),
            currency="NGN",
            email=email,
            tx_ref=f"sub_{user_id}_{uuid.uuid4().hex[:8]}",
            phone=current_user.get('phone'),
            name=f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip()
        )
        
        if paystack_response.get('status') != 'success':
            raise HTTPException(status_code=400, detail=paystack_response.get('message'))
        
        # Store pending subscription
        subscription_data = {
            "user_id": user_id,
            "plan_id": plan['id'],
            "plan_code": plan_code,
            "status": "pending",
            "amount": plan['amount'],
            "currency": "NGN",
            "metadata": {
                "payment_link": paystack_response['payment_link'],
                "tx_ref": paystack_response['tx_ref']
            }
        }
        
        supabase.from_("user_subscriptions").insert(subscription_data).execute()
        
        logger.info(f"✅ Subscription initialized for user {user_id}: {plan_code}")
        
        return {
            "success": True,
            "payment_link": paystack_response['payment_link'],
            "message": "Complete payment to activate subscription"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Subscription Init] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel")
async def cancel_subscription(
    current_user: Dict = Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """❌ Cancel active subscription"""
    try:
        user_id = current_user['id']
        
        # Get active subscription
        result = supabase.from_("user_subscriptions")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("status", "active")\
            .single()\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="No active subscription")
        
        subscription = result.data
        
        # Update status
        supabase.from_("user_subscriptions")\
            .update({
                "status": "cancelled",
                "cancelled_at": datetime.now(timezone.utc).isoformat()
            })\
            .eq("id", subscription['id'])\
            .execute()
        
        logger.info(f"✅ Subscription cancelled for user {user_id}")
        
        return {
            "success": True,
            "message": "Subscription cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Subscription Cancel] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/paystack")
async def paystack_webhook(
    request: Request,
    supabase=Depends(get_supabase_client)
):
    """
    🚨 MISSION CRITICAL: Handle Paystack webhook events
    Events: charge.success, subscription.disable, invoice.payment_failed
    """
    try:
        # Verify Paystack signature
        settings = Settings()
        paystack_secret = settings.PAYSTACK_SECRET_KEY.get_secret_value()
        
        signature = request.headers.get('x-paystack-signature')
        body = await request.body()
        
        computed_signature = hmac.new(
            paystack_secret.encode(),
            body,
            hashlib.sha512
        ).hexdigest()
        
        if signature != computed_signature:
            logger.warning("❌ Invalid Paystack webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse event
        event_data = await request.json()
        event_type = event_data.get('event')
        data = event_data.get('data', {})
        
        logger.info(f"📥 Paystack webhook: {event_type}")
        
        # Handle events
        if event_type == 'charge.success':
            # Payment successful - activate subscription
            tx_ref = data.get('reference')
            
            # Find pending subscription by tx_ref
            result = supabase.from_("user_subscriptions")\
                .select("*")\
                .filter("metadata->>tx_ref", "eq", tx_ref)\
                .eq("status", "pending")\
                .execute()
            
            if result.data:
                subscription = result.data[0]
                
                # Activate subscription
                supabase.from_("user_subscriptions")\
                    .update({
                        "status": "active",
                        "paystack_customer_code": data.get('customer', {}).get('customer_code'),
                        "start_date": datetime.now(timezone.utc).isoformat(),
                        "next_payment_date": data.get('next_payment_date')
                    })\
                    .eq("id", subscription['id'])\
                    .execute()
                
                logger.info(f"✅ Subscription activated: {subscription['id']}")
        
        elif event_type == 'subscription.disable':
            # Subscription cancelled/disabled
            subscription_code = data.get('subscription_code')
            
            supabase.from_("user_subscriptions")\
                .update({
                    "status": "cancelled",
                    "cancelled_at": datetime.now(timezone.utc).isoformat()
                })\
                .eq("paystack_subscription_code", subscription_code)\
                .execute()
        
        elif event_type == 'invoice.payment_failed':
            # Payment failed
            subscription_code = data.get('subscription', {}).get('subscription_code')
            
            supabase.from_("user_subscriptions")\
                .update({"status": "payment_failed"})\
                .eq("paystack_subscription_code", subscription_code)\
                .execute()
        
        return {"success": True, "message": "Webhook processed"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Paystack Webhook] Error: {e}")
        return {"success": False, "message": str(e)}