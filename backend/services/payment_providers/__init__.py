# File: backend/services/payment_providers/__init__.py
"""
Payment Provider Registry
Supports: Flutterwave, Paystack, Cashramp, Pretium
"""

from .flutterwave import FlutterwaveProvider
from .paystack import PaystackProvider

# Import Pretium
try:
    from .pretium import PretiumProvider
    PRETIUM_AVAILABLE = True
except ImportError as e:
    import logging
    logging.warning(f"⚠️ Pretium provider unavailable: {e}")
    PretiumProvider = None
    PRETIUM_AVAILABLE = False

__all__ = [
    "FlutterwaveProvider",
    "PaystackProvider",
    "PretiumProvider",
    "PRETIUM_AVAILABLE"
]