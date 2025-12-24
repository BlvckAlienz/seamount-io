#!/bin/bash
# File: run_all_quidax_tests.sh
# Master script to run all Quidax tests

echo "🚀 QUIDAX INTEGRATION TEST SUITE"
echo "================================="
echo ""

# Check if server is running
if ! curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "❌ Server not running! Please start:"
    echo "   cd backend && uvicorn api.main:app --reload"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Test 1: Python Integration Tests
echo "🧪 Running Python Integration Tests..."
python backend/tests/test_quidax_integration.py
PYTHON_RESULT=$?
echo ""

# Test 2: API Endpoint Tests
echo "🧪 Running API Endpoint Tests..."
./test_quidax_endpoints.sh
API_RESULT=$?
echo ""

# Test 3: Webhook Tests
echo "🧪 Running Webhook Tests..."
./test_quidax_webhook.sh
WEBHOOK_RESULT=$?
echo ""

# Summary
echo "================================="
echo "📊 FINAL SUMMARY"
echo "================================="

if [ $PYTHON_RESULT -eq 0 ]; then
    echo "✅ Python Tests: PASSED"
else
    echo "❌ Python Tests: FAILED"
fi

if [ $API_RESULT -eq 0 ]; then
    echo "✅ API Tests: PASSED"
else
    echo "❌ API Tests: FAILED"
fi

if [ $WEBHOOK_RESULT -eq 0 ]; then
    echo "✅ Webhook Tests: PASSED"
else
    echo "❌ Webhook Tests: FAILED"
fi

echo ""

if [ $PYTHON_RESULT -eq 0 ] && [ $API_RESULT -eq 0 ] && [ $WEBHOOK_RESULT -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED! Ready for production."
    exit 0
else
    echo "⚠️ SOME TESTS FAILED. Review logs above."
    exit 1
fi