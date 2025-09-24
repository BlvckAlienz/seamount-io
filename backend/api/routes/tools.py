from fastapi import APIRouter, HTTPException
from decimal import Decimal
import httpx
from typing import Dict, Any
import logging
from ...config import BusinessModelConfig, settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Country to currency mapping with regional pricing adjustments
COUNTRY_DATA = {
    "NG": {"currency": "NGN", "name": "Nigeria", "traditional_spread": 0.08, "region": "west_africa"},
    "KE": {"currency": "KES", "name": "Kenya", "traditional_spread": 0.07, "region": "east_africa"},
    "GH": {"currency": "GHS", "name": "Ghana", "traditional_spread": 0.075, "region": "west_africa"},
    "ZA": {"currency": "ZAR", "name": "South Africa", "traditional_spread": 0.06, "region": "southern_africa"},
    "CA": {"currency": "CAD", "name": "Canada", "traditional_spread": 0.04, "region": "north_america"},
    "TR": {"currency": "TRY", "name": "Turkey", "traditional_spread": 0.09, "region": "middle_east"},
    "CN": {"currency": "CNY", "name": "China", "traditional_spread": 0.05, "region": "asia"},
    "IN": {"currency": "INR", "name": "India", "traditional_spread": 0.065, "region": "asia"},
    "US": {"currency": "USD", "name": "United States", "traditional_spread": 0.03, "region": "north_america"},
    "UK": {"currency": "GBP", "name": "United Kingdom", "traditional_spread": 0.035, "region": "europe"},
    "AE": {"currency": "AED", "name": "United Arab Emirates", "traditional_spread": 0.045, "region": "middle_east"},
    "SG": {"currency": "SGD", "name": "Singapore", "traditional_spread": 0.04, "region": "asia"},
}

# Free FX Rate APIs (with fallbacks)
FX_API_SOURCES = [
    "https://api.exchangerate.host/latest?base=USD",
    "https://api.frankfurter.app/latest?from=USD",
    "https://open.er-api.com/v6/latest/USD"
]

async def get_live_fx_rates() -> Dict[str, float]:
    """Get live FX rates with fallback to multiple free APIs"""
    for api_url in FX_API_SOURCES:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    if 'rates' in data:
                        logger.info(f"Successfully fetched rates from {api_url}")
                        return data['rates']
        except Exception as e:
            logger.warning(f"Failed to fetch from {api_url}: {e}")
            continue
    
    # Fallback rates if all APIs fail
    return {
        "NGN": 1500.0, "KES": 150.0, "GHS": 12.0, "ZAR": 18.0,
        "CAD": 1.35, "TRY": 30.0, "CNY": 7.2, "INR": 83.0,
        "USD": 1.0, "GBP": 0.79, "AED": 3.67, "SGD": 1.34
    }

@router.get("/calculate-cross-border-savings")
async def calculate_cross_border_savings(
    amount: float, 
    from_country: str, 
    to_country: str
) -> Dict[str, Any]:
    """
    Calculate real savings based on live FX rates and business logic
    """
    try:
        # Validate countries
        if from_country not in COUNTRY_DATA or to_country not in COUNTRY_DATA:
            raise HTTPException(status_code=400, detail="Invalid country code")
        
        # Get live FX rates
        fx_rates = await get_live_fx_rates()
        
        from_data = COUNTRY_DATA[from_country]
        to_data = COUNTRY_DATA[to_country]
        
        # Convert amount to USD for calculation
        amount_usd = amount / fx_rates.get(from_data['currency'], 1.0)
        
        # Calculate traditional transfer cost (banks + FX spread)
        traditional_spread = max(from_data['traditional_spread'], to_data['traditional_spread'])
        traditional_fee_rate = Decimal("0.08")  # 8% average bank fee
        traditional_total_cost = amount_usd * (1 + Decimal(str(traditional_spread)) + traditional_fee_rate)
        
        # Calculate Seamount cost (using our business model)
        seamount_fee, details = BusinessModelConfig.calculate_on_ramp_fee(
            Decimal(str(amount_usd)), 
            is_licensed=False
        )
        seamount_total_cost = amount_usd + float(seamount_fee)
        
        # Calculate savings
        savings_amount = traditional_total_cost - seamount_total_cost
        savings_percentage = (savings_amount / traditional_total_cost) * 100
        
        # Generate educational message based on volatility
        volatility_insight = generate_volatility_insight(from_data, to_data, fx_rates)
        stablecoin_education = generate_stablecoin_education()
        
        return {
            "success": True,
            "amount_sent": amount,
            "from_country": from_data['name'],
            "to_country": to_data['name'],
            "from_currency": from_data['currency'],
            "to_currency": to_data['currency'],
            "fx_rate_usd_to_from": fx_rates.get(from_data['currency'], 1.0),
            "fx_rate_usd_to_to": fx_rates.get(to_data['currency'], 1.0),
            "traditional_cost_usd": float(traditional_total_cost),
            "seamount_cost_usd": seamount_total_cost,
            "savings_amount_usd": savings_amount,
            "savings_percentage": savings_percentage,
            "volatility_insight": volatility_insight,
            "stablecoin_education": stablecoin_education,
            "seamount_value_prop": "Seamount uses stablecoins to eliminate FX volatility and reduce costs by up to 80% compared to traditional banks.",
            "shareable_message": f"I save {savings_percentage:.1f}% on {amount} {from_data['currency']} transfers to {to_data['name']} with @SeamountApp! 🚀 No hidden FX spreads.",
            "timestamp": "2024-01-01T00:00:00Z"  # You'd use actual timestamp
        }
        
    except Exception as e:
        logger.error(f"Calculation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate savings")

def generate_volatility_insight(from_data: Dict, to_data: Dict, fx_rates: Dict) -> str:
    """Generate educational insight about FX volatility"""
    insights = [
        f"FX rates between {from_data['name']} and {to_data['name']} can fluctuate up to 5% daily.",
        "Traditional banks often hide 3-8% spreads in their exchange rates.",
        "Stablecoins maintain 1:1 USD peg, eliminating volatility during transfers.",
        f"Seamount's transparent pricing saves you from hidden bank fees in {from_data['currency']}-{to_data['currency']} corridors."
    ]
    return insights[hash(f"{from_data['name']}{to_data['name']}") % len(insights)]

def generate_stablecoin_education() -> str:
    """Generate educational content about stablecoins"""
    education_points = [
        "Stablecoins are digital currencies pegged to stable assets like USD",
        "They enable instant, low-cost cross-border transfers without banks",
        "Seamount uses regulated stablecoins for maximum security and compliance",
        "No volatility risk during transfer - value stays constant in USD terms"
    ]
    return " • ".join(education_points)

@router.get("/supported-countries")
async def get_supported_countries():
    """Get list of supported countries for the calculator"""
    return {
        "countries": [
            {"code": code, "name": data["name"], "currency": data["currency"], "region": data["region"]}
            for code, data in COUNTRY_DATA.items()
        ]
    }