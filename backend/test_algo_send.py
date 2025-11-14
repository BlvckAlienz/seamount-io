# File: backend/test_algo_send.py
"""
🧪 ALGO SEND TEST - Self-Transfer Edition
Tests send_payment() with sender = recipient (safest test method)
"""

import asyncio
from decimal import Decimal
from algosdk import encoding

from backend.config import get_settings
from backend.services.database_service import DatabaseService
from backend.services.algorand_service import AlgorandService
from backend.services.oracle_service import OracleService
from backend.services.fee_calculator import FeeCalculatorService
from backend.services.multi_chain_wallet_service import MultiChainWalletService


async def test_algo_send():
    settings = get_settings()
    db = DatabaseService()
    algo = AlgorandService(settings)
    oracle = OracleService(db)
    fees = FeeCalculatorService(db)
    
    wallet_service = MultiChainWalletService(db, algo, fees, oracle)
    
    # Your actual user ID
    test_user_id = "72844868-7efc-406b-b12f-57c4ff0793aa"
    test_amount = Decimal("0.001")  # Small test amount
    
    # ✅ OPTION A: Use your own address as recipient (safest for testing)
    print("\n🔍 FETCHING YOUR WALLET ADDRESS...")
    wallet_check = db.supabase.table('user_wallets')\
        .select('algorand_address')\
        .eq('user_id', test_user_id)\
        .execute()
    
    if not wallet_check.data or len(wallet_check.data) == 0:
        print(f"❌ ERROR: No wallet found for user {test_user_id}")
        return
    
    sender_address = wallet_check.data[0]['algorand_address']
    test_recipient = sender_address  # ✅ SEND TO YOURSELF (account exists!)
    
    print(f"✅ Using your own address as recipient (self-transfer for testing)")
    print(f"   Sender: {sender_address}")
    print(f"   Recipient: {test_recipient}")
    
    # Validate addresses
    if not encoding.is_valid_address(sender_address):
        print(f"❌ ERROR: Sender address has invalid checksum!")
        return
    print(f"✅ Sender address checksum validated")
    
    if not encoding.is_valid_address(test_recipient):
        print(f"❌ ERROR: Recipient address has invalid checksum!")
        return
    print(f"✅ Recipient address checksum validated")
    
    print(f"\n📋 TEST PARAMETERS:")
    print(f"   User ID: {test_user_id}")
    print(f"   Amount: {test_amount} ALGO")
    print(f"   Type: Self-transfer (sender = recipient)")
    
    # Check balance
    print(f"\n💰 CHECKING BALANCE...")
    try:
        account_info = await algo.get_account_info(sender_address)
        if account_info:
            balance_microalgos = account_info.get('amount', 0)
            balance_algo = Decimal(balance_microalgos) / Decimal(1_000_000)
            print(f"✅ Current balance: {balance_algo} ALGO")
            
            # Need enough for amount + fee (0.001 ALGO standard fee)
            required = test_amount + Decimal("0.001")
            if balance_algo < required:
                print(f"❌ ERROR: Insufficient balance. Need {required} ALGO (amount + fee), have {balance_algo} ALGO")
                return
            
            print(f"✅ Sufficient balance for transaction")
        else:
            print(f"⚠️ WARNING: Could not fetch account info")
    except Exception as balance_err:
        print(f"⚠️ WARNING: Balance check failed: {balance_err}")
    
    # Attempt send
    print(f"\n🚀 INITIATING SELF-TRANSFER TRANSACTION...")
    try:
        result = await wallet_service.send_payment(
            user_id=test_user_id,
            recipient=test_recipient,
            asset="ALGO",
            amount=test_amount,
            memo="Self-transfer test"
        )
        
        if result['success']:
            print(f"\n✅ ✅ ✅ TRANSACTION SUCCESS! ✅ ✅ ✅")
            print(f"   Transaction ID: {result.get('transaction_id')}")
            print(f"   Amount: {result.get('amount')} ALGO")
            print(f"   Fee: ${result.get('fee')}")
            print(f"   View on AlgoExplorer: https://algoexplorer.io/tx/{result.get('transaction_id')}")
        else:
            print(f"\n❌ TRANSACTION FAILED")
            print(f"   Error: {result.get('message')}")
            print(f"   Details: {result.get('error')}")
            
    except Exception as e:
        print(f"\n❌ EXCEPTION DURING SEND:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_algo_send())