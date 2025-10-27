# backend/scripts/clean_ton_chains.py
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.dependencies import get_database_service

async def clean_ton_chains():
    """Remove any 'ton' chain records from the database"""
    db = get_database_service()
    
    try:
        # Delete wallet_creation_status records for 'ton'
        result = db.supabase.table("wallet_creation_status")\
            .delete()\
            .eq("chain", "ton")\
            .execute()
        print(f"✅ Deleted {len(result.data)} 'ton' records from wallet_creation_status")
        
        # Delete wallet_creation_queue records for 'ton'  
        result = db.supabase.table("wallet_creation_queue")\
            .delete()\
            .eq("chain", "ton")\
            .execute()
        print(f"✅ Deleted {len(result.data)} 'ton' records from wallet_creation_queue")
        
        print("🎯 Database cleaned of 'ton' chain records")
        
    except Exception as e:
        print(f"❌ Error cleaning 'ton' chains: {e}")

if __name__ == "__main__":
    asyncio.run(clean_ton_chains())