# File: backend/services/aml_scoring_service.py
"""
AML Real-Time Transaction Scoring Engine
=========================================
Architecture: A + B + C + D

A — Pattern Tiering      : Tier1/Tier2 for cosine sim; OFAC via fuzzy string match only.
B — Confidence Banding   : GREEN(<0.45) / AMBER(0.45-0.72) / RED(≥0.72) with explicit uncertainty.
C — Factor Matrix        : 5-signal weighted composite score (weights sum to 1.0).
D — Claim Verification   : LLM receives evidence_bundle of DB-verified facts only.
                           Fill-in-the-blanks prompt. seed=42 for reproducibility.

Entry: score_transaction(tx_data, db_service) — async, non-blocking, never raises.
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

SCORING_VERSION = "1.0.0"

# Regulatory reporting thresholds by asset (CBN/NFIU + FRC Kenya + FATF)
REPORTING_THRESHOLDS: Dict[str, float] = {
    'USD': 10_000.0,  'USDT': 10_000.0, 'USDT_TRON': 10_000.0,
    'USDT_ETH': 10_000.0, 'USDT_POLYGON': 10_000.0, 'USDT_SOLANA': 10_000.0,
    'USDT_ALGO': 10_000.0, 'USDC': 10_000.0, 'USDC_ETH': 10_000.0,
    'USDC_POLYGON': 10_000.0, 'USDC_SOLANA': 10_000.0, 'USDCa': 10_000.0,
    'RLUSD': 10_000.0, 'XRP': 15_000.0,
    'NGN': 5_000_000.0,   # CBN cash transaction reporting threshold
    'KES': 1_000_000.0,   # Kenya FRC threshold
    'ALGO': 90_000.0, 'BTC': 0.13, 'ETH': 3.5,
    'SOL': 100.0,     'TRX': 90_000.0, 'MATIC': 13_000.0,
}
STRUCT_LOW, STRUCT_HIGH = 0.80, 0.995   # structuring zone: 80–99.5% of threshold

# Option C: Factor weights — must sum to 1.0
FACTOR_WEIGHTS: Dict[str, float] = {
    'pattern_similarity': 0.40,
    'structuring':        0.20,
    'velocity_anomaly':   0.20,
    'counterparty_risk':  0.15,
    'time_anomaly':       0.05,
}
assert abs(sum(FACTOR_WEIGHTS.values()) - 1.0) < 1e-9

# Option B: Band thresholds
BAND_GREEN = 0.45
BAND_RED   = 0.72

# Pattern factor normalisation range
PAT_FLOOR  = 0.30   # below this weighted sim → 0.0 factor score
PAT_CEIL   = 0.72   # at/above this → 1.0 factor score

OFAC_SIM_THRESHOLD = 0.88   # minimum SequenceMatcher ratio for OFAC hit
CACHE_TTL           = 300   # pattern cache TTL in seconds
OFAC_CACHE_TTL      = 1800  # OFAC cache TTL (30 min — names don't change often)
EMBED_TIMEOUT       = 30    # seconds
LLM_TIMEOUT         = 45    # seconds
VELOCITY_MINS       = 60    # lookback window for velocity count

# ---------------------------------------------------------------------------
# Option D: QVAC PROMPTS (fill-in-the-blanks, no open-ended investigation)
# ---------------------------------------------------------------------------

_STR_SYSTEM = (
    "You are an AML compliance officer at a CBN/FRC-licensed payment service provider. "
    "Your role is to draft Suspicious Transaction Reports (STRs) for FIU submission.\n\n"
    "ABSOLUTE RULES:\n"
    "1. Use ONLY the facts in the Evidence Bundle. Do not infer, speculate, or hallucinate.\n"
    "2. Do not name OFAC entities unless ofac_match=True AND ofac_matched_name is provided.\n"
    "3. If evidence is ambiguous, write: 'Insufficient evidence — human review required.'\n"
    "4. Maximum 200 words. Formal compliance language. No preamble or sign-off."
)

_STR_USER = (
    "Draft a Suspicious Transaction Report using ONLY the evidence below. "
    "Do not add any fact not present here.\n\n"
    "EVIDENCE BUNDLE:\n"
    "  TX ID           : {tx_id}\n"
    "  Amount          : {amount} {asset} on {chain}\n"
    "  Timestamp (UTC) : {created_at}\n"
    "  Pattern Match   : \"{matched_pattern_label}\" "
    "(similarity={pattern_similarity:.3f}, tier={pattern_tier})\n"
    "  Structuring     : {structuring_flag} — {structuring_detail}\n"
    "  Velocity        : {velocity_detail}\n"
    "  Counterparty    : {counterparty_detail}\n"
    "  OFAC            : {ofac_match} — {ofac_detail}\n"
    "  Risk Score      : {combined_score:.3f} (RED band ≥ 0.72)\n"
    "  Factor Scores   :\n{factor_lines}\n\n"
    "Output this exact format — nothing else:\n"
    "SUMMARY: [one sentence: amount/asset/chain and primary reason flagged]\n"
    "TRIGGERED FACTORS: [bullet list, only from evidence above]\n"
    "RISK LEVEL: RED\n"
    "RECOMMENDED ACTION: [one of: File STR with FIU / "
    "Escalate to compliance team / Place transaction hold]\n"
    "EXPLANATION: [≤150 words, evidence-based only]"
)

_AMBER_TEMPLATE = (
    "⚠️  AMBER ALERT — Human Review Required\n\n"
    "Transaction  : {tx_id}\n"
    "Risk Score   : {combined_score:.3f}  "
    "(AMBER band: 0.45–0.72 | STR threshold: ≥0.72)\n"
    "Top Pattern  : \"{matched_pattern_label}\" "
    "(similarity={pattern_similarity:.3f})\n\n"
    "Triggered signals:\n{factor_lines}\n\n"
    "IMPORTANT: This is a statistical alert — NOT a confirmed suspicious transaction.\n"
    "A compliance officer must review transaction {tx_id} within 24 hours "
    "and determine whether a manual STR is warranted.\n\n"
    "Automated STR filing is reserved for RED band alerts (score ≥ 0.72)."
)

# ---------------------------------------------------------------------------
# DATA CLASSES
# ---------------------------------------------------------------------------

@dataclass
class _PatternCache:
    normalized: np.ndarray   # (N, 1024) pre-L2-normalised for O(N) cosine
    weights:    np.ndarray   # (N,) scoring_weight per pattern
    patterns:   List[Dict]   # [{pattern_id, label, tier, scoring_weight}, ...]
    loaded_at:  float

    @property
    def stale(self) -> bool:
        return (time.time() - self.loaded_at) > CACHE_TTL


@dataclass
class _OFACCache:
    names:     List[str]   # lowercase entity names
    loaded_at: float

    @property
    def stale(self) -> bool:
        return (time.time() - self.loaded_at) > OFAC_CACHE_TTL

# ---------------------------------------------------------------------------
# MODULE-LEVEL STATE (singletons)
# ---------------------------------------------------------------------------

_session:        Optional[requests.Session] = None
_session_lock    = threading.Lock()
_pattern_cache:  Optional[_PatternCache] = None
_pattern_lock    = asyncio.Lock()
_ofac_cache:     Optional[_OFACCache] = None
_ofac_lock       = asyncio.Lock()
_qvac_url:       Optional[str] = None
_qvac_url_lock   = asyncio.Lock()

# ---------------------------------------------------------------------------
# HTTP SESSION (reused, thread-safe)
# ---------------------------------------------------------------------------

def _get_session() -> requests.Session:
    global _session
    with _session_lock:
        if _session is None:
            s = requests.Session()
            retry = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503])
            adapter = HTTPAdapter(max_retries=retry, pool_connections=2, pool_maxsize=4)
            s.mount("http://", adapter)
            s.mount("https://", adapter)
            key = settings.QVAC_API_KEY.get_secret_value() if settings.QVAC_API_KEY else ""
            if key:
                s.headers["Authorization"] = f"Bearer {key}"
            s.headers["Content-Type"] = "application/json"
            _session = s
        return _session

# ---------------------------------------------------------------------------
# QVAC URL RESOLVER
# ---------------------------------------------------------------------------

async def _get_qvac_url() -> str:
    global _qvac_url
    if _qvac_url:
        return _qvac_url
    async with _qvac_url_lock:
        if _qvac_url:
            return _qvac_url
        for candidate in ["http://localhost:11434", "http://127.0.0.1:11434"]:
            try:
                r = await asyncio.to_thread(
                    lambda u=candidate: _get_session().get(f"{u}/v1/models", timeout=4)
                )
                if r.status_code == 200:
                    logger.info(f"AML: QVAC resolved → {candidate}")
                    _qvac_url = candidate
                    return candidate
            except Exception:
                continue
        fb = settings.QVAC_API_URL.rstrip('/')
        logger.warning(f"AML: QVAC localhost unreachable, falling back to {fb}")
        _qvac_url = fb
        return fb

# ---------------------------------------------------------------------------
# QVAC HELPERS (sync → called via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _embed_sync(text: str, url: str) -> Optional[List[float]]:
    try:
        r = _get_session().post(
            f"{url}/v1/embeddings",
            json={"model": "embedder", "input": text[:1500]},
            timeout=EMBED_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"AML embed failed: {e}")
        return None


def _complete_sync(messages: List[Dict], url: str) -> Optional[str]:
    try:
        r = _get_session().post(
            f"{url}/v1/chat/completions",
            json={
                "model": "str-generator",
                "messages": messages,
                "stream": False,
                "max_tokens": 350,
                "temperature": 0.1,    # near-deterministic
                "top_p": 0.85,
                "seed": 42,            # QVAC supports seed → reproducible STRs
            },
            timeout=LLM_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"AML LLM call failed: {e}")
        return None


async def _embed(text: str) -> Optional[List[float]]:
    url = await _get_qvac_url()
    return await asyncio.to_thread(_embed_sync, text, url)


async def _complete(messages: List[Dict]) -> Optional[str]:
    url = await _get_qvac_url()
    return await asyncio.to_thread(_complete_sync, messages, url)

# ---------------------------------------------------------------------------
# PATTERN CACHE (A: Tier 1+2 only)
# ---------------------------------------------------------------------------

async def _load_pattern_cache(db_service) -> _PatternCache:
    """Load scoring patterns from Supabase. Paginated. Tier 3 excluded."""
    patterns: List[Dict] = []
    page_size, offset = 200, 0

    while True:
        chunk = await asyncio.to_thread(
            lambda o=offset: db_service.supabase
                .table('aml_fraud_patterns')
                .select('pattern_id, label, tier, scoring_weight, embedding')
                .neq('excluded_from_scoring', True)
                .range(o, o + page_size - 1)
                .execute()
        )
        rows = chunk.data or []
        for p in rows:
            emb = p.get('embedding')
            if emb and len(emb) == 1024 and p.get('tier') in (None, 1, 2):
                patterns.append(p)
        if len(rows) < page_size:
            break
        offset += page_size

    if not patterns:
        raise RuntimeError(
            "AML pattern cache empty — run aml_pattern_service.py then backfill_pattern_tiers.py"
        )

    emb_matrix = np.array([p['embedding'] for p in patterns], dtype=np.float32)
    norms      = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    normalized = emb_matrix / np.maximum(norms, 1e-9)
    weights    = np.array([float(p.get('scoring_weight') or 0.5) for p in patterns], dtype=np.float32)
    meta       = [{'pattern_id': p['pattern_id'], 'label': p.get('label', ''),
                   'tier': p.get('tier', 2)} for p in patterns]

    logger.info(f"AML: Pattern cache ready — {len(patterns)} patterns")
    return _PatternCache(normalized=normalized, weights=weights,
                         patterns=meta, loaded_at=time.time())


async def _get_pattern_cache(db_service) -> _PatternCache:
    global _pattern_cache
    if _pattern_cache and not _pattern_cache.stale:
        return _pattern_cache
    async with _pattern_lock:
        if _pattern_cache and not _pattern_cache.stale:
            return _pattern_cache
        _pattern_cache = await _load_pattern_cache(db_service)
    return _pattern_cache

# ---------------------------------------------------------------------------
# OFAC CACHE (A: name-match only, not cosine)
# ---------------------------------------------------------------------------

async def _get_ofac_names(db_service) -> List[str]:
    global _ofac_cache
    if _ofac_cache and not _ofac_cache.stale:
        return _ofac_cache.names
    async with _ofac_lock:
        if _ofac_cache and not _ofac_cache.stale:
            return _ofac_cache.names
        try:
            res = await asyncio.to_thread(
                lambda: db_service.supabase.table('ofac_sanctions')
                    .select('entity_name').execute()
            )
            names = [r['entity_name'].strip().lower()
                     for r in (res.data or []) if r.get('entity_name')]
            _ofac_cache = _OFACCache(names=names, loaded_at=time.time())
            logger.info(f"AML: OFAC cache ready — {len(names)} entities")
        except Exception as e:
            logger.warning(f"AML: OFAC cache failed (non-fatal): {e}")
            _ofac_cache = _OFACCache(names=[], loaded_at=time.time())
    return _ofac_cache.names

# ---------------------------------------------------------------------------
# FACTOR FUNCTIONS (each returns (score: float, detail: str))
# ---------------------------------------------------------------------------

def _factor_structuring(amount: float, asset: str) -> Tuple[float, str]:
    """Detect structuring: amount in 80–99.5% zone of a reporting threshold."""
    base = asset.split('_')[0].upper()
    threshold = REPORTING_THRESHOLDS.get(asset) or REPORTING_THRESHOLDS.get(base)
    if not threshold:
        return 0.0, f"no threshold defined for {asset}"
    ratio = amount / threshold
    if STRUCT_LOW <= ratio < STRUCT_HIGH:
        return 1.0, (
            f"{amount:,.2f} {asset} = {ratio*100:.1f}% of {threshold:,.0f} "
            f"reporting threshold — structuring pattern"
        )
    if 0.65 <= ratio < STRUCT_LOW:
        return 0.2, (
            f"{amount:,.2f} {asset} = {ratio*100:.1f}% of threshold — approaching zone"
        )
    return 0.0, f"{amount:,.2f} {asset} = {ratio*100:.1f}% of threshold"


def _factor_time(hour: int, typical_hours: List[int]) -> Tuple[float, str]:
    """Flag unusual transaction hours relative to user's own activity window."""
    if not typical_hours:
        return 0.0, "no time baseline established"
    if hour in typical_hours:
        return 0.0, f"{hour:02d}:00 UTC — within user's typical window"
    if 0 <= hour <= 3:
        return 1.0, f"{hour:02d}:00 UTC — deep overnight (highest fraud correlation)"
    if hour in [4, 5]:
        return 0.6, f"{hour:02d}:00 UTC — early morning, outside typical window"
    return 0.35, f"{hour:02d}:00 UTC — outside user's typical activity window"


