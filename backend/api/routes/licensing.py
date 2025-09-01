# File Location: backend/api/routes/licensing.py

import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

# Core dependencies
from supabase import Client
from dependencies import get_current_user, get_supabase_client
from models import (
    LicensePurchaseRequest, LicensePurchaseResponse, LicenseInfo,
    TierUpgradeRequest, LicenseUsageStats, TransactionFeeCalculation,
    LicenseTier
)
from services.licensing_service import LicensingService
from services.audit_service import AuditService
from services.notification_service import NotificationService
from config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/licensing", tags=["SMB Licensing"])

def get_licensing_service(
    supabase: Client = Depends(get_supabase_client)
) -> LicensingService:
    """Dependency to get licensing service instance"""
    settings = get_settings()
    
    # Initialize required services (in production, these would be injected)
    from services.audit_service import AuditService
    from services.notification_service import NotificationService
    from services.email_service import EmailService
    
    email_service = EmailService(settings)
    notification_service = NotificationService(email_service)
    audit_service = AuditService(supabase)
    
    return LicensingService(settings, supabase, audit_service, notification_service)

@router.get("/tiers", summary="Get available license tiers and pricing")
async def get_license_tiers(region: str = "nigeria"):
    """Get all available license tiers with pricing for specified region"""
    try:
        from config import BusinessModelConfig, PricingRegion
        
        # Convert string to enum safely
        try:
            pricing_region = PricingRegion(region.lower())
        except ValueError:
            pricing_region = PricingRegion.DEFAULT
        
        business_model = BusinessModelConfig()
        tiers_info = []
        
        for tier in LicenseTier:
            license_fee = business_model.calculate_license_fee(tier, pricing_region)
            transaction_rate = business_model.TRANSACTION_FEES[tier]
            employee_limit = business_model.EMPLOYEE_LIMITS[tier]
            discount = business_model.get_discount_percentage(tier)
            
            # Get currency for region
            currency_map = {
                PricingRegion.NIGERIA: "NGN",
                PricingRegion.KENYA: "KES", 
                PricingRegion.DEFAULT: "USD"
            }
            currency = currency_map.get(pricing_region, "USD")
            
            tier_info = {
                "tier": tier.value,
                "name": tier.value.title(),
                "license_fee": float(license_fee),
                "currency": currency,
                "transaction_rate": float(transaction_rate),
                "discount_percentage": discount,
                "employee_limit": employee_limit if employee_limit != float('inf') else None,
                "features": licensing_service._get_tier_features(tier) if 'licensing_service' in locals() else [],
                "recommended": tier == LicenseTier.PRO
            }
            tiers_info.append(tier_info)
        
        return {
            "tiers": tiers_info,
            "region": pricing_region.value,
            "individual_rate": float(business_model.INDIVIDUAL_BASE_RATE),
            "currency": currency
        }
        
    except Exception as e:
        logger.error(f"Failed to get license tiers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve license tiers")

@router.get("/my-license", response_model=Optional[LicenseInfo], summary="Get current user license")
async def get_my_license(
    current_user: Dict[str, Any] = Depends(get_current_user),
    licensing_service: LicensingService = Depends(get_licensing_service)
):
    """Get current user's active license information"""
    user_id = current_user.get("id")
    return await licensing_service.get_user_license(str(user_id))

@router.get("/usage-stats", response_model=Optional[LicenseUsageStats], summary="Get license usage statistics")
async def get_usage_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    licensing_service: LicensingService = Depends(get_licensing_service)
):
    """Get current month usage statistics for user's license"""
    user_id = current_user.get("id")
    return await licensing_service.get_license_usage_stats(str(user_id))

@router.post("/purchase", response_model=LicensePurchaseResponse, summary="Purchase SMB license")
async def purchase_license(
    request: LicensePurchaseRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    licensing_service: LicensingService = Depends(get_licensing_service)
):
    """Initiate SMB license purchase"""
    user_id = str(current_user.get("id"))
    user_email = current_user.get("email")
    
    if not user_email:
        raise HTTPException(status_code=400, detail="User email required for license purchase")
    
    # Validate employee count against tier limits
    from config import BusinessModelConfig
    business_model = BusinessModelConfig()
    employee_limit = business_model.EMPLOYEE_LIMITS.get(request.tier)
    
    if (request.employee_count and employee_limit and 
        employee_limit != float('inf') and request.employee_count > employee_limit):
        raise HTTPException(
            status_code=400, 
            detail=f"{request.tier.value.title()} tier supports up to {employee_limit} employees. Consider upgrading to a higher tier."
        )
    
    result = await licensing_service.initiate_license_purchase(user_id, user_email, request)
    
    # Log successful purchase initiation
    logger.info(f"License purchase initiated: {result.license_id} for user {user_id}")
    
    return result

@router.post("/calculate-fee", response_model=TransactionFeeCalculation, summary="Calculate transaction fee")
async def calculate_transaction_fee(
    amount: float,
    current_user: Dict[str, Any] = Depends(get_current_user),
    licensing_service: LicensingService = Depends(get_licensing_service)
):
    """Calculate transaction fee based on user's license tier"""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    user_id = str(current_user.get("id"))
    return licensing_service.calculate_smb_transaction_fee(user_id, Decimal(str(amount)))

