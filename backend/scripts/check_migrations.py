"""
Check Supabase database migration status - SIMPLIFIED VERSION
"""

import os
import sys
from supabase import create_client
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def check_tables():
    """Check which tables exist using direct SQL query via Supabase API"""
    
    try:
        # Initialize Supabase
        supabase = create_client(
            os.getenv("SUPABASE_URL", "https://opqnoficlhbylxfpaehp.supabase.co"),
            os.getenv("SUPABASE_SERVICE_KEY")
        )
        
        # List of tables we expect to exist
        expected_tables = [
            'users',
            'user_wallets',
            'multi_chain_addresses',
            'transactions',
            'custodian_integrations',
            'tokenized_assets',
            'asset_offers',
            'repo_trades',
            'collateral_positions',
            'settlement_transactions',
            'platform_fees'
        ]
        
        print("\n📊 CHECKING TABLES:")
        print("-" * 60)
        
        existing_tables = []
        
        for table_name in expected_tables:
            try:
                # Try to query the table (limit 0 = metadata only)
                result = supabase.table(table_name).select('*').limit(0).execute()
                
                # If no error, table exists
                existing_tables.append(table_name)
                print(f"  ✅ {table_name:<40} EXISTS")
                
            except Exception as table_err:
                # Table doesn't exist or no permissions
                if '42P01' in str(table_err):  # PostgreSQL "relation does not exist"
                    print(f"  ❌ {table_name:<40} MISSING")
                elif 'permission denied' in str(table_err).lower():
                    print(f"  ⚠️  {table_name:<40} NO PERMISSIONS")
                else:
                    print(f"  ❓ {table_name:<40} UNKNOWN ({str(table_err)[:30]}...)")
        
        # Tokenization tables check
        print("\n🔍 TOKENIZATION SCHEMA STATUS:")
        print("-" * 60)
        
        tokenization_tables = [
            'custodian_integrations',
            'tokenized_assets',
            'asset_offers',
            'repo_trades',
            'collateral_positions',
            'settlement_transactions',
            'platform_fees'
        ]
        
        missing_tokenization_tables = [t for t in tokenization_tables if t not in existing_tables]
        
        if missing_tokenization_tables:
            print(f"  ❌ MISSING {len(missing_tokenization_tables)} tables:")
            for table in missing_tokenization_tables:
                print(f"     - {table}")
            print("\n  📝 ACTION: Run tokenization schema migration in Supabase SQL Editor")
        else:
            print("  ✅ All tokenization tables exist")
        
        # Revenue tracking check
        if 'platform_fees' in existing_tables:
            try:
                fee_count = supabase.table('platform_fees').select('id', count='exact').execute()
                print(f"\n💰 REVENUE TRACKING:")
                print(f"     Status: ACTIVE")
                print(f"     Fees Recorded: {fee_count.count}")
            except:
                print(f"\n💰 REVENUE TRACKING:")
                print(f"     Status: TABLE EXISTS (permissions issue)")
        else:
            print(f"\n💰 REVENUE TRACKING:")
            print(f"     Status: NOT DEPLOYED")
            print(f"     Action: Deploy migrations/005_revenue_tracking.sql")
        
        return existing_tables
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return []

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  SEAMOUNT DATABASE MIGRATION STATUS")
    print("="*60)
    
    tables = check_tables()
    
    print(f"\n📈 Summary:")
    print(f"   Tables Found: {len(tables)}")
    print(f"   Core Tables: {'✅ OK' if len(tables) >= 4 else '❌ INCOMPLETE'}")
    print(f"   Tokenization: {'✅ OK' if 'tokenized_assets' in tables else '❌ MISSING'}")
    print(f"   Revenue Tracking: {'✅ OK' if 'platform_fees' in tables else '❌ MISSING'}")
    
    print("="*60 + "\n")