async def _factor_velocity(user_id: str, db_service) -> Tuple[float, str]:
    """Velocity anomaly: user's current rate vs their own rolling baseline."""
    try:
        cutoff = (datetime.utcnow() - timedelta(minutes=VELOCITY_MINS)).isoformat()
        res = await asyncio.to_thread(
            lambda: db_service.supabase.table('blockchain_transactions')
                .select('id', count='exact')
                .eq('user_id', user_id)
                .gte('created_at', cutoff)
                .execute()
        )
        count = res.count or 0
        current_rate = count * (60.0 / VELOCITY_MINS)  # normalise to per-hour

        bres = await asyncio.to_thread(
            lambda: db_service.supabase.table('user_tx_baselines')
                .select('avg_hourly_txns, baseline_sample_count')
                .eq('user_id', user_id)
                .maybe_single()
                .execute()
        )
        baseline = 2.0
        n_samples = 0
        if bres.data:
            baseline  = max(1.0, float(bres.data.get('avg_hourly_txns') or 2.0))
            n_samples = int(bres.data.get('baseline_sample_count') or 0)

        ratio = current_rate / baseline
        # Score: 0 below 1.5x baseline, linear to 1.0 at 5x
        raw_score = min(1.0, max(0.0, (ratio - 1.5) / 3.5))
        # Discount on immature baseline (<10 samples)
        score = raw_score * (0.4 if n_samples < 10 else 1.0)
        detail = (
            f"{count} txns in {VELOCITY_MINS}min "
            f"({current_rate:.1f}/hr vs baseline {baseline:.1f}/hr, ratio={ratio:.1f}x"
            + (f", low-confidence: {n_samples} samples)" if n_samples < 10 else ")")
        )
        return score, detail
    except Exception as e:
        logger.debug(f"Velocity factor: {e}")
        return 0.0, "velocity check unavailable"


