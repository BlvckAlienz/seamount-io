# File: backend/tests/test_integration.py
"""
Comprehensive Integration Tests for Seamount Core Features
Tests A-B-C-D components end-to-end
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from backend.services.onramp_aggregator_service import OnRampAggregatorService
from backend.services.offramp_service import OfframpService
from backend.services.wallet_connect_service import WalletConnectService
from backend.services.yield_manager_service import YieldManagerService, YieldTier
from backend.services.database_service import DatabaseService
from backend.services.audit_service import AuditService
from backend.services.oracle_service import EnhancedOracleService
from backend.services.payment_providers.paystack import PaystackProvider
from backend.services.cashramp_service import CashrampService
from backend.config import settings

from algosdk.v2client import algod, indexer

# Test fixtures
@pytest.fixture
async def db_service():
    """Database service fixture"""
    return DatabaseService()

@pytest.fixture
async def audit_service(db_service):
    """Audit service fixture"""
    return AuditService(db_service)

@pytest.fixture
async def oracle_service(db_service):
    """Oracle service fixture"""
    return EnhancedOracleService(db_service)

@pytest.fixture
def test_user_id():
    """Test user ID"""
    return str(uuid4())

@pytest.fixture
def test_wallet_address():
    """Test Algorand wallet address"""
    # Use a valid Algorand address format for testing
    return "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

# ============================================================================
# COMPONENT A TESTS: ON-RAMP AGGREGATOR
# ============================================================================

@pytest.mark.asyncio
async def test_onramp_initialize(db_service, audit_service, test_user_id):
    """Test on-ramp initialization"""
    
    print("\n🧪 Testing Component A: On-Ramp Aggregator")
    
    service = OnRampAggregatorService(db_service, audit_service)
    
    # Test data
    request = {
        "user_id": test_user_id,
        "user_email": "test@seamount.io",
        "amount_fiat": 100.0,
        "currency": "NGN",
        "crypto_asset": "USDT",
        "user_wallet_address": "TESTADDRESS123",
        "user_country": "NG"
    }
    
    try:
        result = await service.initialize_onramp(**request)
        
        assert result["success"] == True
        assert "transaction_id" in result
        assert "checkout_url" in result
        assert result["currency"] == "NGN"
        assert result["crypto_asset"] == "USDT"
        assert float(result["seamount_fee"]) > 0
        
        print(f"✅ On-ramp initialized: {result['transaction_id']}")
        print(f"   Provider: {result['provider']}")
        print(f"   Fee: ${result['seamount_fee']}")
        print(f"   Checkout: {result['checkout_url'][:50]}...")
        
        return result
        
    except Exception as e:
        print(f"❌ On-ramp test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_onramp_get_providers(db_service, audit_service):
    """Test getting supported on-ramp providers"""
    
    print("\n🧪 Testing On-Ramp Provider List")
    
    service = OnRampAggregatorService(db_service, audit_service)
    
    try:
        providers = await service.get_supported_providers(currency="NGN", crypto="USDT")
        
        assert len(providers) > 0
        
        print(f"✅ Found {len(providers)} providers supporting NGN→USDT")
        for provider in providers[:3]:
            print(f"   - {provider['name']}: {provider['fee_estimate']} fee, {provider['settlement_time']}")
        
        return providers
        
    except Exception as e:
        print(f"❌ Provider list test failed: {e}")
        raise

# ============================================================================
# COMPONENT B TESTS: OFF-RAMP SERVICE
# ============================================================================

@pytest.mark.asyncio
async def test_offramp_withdrawal(db_service, audit_service, oracle_service, test_user_id):
    """Test off-ramp withdrawal initialization"""
    
    print("\n🧪 Testing Component B: Off-Ramp Service")
    
    # Setup services
    paystack = PaystackProvider(settings)
    cashramp = CashrampService(db_service)
    
    service = OfframpService(db_service, audit_service, paystack, cashramp, oracle_service)
    
    # Mock user balance (in production, this would be real)
    await _mock_user_balance(db_service, test_user_id, "USDT", 1000.0)
    
    # Test withdrawal
    recipient_details = {
        "country": "NG",
        "currency": "NGN",
        "payment_method": "bank_transfer",
        "account_name": "Test User",
        "account_number": "0123456789",
        "bank_code": "058"  # GTBank
    }
    
    try:
        result = await service.initialize_withdrawal(
            user_id=test_user_id,
            crypto_asset="USDT",
            crypto_amount=50.0,
            recipient_details=recipient_details
        )
        
        assert result["success"] == True
        assert "transaction_id" in result
        assert result["status"] == "processing"
        assert float(result["seamount_fee"]) > 0
        
        print(f"✅ Off-ramp initialized: {result['transaction_id']}")
        print(f"   Amount: {result['crypto_amount']} USDT → {result['fiat_amount']} {result['fiat_currency']}")
        print(f"   Fee: ${result['seamount_fee']}")
        print(f"   Provider: {result['provider']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Off-ramp test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_offramp_get_limits(db_service, audit_service, oracle_service):
    """Test getting withdrawal limits"""
    
    print("\n🧪 Testing Off-Ramp Limits")
    
    paystack = PaystackProvider(settings)
    cashramp = CashrampService(db_service)
    
    service = OfframpService(db_service, audit_service, paystack, cashramp, oracle_service)
    
    try:
        limits = await service.get_withdrawal_limits("NG")
        
        assert "bank_transfer" in limits
        
        print(f"✅ Withdrawal limits for Nigeria:")
        for method, config in limits.items():
            print(f"   {method}: {config['min']}-{config['max']} {config['currency']}")
        
        return limits
        
    except Exception as e:
        print(f"❌ Limits test failed: {e}")
        raise

# ============================================================================
# COMPONENT C TESTS: WALLET CONNECT
# ============================================================================

@pytest.mark.asyncio
async def test_wallet_generate_deposit_address(db_service, audit_service, test_user_id, test_wallet_address):
    """Test deposit address generation"""
    
    print("\n🧪 Testing Component C: Wallet Connect")
    
    # Mock user wallet
    await _mock_user_wallet(db_service, test_user_id, test_wallet_address)
    
    algod_client = algod.AlgodClient("", settings.ALGORAND_NODE_URL)
    indexer_client = indexer.IndexerClient("", settings.ALGORAND_INDEXER_URL)
    
    service = WalletConnectService(db_service, audit_service, algod_client, indexer_client)
    
    try:
        result = await service.generate_deposit_address(
            user_id=test_user_id,
            asset="USDT"
        )
        
        assert result["success"] == True
        assert "deposit_id" in result
        assert result["address"] == test_wallet_address
        assert result["asset"] == "USDT"
        assert result["network"] == "Algorand"
        
        print(f"✅ Deposit address generated: {result['deposit_id']}")
        print(f"   Address: {result['address']}")
        print(f"   Asset: {result['asset']}")
        print(f"   Instructions: {len(result['instructions'])} steps")
        
        return result
        
    except Exception as e:
        print(f"❌ Deposit address test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_wallet_get_exchanges(db_service, audit_service):
    """Test getting supported exchanges"""
    
    print("\n🧪 Testing Supported Exchanges")
    
    algod_client = algod.AlgodClient("", settings.ALGORAND_NODE_URL)
    indexer_client = indexer.IndexerClient("", settings.ALGORAND_INDEXER_URL)
    
    service = WalletConnectService(db_service, audit_service, algod_client, indexer_client)
    
    try:
        exchanges = await service.get_supported_exchanges()
        
        assert len(exchanges) > 0
        
        print(f"✅ Found {len(exchanges)} supported exchanges")
        for exchange in exchanges[:5]:
            print(f"   - {exchange['name']}: {', '.join(exchange['supported_assets'])}")
        
        return exchanges
        
    except Exception as e:
        print(f"❌ Exchanges test failed: {e}")
        raise

# ============================================================================
# COMPONENT D TESTS: YIELD MANAGER
# ============================================================================

@pytest.mark.asyncio
async def test_yield_stake_creation(db_service, audit_service, oracle_service, test_user_id):
    """Test yield stake creation"""
    
    print("\n🧪 Testing Component D: Yield Manager")
    
    service = YieldManagerService(db_service, audit_service, oracle_service)
    
    # Mock user balance
    await _mock_user_balance(db_service, test_user_id, "USDT", 1000.0)
    
    try:
        result = await service.stake_funds(
            user_id=test_user_id,
            asset="USDT",
            amount=100.0,
            tier=YieldTier.STABLE
        )
        
        assert result["success"] == True
        assert "stake_id" in result
        assert result["tier"] == "stable"
        assert result["amount_staked"] == 100.0
        assert "7.5%" in result["target_apy"]
        
        print(f"✅ Yield stake created: {result['stake_id']}")
        print(f"   Tier: {result['tier']}")
        print(f"   Amount: {result['amount_staked']} {result['asset']}")
        print(f"   Target APY: {result['target_apy']}")
        print(f"   Expected annual yield: ${result['expected_annual_yield']:.2f}")
        print(f"   Strategies: {len(result['strategies'])}")
        
        return result
        
    except Exception as e:
        print(f"❌ Stake creation test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_yield_calculate(db_service, audit_service, oracle_service, test_user_id):
    """Test yield calculation"""
    
    print("\n🧪 Testing Yield Calculation")
    
    service = YieldManagerService(db_service, audit_service, oracle_service)
    
    # Create stake first
    await _mock_user_balance(db_service, test_user_id, "USDT", 1000.0)
    
    stake_result = await service.stake_funds(
        user_id=test_user_id,
        asset="USDT",
        amount=100.0,
        tier=YieldTier.GROWTH
    )
    
    stake_id = stake_result["stake_id"]
    
    # Wait a bit to accrue some yield (simulate)
    await asyncio.sleep(1)
    
    try:
        result = await service.calculate_current_yield(stake_id)
        
        assert "current_value" in result
        assert "net_yield" in result
        assert "current_apy" in result
        
        print(f"✅ Yield calculated for stake: {stake_id}")
        print(f"   Principal: ${result['principal']}")
        print(f"   Current value: ${result['current_value']}")
        print(f"   Net yield: ${result['net_yield']}")
        print(f"   Current APY: {result['current_apy']}")
        print(f"   Management fee: ${result['fees']['management_fee']}")
        print(f"   Performance fee: ${result['fees']['performance_fee']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Yield calculation test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_yield_get_tiers(db_service, audit_service, oracle_service):
    """Test getting tier information"""
    
    print("\n🧪 Testing Tier Information")
    
    service = YieldManagerService(db_service, audit_service, oracle_service)
    
    try:
        tiers = await service.get_tier_info()
        
        assert len(tiers) == 3  # Stable, Growth, Alpha
        
        print(f"✅ Retrieved {len(tiers)} yield tiers:")
        for tier in tiers:
            print(f"   {tier['tier'].upper()}: {tier['target_apy']} APY ({tier['risk_level']} risk)")
            print(f"      {len(tier['strategies'])} strategies, rebalances {tier['rebalance_frequency']}")
        
        return tiers
        
    except Exception as e:
        print(f"❌ Tier info test failed: {e}")
        raise

# ============================================================================
# END-TO-END INTEGRATION TEST
# ============================================================================

@pytest.mark.asyncio
async def test_complete_user_journey(db_service, audit_service, oracle_service):
    """Test complete user journey: deposit → stake → earn → withdraw"""
    
    print("\n" + "="*80)
    print("🚀 COMPLETE USER JOURNEY TEST")
    print("="*80)
    
    test_user_id = str(uuid4())
    test_wallet = "TESTWALLETADDRESS123456789012345678901234567890123456"
    
    # Mock user wallet
    await _mock_user_wallet(db_service, test_user_id, test_wallet)
    
    try:
        # STEP 1: On-Ramp (Deposit fiat)
        print("\n📥 STEP 1: On-Ramp (NGN → USDT)")
        onramp_service = OnRampAggregatorService(db_service, audit_service)
        
        onramp_result = await onramp_service.initialize_onramp(
            user_id=test_user_id,
            user_email="journey@seamount.io",
            amount_fiat=50000,  # 50K NGN
            currency="NGN",
            crypto_asset="USDT",
            user_wallet_address=test_wallet,
            user_country="NG"
        )
        
        print(f"   ✅ On-ramp: {onramp_result['transaction_id']}")
        print(f"   💰 Net USDT: {onramp_result['net_amount']}")
        
        # Simulate deposit completion - credit balance
        net_usdt = Decimal(str(onramp_result['net_amount']))
        await _mock_user_balance(db_service, test_user_id, "USDT", float(net_usdt))
        
        # STEP 2: Stake for yield
        print("\n📈 STEP 2: Stake USDT for 9% APY (Growth Tier)")
        yield_service = YieldManagerService(db_service, audit_service, oracle_service)
        
        stake_result = await yield_service.stake_funds(
            user_id=test_user_id,
            asset="USDT",
            amount=float(net_usdt * Decimal("0.8")),  # Stake 80%
            tier=YieldTier.GROWTH
        )
        
        print(f"   ✅ Staked: {stake_result['stake_id']}")
        print(f"   💵 Amount: {stake_result['amount_staked']} USDT")
        print(f"   📊 Expected annual: ${stake_result['expected_annual_yield']:.2f}")
        
        # STEP 3: Wait and check yield (simulate)
        print("\n⏳ STEP 3: Checking yield after staking...")
        await asyncio.sleep(1)
        
        yield_calc = await yield_service.calculate_current_yield(stake_result['stake_id'])
        
        print(f"   ✅ Current value: ${yield_calc['current_value']}")
        print(f"   💸 Net yield: ${yield_calc['net_yield']}")
        print(f"   📈 Current APY: {yield_calc['current_apy']}")
        
        # STEP 4: Partial unstake
        print("\n💳 STEP 4: Partial unstake (50%)")
        
        unstake_amount = float(Decimal(str(stake_result['amount_staked'])) * Decimal("0.5"))
        
        unstake_result = await yield_service.unstake_funds(
            user_id=test_user_id,
            stake_id=stake_result['stake_id'],
            partial_amount=unstake_amount
        )
        
        print(f"   ✅ Unstaked: ${unstake_result['unstaked_amount']}")
        print(f"   💰 Yield earned: ${unstake_result['total_yield_earned']:.4f}")
        print(f"   💼 Remaining staked: ${unstake_result['remaining_staked']}")
        
        # STEP 5: Off-ramp (Withdraw to bank)
        print("\n💸 STEP 5: Off-Ramp (USDT → NGN Bank)")
        
        paystack = PaystackProvider(settings)
        cashramp = CashrampService(db_service)
        offramp_service = OfframpService(db_service, audit_service, paystack, cashramp, oracle_service)
        
        # Mock balance update
        current_balance = float(net_usdt * Decimal("0.2")) + unstake_result['unstaked_amount']
        await _update_user_balance(db_service, test_user_id, "USDT", current_balance)
        
        withdrawal_amount = 10.0  # Withdraw 10 USDT
        
        offramp_result = await offramp_service.initialize_withdrawal(
            user_id=test_user_id,
            crypto_asset="USDT",
            crypto_amount=withdrawal_amount,
            recipient_details={
                "country": "NG",
                "currency": "NGN",
                "payment_method": "bank_transfer",
                "account_name": "Journey Test",
                "account_number": "0123456789",
                "bank_code": "058"
            }
        )
        
        print(f"   ✅ Withdrawal: {offramp_result['transaction_id']}")
        print(f"   💵 Fiat amount: {offramp_result['fiat_amount']} {offramp_result['fiat_currency']}")
        print(f"   💸 Fee: ${offramp_result['seamount_fee']}")
        
        # SUMMARY
        print("\n" + "="*80)
        print("🎉 USER JOURNEY COMPLETE!")
        print("="*80)
        print(f"   Initial deposit: 50,000 NGN")
        print(f"   Net USDT received: {onramp_result['net_amount']}")
        print(f"   Staked for yield: {stake_result['amount_staked']} USDT")
        print(f"   Yield earned: ${unstake_result['total_yield_earned']:.4f}")
        print(f"   Withdrawn to bank: {offramp_result['fiat_amount']} NGN")
        print(f"   Platform revenue: ${float(onramp_result['seamount_fee']) + float(offramp_result['seamount_fee']) + unstake_result['fees_paid']:.2f}")
        print("="*80)
        
        return {
            "success": True,
            "onramp": onramp_result,
            "stake": stake_result,
            "yield": yield_calc,
            "unstake": unstake_result,
            "offramp": offramp_result
        }
        
    except Exception as e:
        print(f"\n❌ USER JOURNEY FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _mock_user_wallet(db_service: DatabaseService, user_id: str, wallet_address: str):
    """Create mock user wallet"""
    query = """
        INSERT INTO user_wallets (user_id, algorand_address, created_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE SET algorand_address = %s
    """
    await db_service.execute_query(query, (user_id, wallet_address, wallet_address))

async def _mock_user_balance(db_service: DatabaseService, user_id: str, asset: str, amount: float):
    """Create/update mock user balance"""
    query = f"""
        INSERT INTO wallet_balances (user_id, {asset.lower()}_balance, created_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE SET {asset.lower()}_balance = %s
    """
    await db_service.execute_query(query, (user_id, amount, amount))

async def _update_user_balance(db_service: DatabaseService, user_id: str, asset: str, amount: float):
    """Update user balance"""
    query = f"""
        UPDATE wallet_balances 
        SET {asset.lower()}_balance = %s
        WHERE user_id = %s
    """
    await db_service.execute_query(query, (amount, user_id))

# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 SEAMOUNT INTEGRATION TEST SUITE")
    print("="*80)
    
    # Run pytest
    pytest.main([__file__, "-v", "-s"])