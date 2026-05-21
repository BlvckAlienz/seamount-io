# FILE: backend/services/qvac_service.py
# QVAC HTTP client — shared service for all QVAC inference calls

import os
import logging
import asyncio
import json
from typing import Any, Dict, Optional, AsyncGenerator
 
import httpx

logger = logging.getLogger(__name__)

# ── Config — read at call time so env vars are always fresh ──────────────────
def _base_url() -> str:
    return os.getenv("QVAC_API_URL", "http://localhost:11435").rstrip("/")

def _api_key() -> str:
    return os.getenv("QVAC_API_KEY", "qvac-local-key")

def _headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-API-Key":    _api_key(),
    }


async def _post_with_retry(
    path: str,
    payload: Dict[str, Any],
    retries: int = 1,
    read_timeout: float = 120.0,
) -> Dict[str, Any]:
    """
    POST to QVAC with explicit per-segment timeout and minimal retries.
    read_timeout controls how long to wait for the LLM to finish responding.
    """
    url        = f"{_base_url()}{path}"
    timeout    = httpx.Timeout(connect=10.0, read=read_timeout, write=10.0, pool=5.0)
    last_error = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, retries + 1):
            try:
                logger.info(f"[QVAC] POST {path} (attempt {attempt}/{retries})")
                response = await client.post(url, json=payload, headers=_headers())
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(
                    f"[QVAC] HTTP {e.response.status_code} on {path}: "
                    f"{e.response.text[:300]}"
                )
                # Never retry auth or client errors
                if e.response.status_code in (400, 401, 403, 422):
                    raise
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)

            except httpx.ReadTimeout as e:
                last_error = e
                logger.error(
                    f"[QVAC] ReadTimeout on {path} after {read_timeout}s "
                    f"(attempt {attempt}/{retries}) — model still generating"
                )
                # Don't retry timeouts — model is still working, retry = duplicate queue entry
                raise RuntimeError(
                    f"QVAC response timeout after {read_timeout}s. "
                    "The model is under load — please try again in a moment."
                ) from e

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                logger.warning(f"[QVAC] Connection error attempt {attempt}: {e}")
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)

    raise RuntimeError(
        f"QVAC unreachable after {retries} attempt(s). "
        f"Last error: {last_error}"
    )


# ── Health ────────────────────────────────────────────────────────────────────

async def health_check() -> Dict[str, Any]:
    """Check QVAC server health. Never raises — returns error dict on failure."""
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)
        ) as client:
            r = await client.get(f"{_base_url()}/health", headers=_headers())
            return r.json()
    except Exception as e:
        logger.warning(f"[QVAC] Health check failed: {e}")
        return {"status": "unreachable", "error": str(e)}


# ── Loop A: Finance Quest Tutor ───────────────────────────────────────────────

async def tutor_ask(
    message: str,
    context: Optional[Dict] = None,
    device_tier: str = "desktop",
) -> str:
    """Ask the QVAC tutor a financial literacy question."""
    payload = {
        "message":     message,
        "context":     context or {},
        "stream":      False,
        "device_tier": device_tier,
    }
    result = await _post_with_retry(
        "/v1/tutor/ask",
        payload,
        retries=1,
        read_timeout=120.0,
    )
    return result.get("response", "")


# ── Loop C: Wellbeing Coach ───────────────────────────────────────────────────

async def coach_analyze(
    message: str,
    profile: Dict[str, Any],
    device_tier: str = "desktop",
) -> str:
    """Ask the coach to analyse a financial situation with user profile context."""
    payload = {
        "message":     message,
        "profile":     profile,
        "stream":      False,
        "device_tier": device_tier,
    }
    result = await _post_with_retry(
        "/v1/coach/analyze",
        payload,
        retries=1,
        read_timeout=120.0,
    )
    return result.get("response", "")


async def generate_wellbeing_score(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a structured Wellbeing Score (0-100) with breakdown.
    Returns: { score, breakdown, summary, top_action, risk_flags }
    """
    result = await _post_with_retry(
        "/v1/coach/score",
        {"profile": profile},
        retries=1,
        read_timeout=120.0,
    )

    if result.get("fallback"):
        logger.warning("[QVAC] Wellbeing score fell back — LLM parse error")
        raise RuntimeError("Score generation failed — please try again shortly")

    if result.get("score") is None:
        raise RuntimeError("Score generation returned no data — please try again")

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
    result = await _post_with_retry(
        "/v1/validator/score",
        {"signal": signal, "submitter_stats": submitter_stats or {}},
        retries=1,
        read_timeout=90.0,
    )

    if result.get("recommendation") == "SCAM_ALERT":
        logger.warning(
            f"[QVAC] SCAM_ALERT: {signal.get('asset_symbol')} "
            f"user={signal.get('user_id')} "
            f"flags={result.get('manipulation_flags')}"
        )

    return result


# ── AML — fraud detection ─────────────────────────────────────────────────────

async def aml_analyze(
    transaction: Dict[str, Any],
    patterns: Optional[list] = None,
) -> Dict[str, Any]:
    """
    AML transaction analysis.
    Returns: { risk_level, risk_score, flags, str_required,
               str_narrative, recommended_action }
    """
    return await _post_with_retry(
        "/v1/aml/analyze",
        {"transaction": transaction, "patterns": patterns or []},
        retries=1,
        read_timeout=120.0,
    )


async def stream_qvac_response(path: str, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """
    Streams the QVAC response token-by-token to prevent proxy timeouts
    and provide a real-time UI experience.
    """
    url = f"{_base_url()}{path}"
    payload["stream"] = True
    timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=5.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json=payload, headers=_headers()) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"[QVAC Stream Error] {response.status_code}: {error_text}")
                yield "⚠️ The AI engine is currently overloaded. Please try again in a moment."
                return
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "token" in data:
                            yield data["token"]
                    except Exception:
                        continue