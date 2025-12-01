# File: backend/services/prediction_markets_data.py

PREDICTION_MARKETS = [
    {
        "id": 1,
        "question": "Will Super Eagles win AFCON 2025 in Morocco?",
        "description": "Nigeria to win Africa Cup of Nations 2025 (Dec 21, 2024 - Jan 18, 2025). Current odds: Favorites after runner-up finish in 2023.",
        "end_time": "2025-01-18 23:59:59", 
        "category": "sports",
        "trending_score": 99
    },
    {
        "id": 2,
        "question": "Will Bitcoin hit $150K in Q1 2026?",
        "description": "BTC price prediction for Jan-Mar 2026 (current: ~$95K)",
        "end_time": "2026-03-31 23:59:59",
        "category": "crypto",
        "trending_score": 92
    },
    {
        "id": 3,
        "question": "Will NGN exchange rate go below ₦1,350/USD by end of Q1 2026?",
        "description": "Naira devaluation prediction (current: ~₦1,500/USD)",
        "end_time": "2026-03-31 23:59:59",
        "category": "forex",
        "trending_score": 95
    },
    {
        "id": 4,
        "question": "Will Arsenal win the 2025/2026 UEFA Champions League?",
        "description": "Arsenal to win UCL final on June 7, 2026 (Allianz Stadium, Munich)",
        "end_time": "2026-06-07 23:59:59",  # ✅ CORRECTED: 2026 final
        "category": "sports",
        "trending_score": 88
    },
    {
        "id": 5,
        "question": "Will Goodluck Jonathan contest 2027 Presidential Election under PDP?",
        "description": "Former President Goodluck Jonathan to run under PDP in Feb 2027 elections",
        "end_time": "2027-01-31 23:59:59",  # Before election day
        "category": "politics",
        "trending_score": 96
    }
]