import logging
from decimal import Decimal
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

router = APIRouter()
logger = logging.getLogger(__name__)

# Traditional bank fee structure (5-8%)
TRADITIONAL_FEES = {
    "NG": {"US": 0.075, "UK": 0.070, "KE": 0.065, "GH": 0.060, "SA": 0.070, "CA": 0.065},
    "KE": {"US": 0.080, "UK": 0.075, "NG": 0.065, "GH": 0.060, "SA": 0.075, "CA": 0.070},
    "GH": {"US": 0.070, "UK": 0.065, "NG": 0.060, "KE": 0.060, "SA": 0.065, "CA": 0.060},
    "SA": {"US": 0.075, "UK": 0.070, "NG": 0.065, "KE": 0.065, "GH": 0.065, "CA": 0.070},
    "CA": {"US": 0.065, "UK": 0.070, "NG": 0.075, "KE": 0.075, "GH": 0.075, "SA": 0.075},
    "default": 0.065
}

# Seamount premium fees (3%)
SEAMOUNT_FEES = {
    "NG": {"US": 0.030, "UK": 0.030, "KE": 0.025, "GH": 0.025, "SA": 0.030, "CA": 0.030},
    "KE": {"US": 0.030, "UK": 0.030, "NG": 0.025, "GH": 0.025, "SA": 0.030, "CA": 0.030},
    "GH": {"US": 0.030, "UK": 0.030, "NG": 0.025, "KE": 0.025, "SA": 0.030, "CA": 0.030},
    "SA": {"US": 0.030, "UK": 0.030, "NG": 0.025, "KE": 0.025, "GH": 0.025, "CA": 0.030},
    "CA": {"US": 0.025, "UK": 0.030, "NG": 0.030, "KE": 0.030, "GH": 0.030, "SA": 0.030},
    "default": 0.030
}

@router.get("/calculate-savings")
async def calculate_savings(amount: float, from_country: str, to_country: str) -> Dict[str, Any]:
    """
    Calculate savings between traditional methods and Seamount
    """
    try:
        amount_dec = Decimal(str(amount))
        
        # Get traditional fee
        traditional_fee_rate = TRADITIONAL_FEES.get(from_country, {}).get(
            to_country, TRADITIONAL_FEES["default"]
        )
        traditional_fee = amount_dec * Decimal(str(traditional_fee_rate))
        
        # Get Seamount fee
        seamount_fee_rate = SEAMOUNT_FEES.get(from_country, {}).get(
            to_country, SEAMOUNT_FEES["default"]
        )
        seamount_fee = amount_dec * Decimal(str(seamount_fee_rate))
        
        # Calculate savings
        savings = traditional_fee - seamount_fee
        savings_percentage = ((traditional_fee - seamount_fee) / traditional_fee) * 100
        
        return {
            "amount": float(amount_dec),
            "from_country": from_country,
            "to_country": to_country,
            "traditional_fee": float(traditional_fee),
            "traditional_fee_rate": traditional_fee_rate * 100,
            "seamount_fee": float(seamount_fee),
            "seamount_fee_rate": seamount_fee_rate * 100,
            "savings": float(savings),
            "savings_percentage": float(savings_percentage),
            "shareable_message": f"I just saved ${savings:.2f} ({savings_percentage:.1f}%) on cross-border transfers with @SeamountApp! 🚀"
        }
        
    except Exception as e:
        logger.error(f"Savings calculation failed: {e}")
        raise HTTPException(status_code=500, detail="Could not calculate savings")

@router.post("/generate-share-image")
async def generate_share_image(amount: float, savings: float, from_country: str, to_country: str):
    """
    Generate a shareable image for social media
    """
    # This would integrate with a service like Cloudinary or generate image server-side
    return {"image_url": f"https://api.seamount.io/tools/share-image?amount={amount}&savings={savings}&from={from_country}&to={to_country}"}