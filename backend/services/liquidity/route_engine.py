# FILE: backend/services/liquidity/route_engine.py

import logging
import os
from typing import Any, Dict, List
from urllib.parse import urlencode

from backend.dependencies import get_supabase_client

logger = logging.getLogger(__name__)

# ── Transak-supported fiat currencies ─────────────────────────
TRANSAK_SUPPORTED_FIATS = {
    "KES", "NGN", "GHS", "UGX", "TZS", "ZAR",
    "USD", "GBP", "EUR", "INR", "PHP"
}

# ── Tokens supported via Coinbase Onramp (USDC on Base only) ──
COINBASE_SUPPORTED_TOKENS = {"USDC_ETH", "USDC_POLYGON", "USDC_SOLANA"}


async def find_best_route(
    token: str,
    fiat_currency: str,
    fiat_amount: float,
    payment_methods: List[str]
) -> List[Dict[str, Any]]:
    """
    Given a user's context, return all available on-ramp routes
    sorted by cheapest fee first, then fastest time.

    Route priority:
      1. P2P Merchant   — cheapest (0.3% platform fee only)
      2. Transak        — bank transfer ~1%, card ~3.5%
      3. MoonPay        — ~1–4.5% via WDK protocol
      4. Coinbase       — 0% fee but USDC on Base only
    """
    routes: List[Dict[str, Any]] = []

    # ── Route 1: P2P Merchant ──────────────────────────────────
    p2p_route = await _check_p2p_merchants(token, fiat_currency, fiat_amount, payment_methods)
    if p2p_route:
        routes.append(p2p_route)

    # ── Route 2: Transak ──────────────────────────────────────
    if fiat_currency in TRANSAK_SUPPORTED_FIATS:
        is_bank = "bank_transfer" in payment_methods or "Bank Transfer" in payment_methods
        routes.append({
            "provider": "transak",
            "estimated_fee_pct": 1.0 if is_bank else 3.5,
            "estimated_time_mins": 30 if is_bank else 5,
            "metadata": {
                "widget_url": _build_transak_url(token, fiat_currency, fiat_amount),
                "payment_type": "bank_transfer" if is_bank else "card"
            }
        })

    # ── Route 3: MoonPay (via WDK) ────────────────────────────
    routes.append({
        "provider": "moonpay",
        "estimated_fee_pct": 1.0,
        "estimated_time_mins": 10,
        "metadata": {
            "wdk_protocol": "wdk-protocol-fiat-moonpay",
            "note": "Integrated via Tether WDK"
        }
    })

    # ── Route 4: Coinbase Onramp (USDC on Base — 0% fee) ──────
    if token in COINBASE_SUPPORTED_TOKENS:
        routes.append({
            "provider": "coinbase",
            "estimated_fee_pct": 0.0,
            "estimated_time_mins": 5,
            "metadata": {
                "note": "USDC on Base only. Zero platform fee.",
                "onramp_url": _build_coinbase_url(fiat_amount)
            }
        })

    # Sort: cheapest fee first, then fastest time as tiebreaker
    routes.sort(key=lambda r: (r["estimated_fee_pct"], r["estimated_time_mins"]))

    logger.info(
        f"[Liquidity] Routes for {token}/{fiat_currency} "
        f"amount={fiat_amount}: {[r['provider'] for r in routes]}"
    )
    return routes


# ── INTERNAL HELPERS ──────────────────────────────────────────

async def _check_p2p_merchants(
    token: str,
    fiat_currency: str,
    fiat_amount: float,
    payment_methods: List[str]
) -> Dict[str, Any] | None:
    """
    Query active listings matching token, fiat, and amount range.
    Returns a route dict if at least one online merchant matches,
    otherwise returns None so the caller falls through to the next route.
    """
    try:
        supabase = get_supabase_client()

        res = supabase.table("p2p_listings") \
            .select("id, price_per_token, available_amount, payment_methods, p2p_merchants(is_online, completion_rate)") \
            .eq("token", token) \
            .eq("fiat_currency", fiat_currency) \
            .eq("is_active", True) \
            .lte("min_order_fiat", fiat_amount) \
            .gte("max_order_fiat", fiat_amount) \
            .order("price_per_token", desc=False) \
            .execute()

        listings = res.data or []

        # Filter: merchant must be online AND support at least one
        # of the user's available payment methods
        matched = [
            l for l in listings
            if _is_online(l) and _has_matching_method(l, payment_methods)
        ]

        if not matched:
            return None

        best = matched[0]
        return {
            "provider": "p2p_merchant",
            "estimated_fee_pct": 0.3,
            "estimated_time_mins": 15,
            "metadata": {
                "listing_count": len(matched),
                "best_price": best["price_per_token"],
                "top_listing_id": best["id"]
            }
        }

    except Exception as e:
        logger.error(f"[Liquidity] P2P merchant check failed: {e}")
        return None


def _is_online(listing: Dict[str, Any]) -> bool:
    merchant = listing.get("p2p_merchants")
    if isinstance(merchant, list):
        return bool(merchant[0].get("is_online")) if merchant else False
    if isinstance(merchant, dict):
        return bool(merchant.get("is_online"))
    return False


def _has_matching_method(listing: Dict[str, Any], user_methods: List[str]) -> bool:
    listing_methods: List[str] = listing.get("payment_methods") or []
    listing_lower = [m.lower() for m in listing_methods]
    return any(um.lower() in listing_lower for um in user_methods)


def _build_transak_url(token: str, fiat_currency: str, fiat_amount: float) -> str:
    # Token display name for Transak (strip chain suffix e.g. USDT_TRON → USDT)
    crypto_code = token.split("_")[0]
    params = {
        "apiKey": os.getenv("TRANSAK_API_KEY", ""),
        "environment": "PRODUCTION",
        "cryptoCurrencyCode": crypto_code,
        "fiatCurrency": fiat_currency,
        "fiatAmount": str(fiat_amount),
        "networks": "tron,polygon,ethereum,solana",
        "themeColor": "0066FF"
    }
    return f"https://global.transak.com/?{urlencode(params)}"


def _build_coinbase_url(fiat_amount: float) -> str:
    import json
    dest = json.dumps([{"assets": ["USDC"], "supportedNetworks": ["base"]}])
    params = {
        "appId": os.getenv("COINBASE_APP_ID", ""),
        "destinationWallets": dest,
        "presetFiatAmount": str(fiat_amount)
    }
    return f"https://pay.coinbase.com/buy/select-asset?{urlencode(params)}"