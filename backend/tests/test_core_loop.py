"""
Core Loop Test Script for Seamount.io
Tests: Register → KYC → Wallet → USDS Mint → Transfer → Off-ramp
File Location: backend/tests/test_core_loop.py
"""

import asyncio
import pytest
from decimal import Decimal
from datetime import datetime
import logging
from unittest.mock import AsyncMock, MagicMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockServices:
    """Mock services for testing"""
    
    def __init__(self):
        self.users = {}
        self.wallets = {}
        self.balances = {}
        self.treasury = {
            'usds_circulation': Decimal('0'),
            'fiat_reserves': Decimal('100000'),
            'reserve_ratio': Decimal('1.0')
        }
        self.transactions = []
    
    async def register_user(self, user_data):
        """Mock user registration"""
        user_id = user_data['user_id']
        wallet_address = f"ALGO_{user_id}_WALLET"
        
        self.users[user_id] = {
            **user_data,
            'kyc_status': 'pending',
            'wallet_address': wallet_address,
            'created_at': datetime.now()
        }
        
        self.wallets[wallet_address] = {
            'user_id': user_id,
            'balance': Decimal('0'),
            'created_at': datetime.now()
        }
        
        return {
            'success': True,
            'user_id': user_id,
            'wallet_address': wallet_address,
            'kyc_status': 'pending'
        }
    
    async def complete_kyc(self, user_id):
        """Mock KYC completion"""
        if user_id not in self.users:
            return {'success': False, 'error': 'User not found'}
        
        self.users[user_id]['kyc_status'] = 'approved'
        self.users[user_id]['kyc_completed_at'] = datetime.now()
        
        return {
            'success': True,
            'user_id': user_id,
            'status': 'approved'
        }
    
    async def process_fiat_deposit(self, user_id, amount, payment_method):
        """Mock fiat deposit and USDS minting"""
        if user_id not in self.users:
            return {'success': False, 'error': 'User not found'}
        
        if self.users[user_id]['kyc_status'] != 'approved':
            return {'success': False, 'error': 'KYC not approved'}
        
        wallet_address = self.users[user_id]['wallet_address']
        
        # Mint USDS
        self.wallets[wallet_address]['balance'] += amount
        self.treasury['usds_circulation'] += amount
        
        # Record transaction
        self.transactions.append({
            'type': 'deposit',
            'user_id': user_id,
            'amount': amount,
            'payment_method': payment_method,
            'timestamp': datetime.now()
        })
        
        return {
            'success': True,
            'user_id': user_id,
            'amount': amount,
            'usds_minted': amount,
            'new_balance': self.wallets[wallet_address]['balance']
        }
    
    async def process_transfer(self, sender_id, recipient_id, amount):
        """Mock USDS transfer"""
        if sender_id not in self.users or recipient_id not in self.users:
            return {'success': False, 'error': 'User not found'}
        
        sender_wallet = self.users[sender_id]['wallet_address']
        recipient_wallet = self.users[recipient_id]['wallet_address']
        
        if self.wallets[sender_wallet]['balance'] < amount:
            return {'success': False, 'error': 'Insufficient balance'}
        
        # Transfer with minimal fee
        fee = Decimal('0.001')
        transfer_amount = amount - fee
        
        self.wallets[sender_wallet]['balance'] -= amount
        self.wallets[recipient_wallet]['balance'] += transfer_amount
        
        # Record transaction
        self.transactions.append({
            'type': 'transfer',
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'amount': amount,
            'fee': fee,
            'timestamp': datetime.now()
        })
        
        return {
            'success': True,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'amount_sent': amount,
            'amount_received': transfer_amount,
            'fee': fee
        }
    
    async def process_fiat_withdrawal(self, user_id, amount, withdrawal_method):
        """Mock fiat withdrawal and USDS burning"""
        if user_id not in self.users:
            return {'success': False, 'error': 'User not found'}
        
        wallet_address = self.users[user_id]['wallet_address']
        
        if self.wallets[wallet_address]['balance'] < amount:
            return {'success': False, 'error': 'Insufficient balance'}
        
        # Burn USDS
        self.wallets[wallet_address]['balance'] -= amount
        self.treasury['usds_circulation'] -= amount
        
        # Record transaction
        self.transactions.append({
            'type': 'withdrawal',
            'user_id': user_id,
            'amount': amount,
            'withdrawal_method': withdrawal_method,
            'timestamp': datetime.now()
        })
        
        return {
            'success': True,
            'user_id': user_id,
            'amount': amount,
            'usds_burned': amount,
            'new_balance': self.wallets[wallet_address]['balance']
        }
    
    def get_treasury_status(self):
        """Get treasury health status"""
        return {
            'usds_circulation': float(self.treasury['usds_circulation']),
            'fiat_reserves': float(self.treasury['fiat_reserves']),
            'reserve_ratio': float(self.treasury['reserve_ratio']),
            'health_status': 'healthy' if self.treasury['reserve_ratio'] >= 1.0 else 'warning'
        }

