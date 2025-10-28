#!/usr/bin/env python3
"""
TON ELIMINATION SCRIPT - LOADS FROM .ENV FILE
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def nuke_ton_forever():
    print("💣 INITIATING TON ELIMINATION PROTOCOL...")
    
    # Get environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    print(f"🔑 Supabase URL: {supabase_url}")
    print(f"🔑 Supabase Key: {supabase_key[:10]}...")  # Only show first 10 chars
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        print("💡 Make sure SUPABASE_URL and SUPABASE_SERVICE_KEY are set in backend/.env")
        return
    
    headers = {
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }
    
    try:
        # 1. DELETE FROM wallet_creation_status
        url = f"{supabase_url}/rest/v1/wallet_creation_status"
        params = {'chain': 'eq.ton'}
        response = requests.delete(url, headers=headers, params=params)
        print(f"✅ DELETED TON from wallet_creation_status: {response.status_code}")
        
        # 2. DELETE FROM wallet_creation_queue  
        url = f"{supabase_url}/rest/v1/wallet_creation_queue"
        params = {'chain': 'eq.ton'}
        response = requests.delete(url, headers=headers, params=params)
        print(f"✅ DELETED TON from wallet_creation_queue: {response.status_code}")
        
        # 3. DELETE FROM multi_chain_addresses
        url = f"{supabase_url}/rest/v1/multi_chain_addresses"
        params = {'blockchain': 'eq.ton'}
        response = requests.delete(url, headers=headers, params=params)
        print(f"✅ DELETED TON from multi_chain_addresses: {response.status_code}")
        
        print("🎯 TON COMPLETELY ELIMINATED FROM DATABASE!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    nuke_ton_forever()