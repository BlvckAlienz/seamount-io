# File: backend/scripts/backfill_pattern_tiers.py
"""
One-time migration: tag aml_fraud_patterns with tier/modality/scoring_weight
and migrate OFAC entries into ofac_sanctions.

Timeout fix: fetches pattern_ids first (small payload), then updates
in batches of ID_BATCH rows — never hits Supabase's statement timeout.

Run after migration 002_aml_pipeline.sql:
  python -m backend.scripts.backfill_pattern_tiers
Idempotent — safe to re-run.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from backend.dependencies import get_database_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

ID_BATCH = 150   # pattern_ids per UPDATE call — stays well under timeout

# Source → (tier, modality, scoring_weight, excluded_from_scoring)
SOURCE_TIER_MAP = [
    (['manual_typology'],       1, 'behavioral',  1.0, False),
    (['nigeria', 'kenya'],      2, 'document',    0.5, False),
    (['ofac_sdn', 'ofac_alt'],  3, 'entity_name', 0.0, True),
    (['cryptoscamdb'],          3, 'url',          0.0, True),
]


def _fetch_ids_for_sources(db_service, sources: List[str]) -> List[str]:
    """Paginated fetch of pattern_ids matching given source values."""
    ids: List[str] = []
    page, offset = 500, 0
    while True:
        query = (db_service.supabase
                 .table('aml_fraud_patterns')
                 .select('pattern_id'))
        query = (query.eq('source', sources[0])
                 if len(sources) == 1
                 else query.in_('source', sources))
        res = query.range(offset, offset + page - 1).execute()
        batch = [r['pattern_id'] for r in (res.data or [])]
        ids.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return ids


def _batch_update(db_service, ids: List[str], payload: Dict) -> int:
    """Update rows by pattern_id in ID_BATCH-sized chunks. Returns success count."""
    ok = 0
    for i in range(0, len(ids), ID_BATCH):
        chunk = ids[i:i + ID_BATCH]
        try:
            db_service.supabase.table('aml_fraud_patterns')\
                .update(payload)\
                .in_('pattern_id', chunk)\
                .execute()
            ok += len(chunk)
            print(f"  Updated {ok}/{len(ids)}...", end='\r')
        except Exception as e:
            logger.error(f"  Batch {i} failed: {e}")
    print()
    return ok


def parse_ofac(pattern_id: str, description: str, source: str) -> Dict:
    parts = [p.strip() for p in (description or '').split('|')]
    sdn_id = None
    if source == 'ofac_sdn':
        raw = pattern_id.replace('ofac_', '')
        sdn_id = raw.split('_')[0] if '_' in raw else raw
    return {
        'pattern_id':  pattern_id,
        'sdn_id':      sdn_id,
        'entity_name': (parts[0] if parts else description or 'UNKNOWN')[:500],
        'entity_type': parts[1] if len(parts) > 1 else None,
        'program':     parts[2] if len(parts) > 2 else None,
        'remarks':     parts[3] if len(parts) > 3 else None,
        'aliases':     [],
        'source':      source,
    }


def run(db_service):
    logger.info("🏷️  Starting pattern tier backfill (batched by ID, timeout-proof)...")

    total_updated = 0

    for sources, tier, modality, weight, excluded in SOURCE_TIER_MAP:
        payload = {
            'tier':                  tier,
            'modality':              modality,
            'scoring_weight':        weight,
            'excluded_from_scoring': excluded,
        }

        logger.info(f"Fetching IDs for source={sources}...")
        ids = _fetch_ids_for_sources(db_service, sources)

        if not ids:
            logger.info(f"  ℹ️  No patterns found for source={sources} — skipping")
            continue

        logger.info(f"  Updating {len(ids)} patterns → tier={tier}, excluded={excluded}")
        ok = _batch_update(db_service, ids, payload)
        total_updated += ok
        logger.info(f"  ✅ {ok}/{len(ids)} updated for source={sources}")

    # ── OFAC migration to ofac_sanctions ────────────────────────────────────
    logger.info("🔐 Fetching OFAC patterns for ofac_sanctions...")
    ofac_ids = _fetch_ids_for_sources(db_service, ['ofac_sdn', 'ofac_alt'])
    ofac_ok = ofac_fail = 0

    if ofac_ids:
        # Fetch full rows for parsing
        ofac_rows: List[Dict] = []
        for i in range(0, len(ofac_ids), 500):
            chunk = ofac_ids[i:i + 500]
            res = db_service.supabase.table('aml_fraud_patterns')\
                .select('pattern_id, source, description')\
                .in_('pattern_id', chunk)\
                .execute()
            for p in (res.data or []):
                ofac_rows.append(
                    parse_ofac(p['pattern_id'], p.get('description', ''), p.get('source', 'ofac_sdn'))
                )

        for i in range(0, len(ofac_rows), ID_BATCH):
            chunk = ofac_rows[i:i + ID_BATCH]
            try:
                db_service.supabase.table('ofac_sanctions')\
                    .upsert(chunk, on_conflict='pattern_id')\
                    .execute()
                ofac_ok += len(chunk)
            except Exception as e:
                logger.error(f"  OFAC batch {i} failed: {e}")
                ofac_fail += len(chunk)
        logger.info(f"  ✅ OFAC: {ofac_ok} migrated, {ofac_fail} failed")
    else:
        logger.info("  ℹ️  No OFAC patterns in aml_fraud_patterns (run aml_pattern_service.py first)")

    # ── Verification counts ──────────────────────────────────────────────────
    try:
        rows = db_service.supabase.table('aml_fraud_patterns')\
            .select('tier, excluded_from_scoring', count='exact')\
            .execute()
        from collections import Counter
        tier_counts = Counter(r['tier'] for r in (rows.data or []))
        excl_count  = sum(1 for r in (rows.data or []) if r.get('excluded_from_scoring'))
    except Exception:
        tier_counts = {}
        excl_count  = '?'

    print(f"\n{'='*62}")
    print(f"✅ Backfill complete  ({total_updated} total rows updated)")
    print(f"  Tier 1 — behavioral, cosine weight 1.0  : {tier_counts.get(1,'?'):>6}")
    print(f"  Tier 2 — document,   cosine weight 0.5  : {tier_counts.get(2,'?'):>6}")
    print(f"  Tier 3 — excluded from cosine scoring   : {excl_count:>6}")
    print(f"  OFAC rows in ofac_sanctions table        : {ofac_ok:>6}")
    print(f"{'='*62}")
    print(f"\n▶ Next: python -m backend.services.aml_scoring_service")


if __name__ == '__main__':
    db = get_database_service()
    run(db)