# Test fixtures
@pytest.fixture
def mock_services():
    """Provide mock services for testing"""
    return MockServices()

@pytest.fixture
def test_user_nigeria():
    """Test user from Nigeria"""
    return {
        'user_id': 'test_user_ng_001',
        'email': 'test.ng@seamount.io',
        'country': 'NG',
        'phone': '+2348123456789',
        'first_name': 'John',
        'last_name': 'Doe'
    }

@pytest.fixture
def test_user_ghana():
    """Test user from Ghana"""
    return {
        'user_id': 'test_user_gh_001',
        'email': 'test.gh@seamount.io',
        'country': 'GH',
        'phone': '+233201234567',
        'first_name': 'Jane',
        'last_name': 'Smith'
    }

# Core Loop Tests
@pytest.mark.asyncio
async def test_user_registration(mock_services, test_user_nigeria):
    """Test: User Registration → Wallet Creation"""
    logger.info("🔄 Testing user registration...")
    
    result = await mock_services.register_user(test_user_nigeria)
    
    assert result['success'] == True
    assert result['user_id'] == test_user_nigeria['user_id']
    assert result['wallet_address'].startswith('ALGO_')
    assert result['kyc_status'] == 'pending'
    
    # Verify user stored
    assert test_user_nigeria['user_id'] in mock_services.users
    assert mock_services.users[test_user_nigeria['user_id']]['kyc_status'] == 'pending'
    
    logger.info(f"✅ User registered: {result['wallet_address']}")

@pytest.mark.asyncio
async def test_kyc_completion(mock_services, test_user_nigeria):
    """Test: KYC Verification"""
    logger.info("🔄 Testing KYC completion...")
    
    # Register user first
    await mock_services.register_user(test_user_nigeria)
    
    # Complete KYC
    result = await mock_services.complete_kyc(test_user_nigeria['user_id'])
    
    assert result['success'] == True
    assert result['status'] == 'approved'
    
    # Verify KYC status updated
    assert mock_services.users[test_user_nigeria['user_id']]['kyc_status'] == 'approved'
    
    logger.info("✅ KYC completed successfully")

@pytest.mark.asyncio
async def test_fiat_deposit_usds_mint(mock_services, test_user_nigeria):
    """Test: Fiat Deposit → USDS Minting"""
    logger.info("🔄 Testing fiat deposit and USDS minting...")
    
    # Setup: Register user and complete KYC
    await mock_services.register_user(test_user_nigeria)
    await mock_services.complete_kyc(test_user_nigeria['user_id'])
    
    deposit_amount = Decimal('100.00')
    
    # Process deposit
    result = await mock_services.process_fiat_deposit(
        user_id=test_user_nigeria['user_id'],
        amount=deposit_amount,
        payment_method='bank_transfer_ng'
    )
    
    assert result['success'] == True
    assert result['amount'] == deposit_amount
    assert result['usds_minted'] == deposit_amount
    assert result['new_balance'] == deposit_amount
    
    # Verify treasury updated
    treasury_status = mock_services.get_treasury_status()
    assert treasury_status['usds_circulation'] == float(deposit_amount)
    
    logger.info(f"✅ Deposited ${deposit_amount}, minted {deposit_amount} USDS")