@router.get("/savings-calculator", summary="Calculate potential savings by tier")
async def savings_calculator(
    annual_volume: float,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Calculate potential annual savings for each tier"""
    if annual_volume <= 0:
        raise HTTPException(status_code=400, detail="Annual volume must be positive")
    
    from config import BusinessModelConfig
    business_model = BusinessModelConfig()
    
    annual_volume_decimal = Decimal(str(annual_volume))
    individual_cost = annual_volume_decimal * business_model.INDIVIDUAL_BASE_RATE
    
    savings_by_tier = {}
    
    for tier in LicenseTier:
        # Get license fee (assume Nigeria for demo)
        from config import PricingRegion
        license_fee = business_model.calculate_license_fee(tier, PricingRegion.NIGERIA)
        
        # Calculate tier transaction costs
        tier_rate = business_model.TRANSACTION_FEES[tier]
        tier_transaction_cost = annual_volume_decimal * tier_rate
        total_tier_cost = license_fee + tier_transaction_cost
        
        # Calculate savings
        annual_savings = individual_cost - tier_transaction_cost
        net_savings = annual_savings - license_fee
        break_even_volume = license_fee / (business_model.INDIVIDUAL_BASE_RATE - tier_rate)
        
        savings_by_tier[tier.value] = {
            "license_fee": float(license_fee),
            "transaction_cost": float(tier_transaction_cost),
            "total_first_year_cost": float(total_tier_cost),
            "annual_savings": float(annual_savings),
            "net_first_year_savings": float(net_savings),
            "break_even_volume": float(break_even_volume),
            "transaction_rate": float(tier_rate),
            "discount_percentage": business_model.get_discount_percentage(tier)
        }
    
    return {
        "annual_volume": annual_volume,
        "individual_annual_cost": float(individual_cost),
        "individual_rate": float(business_model.INDIVIDUAL_BASE_RATE),
        "savings_by_tier": savings_by_tier
    }

# Webhook endpoint for payment completion (would typically be in webhooks.py)
@router.post("/webhooks/payment-completed", summary="Handle license payment completion")
async def handle_license_payment_completion(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    licensing_service: LicensingService = Depends(get_licensing_service)
):
    """Handle license payment completion webhook from Flutterwave"""
    try:
        transaction_id = payload.get("tx_ref")
        if not transaction_id or not transaction_id.startswith("LICENSE_"):
            return JSONResponse({"status": "ignored"})
        
        # Process license activation in background
        background_tasks.add_task(
            licensing_service.finalize_license_purchase,
            transaction_id
        )
        
        return JSONResponse({"status": "processing"})
        
    except Exception as e:
        logger.error(f"License payment webhook processing failed: {e}")
        return JSONResponse(
            status_code=500, 
            content={"status": "error", "message": "Failed to process payment"}
        )

@router.put("/upgrade", response_model=Dict[str, Any], summary="Upgrade license tier")
async def upgrade_license_tier(
    request: TierUpgradeRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    licensing_service: LicensingService = Depends(get_licensing_service)
):
    """Upgrade existing license to higher tier"""
    user_id = str(current_user.get("id"))
    user_email = current_user.get("email")
    
    if not user_email:
        raise HTTPException(status_code=400, detail="User email required for upgrade")
    
    # Check if user has existing license
    current_license = await licensing_service.get_user_license(user_id)
    if not current_license:
        raise HTTPException(status_code=404, detail="No active license found")
    
    # Validate upgrade path
    tier_hierarchy = [LicenseTier.BASIC, LicenseTier.PRO, LicenseTier.ENTERPRISE]
    current_tier_idx = tier_hierarchy.index(current_license.tier)
    target_tier_idx = tier_hierarchy.index(request.target_tier)
    
    if target_tier_idx <= current_tier_idx:
        raise HTTPException(
            status_code=400,
            detail="Can only upgrade to higher tier"
        )
    
    result = await licensing_service.initiate_tier_upgrade(
        user_id, user_email, request.target_tier, request.employee_count
    )
    
    logger.info(f"License upgrade initiated: {current_license.tier} -> {request.target_tier} for user {user_id}")
    
    return {
        "upgrade_id": result.license_id,
        "payment_link": result.payment_link,
        "current_tier": current_license.tier.value,
        "target_tier": request.target_tier.value,
        "amount": float(result.amount_due),
        "expires_at": result.expires_at.isoformat() if result.expires_at else None
    }

@router.post("/validate-usage", summary="Validate transaction against license limits")
async def validate_transaction_usage(
    amount: float,
    current_user: Dict[str, Any] = Depends(get_current_user),
    licensing_service: LicensingService = Depends(get_licensing_service)
):
    """Check if transaction is allowed under current license"""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    user_id = str(current_user.get("id"))
    
    try:
        is_valid, message = await licensing_service.validate_transaction_limits(
            user_id, Decimal(str(amount))
        )
        
        if not is_valid:
            return JSONResponse(
                status_code=403,
                content={
                    "allowed": False,
                    "message": message,
                    "requires_upgrade": "upgrade" in message.lower()
                }
            )
        
        return {
            "allowed": True,
            "message": "Transaction approved",
            "fee_calculation": licensing_service.calculate_smb_transaction_fee(
                user_id, Decimal(str(amount))
            )
        }
        
    except Exception as e:
        logger.error(f"Failed to validate transaction usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate transaction")

@router.delete("/cancel/{license_id}", summary="Cancel pending license purchase")
async def cancel_license_purchase(
    license_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    licensing_service: LicensingService = Depends(get_licensing_service)
):
    """Cancel pending license purchase"""
    user_id = str(current_user.get("id"))
    
    success = await licensing_service.cancel_license_purchase(user_id, license_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="License purchase not found or cannot be cancelled"
        )
    
    return {"message": "License purchase cancelled successfully"}

# Admin endpoints (would typically require admin role check)
@router.get("/admin/stats", summary="Get licensing statistics (Admin only)")
async def get_licensing_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    licensing_service: LicensingService = Depends(get_licensing_service)
):
    """Get overall licensing statistics (admin only)"""
    # TODO: Add admin role check using your role_check middleware
    
    try:
        stats = await licensing_service.get_admin_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get licensing stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve licensing statistics")