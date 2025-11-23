# 📍 CREATE NEW FILE: backend/services/revenue_projections.py
"""
Revenue projections with new competitive fee structure
"""

from decimal import Decimal
from typing import Dict

def calculate_revenue_projections() -> Dict:
    """
    Compare old vs new fee structure revenue
    """
    
    # Assumptions
    total_users = 1000
    avg_swap_amount = Decimal("100")
    swaps_per_user_per_month = 4
    
    # Old model (1.2% flat fee)
    old_fee_rate = Decimal("0.012")
    old_adoption = Decimal("0.30")  # 30% adoption
    old_active_users = int(total_users * old_adoption)
    old_monthly_volume = old_active_users * avg_swap_amount * swaps_per_user_per_month
    old_revenue = old_monthly_volume * old_fee_rate
    old_annual = old_revenue * 12
    
    # New model (0.3-0.8% avg = 0.5% effective)
    new_avg_fee_rate = Decimal("0.005")
    new_adoption = Decimal("0.80")  # 80% adoption
    new_swaps_per_user = 6  # More frequent due to lower fees
    new_active_users = int(total_users * new_adoption)
    new_monthly_volume = new_active_users * avg_swap_amount * new_swaps_per_user
    new_revenue = new_monthly_volume * new_avg_fee_rate
    new_annual = new_revenue * 12
    
    return {
        "old_model": {
            "fee_rate": "1.2%",
            "adoption": "30%",
            "active_users": old_active_users,
            "monthly_volume": float(old_monthly_volume),
            "monthly_revenue": float(old_revenue),
            "annual_revenue": float(old_annual)
        },
        "new_model": {
            "avg_fee_rate": "0.5%",
            "adoption": "80%",
            "active_users": new_active_users,
            "monthly_volume": float(new_monthly_volume),
            "monthly_revenue": float(new_revenue),
            "annual_revenue": float(new_annual)
        },
        "comparison": {
            "revenue_gain": float(new_annual - old_annual),
            "percentage_gain": float((new_annual - old_annual) / old_annual * 100),
            "volume_increase": float((new_monthly_volume - old_monthly_volume) / old_monthly_volume * 100)
        }
    }

# Example output:
# {
#   "old_model": {
#     "monthly_revenue": 1440,
#     "annual_revenue": 17280
#   },
#   "new_model": {
#     "monthly_revenue": 2400,
#     "annual_revenue": 28800
#   },
#   "comparison": {
#     "revenue_gain": 11520,
#     "percentage_gain": 67%,
#     "volume_increase": 300%
#   }
# }