@pytest.mark.asyncio
async def test_cross_border_transfer(mock_services, test_user_nigeria, test_user_ghana):
    """Test: Cross-border USDS Transfer"""
    logger.info("🔄 Testing cross-border transfer...")
    
    # Setup: Register both users and complete KYC
    await mock_services.register_user(test_user_nigeria)
    await mock_services.complete_kyc(test_user_nigeria['user_id'])
    
    await mock_services.register_user(test_user_ghana)
    await mock_services.complete_kyc(test_user_ghana['user_id'])
    
    # Fund sender account
    await mock_services.process_fiat_deposit(
        user_id=test_user_nigeria['user_id'],
        amount=Decimal('100.00'),
        payment_method='bank_transfer_ng'
    )
    
    # Process transfer
    transfer_amount = Decimal('50.00')
    result = await mock_services.process_transfer(
        sender_id=test_user_nigeria['user_id'],
        recipient_id=test_user_ghana['user_id'],
        amount=transfer_amount
    )
    
    assert result['success'] == True
    assert result['amount_sent'] == transfer_amount
    assert result['fee'] == Decimal('0.001')
    
    # Verify balances
    sender_wallet = mock_services.users[test_user_nigeria['user_id']]['wallet_address']
    recipient_wallet = mock_services.users[test_user_ghana['user_id']]['wallet_address']
    
    assert mock_services.wallets[sender_wallet]['balance'] == Decimal('50.00')  # 100 - 50
    assert mock_services.wallets[recipient_wallet]['balance'] == Decimal('49.999')  # 50 - 0.001 fee
    
    logger.info(f"✅ Transferred {transfer_amount} USDS from NG to GH")

@pytest.mark.asyncio
async def test_fiat_withdrawal(mock_services, test_user_ghana):
    """Test: USDS → Fiat Off-ramp"""
    logger.info("🔄 Testing fiat withdrawal...")
    
    # Setup: Register user, complete KYC, and fund account
    await mock_services.register_user(test_user_ghana)
    await mock_services.complete_kyc(test_user_ghana['user_id'])
    
    await mock_services.process_fiat_deposit(
        user_id=test_user_ghana['user_id'],
        amount=Decimal('50.00'),
        payment_method='mobile_money_gh'
    )
    
    # Process withdrawal
    withdrawal_amount = Decimal('25.00')
    result = await mock_services.process_fiat_withdrawal(
        user_id=test_user_ghana['user_id'],
        amount=withdrawal_amount,
        withdrawal_method='mobile_money_gh'
    )
    
    assert result['success'] == True
    assert result['amount'] == withdrawal_amount
    assert result['usds_burned'] == withdrawal_amount
    assert result['new_balance'] == Decimal('25.00')  # 50 - 25
    
    # Verify treasury updated
    treasury_status = mock_services.get_treasury_status()
    assert treasury_status['usds_circulation'] == 25.00  # 50 - 25 burned
    
    logger.info(f"✅ Withdrew ${withdrawal_amount} to Ghana mobile money")

@pytest.mark.asyncio
async def test_treasury_health_monitoring(mock_services, test_user_nigeria):
    """Test: Treasury Health Monitoring"""
    logger.info("🔄 Testing treasury health monitoring...")
    
    # Setup: Register user, complete KYC, and process some transactions
    await mock_services.register_user(test_user_nigeria)
    await mock_services.complete_kyc(test_user_nigeria['user_id'])
    
    # Process deposit
    await mock_services.process_fiat_deposit(
        user_id=test_user_nigeria['user_id'],
        amount=Decimal('100.00'),
        payment_method='bank_transfer_ng'
    )
    
    # Check treasury health
    treasury_status = mock_services.get_treasury_status()
    
    assert treasury_status['health_status'] == 'healthy'
    assert treasury_status['reserve_ratio'] >= 1.0
    assert treasury_status['usds_circulation'] == 100.00
    assert treasury_status['fiat_reserves'] == 100000.00
    
    logger.info("✅ Treasury health monitoring confirmed")

