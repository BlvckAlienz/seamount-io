# Seamount.io Deployment Checklist

## Pre-Deployment Requirements
- [ ] Supabase project created and credentials added to `.env`
- [ ] ComplyCube API key obtained and added to `.env`
- [ ] Flutterwave account set up with test/live credentials
- [ ] M-Pesa credentials obtained (for Kenyan users)
- [ ] Vercel account for backend deployment
- [ ] Netlify account for frontend deployment

## Backend Deployment
- [ ] Run `node scripts/deploy-vercel.js` to deploy the backend
- [ ] Note the Vercel deployment URL for the backend
- [ ] Add the backend URL to environment variables:
  - `BACKEND_URL=your-vercel-deployment-url`
  - `VITE_BACKEND_URL=your-vercel-deployment-url`

## Supabase Database Setup
- [ ] Run migrations to set up database tables
- [ ] Configure authentication settings in Supabase dashboard:
  - Enable Email/Password sign-in
  - Set custom redirect URLs for email confirmation
  - Configure password requirements

## Frontend Deployment
- [ ] Update environment variables in Netlify dashboard
- [ ] Run `npm run build` to build the frontend
- [ ] Run `npm run deploy` to deploy to Netlify

## Post-Deployment Configuration
- [ ] Set up Flutterwave webhook URLs
- [ ] Configure ComplyCube webhook callbacks
- [ ] Test authentication flow
- [ ] Test KYC verification flow
- [ ] Test cross-border payment flow
- [ ] Test USDS transaction fees

## Production Security Checks
- [ ] Enable Supabase RLS (Row Level Security) for all tables
- [ ] Set up Sentry for error monitoring
- [ ] Configure proper CORS settings
- [ ] Set up rate limiting for API endpoints

## Monitoring Setup
- [ ] Set up uptime monitoring for backend
- [ ] Configure performance monitoring
- [ ] Set up alerts for payment failures
- [ ] Configure transaction monitoring for compliance

## Documentation
- [ ] Update API documentation with endpoints
- [ ] Document KYC verification process
- [ ] Document payment flows
- [ ] Create user guides for the platform

## Final Checklist
- [ ] Test end-to-end flow from signup to payment
- [ ] Verify all transaction fees are paid in USDS
- [ ] Check mobile responsiveness
- [ ] Verify cross-browser compatibility
- [ ] Test with real API keys in staging environment