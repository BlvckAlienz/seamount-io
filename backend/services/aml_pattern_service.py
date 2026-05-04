# File: backend/services/aml_pattern_service.py
"""
AML Fraud Pattern Library — seeds Supabase with QVAC embeddings.

Fixes applied vs previous version:
  1. Direct localhost QVAC (bypasses ngrok entirely)
  2. Batch embedding calls (10 texts per request)
  3. Max chunk size 1500 chars (fits GTE-Large 512-token window)
  4. Checkpoint/resume — crashes don't restart from zero
  5. requests.Session with connection pooling + HTTPAdapter retries
  6. Fixed empty pattern_id bug in CryptoScamDB parser
"""

import csv
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yaml

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

from backend.config import get_settings
from backend.dependencies import get_database_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
settings = get_settings()

# 🚨 CRITICAL: Try localhost first. Ngrok is a tunnel for external access —
# never use it for local-to-local calls. It will throttle and drop you.
_QVAC_REMOTE = settings.QVAC_API_URL.rstrip('/')
QVAC_KEY = settings.QVAC_API_KEY.get_secret_value() if settings.QVAC_API_KEY else ""

# QVAC default port is 11434. Adjust if you changed it in qvac.config.json.
_QVAC_LOCAL_CANDIDATES = [
    "http://localhost:11434",
    "http://127.0.0.1:11434",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

DATA_DIR      = Path(__file__).resolve().parent.parent / "data" / "fraud_sources"
CHECKPOINT    = Path(__file__).resolve().parent.parent / "data" / ".aml_checkpoint.json"
BATCH_SIZE    = 10      # texts per /v1/embeddings call
MAX_CHUNK     = 1500    # chars — GTE-Large is 512 tokens ≈ 2000 chars; stay safe
EMBED_TIMEOUT = 60      # seconds per batch call (10 texts × 1500 chars is fast locally)

# ---------------------------------------------------------------------------
# SESSION WITH BUILT-IN RETRY (transport layer only — we handle app retries)
# ---------------------------------------------------------------------------

def _make_session() -> requests.Session:
    sess = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST", "GET"],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=2, pool_maxsize=4)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    if QVAC_KEY:
        sess.headers.update({"Authorization": f"Bearer {QVAC_KEY}"})
    sess.headers.update({"Content-Type": "application/json"})
    return sess

SESSION: Optional[requests.Session] = None
QVAC_URL: Optional[str] = None   # resolved at runtime

# ---------------------------------------------------------------------------
# QVAC URL RESOLUTION (localhost first, ngrok fallback)
# ---------------------------------------------------------------------------

def resolve_qvac_url(sess: requests.Session) -> str:
    """Prefer localhost. Fall back to ngrok only if nothing local responds."""
    for candidate in _QVAC_LOCAL_CANDIDATES:
        try:
            r = sess.get(f"{candidate}/v1/models", timeout=5)
            if r.status_code == 200:
                logger.info(f"✅ QVAC resolved to local: {candidate}")
                print(f"✅ QVAC: using local {candidate} (no ngrok latency)")
                return candidate
        except Exception:
            continue

    # fallback to configured remote (ngrok / cloud)
    try:
        r = sess.get(f"{_QVAC_REMOTE}/v1/models", timeout=10)
        if r.status_code == 200:
            logger.warning(
                f"⚠️  QVAC not found locally — falling back to remote: {_QVAC_REMOTE}. "
                "Expect slower ingestion and possible timeouts."
            )
            print(f"⚠️  QVAC: using remote {_QVAC_REMOTE} — consider running QVAC locally!")
            return _QVAC_REMOTE
    except Exception as e:
        logger.error(f"QVAC remote also unreachable: {e}")

    raise RuntimeError(
        "QVAC is not reachable locally or remotely. "
        "Start QVAC with: qvac serve  (check qvac.config.json port)"
    )

# ---------------------------------------------------------------------------
# BATCH EMBEDDING
# ---------------------------------------------------------------------------

def embed_batch(texts: List[str], max_retries: int = 4) -> List[Optional[List[float]]]:
    """
    Embed a batch of texts in a single HTTP call.
    Returns a list of embeddings (same order as input); None for any that fail.
    """
    global SESSION, QVAC_URL
    url     = f"{QVAC_URL}/v1/embeddings"
    payload = {"model": "embedder", "input": texts}

    for attempt in range(1, max_retries + 1):
        try:
            resp = SESSION.post(url, json=payload, timeout=EMBED_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            # OpenAI-compatible response: data["data"] is a list sorted by index
            embeddings = [None] * len(texts)
            for item in data.get("data", []):
                embeddings[item["index"]] = item["embedding"]
            return embeddings
        except requests.exceptions.Timeout:
            wait = 2 ** attempt
            logger.warning(f"Embed timeout (attempt {attempt}/{max_retries}), retrying in {wait}s...")
            time.sleep(wait)
        except requests.exceptions.ConnectionError as e:
            wait = 2 ** attempt
            logger.warning(f"Embed connection error (attempt {attempt}/{max_retries}): {e}, retrying in {wait}s...")
            time.sleep(wait)
        except Exception as e:
            logger.error(f"Embed unexpected error (attempt {attempt}/{max_retries}): {e}")
            time.sleep(2)

    logger.error(f"Batch embedding failed after {max_retries} attempts — skipping {len(texts)} patterns")
    return [None] * len(texts)

# ---------------------------------------------------------------------------
# CHECKPOINT (resume support)
# ---------------------------------------------------------------------------

def load_checkpoint() -> set:
    """Return set of already-ingested pattern_ids."""
    if CHECKPOINT.exists():
        try:
            data = json.loads(CHECKPOINT.read_text())
            ids  = set(data.get("done", []))
            logger.info(f"📌 Checkpoint loaded: {len(ids)} patterns already done")
            print(f"📌 Resuming — {len(ids)} patterns already ingested, skipping them")
            return ids
        except Exception as e:
            logger.warning(f"Checkpoint load failed (starting fresh): {e}")
    return set()

def save_checkpoint(done_ids: set):
    try:
        CHECKPOINT.write_text(json.dumps({"done": list(done_ids), "ts": datetime.utcnow().isoformat()}))
    except Exception as e:
        logger.warning(f"Checkpoint save failed: {e}")

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def extract_text_from_pdf(file_path: str) -> str:
    if PdfReader is None:
        logger.warning("PyPDF2 not installed — skipping PDF")
        return ""
    try:
        reader = PdfReader(file_path)
        return '\n'.join(page.extract_text() or '' for page in reader.pages)
    except Exception as e:
        logger.error(f"PDF extract {file_path}: {e}")
        return ""

def read_text_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

def chunk_text(text: str, max_chars: int = MAX_CHUNK) -> List[str]:
    """Split at word boundaries, max_chars per chunk."""
    words    = text.split()
    chunks   = []
    current  = []
    cur_len  = 0
    for word in words:
        if cur_len + len(word) + 1 > max_chars and current:
            chunks.append(' '.join(current))
            current = [word]
            cur_len = len(word)
        else:
            current.append(word)
            cur_len += len(word) + 1
    if current:
        chunks.append(' '.join(current))
    return chunks or [text[:max_chars]]

# ---------------------------------------------------------------------------
# PARSERS
# ---------------------------------------------------------------------------

def parse_ofac_files(ofac_dir: str) -> List[Dict[str, str]]:
    patterns = []
    base     = Path(ofac_dir)
    sdn_path = base / "sdn.csv"
    if not sdn_path.exists():
        return patterns

    with open(sdn_path, 'r', encoding='utf-8', errors='ignore') as f:
        for row in csv.DictReader(f):
            name = row.get('sdn_name', '').strip()
            if not name:
                continue
            combined = clean_text(
                f"{name} | {row.get('sdn_type','')} | {row.get('program','')} | {row.get('remarks','')}"
            )
            patterns.append({
                "pattern_id": f"ofac_{row.get('sdn_id','')}",
                "label":      "OFAC Sanction",
                "description": combined,
                "source":     "ofac_sdn",
            })

    alt_path = base / "alt.csv"
    if alt_path.exists():
        with open(alt_path, 'r', encoding='utf-8', errors='ignore') as f:
            for row in csv.DictReader(f):
                alt = row.get('alt_name', '').strip()
                if not alt:
                    continue
                patterns.append({
                    "pattern_id": f"ofac_alt_{row.get('ent_num',row.get('sdn_id',''))}_{row.get('alt_name','').replace(' ','_')[:20]}",
                    "label":      "OFAC Alias",
                    "description": clean_text(alt),
                    "source":     "ofac_alt",
                })
    return patterns


def parse_cryptoscamdb(data_dir: str) -> List[Dict[str, str]]:
    """
    Fixed: generates stable, non-empty pattern_ids using URL hash.
    Previous bug: all entries got id 'cscamdb_' because name was empty.
    """
    patterns = []
    base     = Path(data_dir)

    for yaml_file in ['urls.yaml']:
        file_path = base / yaml_file
        if not file_path.exists():
            continue
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                entries = yaml.safe_load(f)
            except yaml.YAMLError as e:
                logger.warning(f"YAML parse error {yaml_file}: {e}")
                continue

        if not isinstance(entries, list):
            entries = [entries] if entries else []

        for entry in entries:
            if isinstance(entry, str):
                entry = entry.strip()
                if not entry:
                    continue
                # Use hash of URL as stable ID
                uid = re.sub(r'[^a-zA-Z0-9]', '_', entry)[:40]
                patterns.append({
                    "pattern_id": f"cscamdb_{uid}",
                    "label":      "CryptoScamDB URI",
                    "description": entry,
                    "source":     "cryptoscamdb",
                })
            elif isinstance(entry, dict):
                name = entry.get('name', '').strip() or entry.get('url', '').strip()
                if not name:
                    continue
                uid     = re.sub(r'[^a-zA-Z0-9]', '_', name)[:40]
                pid     = entry.get('id') or uid
                combined = clean_text(
                    f"{name} | {entry.get('category','')} | {entry.get('description','')} | {entry.get('url','')}"
                )
                patterns.append({
                    "pattern_id": f"cscamdb_{pid}",
                    "label":      f"CryptoScamDB {entry.get('category','')}",
                    "description": combined,
                    "source":     "cryptoscamdb",
                })

    # Deduplicate by pattern_id (YAML can have dupes)
    seen = {}
    for p in patterns:
        seen[p['pattern_id']] = p
    return list(seen.values())


def parse_country_documents(country_dir: str, source_label: str) -> List[Dict[str, str]]:
    patterns = []
    base     = Path(country_dir)
    if not base.exists():
        return patterns

    for file_path in sorted(base.iterdir()):
        if file_path.suffix in ('.txt', '.md'):
            raw = read_text_file(str(file_path))
        elif file_path.suffix == '.pdf':
            raw = extract_text_from_pdf(str(file_path))
        else:
            continue

        raw = clean_text(raw)
        if not raw:
            continue

        chunks = chunk_text(raw, max_chars=MAX_CHUNK)
        for i, chunk in enumerate(chunks):
            patterns.append({
                "pattern_id": f"{source_label}_{file_path.stem}_p{i+1:04d}",
                "label":      f"{source_label.upper()} Doc chunk {i+1}/{len(chunks)}",
                "description": chunk,
                "source":     source_label,
            })

    return patterns

# ---------------------------------------------------------------------------
# BATCH UPSERT HELPER
# ---------------------------------------------------------------------------

def upsert_batch(
    db_service,
    batch: List[Tuple[Dict, List[float]]],
    done_ids: set,
) -> Tuple[int, int]:
    """Upsert a list of (pattern, embedding) pairs. Returns (ok, fail)."""
    ok = fail = 0
    for pattern, emb in batch:
        if emb is None:
            fail += 1
            continue
        try:
            db_service.supabase.table('aml_fraud_patterns').upsert({
                'pattern_id':  pattern['pattern_id'],
                'label':       pattern['label'],
                'description': pattern['description'],
                'embedding':   emb,
                'source':      pattern['source'],
                'created_at':  datetime.utcnow().isoformat(),
            }, on_conflict='pattern_id').execute()
            done_ids.add(pattern['pattern_id'])
            ok += 1
        except Exception as e:
            logger.error(f"Upsert failed {pattern['pattern_id']}: {e}")
            fail += 1
    save_checkpoint(done_ids)
    return ok, fail

# ---------------------------------------------------------------------------
# MAIN INGESTION
# ---------------------------------------------------------------------------

def ingest_fraud_patterns(db_service):
    global SESSION, QVAC_URL

    SESSION  = _make_session()
    QVAC_URL = resolve_qvac_url(SESSION)   # localhost wins if available

    done_ids = load_checkpoint()
    total_ok = total_fail = 0

    # Collect all pattern sources
    all_sources: List[Tuple[str, List[Dict]]] = []

    # 1) Hand-crafted typologies
    all_sources.append(("typologies", [
        {"pattern_id": p['id'], "label": p['label'], "description": p['description'], "source": "manual_typology"}
        for p in NIGERIA_KENYA_TYPOLOGIES
    ]))

    # 2) OFAC
    ofac_dir = DATA_DIR / "ofac"
    if ofac_dir.exists():
        all_sources.append(("OFAC", parse_ofac_files(str(ofac_dir))))

    # 3) CryptoScamDB
    cscam_dir = DATA_DIR / "cryptoscamdb"
    if cscam_dir.exists():
        all_sources.append(("CryptoScamDB", parse_cryptoscamdb(str(cscam_dir))))

    # 4) Nigeria docs
    all_sources.append(("Nigeria", parse_country_documents(str(DATA_DIR / "nigeria"), "nigeria")))

    # 5) Kenya docs
    all_sources.append(("Kenya", parse_country_documents(str(DATA_DIR / "kenya"), "kenya")))

    for source_name, patterns in all_sources:
        # Skip already-done
        pending = [p for p in patterns if p['pattern_id'] not in done_ids]
        if not pending:
            print(f"⏭️  {source_name}: all {len(patterns)} already ingested")
            continue

        print(f"\n🔄 {source_name}: {len(pending)} pending / {len(patterns)} total")

        # Process in batches
        for i in range(0, len(pending), BATCH_SIZE):
            batch_patterns = pending[i:i + BATCH_SIZE]
            texts          = [f"{p['label']}: {p['description']}" for p in batch_patterns]
            embeddings     = embed_batch(texts)

            pairs = list(zip(batch_patterns, embeddings))
            ok, fail = upsert_batch(db_service, pairs, done_ids)
            total_ok   += ok
            total_fail += fail

            pct  = (i + len(batch_patterns)) / len(pending) * 100
            print(f"  {source_name}: {i + len(batch_patterns)}/{len(pending)} ({pct:.0f}%) | ✅{ok} ❌{fail}", end='\r')

        print()  # newline after \r progress

    print(f"\n{'='*60}")
    print(f"✅ Ingestion complete: {total_ok} inserted, {total_fail} failed")
    print(f"📌 Checkpoint saved to {CHECKPOINT}")
    if total_fail > 0:
        print(f"⚠️  Re-run script to retry {total_fail} failed patterns (checkpoint will skip done ones)")


# ---------------------------------------------------------------------------
# TYPOLOGIES
# ---------------------------------------------------------------------------
NIGERIA_KENYA_TYPOLOGIES = [
    {
        "id": "ng_001", "label": "BVN Mule Account",
        "description": "Multiple accounts created with the same BVN or NIN within 24 hours. "
                       "Common in Nigerian fraud rings where synthetic identities are bulk-registered.",
    },
    {
        "id": "ng_002", "label": "Credit Alert Scam",
        "description": "User receives unsolicited credit alert SMS followed by a callback request. "
                       "Fraudster reverses the transaction after victim transfers funds.",
    },
    {
        "id": "ng_003", "label": "Romance Scam Mule",
        "description": "Account with no prior activity suddenly receives large international wire then "
                       "immediately disburses to multiple local accounts. Classic romance scam laundering.",
    },
    {
        "id": "ng_004", "label": "Posh Fraud Ring",
        "description": "Cluster of accounts sharing the same device fingerprint or IP originating "
                       "from a single location, making coordinated small transfers to avoid thresholds.",
    },
    {
        "id": "ke_001", "label": "MPESA Agent Abuse",
        "description": "Agent account processes unusually high volumes of float withdrawals in "
                       "short windows, often used to cash out stolen mobile banking credentials.",
    },
    {
        "id": "ke_002", "label": "SIM Swap Takeover",
        "description": "Account shows login from new device immediately after SIM change, "
                       "followed by rapid fund transfers — textbook SIM-swap account takeover.",
    },
    {
        "id": "cross_001", "label": "Structuring / Smurfing",
        "description": "Multiple transactions just below the regulatory reporting threshold "
                       "(e.g. KES 999,000 or USD 9,900) across different beneficiaries in a short period.",
    },
    {
        "id": "crypto_001", "label": "Rug Pull Exit",
        "description": "Smart contract deployer receives large aggregated deposits then executes "
                       "a single drain transaction to an external wallet, leaving LPs with worthless tokens.",
    },
    # DCI Cases — Kenya regulator ground truth (from DCI_Cases.txt)
    {
        "id": "ke_dci_001", "label": "Fabricated Police Report Fraud",
        "description": "Suspects file false reports at police stations claiming to be fraud victims, "
                       "producing forged debt acknowledgement documents to extort a real businessman. "
                       "Victim abducted by persons posing as police officers, passport seized, "
                       "forced to sign debt agreement under duress. USD 394,209 fraudulent scheme.",
    },
    {
        "id": "ke_dci_002", "label": "Gold Scam with POCAMLA Laundering",
        "description": "Fraudsters pose as gold dealers (495kg gold, Dubai charter), collect "
                       "escrow payments into advocate accounts, then immediately wire funds overseas "
                       "via a mobile phone trading company to obscure origin. Involves fictitious "
                       "legal representation and logistics companies. USD 217,900 loss.",
    },
    {
        "id": "ke_dci_003", "label": "SACCO Internal Fraud via Cheque Kiting",
        "description": "Insider accountant issues 58 off-ledger cheques using member accounts, "
                       "collaborates with external construction company director to cash them. "
                       "Cheques never recorded in ledger. Forged withdrawal slips. KES 16M loss.",
    },
    {
        "id": "ke_dci_004", "label": "Microfinance Cyber Heist via Java Backdoor",
        "description": "Attacker installs malicious Java application on microfinance core banking system, "
                       "executes 38 fraudulent transactions invisible to internal controls, erases "
                       "system and database logs. Launders via multiple mule accounts. KES 11.4M.",
    },
    {
        "id": "ke_dci_005", "label": "Fake Commodity Deal (Mercury / Gold)",
        "description": "Victim lured into bogus commodity trade (mercury/gold), transported to "
                       "unfamiliar location, handed fake product under theatrical conditions. "
                       "Payment via M-Pesa and cash. KES 3.8M loss.",
    },
    {
        "id": "ke_dci_006", "label": "Healthcare Provider SHA Fraud",
        "description": "Hospital director fabricates patient claims and manipulates health documents "
                       "to obtain fraudulent reimbursements from the Social Health Authority. "
                       "Proceeds constitute crime under POCAMLA. KES 2.5M.",
    },
    {
        "id": "ke_dci_007", "label": "Fake Government Recruitment Scam",
        "description": "Suspects including an active government official forge appointment letters "
                       "from Teachers Service Commission, charge victims KES 40M+ for non-existent "
                       "permanent and pensionable positions. Network spans multiple counties.",
    },
]

# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'
    )
    db = get_database_service()
    ingest_fraud_patterns(db)