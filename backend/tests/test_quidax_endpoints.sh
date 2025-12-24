#!/bin/bash
# File: test_quidax_endpoints.sh
# Comprehensive Quidax API endpoint tests

BASE_URL="http://localhost:8000"
AUTH_TOKEN="YOUR_AUTH_TOKEN_HERE"  # Replace with actual token

echo "🧪 Quidax Integration Test Suite"
echo "================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Helper function to test endpoint
test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local auth_required=$5
    
    echo -e "${YELLOW}Testing: $name${NC}"
    
    if [ "$auth_required" = "true" ]; then
        if [ "$method" = "GET" ]; then
            response=$(curl -s -w "\n%{http_code}" \
                -H "Authorization: Bearer $AUTH_TOKEN" \
                "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "\n%{http_code}" \
                -X $method \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $AUTH_TOKEN" \
                -d "$data" \
                "$BASE_URL$endpoint")
        fi
    else
        if [ "$method" = "GET" ]; then
            response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "\n%{http_code}" \
                -X $method \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$BASE_URL$endpoint")
        fi
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✅ PASSED${NC} (HTTP $http_code)"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ FAILED${NC} (HTTP $http_code)"
        echo "$body"
        FAILED=$((FAILED + 1))
    fi
    echo ""
}

# ============================================================================
# TEST 1: Health Check
# ============================================================================
test_endpoint "Health Check" "GET" "/api/v1/health" "" "false"

# ============================================================================
# TEST 2: Get Markets (Public)
# ============================================================================
test_endpoint "Get Markets" "GET" "/api/v1/quidax/markets" "" "false"

# ============================================================================
# TEST 3: Get Ticker (Public)
# ============================================================================
test_endpoint "Get USDT/NGN Ticker" "GET" "/api/v1/quidax/ticker/usdtngn" "" "false"

# ============================================================================
# TEST 4: Get Quote (Requires Auth)
# ============================================================================
QUOTE_DATA='{
  "market": "usdtngn",
  "quote_type": "buy",
  "amount": 10000,
  "amount_type": "fiat"
}'
test_endpoint "Get Buy Quote (NGN 10,000)" "POST" "/api/v1/quidax/quote" "$QUOTE_DATA" "true"

# ============================================================================
# TEST 5: Get Sell Quote (Requires Auth)
# ============================================================================
SELL_QUOTE_DATA='{
  "market": "usdtngn",
  "quote_type": "sell",
  "amount": 10,
  "amount_type": "crypto"
}'
test_endpoint "Get Sell Quote (10 USDT)" "POST" "/api/v1/quidax/quote" "$SELL_QUOTE_DATA" "true"

# ============================================================================
# SUMMARY
# ============================================================================
echo "================================="
echo "📊 TEST SUMMARY"
echo "================================="
echo -e "${GREEN}✅ Passed: $PASSED${NC}"
echo -e "${RED}❌ Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED!"
    exit 0
else
    echo "⚠️ SOME TESTS FAILED!"
    exit 1
fi