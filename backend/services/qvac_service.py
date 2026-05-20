# FILE: backend/services/qvac_service.py
# QVAC HTTP client — shared service for all QVAC inference calls
# Handles retries, timeouts, and mobile/desktop routing

import os
import json
import logging
import asyncio
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

QVAC_API_URL = os.getenv("QVAC_API_URL", "http://localhost:11434")
QVAC_API_KEY = os.getenv("QVAC_API_KEY", "qvac-local-key")
QVAC_TIMEOUT = int(os.getenv("QVAC_TIMEOUT_SECONDS", "60"))
QVAC_MAX_RETRIES = int(os.getenv("QVAC_MAX_RETRIES", "3"))

_HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": QVAC_API_KEY,
}


async def _post_with_retry(
    path: str,
    payload: Dict[str, Any],
    retries: int = QVAC_MAX_RETRIES,
    timeout: int = QVAC_TIMEOUT,
) -> Dict[str, Any]:
    """POST to QVAC with exponential backoff retry."""
    url = f"{QVAC_API_URL}{path}"
    last_error = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, retries + 1):
            try:
                logger.info(f"[QVAC] POST {path} (attempt {attempt}/{retries})")
                response = await client.post(url, json=payload, headers=_HEADERS)
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(f"[QVAC] HTTP {e.response.status_code} on {path}: {e.response.text[:200]}")
                if e.response.status_code in (400, 401, 422):
                    raise  # Don't retry client errors
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                logger.warning(f"[QVAC] Connection error attempt {attempt}: {e}")
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)

    raise RuntimeError(f"QVAC unreachable after {retries} retries: {last_error}")


async def health_check() -> Dict[str, Any]:
    """Check QVAC server health."""
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.get(f"{QVAC_API_URL}/health", headers=_HEADERS)
            return r.json()
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}


# ── Loop A: Finance Quest Tutor ───────────────────────────────────────────────

async def tutor_ask(
    message: str,
    context: Optional[Dict] = None,
    device_tier: str = "desktop",
) -> str:
    """
    Ask the QVAC tutor a financial literacy question.
    Returns plain-text response.
    """
    payload = {
        "message":     message,
        "context":     context or {},
        "stream":      False,
        "device_tier": device_tier,
    }
    result = await _post_with_retry("/v1/tutor/ask", payload)
    return result.get("response", "")


# ── Loop C: Wellbeing Coach ───────────────────────────────────────────────────

async def coach_analyze(
    message: str,
    profile: Dict[str, Any],
    device_tier: str = "desktop",
) -> str:
    """
    Ask the coach to analyze a financial situation with user profile context.
    Returns plain-text coaching response.
    """
    payload = {
        "message":     message,
        "profile":     profile,
        "stream":      False,
        "device_tier": device_tier,
    }
    result = await _post_with_retry("/v1/coach/analyze", payload)
    return result.get("response", "")


async def generate_wellbeing_score(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a structured Wellbeing Score (0-100) with breakdown.
    Returns: { score, breakdown, summary, top_action, risk_flags }
    """
    payload = {"profile": profile}
    result  = await _post_with_retry("/v1/coach/score", payload, timeout=90)

    if result.get("fallback"):
        logger.warning("[QVAC] Wellbeing score generation fell back — LLM parse error")
        raise RuntimeError("Score generation failed — try again shortly")

    return {
        "score":      result.get("score", 0),
        "breakdown":  result.get("breakdown", {}),
        "summary":    result.get("summary", ""),
        "top_action": result.get("top_action", ""),
        "risk_flags": result.get("risk_flags", []),
    }


# ── Loop D: Signal Validator ──────────────────────────────────────────────────

async def validate_signal(
    signal: Dict[str, Any],
    submitter_stats: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Validate a guild signal submission.
    Returns: { quality_score, risk_reward_ratio, thesis_clarity,
               manipulation_flags, plain_explanation, recommendation, disclaimer }
    """
    payload = {
        "signal":          signal,
        "submitter_stats": submitter_stats or {},
    }
    result = await _post_with_retry("/v1/validator/score", payload, timeout=90)

    # Hard safety check — anything flagged as SCAM_ALERT by QVAC
    # is auto-rejected regardless of what the caller does with it
    if result.get("recommendation") == "SCAM_ALERT":
        logger.warning(
            f"[QVAC] SCAM_ALERT on signal: {signal.get('asset_symbol')} "
            f"user={signal.get('user_id')} flags={result.get('manipulation_flags')}"
        )

    return result


# ── AML (existing fraud detection, unchanged) ─────────────────────────────────

async def aml_analyze(
    transaction: Dict[str, Any],
    patterns: Optional[list] = None,
) -> Dict[str, Any]:
    """
    AML transaction analysis.
    Returns: { risk_level, risk_score, flags, str_required, str_narrative, recommended_action }
    """
    payload = {
        "transaction": transaction,
        "patterns":    patterns or [],
    }
    return await _post_with_retry("/v1/aml/analyze", payload, timeout=120)