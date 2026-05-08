import asyncio
from datetime import datetime
from backend.dependencies import get_database_service
from backend.services.aml_scoring_service import score_transaction

DEMO_TXS = [
    {   # RED: structuring + gold scam pattern
        "tx_id": "demo_red_001",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "amount": 9850.0, "asset": "USDT", "chain": "tron",
        "recipient": "TXdemo1234567890red",
        "memo": "escrow payment for gold commodity deal Dubai",
        "created_at": datetime.utcnow().isoformat(),
    },
    {   # AMBER: velocity + pattern
        "tx_id": "demo_amber_001",
        "user_id": "00000000-0000-0000-0000-000000000002",
        "amount": 4200.0, "asset": "USDT", "chain": "polygon",
        "recipient": "0xdemo1234amber567890",
        "memo": "romance investment returns",
        "created_at": datetime.utcnow().isoformat(),
    },
    {   # RED: KES structuring (Kenya FRC threshold)
        "tx_id": "demo_red_002",
        "user_id": "00000000-0000-0000-0000-000000000003",
        "amount": 949000.0, "asset": "KES", "chain": "algorand",
        "recipient": "ALGO_DEMO_AGENT_WALLETADDR",
        "memo": "MPESA float withdrawal agent network settlement",
        "created_at": datetime.utcnow().isoformat(),
    },
]

async def main():
    db = get_database_service()
    for tx in DEMO_TXS:
        print(f"Scoring {tx['tx_id']}...")
        result = await score_transaction(tx, db)
        if result:
            print(f"  ✅ {result['band']} | {result['combined_score']:.3f} | {result.get('matched_pattern_label','')}")
        else:
            print(f"  ❌ Failed — check QVAC and DB connection")

asyncio.run(main())