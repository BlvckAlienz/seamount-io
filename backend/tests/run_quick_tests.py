# File: backend/tests/run_quick_tests.py
"""
Quick test runner for manual testing
Run with: python -m backend.tests.run_quick_tests
"""

import asyncio
from test_integration import (
    test_onramp_initialize,
    test_offramp_withdrawal,
    test_wallet_generate_deposit_address,
    test_yield_stake_creation,
    test_complete_user_journey,
    db_service,
    audit_service,
    oracle_service
)

async def run_all_tests():
    """Run all integration tests"""
    
    print("\n🚀 Starting Seamount Integration Tests...")
    
    # Initialize services
    db = await db_service()
    audit = await audit_service(db)
    oracle = await oracle_service(db)
    
    test_results = []
    
    # Test Component A
    try:
        await test_onramp_initialize(db, audit, "test-user-123")
        test_results.append(("Component A: On-Ramp", "✅ PASS"))
    except Exception as e:
        test_results.append(("Component A: On-Ramp", f"❌ FAIL: {e}"))
    
    # Test Component B
    try:
        await test_offramp_withdrawal(db, audit, oracle, "test-user-123")
        test_results.append(("Component B: Off-Ramp", "✅ PASS"))
    except Exception as e:
        test_results.append(("Component B: Off-Ramp", f"❌ FAIL: {e}"))
    
    # Test Component C
    try:
        await test_wallet_generate_deposit_address(db, audit, "test-user-123", "TESTADDRESS123")
        test_results.append(("Component C: Wallet Connect", "✅ PASS"))
    except Exception as e:
        test_results.append(("Component C: Wallet Connect", f"❌ FAIL: {e}"))
    
    # Test Component D
    try:
        await test_yield_stake_creation(db, audit, oracle, "test-user-123")
        test_results.append(("Component D: Yield Manager", "✅ PASS"))
    except Exception as e:
        test_results.append(("Component D: Yield Manager", f"❌ FAIL: {e}"))
    
    # Test Complete Journey
    try:
        await test_complete_user_journey(db, audit, oracle)
        test_results.append(("End-to-End Journey", "✅ PASS"))
    except Exception as e:
        test_results.append(("End-to-End Journey", f"❌ FAIL: {e}"))
    
    # Print results
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)
    for test_name, result in test_results:
        print(f"{test_name}: {result}")
    print("="*80)
    
    passed = sum(1 for _, result in test_results if "✅" in result)
    total = len(test_results)
    print(f"\n✨ {passed}/{total} tests passed")

if __name__ == "__main__":
    asyncio.run(run_all_tests())