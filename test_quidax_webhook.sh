#!/bin/bash
# File: test_quidax_webhook.sh
# Test Quidax webhook handling with proper database setup

BASE_URL="http://localhost:8000"

echo "🧪 Testing Quidax Webhook Handler"
echo "================================="
echo ""

# ✅ Load webhook secret from .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/../../.env" ]; then
    export $(grep QUIDAX_WEBHOOK_SECRET "${SCRIPT_DIR}/../../.env" | xargs)
elif [ -f "${SCRIPT_DIR}/../.env" ]; then
    export $(grep QUIDAX_WEBHOOK_SECRET "${SCRIPT_DIR}/../.env" | xargs)
fi

WEBHOOK_SECRET="${QUIDAX_WEBHOOK_SECRET:-test_secret_key}"
echo "🔑 Using webhook secret: ${WEBHOOK_SECRET:0:10}..."

# Generate timestamp
TIMESTAMP=$(date +%s)

# 📋 TEST SCENARIOS
echo ""
echo "Select test scenario:"
echo "1) Test with FAKE order_id (tests error handling)"
echo "2) Test with REAL order_id (requires setup)"
echo ""
read -p "Enter choice (1-2): " choice

case $choice in
    1)
        echo "📦 Testing with FAKE order_id..."
        ORDER_ID="order_test_$(date +%s)"
        PAYLOAD=$(cat <<EOF
{
  "event": "instant_order.done",
  "id": "evt_$(date +%s)",
  "data": {
    "id": "$ORDER_ID",
    "status": "done",
    "market": "usdtngn",
    "type": "buy",
    "price": "1650.50",
    "volume": "6.12",
    "total": "10100.00",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }
}
EOF
)
        echo "⚠️ Expected: Webhook should log 'No transaction found' and return 200"
        ;;
        
    2)
        echo "🔧 Testing with REAL order_id..."
        echo ""
        echo "First, run this SQL in Supabase to create test transaction:"
        echo ""
        echo "INSERT INTO onramp_transactions ("
        echo "    id, user_id, type, status, provider, provider_name, currency, crypto_asset,"
        echo "    amount_fiat, seamount_fee, net_to_user, wallet_address, checkout_url,"
        echo "    user_email, user_country, quidax_order_id, created_at"
        echo ") VALUES ("
        echo "    'onramp_test_' || EXTRACT(EPOCH FROM NOW())::TEXT,"
        echo "    (SELECT id FROM user_profiles LIMIT 1),"
        echo "    'buy', 'pending', 'quidax', 'Quidax', 'NGN', 'USDT',"
        echo "    10100.00, 100.00, 6.12,"
        echo "    'TQn8yKzXp7cBiKjGmP4wZ3aL5rN9vU1mXk',"
        echo "    'https://quidax.com/checkout/test',"
        echo "    'test@seamount.io', 'nigeria',"
        echo "    'qd_test_real_' || EXTRACT(EPOCH FROM NOW())::TEXT,"
        echo "    NOW()"
        echo ") RETURNING quidax_order_id;"
        echo ""
        read -p "Enter the quidax_order_id from SQL output: " ORDER_ID
        
        if [ -z "$ORDER_ID" ]; then
            echo "❌ No order_id provided"
            exit 1
        fi
        
        echo ""
        echo "✅ Using order_id: $ORDER_ID"
        echo ""
        
        PAYLOAD=$(cat <<EOF
{
  "event": "instant_order.done",
  "id": "evt_$(date +%s)",
  "data": {
    "id": "$ORDER_ID",
    "status": "done",
    "market": "usdtngn",
    "type": "buy",
    "price": "1650.50",
    "volume": "6.12",
    "total": "10100.00",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }
}
EOF
)
        echo "✅ Expected: Transaction should be updated to 'completed' status"
        ;;
        
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "📦 Payload:"
echo "$PAYLOAD" | python3 -m json.tool 2>/dev/null || echo "$PAYLOAD"
echo ""

# ✅ USE PRE-GENERATED SIGNATURE (hardcoded for Windows Git Bash compatibility)
# Generated from test_signature.py:
#   Timestamp: 1766602406
#   Signature: 3f958a74635d2b9026ce1462f78559ce43f18f6cdaf009b2638a11c4bbe97619

TIMESTAMP="1766602406"
SIGNATURE="3f958a74635d2b9026ce1462f78559ce43f18f6cdaf009b2638a11c4bbe97619"
SIGNATURE_HEADER="t=${TIMESTAMP},v1=${SIGNATURE}"

echo "🔐 Using hardcoded signature"
echo "🔐 Signature: $SIGNATURE_HEADER"

# Send webhook
echo "📤 Sending webhook to $BASE_URL/api/v1/webhooks/quidax..."
response=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "quidax-signature: $SIGNATURE_HEADER" \
    -d "$PAYLOAD" \
    "$BASE_URL/api/v1/webhooks/quidax")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

echo ""
if [ "$http_code" = "200" ]; then
    echo "✅ Webhook accepted (HTTP $http_code)"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
else
    echo "❌ Webhook failed (HTTP $http_code)"
    echo "$body"
fi

echo ""
echo "📊 Check server logs for processing details"