# ComplyCube KYC Integration for Seamount.io

## Overview

This document outlines how ComplyCube KYC verification is integrated into the Seamount.io Cross-Border Payment Platform. ComplyCube provides an API for document verification and identity checks that help Seamount comply with KYC (Know Your Customer) regulations across African markets.

## Implementation

### Architecture

The integration consists of three main components:

1. **KYCManager** - A class within the `usds_asset_manager.py` file that handles the low-level API interactions with ComplyCube.
2. **UserVerificationManager** - A higher-level service in `user_verification.py` that orchestrates the verification workflow.
3. **KYC API Routes** - FastAPI endpoints in `routes/kyc_routes.py` that provide the HTTP interface for the frontend.

### Data Flow

1. User initiates verification from the frontend
2. API endpoint creates a verification session with ComplyCube
3. User uploads identification documents (ID card/passport and selfie)
4. Documents are submitted to ComplyCube for verification
5. Results are polled asynchronously
6. User's verification status is updated in the database

## Configuration

The integration requires the following environment variables:

```
COMPLYCUBE_API_KEY=your_api_key
COMPLYCUBE_URL=https://api.complycube.com/v1
KYC_REDIRECT_URL=https://seamount.io/verify/complete
```

## API Endpoints

### Start Verification

```
POST /api/v1/kyc/start-verification

Body:
- email: string (required)
- country_code: string (required)
- redirect_url: string (optional)

Response:
{
  "success": true,
  "session_id": "cc-flow-xxx",
  "flow_url": "https://verify.complycube.com/xxx"
}
```

### Submit Documents

```
POST /api/v1/kyc/verify-documents

Body (form-data):
- document_type: string (passport, id_card, drivers_license)
- id_document: file
- selfie: file

Response:
{
  "success": true,
  "check_id": "cc-check-xxx",
  "client_id": "cc-client-xxx",
  "status": "pending"
}
```

### Check Verification Status

```
GET /api/v1/kyc/verification-status

Response:
{
  "success": true,
  "verified": boolean,
  "level": number,
  "status": string,
  "updated": boolean
}
```

## KYC Levels

Seamount uses the following KYC levels:

- **Level 0**: Unverified
- **Level 1**: Email verification
- **Level 2**: Full identity verification (ID + selfie)
- **Level 3**: Enhanced verification (includes proof of address)

## Compliance Considerations

1. **Data Storage**: Only verification statuses and metadata are stored in our database. Document images are not retained after verification.

2. **Regulatory Coverage**: ComplyCube provides verification services compliant with regulations in:
   - Kenya (Central Bank of Kenya)
   - Nigeria (CBN)
   - South Africa (FICA)
   - Ghana (Bank of Ghana)
   - Uganda (Bank of Uganda)

3. **Rate Limits**: The free tier of ComplyCube allows 25 verifications per month. For production, we will need to upgrade to a paid plan.

## Error Handling

The integration includes comprehensive error handling:
- API connectivity issues
- Invalid documents
- Timeout handling
- Verification failures

## Implementation Notes

1. The integration is designed to work with the ComplyCube API v1.
2. We implement retries with exponential backoff for resilience.
3. Verification results are cached to reduce API calls.
4. The KYC status is checked before any financial transaction.

## Limitations

1. The free tier of ComplyCube is limited to 25 verifications per month.
2. Some document types may have lower accuracy rates in certain African countries.
3. Internet connectivity issues may affect verification times in remote areas.