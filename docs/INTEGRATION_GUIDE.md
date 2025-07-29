# Seamount.io Integration Guide

This guide provides step-by-step instructions for integrating all components of Seamount.io.

## 1. Frontend-Backend Integration

### Option A: Running Backend Locally

1. Start your Python backend:
   ```bash
   cd backend
   python main.py
   ```

2. In a new terminal, start the frontend with API connection:
   ```bash
   npm run dev
   ```

3. The frontend will automatically connect to the local backend at `http://localhost:8000`.

### Option B: Connecting to Deployed Backend

1. Deploy your Python backend to a service like Railway, Render, or DigitalOcean:
   ```bash
   # Deploy using Vercel
   npm run deploy:vercel
   ```

2. Get the deployed URL (e.g., `https://seamount-api.railway.app`)

3. Update your `src/config/api.ts` file:
   ```typescript
   // Replace this line
   const PRODUCTION_API_URL = 'https://your-vercel-deployment-url.vercel.app';
   
   // With your actual backend URL
   const PRODUCTION_API_URL = 'https://seamount-api.vercel.app';
   ```

4. Build and deploy your frontend:
   ```bash
   npm run build
   npm run deploy
   ```

## 2. Flutterwave Integration

### Configure Flutterwave Keys

1. Ensure your `.env` file contains your Flutterwave credentials:
   ```
   FLW_PUBLIC_KEY=FLWPUBK-bedaf2ecc2edf9b9e3d6f875617f2691-X
   FLW_SECRET_KEY=FLWSECK-88a8f01a1456a7ba5a4f3b4537bafea8-1979b71429avt-X
   FLW_ENCRYPTION_KEY=88a8f01a14567baf99be703d
   ```

2. Add these to your deployed environment:
   ```bash
   # Netlify
   netlify env:set FLW_PUBLIC_KEY FLWPUBK-bedaf2ecc2edf9b9e3d6f875617f2691-X
   netlify env:set FLW_SECRET_KEY FLWSECK-88a8f01a1456a7ba5a4f3b4537bafea8-1979b71429avt-X
   netlify env:set FLW_ENCRYPTION_KEY 88a8f01a14567baf99be703d
   ```

### Testing Flutterwave Payments

1. Use the frontend's payment flow to initiate a payment.

2. For testing, use Flutterwave's test cards:
   - Card Number: `4187427415564246`
   - CVV: `828`
   - Expiry Date: `09/32`
   - PIN: `3310`
   - OTP: `12345`

3. Monitor the payment in your [Flutterwave Dashboard](https://dashboard.flutterwave.com/transactions).

## 3. ComplyCube KYC Integration

### Configure ComplyCube

1. Ensure your `.env` file contains your ComplyCube API key:
   ```
   COMPLYCUBE_API_KEY=test_cXhMdHdROVpoY2ZzWk5adU06ODVlMWExY2ZlOTJmMTkzMmQwNDJjY2VmNWQxYTk2MjAzZDJjYjczMTczYWEwN2MxOWM1MTljMDY5NzYyZWY5ZQ==
   COMPLYCUBE_URL=https://api.complycube.com/v1
   ```

2. Add these to your deployed environment:
   ```bash
   # Netlify
   netlify env:set COMPLYCUBE_API_KEY test_cXhMdHdROVpoY2ZzWk5adU06ODVlMWExY2ZlOTJmMTkzMmQwNDJjY2VmNWQxYTk2MjAzZDJjYjczMTczYWEwN2MxOWM1MTljMDY5NzYyZWY5ZQ==
   netlify env:set COMPLYCUBE_URL https://api.complycube.com/v1
   ```

### Testing KYC Verification

1. Use the frontend to start KYC verification process.

2. For testing, use ComplyCube's test data:
   - ID Document: Use any sample passport or ID image
   - Selfie: Use any clear face photo
   - Address: Use any address document

## 4. Supabase Database Setup

1. Create the required tables in Supabase:
   ```sql
   -- Payment transactions
   CREATE TABLE public.payment_transactions (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     user_id UUID,
     provider TEXT NOT NULL,
     provider_id TEXT,
     reference TEXT,
     amount DECIMAL NOT NULL,
     fee DECIMAL DEFAULT 0,
     currency TEXT NOT NULL,
     status TEXT NOT NULL,
     sender_address TEXT,
     receiver_address TEXT,
     tx_id TEXT,
     payment_type TEXT NOT NULL,
     country_code TEXT,
     exchange_rate DECIMAL,
     metadata JSONB,
     created_at TIMESTAMPTZ DEFAULT NOW(),
     updated_at TIMESTAMPTZ DEFAULT NOW()
   );

   -- User wallets
   CREATE TABLE public.user_wallets (
     user_id UUID PRIMARY KEY,
     address TEXT UNIQUE NOT NULL,
     created_at TIMESTAMPTZ DEFAULT NOW(),
     updated_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```

2. Enable Row Level Security (RLS) and set up policies.

## 5. Algorand USDS Integration

1. Configure your Algorand connection in the backend:
   ```python
   # backend/config.py
   ALGORAND_NODE_URL = "https://mainnet-api.4160.nodely.io"
   ALGORAND_INDEXER_URL = "https://mainnet-idx.4160.nodely.io"
   ALGORAND_NODE_TOKEN = "98D9CE80660AD243893D56D9F125CD2D"
   USDS_ASSET_ID = 3093700691
   ```

2. Create the minting function in your backend:
   ```python
   # backend/usds.py
   from algosdk.v2client import algod
   from algosdk import account, mnemonic, transaction

   # Initialize Algorand client
   algod_client = algod.AlgodClient(
       ALGORAND_NODE_TOKEN,
       ALGORAND_NODE_URL
   )

   def mint_usds(recipient_address, amount):
       # Implementation details here
       # ...
   ```

## 6. End-to-End Testing

1. Test wallet creation:
   - Register a user
   - Create an Algorand wallet

2. Test Flutterwave payment flow:
   - Initiate payment
   - Complete with test card
   - Verify USDS minting

3. Test cross-border transfer:
   - Send USDS to another wallet
   - Verify transaction confirmation

4. Test KYC verification:
   - Start KYC process
   - Submit test documents
   - Verify KYC status update

## 7. Production Deployment Checklist

- [ ] Update all API URLs to production endpoints
- [ ] Configure all environment variables in deployment platforms
- [ ] Set up proper error monitoring with Sentry
- [ ] Configure webhooks in Flutterwave dashboard
- [ ] Enable proper SSL/TLS for all endpoints
- [ ] Set up database backups for Supabase
- [ ] Configure proper rate limiting for API endpoints
- [ ] Test all flows in production environment

## 8. Updating API Endpoints

If you need to update the backend URL after deployment:

1. Find your deployed backend URL (e.g., from Railway, Render, DigitalOcean)
2. Update the `PRODUCTION_API_URL` in `src/config/api.ts`
3. Rebuild and redeploy your frontend:
   ```bash
   npm run build
   npm run deploy
   ```

## 9. Monitoring and Troubleshooting

- Monitor Sentry for frontend errors
- Check backend logs for API errors
- Review Supabase logs for database issues
- Monitor Flutterwave dashboard for payment issues

For detailed logs in development mode, open your browser's console and look for API requests and responses.