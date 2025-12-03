# 🌊 Seamount.io - African Financial Infrastructure Platform

**Production-ready multi-chain treasury platform with prediction markets, cross-border payments, and DeFi yield optimization**

[![Status](https://img.shields.io/badge/status-production-green)]()
[![Version](https://img.shields.io/badge/version-3.1.6-blue)]()
[![License](https://img.shields.io/badge/license-MIT-orange)]()

---

## 🎯 What We Do

Seamount is the **financial operating system for Africa** - combining three powerful primitives:

1. **💸 Cross-Border Payments** - Move money across 10+ African countries at 0.7% vs traditional 6-8% fees
2. **📊 Prediction Markets** - African-first AMM-based markets with 0.5-1.0% fees (vs Polymarket's 1.8%)
3. **💰 DeFi Treasury** - One-click multi-chain wallets with automated yield optimization via Folks Finance & Pact

**Target:** 1.4B Africans currently underserved by traditional finance

---

## 🚀 Quick Start

```bash
# 1. Clone repository
git clone https://github.com/yourusername/seamount.git
cd seamount

# 2. Install dependencies
npm install
pip install -r backend/requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys (see Configuration section)

# 4. Start development
npm run dev              # Frontend (http://localhost:5173)
python backend/main.py   # Backend (http://localhost:8000)
```

**First-time setup?** See [DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md)

---

## 📦 What's Built & Working

### ✅ Core Infrastructure
- **Multi-Chain Wallets** - Algorand, Bitcoin, Ethereum, Polygon, Tron support via Tether WDK
- **KYC/Compliance** - Regfyl integration with automated tier management
- **Payment Rails** - Cashramp, Paystack, Flutterwave, Pretium Africa for 10+ African countries
- **Smart Oracle** - Tiered price feeds (30s crypto, 5min precious metals, 15min industrial)

### ✅ Prediction Markets (NEW)
- **AMM Engine** - Constant Product (x × y = k) with 5-95% slippage protection
- **Capital Efficient** - 1 CAMP bootstrap minimum (vs 100 CAMP in V1)
- **Competitive Fees** - 0.5-1.0% tiered vs Kalshi's 1.2%
- **Smart Contract** - Production-ready on Basecamp testnet

### ✅ Treasury & Payments
- **One-Click Wallets** - Generate addresses across 5 chains in <2 seconds
- **FX Optimization** - Real-time quotes with 0.5-2% spreads
- **Automated Yield** - Liquidity mining & staking via Folks Finance & Pact (Algorand ecosystem)

### 🚧 In Development
- 🏦 RWA Tokenization (Financial Securities & Critical Minerals)
- 🌍 Prediction & Cross-Border Remittance Markets Dominance
- 🤖 IP Data Acquisition & AI Training/Inferencing
- 💳 Digital Credit Product Offerings

---

## 🏗️ Architecture

```
seamount/
├── frontend/               # React 18 + TypeScript + Tailwind
│   ├── src/
│   │   ├── components/    # Reusable UI (Button, Modal, etc)
│   │   ├── pages/         # Routes (Dashboard, Markets, Wallet)
│   │   ├── hooks/         # Custom React hooks
│   │   └── services/      # API clients
│   └── public/
├── backend/               # Python FastAPI + PostgreSQL
│   ├── api/
│   │   ├── routes/        # REST endpoints
│   │   │   ├── predictions.py     # 📊 Prediction markets
│   │   │   ├── wallet.py          # 💰 Multi-chain wallets
│   │   │   ├── onramp.py          # 💸 Fiat on-ramp
│   │   │   └── oracle.py          # 📈 Price feeds
│   │   └── main.py        # FastAPI app
│   ├── services/          # Business logic
│   │   ├── multi_chain_wallet_service.py
│   │   ├── oracle_service.py
│   │   ├── price_logger_service.py
│   │   └── fee_calculator.py
│   ├── models/            # Pydantic schemas
│   └── config.py          # Settings management
└── contracts/             # Solidity (Prediction Markets)
    └── SeamountPredictions.sol
```

---

## ⚙️ Configuration

### Required API Keys

```bash
# .env file structure

# 🗄️ Database (Supabase)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key

# 🔐 Authentication
JWT_SECRET=your_256_bit_secret
JWT_ALGORITHM=HS256

# 💳 Payment Processors
FLUTTERWAVE_SECRET_KEY=FLWSECK_TEST-xxx
PAYSTACK_SECRET_KEY=sk_test_xxx
CASHRAMP_API_KEY=your_cashramp_key

# 🪙 Blockchain
ALGORAND_API_KEY=your_algod_key
WDK_API_KEY=your_circle_wdk_key
PREDICTIONS_CONTRACT_ADDRESS=0x... # Basecamp testnet

# 📧 Notifications
SENDGRID_API_KEY=SG.xxx (optional - email notifications)

# 🔍 Compliance
REGFYL_API_KEY=your_regfyl_key
IPINFO_TOKEN=your_ipinfo_token
```

**Where to get keys:**
- [Supabase](https://supabase.com) - Free tier includes 500MB database
- [Flutterwave](https://flutterwave.com) - Nigerian payment gateway
- [Tether WDK](https://tether.to/en/wdk) - Multi-chain wallet infrastructure
- [Regfyl](https://regfyl.com) - African KYC provider
- [Basecamp Testnet](https://basecamp.org) - CAMP token & prediction markets

---

## 🎮 Feature Walkthrough

### 1. Prediction Markets

```bash
# Deploy V2 contract to Basecamp
cd contracts
# Use Remix IDE: https://remix.ethereum.org
# Compiler: 0.8.20 | Optimization: 200 runs
# Deploy with constructor args: (none)

# Create market
POST /api/v1/predictions/markets
{
  "question": "Will BTC reach $100k by EOY?",
  "description": "Resolves YES if BTC ≥ $100k on Dec 31",
  "end_time": "2024-12-31T23:59:59Z"
}

# Bootstrap with 1 CAMP
POST /api/v1/predictions/markets/{id}/bootstrap
{ "amount": "1000000000000000000" }

# Place bet
POST /api/v1/predictions/markets/{id}/bet
{
  "prediction": true,  # YES
  "amount": "10000000000000000"  # 0.01 CAMP
}
```

**Live demo:** [seamount.io](https://seamount.io) (Basecamp testnet)

### 2. Cross-Border Payments

```bash
# On-ramp NGN → USDC
POST /api/v1/onramp/initiate
{
  "amount": 50000,  # NGN
  "currency": "NGN",
  "payment_method": "bank_transfer",
  "wallet_address": "0x..."
}

# Check rates
GET /api/v1/oracle/price/NGN-USDC
# Response: {"rate": "0.0013", "spread": "0.5%"}

# Send cross-border
POST /api/v1/wallet/send
{
  "from_chain": "polygon",
  "to_address": "0x...",
  "amount": "100",
  "asset": "USDC"
}
```

### 3. Multi-Chain Wallets

```bash
# Create wallet (one-click)
POST /api/v1/wallet-creation/wallets
# Response: Algorand, BTC, ETH, Polygon, Tron addresses

# Check balances
GET /api/v1/wallet/portfolio/{user_id}

# Swap assets
POST /api/v1/swap
{
  "from_asset": "USDC",
  "to_asset": "USDT",
  "amount": "100",
  "slippage": 0.5
}
```

---

## 💰 Revenue Model

| Revenue Stream | Rate | Annual Projection (10K users) |
|---------------|------|------------------------------|
| **Cross-Border Fees** | 0.7% | $210K (avg $250/user/mo) |
| **Prediction Market Fees** | 0.5-1.0% | $84K ($70/month @100 bets/day) |
| **B2B Licensing** | $3.5-15K/year | $120K (10 enterprise clients) |
| **Staking Fees** | 1-2% mgmt + 20% upside | $50K (500 active stakers) |
| **TOTAL** | | **$464K ARR** |

**Burn rate:** $25K/month → **18+ months runway** at $450K raise

---

## 🚢 Deployment

### Production (Vercel + Render)

```bash
# Frontend (Vercel)
npm run build
vercel --prod

# Backend (Render)
# Push to GitHub → Auto-deploys via render.yaml
git push origin main

# Database migrations
supabase db push --linked
```

### Self-Hosted

```bash
# Docker Compose
docker-compose up -d

# Manual
# Frontend
npm run build
serve -s dist -p 3000

# Backend
gunicorn backend.main:app --workers 4 --bind 0.0.0.0:8000
```

**Monitoring:**
- Frontend errors: Sentry
- Backend: Custom metrics at `/api/v1/health`
- Database: Supabase Dashboard

---

## 🧪 Testing

```bash
# Frontend
npm run test          # Jest unit tests
npm run test:e2e      # Playwright integration

# Backend
pytest backend/tests/ -v --cov

# Load testing
locust -f backend/tests/load_test.py --host http://localhost:8000
```

**Test Credentials (Flutterwave):**
```
Card: 4187427415564246
CVV: 828
Expiry: 09/32
PIN: 3310
OTP: 12345
```

---

## 📊 Competitive Analysis

| Feature | Seamount | Polymarket | Kalshi |
|---------|----------|-----------|--------|
| **Prediction Market Fees** | 0.5-1.0% | 1.8% (→0.01% planned) | 1.2% |
| **African Focus** | ✅ Native | ❌ US-only | ❌ US-only |
| **Cross-Border** | ✅ 10+ countries | ❌ N/A | ❌ N/A |
| **Multi-Chain** | ✅ 5 chains | ❌ Polygon only | ❌ Fiat only |
| **Mobile-First** | ✅ PWA | ⚠️ Desktop-heavy | ⚠️ Desktop-heavy |

**Our edge:** Polymarket raised $200M and operates at loss. We're profitable at $10K/month scale.

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | React 18 + TypeScript | Type safety, component reuse |
| **Styling** | Tailwind CSS | Rapid UI development |
| **Backend** | Python FastAPI | Async-first, OpenAPI docs |
| **Database** | PostgreSQL (Supabase) | RLS, real-time subscriptions |
| **Blockchain** | Algorand + Tether WDK + Basecamp | Low fees, fast finality |
| **Payments** | Flutterwave + Paystack + Pretium | African market penetration |
| **Smart Contracts** | Solidity 0.8.20 | Prediction market AMM |
| **Hosting** | Vercel + Render | CI/CD, auto-scaling |

---

## 🚨 Security

- ✅ Row-Level Security (RLS) on all Supabase tables
- ✅ Rate limiting (10-20 req/min per endpoint)
- ✅ JWT authentication with refresh tokens
- ✅ KYC verification (Regfyl) before withdrawals
- ✅ Reentrancy guards on smart contracts
- ✅ Emergency pause mechanism (admin-only)
- ✅ Audit logging for all financial transactions

**Responsible Disclosure:** security@seamount.io

---

## 📚 Documentation

- [API Reference](./docs/API.md) - Complete endpoint documentation
- [Smart Contracts](./docs/CONTRACTS.md) - Prediction market mechanics
- [Integration Guide](./docs/INTEGRATION_GUIDE.md) - Payment provider setup
- [Deployment Guide](./docs/DEPLOYMENT_GUIDE.md) - Production checklist

---

## 🤝 Contributing

We're a 4-person team building for 1.4B Africans. Contributions welcome!

```bash
# 1. Fork & clone
git clone https://github.com/yourusername/seamount.git

# 2. Create feature branch
git checkout -b feature/amazing-feature

# 3. Commit with semantic messages
git commit -m "feat(predictions): add market resolution UI"

# 4. Push & PR
git push origin feature/amazing-feature
```

---

## 📈 Roadmap

*Strategic roadmap available to partners and investors upon request.*

---

## 💬 Support

- **Email:** support@seamount.io
- **Twitter:** [@Seamountusd](https://twitter.com/Seamountusd)

---

## 📜 License

MIT License - see [LICENSE](./LICENSE) for details.

---

## 🎯 The Bigger Picture

**Vision:** By 2030, 50M Africans managing $10B+ in crypto treasury through Seamount.

**Mission:** Make DeFi accessible to anyone with a $10 smartphone and internet connection.

**Values:**
- 🌍 **African-First** - Built for local context, not Silicon Valley assumptions
- ⚡ **Speed** - Ship fast, iterate faster
- 🔓 **Transparency** - Open-source, auditable, trustless
- 💪 **Resilience** - Designed to work despite poor infrastructure

---

**Built with ❤️ in Lagos | Powered by Algorand + Tether WDK + CAMP | Backed by conviction**

---

## 🔥 Quick Links

- [Live App](https://seamount.io)
- [API Docs](https://api.seamount.io/docs)
- [Contract Explorer](https://basecamp.cloud.blockscout.com/tx/0x319e35a60374195a04b443b712bbb1eca16aac8af6f326fe4de5051d82d74ab3)
- [Pitch Deck](https://bit.ly/Seamount-Deck)

**Last updated:** December 2025 | **Status:** Active Development 🚀