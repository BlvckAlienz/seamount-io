# File: backend/scripts/backfill_pattern_tiers.py
"""
One-time migration: tag aml_fraud_patterns with tier/modality/scoring_weight
and migrate OFAC entries to the ofac_sanctions lookup table.

Run AFTER migration 002_aml_tiering_and_scoring.sql:
  python -m backend.scripts.backfill_pattern_tiers

Idempotent — safe to re-run.
"""

import logging
import sys
from pathlib import Path
from typing import Tuple, List, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.dependencies import get_database_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BATCH = 250  # rows per upsert call

# ---------------------------------------------------------------------------
# TIER CLASSIFICATION
# ---------------------------------------------------------------------------

def classify(pattern_id: str, source: str, label: str) -> Tuple[int, str, float, bool]:
    """
    Returns (tier, modality, scoring_weight, excluded_from_scoring).

    Tier 1 — behavioral ground truth, cosine weight 1.0
    Tier 2 — regulatory document chunks, cosine weight 0.5 (corroboration required)
    Tier 3 — wrong modality: excluded from cosine scoring entirely
    """
    src = (source or '').lower().strip()
    pid = (pattern_id or '').lower().strip()
    lbl = (label or '').lower()

    # ── Tier 1: Behavioral ground truth ──────────────────────────────────────
    if src == 'manual_typology':
        return 1, 'behavioral', 1.0, False

    if pid.startswith('ke_dci') or src == 'ke_dci':
        return 1, 'behavioral', 1.0, False

    if 'typology' in src or 'typology' in lbl:
        return 1, 'behavioral', 1.0, False

    # Pattern IDs that are hand-crafted (ng_*, ke_*, cross_*, crypto_*)
    for prefix in ('ng_0', 'ke_0', 'cross_0', 'crypto_0'):
        if pid.startswith(prefix):
            return 1, 'behavioral', 1.0, False

    # ── Tier 2: Country regulatory PDF chunks ────────────────────────────────
    if src in ('nigeria', 'kenya', 'ghana', 'south_africa', 'sa'):
        return 2, 'document', 0.5, False

    # ── Tier 3 excluded: OFAC (entity names — wrong modality for text similarity)
    if src in ('ofac_sdn', 'ofac_alt', 'ofac'):
        return 3, 'entity_name', 0.0, True

    # ── Tier 3 excluded: CryptoScamDB (URLs — irrelevant for txn fingerprints)
    if src == 'cryptoscamdb':
        return 3, 'url', 0.0, True

    # Default: Tier 2 unclassified
    logger.debug(f"Unclassified source='{source}' pid='{pattern_id}' → Tier 2 default")
    return 2, 'behavioral', 0.5, False


# ---------------------------------------------------------------------------
# OFAC DESCRIPTION PARSER
# ---------------------------------------------------------------------------

def parse_ofac(pattern_id: str, description: str, source: str) -> Dict:
    """
    SDN format: "{name} | {type} | {program} | {remarks}"
    Alt format:  just the alias name
    """
    parts = [p.strip() for p in (description or '').split('|')]
    entity_name = parts[0] if parts else description[:200]

    sdn_id = None
    if source == 'ofac_sdn':
        raw = pattern_id.replace('ofac_', '')
        sdn_id = raw.split('_')[0] if '_' in raw else raw

    return {
        'pattern_id':  pattern_id,
        'sdn_id':      sdn_id,
        'entity_name': entity_name[:500] if entity_name else 'UNKNOWN',
        'entity_type': parts[1] if len(parts) > 1 else None,
        'program':     parts[2] if len(parts) > 2 else None,
        'remarks':     (parts[3] if len(parts) > 3 else None),
        'aliases':     [],
        'source':      source,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run(db_service):
    logger.info("🏷️  Fetching all patterns...")

    # Paginated fetch
    all_patterns: List[Dict] = []
    offset, page = 0, 500
    while True:
        res = db_service.supabase.table('aml_fraud_patterns')\
            .select('pattern_id, source, label, description')\
            .range(offset, offset + page - 1).execute()
        chunk = res.data or []
        all_patterns.extend(chunk)
        if len(chunk) < page:
            break
        offset += page

    logger.info(f"📦 {len(all_patterns)} patterns fetched")

    tag_rows: List[Dict]  = []
    ofac_rows: List[Dict] = []
    counts = {1: 0, 2: 0, 3: 0, 'ofac': 0, 'scam': 0}

    for p in all_patterns:
        pid  = p['pattern_id']
        src  = p.get('source', '')
        lbl  = p.get('label', '')
        desc = p.get('description', '')

        tier, modality, weight, excluded = classify(pid, src, lbl)
        counts[tier] += 1
        if modality == 'url':
            counts['scam'] += 1
        if modality == 'entity_name':
            counts['ofac'] += 1

        tag_rows.append({
            'pattern_id':            pid,
            'tier':                  tier,
            'modality':              modality,
            'scoring_weight':        weight,
            'excluded_from_scoring': excluded,
        })

        if src in ('ofac_sdn', 'ofac_alt'):
            ofac_rows.append(parse_ofac(pid, desc, src))

    # ── Tag aml_fraud_patterns ────────────────────────────────────────────
    ok = fail = 0
    for i in range(0, len(tag_rows), BATCH):
        chunk = tag_rows[i:i + BATCH]
        try:
            db_service.supabase.table('aml_fraud_patterns')\
                .upsert(chunk, on_conflict='pattern_id').execute()
            ok += len(chunk)
            print(f"  Tagged {ok}/{len(tag_rows)}...", end='\r')
        except Exception as e:
            logger.error(f"  Tag batch {i} failed: {e}")
            fail += len(chunk)
    print()
    if fail:
        logger.warning(f"⚠️  {fail} tag failures — re-run to retry")

    # ── Migrate OFAC to ofac_sanctions ────────────────────────────────────
    ofac_ok = ofac_fail = 0
    if ofac_rows:
        logger.info(f"🔐 Migrating {len(ofac_rows)} OFAC entries → ofac_sanctions...")
        for i in range(0, len(ofac_rows), BATCH):
            chunk = ofac_rows[i:i + BATCH]
            try:
                db_service.supabase.table('ofac_sanctions')\
                    .upsert(chunk, on_conflict='pattern_id').execute()
                ofac_ok += len(chunk)
            except Exception as e:
                logger.error(f"  OFAC batch {i} failed: {e}")
                ofac_fail += len(chunk)
        logger.info(f"✅ OFAC migration: {ofac_ok} OK, {ofac_fail} failed")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print(f"✅ Backfill complete")
    print(f"  Tier 1 — behavioral, cosine weight 1.0 :  {counts[1]:>6}")
    print(f"  Tier 2 — document,   cosine weight 0.5 :  {counts[2]:>6}")
    print(f"  Tier 3 — OFAC names  (excluded, fuzzy) :  {counts['ofac']:>6}")
    print(f"  Tier 3 — CryptoScamDB URLs (excluded)  :  {counts['scam']:>6}")
    print(f"  OFAC rows in ofac_sanctions table      :  {ofac_ok:>6}")
    print(f"{'='*62}")
    print("\n▶ Next: python -m backend.services.aml_scoring_service --test")


if __name__ == '__main__':
    db = get_database_service()
    run(db)