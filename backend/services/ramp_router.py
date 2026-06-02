# File: backend/services/ramp_router.py
"""
RampRouter — single source of truth for currency → provider routing.
Never expose provider names to the frontend; route silently server-side.
"""
from decimal import Decimal
from typing import Literal

# ── Routing table ──────────────────────────────────────────────────────────────
CURRENCY_TO_PROVIDER: dict[str, str] = {
    "NGN": "busha",
    "KES": "busha",
    "GHS": "kotani",
    "UGX": "kotani",
    "TZS": "kotani",
    "RWF": "kotani",
    "ZMW": "kotani",
    "XOF": "kotani",
    "XAF": "kotani",
    # Flutterwave-backed currencies (existing onramp.py handles these)
    "ZAR": "flutterwave",
    "USD": "flutterwave",
    "EUR": "flutterwave",
    "GBP": "flutterwave",
}

# Info returned to frontend for UI labelling
CURRENCY_INFO: dict[str, dict] = {
    "NGN": {"name": "Nigerian Naira",      "symbol": "₦",    "flag": "🇳🇬", "provider_label": "Busha",      "pay_in": "bank_account"},
    "KES": {"name": "Kenyan Shilling",     "symbol": "KSh",  "flag": "🇰🇪", "provider_label": "Busha",      "pay_in": "bank_account"},
    "GHS": {"name": "Ghanaian Cedi",       "symbol": "GH₵",  "flag": "🇬🇭", "provider_label": "Kotani Pay", "pay_in": "mobile_money"},
    "UGX": {"name": "Ugandan Shilling",    "symbol": "USh",  "flag": "🇺🇬", "provider_label": "Kotani Pay", "pay_in": "mobile_money"},
    "TZS": {"name": "Tanzanian Shilling",  "symbol": "TSh",  "flag": "🇹🇿", "provider_label": "Kotani Pay", "pay_in": "mobile_money"},
    "RWF": {"name": "Rwandan Franc",       "symbol": "FRw",  "flag": "🇷🇼", "provider_label": "Kotani Pay", "pay_in": "mobile_money"},
    "ZMW": {"name": "Zambian Kwacha",      "symbol": "ZK",   "flag": "🇿🇲", "provider_label": "Kotani Pay", "pay_in": "mobile_money"},
    "XOF": {"name": "West African CFA",    "symbol": "CFA",  "flag": "🌍",  "provider_label": "Kotani Pay", "pay_in": "mobile_money"},
    "XAF": {"name": "Central African CFA", "symbol": "FCFA", "flag": "🌍",  "provider_label": "Kotani Pay", "pay_in": "mobile_money"},
    "ZAR": {"name": "South African Rand",  "symbol": "R",    "flag": "🇿🇦", "provider_label": "Flutterwave","pay_in": "redirect"},
}

MARKUP_PCT = Decimal("0.025")  # 2.5% — single source of truth


def get_provider(currency: str) -> str:
    provider = CURRENCY_TO_PROVIDER.get(currency.upper())
    if not provider:
        raise ValueError(f"Currency '{currency}' is not supported for on/off-ramp.")
    return provider


def get_currency_info(currency: str) -> dict:
    return CURRENCY_INFO.get(currency.upper(), {})


def get_busha_service(settings) -> "BushaService":        # noqa: F821
    from backend.services.busha_service import BushaService
    sk = settings.BUSHA_SECRET_KEY
    secret = sk.get_secret_value() if hasattr(sk, "get_secret_value") else sk
    return BushaService(
        secret_key=secret,
        environment=getattr(settings, "BUSHA_ENVIRONMENT", "sandbox"),
    )


def get_kotani_service(settings) -> "KotaniService":      # noqa: F821
    from backend.services.kotani_service import KotaniService
    ak  = settings.KOTANI_API_KEY
    wsk = settings.KOTANI_WEBHOOK_SECRET
    api_key        = ak.get_secret_value()  if hasattr(ak,  "get_secret_value") else (ak  or "")
    webhook_secret = wsk.get_secret_value() if hasattr(wsk, "get_secret_value") else (wsk or "")
    return KotaniService(
        api_key=api_key,
        webhook_secret=webhook_secret,
        environment=getattr(settings, "KOTANI_ENVIRONMENT", "sandbox"),
    )