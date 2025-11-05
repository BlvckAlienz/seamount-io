#!/bin/bash

API_URL="https://seamount-api.onrender.com/api/v1"
BEARER_TOKEN="I6hCDIA5CkpdCKEsrQdqflpzckUoDKBkJ446zY88+2lPeGozVPYHT+1nikdAjD2Twmu3S2PrhJNbDtQqPRvh6Q=="
API_KEY="smnt_test_-GKRaXHivxucWFE-m_Tz4MQLMT_IxKQ1VcXxD1gOcxw"

echo "=== 🚀 Seamount API Smoke Test Suite ==="
echo "API URL: $API_URL"
echo "----------------------------------------"

# Health check
echo "[1] Health check..."
curl -s -X GET "https://seamount-api.onrender.com/" | jq .

# Investor contact
echo "[2] Investor contact..."
curl -s -X POST "$API_URL/investor-contact" \
-H "Content-Type: application/json" \
-d '{"name":"John Doe","email":"john@example.com","company":"TestCorp","checkSize":"$50k-$100k","message":"Interested"}' | jq .

# User profile
echo "[3] User profile..."
curl -s -X GET "$API_URL/user/profile" \
-H "Authorization: Bearer $BEARER_TOKEN" | jq .

# Provision wallets
echo "[4] Provision wallets..."
curl -s -X POST "$API_URL/user/provision-wallets" \
-H "Authorization: Bearer $BEARER_TOKEN" | jq .

# Wallet balance
echo "[5] Wallet balance..."
curl -s -X GET "$API_URL/wallet/balance" \
-H "Authorization: Bearer $BEARER_TOKEN" | jq .

# P2P payment
echo "[6] P2P payment..."
curl -s -X POST "$API_URL/payments/p2p" \
-H "Authorization: Bearer $BEARER_TOKEN" \
-H "Content-Type: application/json" \
-d '{"recipient_address":"ALGO456","amount":100,"memo":"Test"}' | jq .

# Initialize deposit
echo "[7] Initialize deposit..."
curl -s -X POST "$API_URL/payments/initialize-deposit" \
-H "Authorization: Bearer $BEARER_TOKEN" \
-H "Content-Type: application/json" \
-d '{"amount":100,"currency":"USD"}' | jq .

# Market price
echo "[8] Market price..."
curl -s -X GET "$API_URL/market/price/USDS/USD" \
-H "Authorization: Bearer $BEARER_TOKEN" | jq .

# Whitelabel quote
echo "[9] Whitelabel quote..."
curl -s -X POST "$API_URL/whitelabel/quote" \
-H "Authorization: Bearer $API_KEY" \
-H "Content-Type: application/json" \
-d '{"from_currency":"USD","to_currency":"KES","amount":100}' | jq .

# marketData summary
echo "[10] marketData summary..."
curl -s -X GET "$API_URL/marketData/summary" \
-H "Authorization: Bearer $BEARER_TOKEN" | jq .

# Compliance alerts
echo "[11] Compliance alerts..."
curl -s -X GET "$API_URL/compliance/alerts?status=pending" \
-H "Authorization: Bearer $BEARER_TOKEN" | jq .

# Compliance dashboard
echo "[12] Compliance dashboard..."
curl -s -X GET "$API_URL/compliance/dashboard" \
-H "Authorization: Bearer $BEARER_TOKEN" | jq .

# Cookie consent
echo "[13] Cookie consent..."
curl -s -X POST "$API_URL/consent/cookies" \
-H "Content-Type: application/json" \
-d '{"preferences":{"analytics":true,"marketing":false}}' | jq .

echo "=== ✅ Smoke Test Completed ==="
