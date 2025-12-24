#!/bin/bash
# File: test_quidax_webhook.sh
# Test Quidax webhook handling

BASE_URL="http://localhost:8000"

echo "🧪 Testing Quidax Webhook Handler"
echo "================================="
echo ""

# Generate test signature
WEBHOOK_SECRET="test_secret_key"
TIMESTAMP=$(date +%s)
PAYLOAD='{"event":"instant_order.done","data":{"id":"order_test_123","status":"done","market":"usdtngn","type":"buy","price":"1650.50","total":"10100.00"}}'

# Calculate HMAC signature
SIGNED_PAYLOAD="${TIMESTAMP}.${PAYLOAD}"
SIGNATURE=$(echo -n "$SIGNED_PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')
SIGNATURE_HEADER="t=${TIMESTAMP},v1=${SIGNATURE}"

echo "📦 Test Payload:"
echo "$PAYLOAD" | jq '.'
echo ""

echo "🔐 Signature Header:"
echo "$SIGNATURE_HEADER"
echo ""

# Test webhook endpoint
echo "📤 Sending webhook..."
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "quidax-signature: $SIGNATURE_HEADER" \
    -d "$PAYLOAD" \
    "$BASE_URL/api/v1/webhooks/quidax")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo "✅ Webhook processed successfully (HTTP $http_code)"
    echo "$body" | jq '.'
else
    echo "❌ Webhook processing failed (HTTP $http_code)"
    echo "$body"
fi