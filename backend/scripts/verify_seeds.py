# Create this file: backend/scripts/verify_seeds.py
from cryptography.fernet import Fernet
import os
import asyncio
from backend.config import get_settings

async def verify_user_seeds(user_id: str):
    """Quick verification script for seed architecture"""
    settings = get_settings()
    
    # Get encryption key
    encryption_key = os.getenv('ENCRYPTION_KEY')
    if not encryption_key:
        print("❌ ENCRYPTION_KEY not found")
        return
    
    fernet = Fernet(encryption_key.encode())
    
    # Query both tables (you'll need your database connection here)
    # This is pseudocode - adapt to your actual DB service
    
    print(f"🔍 Verifying seed architecture for user: {user_id}")
    print("=" * 50)
    
    # Check if seeds are the same across chains
    # If they decrypt to the same value = Single Seed Architecture ✅
    # If different = Multi Seed Architecture ❌
    
    # Your actual implementation here