async def _factor_counterparty(recipient: str, db_service) -> Tuple[float, str]:
    """Check if recipient appears in prior RED alerts or confirmed fraud cases."""
    if not recipient or len(recipient) < 10:
        return 0.0, "no recipient address"
    try:
        res = await asyncio.to_thread(
            lambda: db_service.supabase.table('aml_risk_scores')
                .select('id, status')
                .eq('recipient_address', recipient)
                .eq('band', 'RED')
                .limit(10)
                .execute()
        )
        flags = res.data or []
        if not flags:
            return 0.0, "no prior flags on counterparty"
        confirmed = sum(1 for f in flags if f.get('status') == 'confirmed_fraud')
        if confirmed:
            return 1.0, f"recipient has {confirmed} confirmed fraud case(s) in system"
        return 0.65, f"recipient appeared in {len(flags)} prior RED alert(s)"
    except Exception as e:
        logger.debug(f"Counterparty factor: {e}")
        return 0.0, "counterparty check unavailable"

# ---------------------------------------------------------------------------
# OFAC FUZZY MATCHING (A: separate path, not cosine)
# ---------------------------------------------------------------------------

def _check_ofac(memo: str, recipient: str, names: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Token-level fuzzy match against OFAC entity names.
    Requires >=2 significant tokens to avoid false positives on common words.
    Only checks memo text — NOT wallet addresses (hex/base58 would never match a name).
    """
    if not names or not memo:
        return False, None
    tokens = [t.lower().strip() for t in memo.split() if len(t.strip()) > 3]
    if len(tokens) < 2:
        return False, None
    for token in tokens:
        tlen = len(token)
        for name in names[:3000]:  # cap for performance
            if abs(tlen - len(name)) > max(tlen, 3) * 0.4:
                continue  # quick length filter
            if SequenceMatcher(None, token, name).ratio() >= OFAC_SIM_THRESHOLD:
                return True, name
    return False, None

# ---------------------------------------------------------------------------
# TRANSACTION FINGERPRINT
# ---------------------------------------------------------------------------

def _fingerprint(tx: Dict) -> str:
    """
    Build a text representation that semantically activates relevant fraud pattern embeddings.
    Kept under 300 chars — comfortably within GTE-Large's 512-token context.
    """
    amount = tx.get('amount', 0)
    asset  = tx.get('asset', '')
    chain  = tx.get('chain', '')
    memo   = (tx.get('memo') or '')[:200]
    parts  = [
        f"Blockchain transfer: {amount} {asset}",
        f"Network: {chain}",
        f"Memo: {memo}" if memo else "No stated purpose",
    ]
    base = asset.split('_')[0].upper()
    if base in ('USDT', 'USDC', 'USDCA', 'RLUSD'):
        parts.append("Stablecoin transfer")
    try:
        if float(amount) >= 5000:
            parts.append("High-value transfer")
    except Exception:
        pass
    return ' | '.join(parts)[:1400]

# ---------------------------------------------------------------------------
# EVIDENCE BUNDLE ASSEMBLER (D: verified facts only, no inference)
# ---------------------------------------------------------------------------

def _assemble_bundle(
    tx: Dict, pattern: Dict, raw_sim: float,
    factors: Dict, combined: float,
    ofac_hit: bool, ofac_name: Optional[str],
) -> Dict:
    return {
        "tx_id":                 tx.get('tx_id'),
        "amount":                tx.get('amount'),
        "asset":                 tx.get('asset'),
        "chain":                 tx.get('chain'),
        "created_at":            tx.get('created_at'),
        "matched_pattern_label": pattern.get('label', 'Unknown'),
        "matched_pattern_id":    pattern.get('pattern_id'),
        "pattern_similarity":    round(raw_sim, 4),
        "pattern_tier":          pattern.get('tier', 2),
        "structuring_flag":      factors['structuring'][0] >= 0.5,
        "structuring_detail":    factors['structuring'][1],
        "velocity_detail":       factors['velocity_anomaly'][1],
        "counterparty_detail":   factors['counterparty_risk'][1],
        "ofac_match":            ofac_hit,
        "ofac_detail":           f"matched: '{ofac_name}'" if ofac_name else "no match",
        "combined_score":        round(combined, 4),
        "factor_breakdown":      {
            k: {"score": round(v[0], 4), "detail": v[1]}
            for k, v in factors.items()
        },
    }

# ---------------------------------------------------------------------------
# EXPLANATION GENERATORS
# ---------------------------------------------------------------------------

async def _generate_str(bundle: Dict) -> str:
    """Option D: LLM STR constrained to verified evidence bundle. seed=42."""
    factor_lines = "\n".join(
        f"    [{k.upper()}] score={v['score']:.3f} — {v['detail']}"
        for k, v in bundle['factor_breakdown'].items()
    )
    user_msg = _STR_USER.format(
        tx_id=bundle['tx_id'], amount=bundle['amount'], asset=bundle['asset'],
        chain=bundle['chain'], created_at=bundle['created_at'],
        matched_pattern_label=bundle['matched_pattern_label'],
        pattern_similarity=bundle['pattern_similarity'],
        pattern_tier=bundle['pattern_tier'],
        structuring_flag=bundle['structuring_flag'],
        structuring_detail=bundle['structuring_detail'],
        velocity_detail=bundle['velocity_detail'],
        counterparty_detail=bundle['counterparty_detail'],
        ofac_match=bundle['ofac_match'], ofac_detail=bundle['ofac_detail'],
        combined_score=bundle['combined_score'], factor_lines=factor_lines,
    )
    text = await _complete([
        {"role": "system", "content": _STR_SYSTEM},
        {"role": "user",   "content": user_msg},
    ])
    if not text:
        # Hard fallback — template-based, no LLM needed
        return (
            f"SUMMARY: {bundle['amount']} {bundle['asset']} on {bundle['chain']} "
            f"triggered RED alert (score {bundle['combined_score']:.3f}).\n"
            f"TRIGGERED FACTORS:\n{factor_lines}\n"
            f"RISK LEVEL: RED\n"
            f"RECOMMENDED ACTION: Escalate to compliance team\n"
            f"EXPLANATION: Automated STR generation failed — LLM unavailable. "
            f"This is a rule-based fallback. Human review required."
        )
    return text


def _generate_amber(bundle: Dict) -> str:
    """Option B: Deterministic template for AMBER — no LLM, zero hallucination risk."""
    factor_lines = "\n".join(
        f"  • [{k.upper()}] score={v['score']:.3f} — {v['detail']}"
        for k, v in bundle['factor_breakdown'].items()
        if v['score'] > 0.05
    ) or "  • No individual signals exceeded the materiality threshold"
    return _AMBER_TEMPLATE.format(
        tx_id=bundle['tx_id'],
        combined_score=bundle['combined_score'],
        red_threshold=BAND_RED,
        matched_pattern_label=bundle['matched_pattern_label'],
        pattern_similarity=bundle['pattern_similarity'],
        factor_lines=factor_lines,
    )

# ---------------------------------------------------------------------------
# USER BASELINE UPDATER (background task)
# ---------------------------------------------------------------------------

async def _update_baseline(user_id: str, amount: float, hour: int, db_service):
    """Exponential moving average update of per-user transaction baseline."""
    try:
        res = await asyncio.to_thread(
            lambda: db_service.supabase.table('user_tx_baselines')
                .select('*').eq('user_id', user_id).maybe_single().execute()
        )
        existing = res.data
        if existing:
            n     = max(1, int(existing.get('baseline_sample_count') or 1))
            alpha = min(0.1, 2.0 / (n + 1))
            new_txns   = (1 - alpha) * float(existing.get('avg_hourly_txns') or 2.0) + alpha
            new_amount = (1 - alpha) * float(existing.get('avg_tx_amount_usd') or 100.0) + alpha * amount
            typical = set(existing.get('typical_hours') or [])
            typical.add(hour)
            if len(typical) > 18:
                typical = set(sorted(typical)[-18:])
            await asyncio.to_thread(
                lambda: db_service.supabase.table('user_tx_baselines').update({
                    'avg_hourly_txns':      round(new_txns, 4),
                    'avg_tx_amount_usd':    round(new_amount, 2),
                    'typical_hours':        sorted(typical),
                    'baseline_sample_count': n + 1,
                    'last_updated':         datetime.utcnow().isoformat(),
                }).eq('user_id', user_id).execute()
            )
        else:
            await asyncio.to_thread(
                lambda: db_service.supabase.table('user_tx_baselines').insert({
                    'user_id':              user_id,
                    'avg_hourly_txns':      2.0,
                    'avg_tx_amount_usd':    round(amount, 2),
                    'typical_hours':        [hour],
                    'baseline_sample_count': 1,
                    'last_updated':         datetime.utcnow().isoformat(),
                }).execute()
            )
    except Exception as e:
        logger.debug(f"Baseline update for {user_id}: {e}")

# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

async def score_transaction(tx_data: Dict[str, Any], db_service) -> Optional[Dict]:
    """
    Non-blocking AML scoring pipeline. Never raises — returns None on failure.

    tx_data keys: tx_id, user_id, amount, asset, chain, recipient, memo, created_at
    """
    tx_id = tx_data.get('tx_id', 'unknown')
    try:
        user_id   = str(tx_data.get('user_id', ''))
        amount    = float(tx_data.get('amount', 0.0))
        asset     = str(tx_data.get('asset', ''))
        chain     = str(tx_data.get('chain', ''))
        memo      = str(tx_data.get('memo') or '')
        recipient = str(tx_data.get('recipient') or '')
        created_at = tx_data.get('created_at', datetime.utcnow().isoformat())
        tx_hour   = datetime.utcnow().hour

        # ── 1. Embed transaction fingerprint ────────────────────────────────
        embedding = await _embed(_fingerprint(tx_data))
        if embedding is None:
            logger.warning(f"AML: QVAC unavailable — scoring skipped for {tx_id}")
            return None

        # ── 2. Pattern similarity (A: Tier 1+2 cosine only) ─────────────────
        cache = await _get_pattern_cache(db_service)
        q = np.array(embedding, dtype=np.float32)
        q /= max(np.linalg.norm(q), 1e-9)

        raw_sims      = cache.normalized @ q         # (N,) cosine similarities
        weighted_sims = raw_sims * cache.weights      # (N,) tier-weighted

        best_idx      = int(np.argmax(weighted_sims))
        best_raw_sim  = float(raw_sims[best_idx])
        best_weighted = float(weighted_sims[best_idx])
        best_pattern  = cache.patterns[best_idx]

        # Normalise into [0, 1] factor score
        pat_factor = min(1.0, max(0.0,
            (best_weighted - PAT_FLOOR) / (PAT_CEIL - PAT_FLOOR)
        ))
        pat_detail = (
            f"similarity={best_raw_sim:.4f} (weighted={best_weighted:.4f}) "
            f"to '{best_pattern['label']}' [Tier {best_pattern['tier']}]"
        )

        # ── 3. OFAC check (A: fuzzy name, not cosine) ───────────────────────
        ofac_names        = await _get_ofac_names(db_service)
        ofac_hit, ofac_nm = _check_ofac(memo, recipient, ofac_names)

        # ── 4. Remaining four factors ────────────────────────────────────────
        struct_s, struct_d = _factor_structuring(amount, asset)
        vel_s,    vel_d    = await _factor_velocity(user_id, db_service)
        cp_s,     cp_d     = await _factor_counterparty(recipient, db_service)

        typical_hours: List[int] = []
        try:
            br = await asyncio.to_thread(
                lambda: db_service.supabase.table('user_tx_baselines')
                    .select('typical_hours').eq('user_id', user_id).maybe_single().execute()
            )
            if br.data:
                typical_hours = br.data.get('typical_hours') or []
        except Exception:
            pass
        time_s, time_d = _factor_time(tx_hour, typical_hours)

        factors = {
            'pattern_similarity': (pat_factor,  pat_detail),
            'structuring':        (struct_s,    struct_d),
            'velocity_anomaly':   (vel_s,       vel_d),
            'counterparty_risk':  (cp_s,        cp_d),
            'time_anomaly':       (time_s,      time_d),
        }

        # ── 5. Weighted score + OFAC override ───────────────────────────────
        combined = sum(factors[k][0] * FACTOR_WEIGHTS[k] for k in FACTOR_WEIGHTS)
        if ofac_hit:
            combined = max(combined, 0.85)
            logger.warning(f"🚨 AML OFAC hit: {tx_id} → '{ofac_nm}'")
        combined = round(min(combined, 1.0), 4)

        # ── 6. Band (B) ──────────────────────────────────────────────────────
        band = 'RED' if combined >= BAND_RED else ('AMBER' if combined >= BAND_GREEN else 'GREEN')

        # ── 7. Evidence bundle + explanation ────────────────────────────────
        bundle = _assemble_bundle(
            tx_data, best_pattern, best_raw_sim,
            factors, combined, ofac_hit, ofac_nm,
        )
        explanation: Optional[str] = None
        if band == 'RED':
            explanation = await _generate_str(bundle)
        elif band == 'AMBER':
            explanation = _generate_amber(bundle)

        # ── 8. Upsert to aml_risk_scores ────────────────────────────────────
        factors_json = {k: {"score": round(v[0], 4), "detail": v[1]} for k, v in factors.items()}
        record = {
            'tx_id':                 tx_id,
            'user_id':               user_id,
            'recipient_address':     recipient[:200] if recipient else None,
            'combined_score':        combined,
            'band':                  band,
            'factors':               factors_json,
            'matched_pattern_id':    best_pattern.get('pattern_id'),
            'matched_pattern_label': best_pattern.get('label'),
            'pattern_similarity':    round(best_raw_sim, 4),
            'ofac_match':            ofac_hit,
            'ofac_matched_name':     ofac_nm,
            'str_explanation':       explanation,
            'evidence_bundle':       bundle,
            'status':                'open',
            'scoring_version':       SCORING_VERSION,
            'created_at':            created_at,
        }

        await asyncio.to_thread(
            lambda: db_service.supabase.table('aml_risk_scores')
                .upsert(record, on_conflict='tx_id').execute()
        )

        # ── 9. Audit log for non-GREEN ───────────────────────────────────────
        if band in ('RED', 'AMBER'):
            top_factor = max(factors, key=lambda k: factors[k][0])
            await asyncio.to_thread(
                lambda: db_service.supabase.table('aml_audit_log').insert({
                    'tx_id':      tx_id,
                    'action':     f'auto_scored_{band.lower()}',
                    'new_status': 'open',
                    'metadata': {
                        'combined_score':  combined,
                        'band':            band,
                        'top_factor':      top_factor,
                        'ofac_match':      ofac_hit,
                        'scoring_version': SCORING_VERSION,
                    },
                    'created_at': datetime.utcnow().isoformat(),
                }).execute()
            )
            logger.warning(
                f"🔴 AML {band}: tx={tx_id} score={combined:.3f} "
                f"pattern='{best_pattern['label']}' ofac={ofac_hit}"
            )
        else:
            logger.debug(f"✅ AML GREEN: tx={tx_id} score={combined:.3f}")

        # ── 10. Background baseline update ──────────────────────────────────
        asyncio.create_task(_update_baseline(user_id, amount, tx_hour, db_service))

        return record

    except Exception as e:
        logger.error(f"AML scoring failed for {tx_id}: {e}", exc_info=True)
        return None  # NEVER propagate — payment flow must not be interrupted

# ---------------------------------------------------------------------------
# HEALTH CHECK (polled by admin dashboard)
# ---------------------------------------------------------------------------

async def health_check(db_service) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "qvac": "unknown", "pattern_cache": "not loaded",
        "open_alerts": -1, "status": "degraded",
    }
    try:
        url = await _get_qvac_url()
        r = await asyncio.to_thread(
            lambda: _get_session().get(f"{url}/v1/models", timeout=4)
        )
        result["qvac"] = "online" if r.status_code == 200 else f"error_{r.status_code}"
    except Exception as e:
        result["qvac"] = f"offline ({e})"

    if _pattern_cache:
        age = int(time.time() - _pattern_cache.loaded_at)
        result["pattern_cache"] = f"{len(_pattern_cache.patterns)} patterns ({age}s old)"
        result["cache_age_s"] = age

    try:
        rs = await asyncio.to_thread(
            lambda: db_service.supabase.table('aml_risk_scores')
                .select('id', count='exact')
                .in_('band', ['RED', 'AMBER'])
                .eq('status', 'open')
                .execute()
        )
        result["open_alerts"] = rs.count or 0
    except Exception:
        pass

    result["status"] = "online" if result["qvac"] == "online" else "degraded"
    return result

# ---------------------------------------------------------------------------
# CLI TEST ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s %(levelname)s %(message)s")
    from backend.dependencies import get_database_service

    async def _test():
        db = get_database_service()
        tx = {
            "tx_id":       "test_score_001",
            "user_id":     "00000000-0000-0000-0000-000000000001",
            "amount":      9850.0,
            "asset":       "USDT",
            "chain":       "tron",
            "recipient":   "TXabcdef1234567890",
            "memo":        "payment for gold investment",
            "created_at":  datetime.utcnow().isoformat(),
        }
        print("\n🔍 Scoring test transaction...")
        result = await score_transaction(tx, db)
        if result:
            print(f"✅ Band: {result['band']} | Score: {result['combined_score']:.3f}")
            print(f"   Pattern: {result['matched_pattern_label']}")
            if result.get('str_explanation'):
                print(f"\n{'='*60}\n{result['str_explanation']}\n{'='*60}")
        else:
            print("❌ Scoring returned None — check QVAC is running")
        hc = await health_check(db)
        print(f"\n🏥 Health: {hc}")

    asyncio.run(_test())