# 🌊 Seamount.io - Digital Assets & Yield-Farming Gateway

**Production-ready cross-border payment platform with one-click multi-chain wallet generation across 4+ chains (Algorand, Bitcoin, Ethereum, and Polygon)**

## 🚀 Quick Setup

```bash
# 1. Install dependencies
npm install

# 2. Start development server
npm run dev

# 3. Deploy to production
./deploy.sh
```

## 🔧 Environment Setup

1. Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
# Edit .env with your values
```

2. Key services you'll need:
   - Supabase account (for database)
   - Regfyl (for KYC verification)
   - Cashramp, Paystack, & Flutterwave (for African payments)
   - Binance & Coin Gecko (for market data)

## 🎯 What Works Right Now

- ✅ **Authentication** - Full login/signup flow with Supabase
- ✅ **KYC Verification** - Regfyl integration for identity verification
- ✅ **One-Click Wallet Creation** - Algorand + Bitcoin + Ethereum + Ploygon compatible addresses
- ✅ **Local Payment Channel Integration** - Pan-African payment processing
- ✅ **Cross-Border Payments** - 10+ African countries supported

## 🚀 Enterprise Features

- **Tight FX Spreads** - Low volatility and improved access to FX
- **Cross-border Payments + Access to DeFi** - Fast settlements + Cost savings vs traditional banking
- **Multi-currency Support** - KES, USD, NGN, ZAR
- **Real-time Analytics** - Monitor assets performance in real-time
- **Mobile-first Design** - Optimized for African markets

## 💰 Revenue Model

- **2.9%** transaction fees
- **$3,500-15K/month** B2B infrastructure licensing
- **1-2% mgt. + 20% on upside** staking fees  
  

## 🌍 Target Markets

**Primary:** Nigeria   
**Secondary:** Kenya, South Africa, Ghana, Uganda

## 📊 Updated Tech Stack

- **Frontend:** React 18 + TypeScript + Tailwind
- **Backend:** Python FastAPI + SQLite/PostgreSQL
- **Blockchain:** Algorand + Bitcoin + Ethereum + Polygon
- **Payments:** Cashramp + Paystack + Flutterwave + M-Pesa integration
- **Deploy:** Vercel (frontend) + Render (backend)
- **Auth & Database:** Supabase
- **KYC:** Regfyl

## 📋 Deployment Guide

### Backend (Vercel)

```bash
# Deploy to Vercel
npm run deploy:vercel
```

### Frontend (Vercel)

```bash
# Build and deploy to Netlify
npm run deploy
```

### Backend (Self-hosted)

```bash
# 1. Install Python dependencies
pip install -r backend/requirements.txt

# 2. Start backend server
cd backend
python main.py
```

### 🔐 Security Notes

- Always store sensitive keys as environment variables
- Ensure proper authentication and authorization
- Enable KYC verification in production environments

### 📊 Monitoring

- Frontend errors tracked with Sentry
- Backend monitoring with custom metrics
- Financial transaction auditing with detailed logging

---

## 🧪 Testing with Flutterwave

For testing payments, use these Flutterwave test credentials:

- **Card Number:** 4187427415564246
- **CVV:** 828
- **Expiry Date:** 09/32
- **PIN:** 3310
- **OTP:** 12345

For full integration instructions, see [INTEGRATION_GUIDE.md](./docs/INTEGRATION_GUIDE.md).

## 🚨 Important Note 

Repo is actively being built and subject to CI/CD
