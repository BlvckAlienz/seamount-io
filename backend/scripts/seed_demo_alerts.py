# File: backend/scripts/seed_demo_alerts.py
"""
Comprehensive AML demo scenario seeder.
Covers all major fraud typologies in the pattern library.

Run:  python -m backend.scripts.seed_demo_alerts
Each transaction is scored directly — no wallet balance or chain tx needed.
Expected bands are approximate; actual score depends on pattern library state.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.dependencies import get_database_service
from backend.services.aml_scoring_service import score_transaction

# ─────────────────────────────────────────────────────────────
# All amounts are chosen to trigger specific factors:
#   • USDT/USDC amounts near $10k  → structuring (FATF)
#   • KES amounts near 1,000,000   → structuring (FRC Kenya)
#   • NGN amounts near 5,000,000   → structuring (CBN)
#   • BTC 0.11-0.12                → structuring (~$10k equiv)
#   • ETH 2.9-3.4                  → structuring (~$10k equiv)
#   • SOL 82-98                    → structuring (~$10k equiv)
#   • TRX 76,000-89,000            → structuring (~$10k equiv)
# ─────────────────────────────────────────────────────────────

SCENARIOS = [

    # ── SCENARIO 1 ─────────────────────────────────────────────────────────
    # Pattern target : ke_dci_002 — Gold Scam with POCAMLA Laundering
    # Chain          : Tron (USDT)
    # Factors firing : pattern_similarity (HIGH) + structuring
    # Expected band  : RED
    {
        "tx_id":      "demo_gold_scam_tron",
        "user_id":    "00000000-0000-0000-0000-000000000001",
        "amount":     9850.0,
        "asset":      "USDT",
        "chain":      "tron",
        "recipient":  "TXGoldDubaiEscrow1234567890",
        "memo":       "escrow payment 495kg gold commodity deal Dubai charter flight",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "Gold scam + structuring at 98.5% of FATF $10K threshold",
    },

    # ── SCENARIO 2 ─────────────────────────────────────────────────────────
    # Pattern target : ng_003 — Romance Scam Mule
    # Chain          : Tron (USDT)
    # Factors firing : pattern_similarity (HIGH) + large amount
    # Expected band  : RED
    {
        "tx_id":      "demo_romance_scam_mule",
        "user_id":    "00000000-0000-0000-0000-000000000002",
        "amount":     18500.0,
        "asset":      "USDT",
        "chain":      "tron",
        "recipient":  "TXRomanceMule987654321XYZ",
        "memo":       "forex investment returns disbursement from offshore account",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "Large international wire + immediate disbursement language",
    },

    # ── SCENARIO 3 ─────────────────────────────────────────────────────────
    # Pattern target : cross_001 — Structuring / Smurfing
    # Chain          : Polygon (USDT) — gasless for small amounts
    # Factors firing : structuring (MAXED) + pattern_similarity
    # Expected band  : RED
    {
        "tx_id":      "demo_structuring_polygon",
        "user_id":    "00000000-0000-0000-0000-000000000003",
        "amount":     9900.0,
        "asset":      "USDT_POLYGON",
        "chain":      "polygon",
        "recipient":  "0xStructuringAddr1234567890abcdef",
        "memo":       "multiple beneficiary payment just below threshold",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "Classic structuring: 99% of $10K FATF threshold on stablecoin",
    },

    # ── SCENARIO 4 ─────────────────────────────────────────────────────────
    # Pattern target : ke_001 — MPESA Agent Abuse
    # Chain          : Algorand (USDT_ALGO)
    # Factors firing : pattern_similarity + KES structuring
    # Expected band  : RED
    {
        "tx_id":      "demo_mpesa_agent_abuse",
        "user_id":    "00000000-0000-0000-0000-000000000004",
        "amount":     949000.0,
        "asset":      "KES",
        "chain":      "algorand",
        "recipient":  "ALGO_MPESA_AGENT_FLOAT_WALLETADDR",
        "memo":       "MPESA float withdrawal agent network cash-out settlement",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "MPESA agent abuse + 94.9% of KES 1M FRC Kenya threshold",
    },

    # ── SCENARIO 5 ─────────────────────────────────────────────────────────
    # Pattern target : crypto_001 — Rug Pull Exit
    # Chain          : Ethereum
    # Factors firing : pattern_similarity (HIGH)
    # Expected band  : RED
    {
        "tx_id":      "demo_rug_pull_eth",
        "user_id":    "00000000-0000-0000-0000-000000000005",
        "amount":     3.45,
        "asset":      "ETH",
        "chain":      "ethereum",
        "recipient":  "0xRugPullDrainWallet1234567890abcd",
        "memo":       "liquidity pool exit smart contract drain token distribution",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "DeFi rug pull: LP drain + 98.6% of ETH structuring threshold",
    },

    # ── SCENARIO 6 ─────────────────────────────────────────────────────────
    # Pattern target : ke_002 — SIM Swap Account Takeover
    # Chain          : Tron (USDT)
    # Factors firing : pattern_similarity + time_anomaly (03:00 UTC)
    # Expected band  : AMBER → RED depending on hour
    {
        "tx_id":      "demo_sim_swap_takeover",
        "user_id":    "00000000-0000-0000-0000-000000000006",
        "amount":     4750.0,
        "asset":      "USDT",
        "chain":      "tron",
        "recipient":  "TXNewDeviceAfterSimChange987",
        "memo":       "urgent account recovery transfer new wallet after sim change",
        "created_at": (datetime.utcnow().replace(hour=3, minute=14)).isoformat(),
        "_note":      "SIM swap + 03:14 UTC deep overnight anomaly",
    },

    # ── SCENARIO 7 ─────────────────────────────────────────────────────────
    # Pattern target : ng_001 — BVN Mule Account
    # Chain          : Polygon (USDT) — small coordinated transfer
    # Factors firing : pattern_similarity
    # Expected band  : AMBER
    {
        "tx_id":      "demo_bvn_mule",
        "user_id":    "00000000-0000-0000-0000-000000000007",
        "amount":     450.0,
        "asset":      "USDT_POLYGON",
        "chain":      "polygon",
        "recipient":  "0xBVNMuleAccount1234pooled",
        "memo":       "BVN account pooled funds disbursement synthetic identity",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "BVN mule: small amount but vocabulary matches fraud typology",
    },

    # ── SCENARIO 8 ─────────────────────────────────────────────────────────
    # Pattern target : ke_dci_007 — Fake Government Recruitment Scam
    # Chain          : Tron (USDT)
    # Factors firing : pattern_similarity (HIGH) + structuring
    # Expected band  : RED
    {
        "tx_id":      "demo_fake_govt_recruitment",
        "user_id":    "00000000-0000-0000-0000-000000000008",
        "amount":     9750.0,
        "asset":      "USDT",
        "chain":      "tron",
        "recipient":  "TXGovtRecruitmentScam123TSC",
        "memo":       "teachers service commission appointment processing fee permanent pensionable",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "Fake TSC appointment scam + 97.5% of FATF structuring threshold",
    },

    # ── SCENARIO 9 ─────────────────────────────────────────────────────────
    # Pattern target : crypto_001 — Rug Pull (Solana DeFi)
    # Chain          : Solana (USDT_SOLANA)
    # Factors firing : pattern_similarity + structuring
    # Expected band  : RED
    {
        "tx_id":      "demo_rug_pull_solana",
        "user_id":    "00000000-0000-0000-0000-000000000009",
        "amount":     97.5,
        "asset":      "SOL",
        "chain":      "solana",
        "recipient":  "SolRugPullDrainWalletAddr1234XYZ",
        "memo":       "token liquidity drain LP exit worthless pool distribution wallet",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "Solana DeFi rug pull + 97.5% of SOL structuring threshold (~$9,750)",
    },

    # ── SCENARIO 10 ────────────────────────────────────────────────────────
    # Pattern target : ke_dci_005 — Fake Commodity Deal (Mercury)
    # Chain          : Algorand (ALGO)
    # Factors firing : pattern_similarity (HIGH)
    # Expected band  : AMBER → RED
    {
        "tx_id":      "demo_mercury_commodity",
        "user_id":    "00000000-0000-0000-0000-000000000010",
        "amount":     63500.0,
        "asset":      "ALGO",
        "chain":      "algorand",
        "recipient":  "ALGO_COMMODITY_MERCURY_DEAL_ADDR",
        "memo":       "mercury commodity advance payment verification theatrical conditions",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "Fake mercury/commodity scam; ALGO amount ~$9,525 near threshold",
    },

    # ── SCENARIO 11 ────────────────────────────────────────────────────────
    # Pattern target : ng_004 — Posh Fraud Ring (Coordinated small transfers)
    # Chain          : Polygon (USDT) — gasless
    # Factors firing : pattern_similarity
    # Expected band  : AMBER
    {
        "tx_id":      "demo_posh_fraud_ring",
        "user_id":    "00000000-0000-0000-0000-000000000011",
        "amount":     890.0,
        "asset":      "USDT_POLYGON",
        "chain":      "polygon",
        "recipient":  "0xCoordinatedSmallTransferRing",
        "memo":       "coordinated small transfer avoid threshold shared device fingerprint",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "Fraud ring: coordinated below-threshold transfers from shared IP",
    },

    # ── SCENARIO 12 ────────────────────────────────────────────────────────
    # Pattern target : ke_dci_004 — Microfinance Cyber Heist
    # Chain          : Bitcoin
    # Factors firing : pattern_similarity + large amount
    # Expected band  : RED
    {
        "tx_id":      "demo_microfinance_heist_btc",
        "user_id":    "00000000-0000-0000-0000-000000000012",
        "amount":     0.121,
        "asset":      "BTC",
        "chain":      "bitcoin",
        "recipient":  "bc1qMicrofinanceHeistDrainWallet",
        "memo":       "core banking system fraudulent transaction mule account launder",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "Cyber heist via core banking + BTC at 93.1% of structuring threshold",
    },

    # ── SCENARIO 13 ────────────────────────────────────────────────────────
    # Pattern target : ke_dci_003 — SACCO Internal Fraud / Cheque Kiting
    # Chain          : Algorand (USDCa)
    # Factors firing : pattern_similarity
    # Expected band  : AMBER
    {
        "tx_id":      "demo_sacco_internal_fraud",
        "user_id":    "00000000-0000-0000-0000-000000000013",
        "amount":     8200.0,
        "asset":      "USDCa",
        "chain":      "algorand",
        "recipient":  "ALGO_SACCO_INSIDER_ACCOUNT_ADDR",
        "memo":       "SACCO member account off-ledger withdrawal forged slip insider",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "SACCO internal fraud vocabulary + 82% of structuring threshold",
    },

    # ── SCENARIO 14 ────────────────────────────────────────────────────────
    # Pattern target : ng_002 — Credit Alert Scam
    # Chain          : Tron (TRX) — small native asset
    # Factors firing : pattern_similarity
    # Expected band  : AMBER
    {
        "tx_id":      "demo_credit_alert_scam",
        "user_id":    "00000000-0000-0000-0000-000000000014",
        "amount":     84000.0,
        "asset":      "TRX",
        "chain":      "tron",
        "recipient":  "TXCreditAlertCallbackReverse99",
        "memo":       "reverse transaction credit alert SMS unsolicited callback reversal",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "Credit alert reversal scam + TRX at 93.3% of structuring threshold",
    },

    # ── SCENARIO 15 ────────────────────────────────────────────────────────
    # Pattern target : ke_dci_001 — Fabricated Police Report + Abduction
    # Chain          : Tron (USDT)
    # Factors firing : pattern_similarity (HIGH) + structuring
    # Expected band  : RED
    {
        "tx_id":      "demo_fabricated_police_report",
        "user_id":    "00000000-0000-0000-0000-000000000015",
        "amount":     9500.0,
        "asset":      "USDT",
        "chain":      "tron",
        "recipient":  "TXForcedDebtAgreementExtort123",
        "memo":       "debt acknowledgement settlement forced agreement police report fraud",
        "created_at": datetime.utcnow().isoformat(),
        "_note":      "Extortion via fabricated police report + 95% of FATF threshold",
    },

]


# ─────────────────────────────────────────────────────────────
async def main():
    db = get_database_service()

    print(f"\n{'='*68}")
    print(f"  SEAMOUNT AML ENGINE — FRAUD SCENARIO COVERAGE TEST")
    print(f"  {len(SCENARIOS)} scenarios across {len({s['chain'] for s in SCENARIOS})} chains")
    print(f"{'='*68}\n")

    results = []
    for scenario in SCENARIOS:
        note = scenario.pop('_note', '')
        print(f"[{scenario['tx_id']}]")
        print(f"  Chain: {scenario['chain']} | Asset: {scenario['asset']} | Amount: {scenario['amount']}")
        print(f"  Scenario: {note}")

        result = await score_transaction(scenario, db)

        if result:
            band  = result['band']
            score = result['combined_score']
            pat   = result.get('matched_pattern_label', 'N/A')
            sim   = result.get('pattern_similarity', 0)

            band_icon = {'RED': '🔴', 'AMBER': '🟡', 'GREEN': '✅'}.get(band, '❓')
            print(f"  {band_icon} {band} | Score: {score:.3f} | Pattern: '{pat}' ({sim:.3f} sim)")

            factors = result.get('factors', {})
            fired = [(k, v['score']) for k, v in factors.items() if v['score'] > 0.05]
            fired.sort(key=lambda x: -x[1])
            if fired:
                factor_str = ' | '.join(f"{k.split('_')[0]}={v:.2f}" for k, v in fired)
                print(f"  Factors: {factor_str}")

            if result.get('str_explanation'):
                preview = result['str_explanation'][:120].replace('\n', ' ')
                print(f"  STR: {preview}...")

            results.append({'tx_id': scenario['tx_id'], 'band': band, 'score': score})
        else:
            print(f"  ❌ Scoring failed — check QVAC and DB connection")
            results.append({'tx_id': scenario['tx_id'], 'band': 'ERROR', 'score': 0})

        print()

    # ── Summary ──────────────────────────────────────────────
    red   = [r for r in results if r['band'] == 'RED']
    amber = [r for r in results if r['band'] == 'AMBER']
    err   = [r for r in results if r['band'] == 'ERROR']

    print(f"{'='*68}")
    print(f"  SUMMARY: {len(red)} RED | {len(amber)} AMBER | {len(err)} ERRORS")
    print(f"{'='*68}")
    for r in sorted(results, key=lambda x: -x['score']):
        icon = {'RED': '🔴', 'AMBER': '🟡', 'GREEN': '✅', 'ERROR': '❌'}.get(r['band'], '❓')
        print(f"  {icon} {r['score']:.3f}  {r['tx_id']}")
    print()


if __name__ == '__main__':
    asyncio.run(main())