@pytest.mark.asyncio
async def test_complete_user_journey(mock_services, test_user_nigeria, test_user_ghana):
    """Test: Complete User Journey End-to-End"""
    logger.info("🚀 Testing complete user journey...")
    
    # Step 1: Register Nigerian user
    ng_reg = await mock_services.register_user(test_user_nigeria)
    assert ng_reg['success'] == True
    
    # Step 2: Complete KYC
    ng_kyc = await mock_services.complete_kyc(test_user_nigeria['user_id'])
    assert ng_kyc['success'] == True
    
    # Step 3: Deposit fiat → Mint USDS
    ng_deposit = await mock_services.process_fiat_deposit(
        user_id=test_user_nigeria['user_id'],
        amount=Decimal('100.00'),
        payment_method='bank_transfer_ng'
    )
    assert ng_deposit['success'] == True
    
    # Step 4: Register Ghanaian user
    gh_reg = await mock_services.register_user(test_user_ghana)
    assert gh_reg['success'] == True
    
    await mock_services.complete_kyc(test_user_ghana['user_id'])
    
    # Step 5: Cross-border transfer
    transfer = await mock_services.process_transfer(
        sender_id=test_user_nigeria['user_id'],
        recipient_id=test_user_ghana['user_id'],
        amount=Decimal('50.00')
    )
    assert transfer['success'] == True
    
    # Step 6: Withdraw to fiat
    gh_withdrawal = await mock_services.process_fiat_withdrawal(
        user_id=test_user_ghana['user_id'],
        amount=Decimal('25.00'),
        withdrawal_method='mobile_money_gh'
    )
    assert gh_withdrawal['success'] == True
    
    # Step 7: Verify treasury health
    treasury_status = mock_services.get_treasury_status()
    assert treasury_status['health_status'] == 'healthy'
    
    # Final assertions
    expected_circulation = 100.00 - 25.00  # Minted - Burned
    assert abs(treasury_status['usds_circulation'] - expected_circulation) < 0.01
    
    logger.info("🎉 COMPLETE USER JOURNEY TEST PASSED!")
    
    return {
        'test_completed': True,
        'users_processed': 2,
        'total_minted': 100.00,
        'total_transferred': 50.00,
        'total_burned': 25.00,
        'final_circulation': treasury_status['usds_circulation'],
        'treasury_health': treasury_status['health_status']
    }

@pytest.mark.asyncio
async def test_error_handling(mock_services):
    """Test: Error Handling and Edge Cases"""
    logger.info("🔄 Testing error handling...")
    
    # Test 1: Deposit without KYC
    await mock_services.register_user({
        'user_id': 'no_kyc_user',
        'email': 'no.kyc@seamount.io',
        'country': 'NG',
        'phone': '+2348123456789',
        'first_name': 'No',
        'last_name': 'KYC'
    })
    
    result = await mock_services.process_fiat_deposit(
        user_id='no_kyc_user',
        amount=Decimal('100.00'),
        payment_method='bank_transfer_ng'
    )
    assert result['success'] == False
    assert 'KYC not approved' in result['error']
    
    # Test 2: Transfer with insufficient balance
    await mock_services.complete_kyc('no_kyc_user')
    
    result = await mock_services.process_transfer(
        sender_id='no_kyc_user',
        recipient_id='no_kyc_user',
        amount=Decimal('100.00')
    )
    assert result['success'] == False
    assert 'Insufficient balance' in result['error']
    
    # Test 3: Withdrawal with insufficient balance
    result = await mock_services.process_fiat_withdrawal(
        user_id='no_kyc_user',
        amount=Decimal('100.00'),
        withdrawal_method='bank_transfer_ng'
    )
    assert result['success'] == False
    assert 'Insufficient balance' in result['error']
    
    logger.info("✅ Error handling tests passed")

# Performance test
@pytest.mark.asyncio
async def test_concurrent_operations(mock_services):
    """Test: Concurrent User Operations"""
    logger.info("🔄 Testing concurrent operations...")
    
    async def process_user(user_id):
        """Process single user journey"""
        user_data = {
            'user_id': f'concurrent_user_{user_id}',
            'email': f'user_{user_id}@seamount.io',
            'country': 'NG',
            'phone': f'+234812345{user_id:04d}',
            'first_name': f'User',
            'last_name': f'{user_id}'
        }
        
        await mock_services.register_user(user_data)
        await mock_services.complete_kyc(user_data['user_id'])
        result = await mock_services.process_fiat_deposit(
            user_id=user_data['user_id'],
            amount=Decimal('10.00'),
            payment_method='bank_transfer_ng'
        )
        return result['success']
    
    # Test 10 concurrent users
    tasks = [process_user(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(results)
    assert success_count == 10
    
    # Verify treasury
    treasury_status = mock_services.get_treasury_status()
    assert treasury_status['usds_circulation'] == 100.00  # 10 users × $10
    
    logger.info(f"✅ Processed {success_count}/10 concurrent users successfully")

if __name__ == "__main__":
    # Run tests directly
    asyncio.run(pytest.main([__file__, "-v"]))