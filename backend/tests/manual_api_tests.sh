# File: backend/tests/manual_api_tests.sh
#!/bin/bash

# Manual API tests for Seamount components
# Usage: ./manual_api_tests.sh

API_URL="http://localhost:8000"
TOKEN="your_auth_token_here"

echo "🧪 Seamount API Integration Tests"
echo "=================================="

# Test 1: On-Ramp - Initialize
echo -e "\n📥 Test 1: Initialize On-Ramp"
curl -X POST "$API_URL/onramp/initialize" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_fiat": 10000,
    "currency": "NGN",
    "crypto_asset": "USDT",
    "user_country": "NG"
  }' | jq

# Test 2: On-Ramp - Get Providers
echo -e "\n📋 Test 2: Get On-Ramp Providers"
curl -X GET "$API_URL/onramp/providers?currency=NGN&crypto=USDT" \
  -H "Authorization: Bearer $TOKEN" | jq

# Test 3: Wallet Connect - Generate Deposit Address
echo -e "\n💳 Test 3: Generate Deposit Address"
curl -X POST "$API_URL/wallet/deposit/address" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset": "USDT"
  }' | jq

# Test 4: Wallet Connect - Get Exchanges
echo -e "\n🏦 Test 4: Get Supported Exchanges"
curl -X GET "$API_URL/wallet/exchanges" \
  -H "Authorization: Bearer $TOKEN" | jq

# Test 5: Yield - Get Tiers
echo -e "\n📈 Test 5: Get Yield Tiers"
curl -X GET "$API_URL/yield/tiers" | jq

# Test 6: Yield - Stake Funds
echo -e "\n💰 Test 6: Stake Funds"
curl -X POST "$API_URL/yield/stake" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset": "USDT",
    "amount": 100.0,
    "tier": "stable"
  }' | jq

# Test 7: Off-Ramp - Get Limits
echo -e "\n💸 Test 7: Get Withdrawal Limits"
curl -X GET "$API_URL/offramp/limits/NG" \
  -H "Authorization: Bearer $TOKEN" | jq

echo -e "\n✅ All manual tests complete!"