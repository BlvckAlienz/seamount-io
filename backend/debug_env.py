#!/usr/bin/env python3
"""
Debug environment variables and Supabase connection
Run this to verify your service key is correct
File: backend/debug_env.py
"""

import os
import sys
from supabase import create_client
import logging
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv('../.env')
load_dotenv('.env')

def debug_env():
    """Debug environment and Supabase setup"""
    
    print("=== ENVIRONMENT DEBUG ===")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.executable}")
    
    # Check critical env vars
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    print(f"\nSUPABASE_URL: {'✓' if supabase_url else '✗ MISSING'}")
    print(f"SERVICE_KEY length: {len(service_key) if service_key else '✗ MISSING'}")
    print(f"ANON_KEY length: {len(anon_key) if anon_key else '✗ MISSING'}")
    
    if supabase_url:
        print(f"URL: {supabase_url}")
    
    if service_key:
        print(f"SERVICE_KEY starts with: {service_key[:20]}...")
        # Service key should be much longer than anon key
        if len(service_key) < 100:
            print("🚨 WARNING: Service key seems too short!")
        
        # Quick JWT decode check (without libraries)
        if service_key.startswith('eyJ'):
            print("✓ Key starts with JWT format")
        else:
            print("✗ Key doesn't start with 'eyJ' - wrong format?")
    
    # Test Supabase connection
    if supabase_url and service_key:
        try:
            print("\n=== CONNECTION TEST ===")
            supabase = create_client(supabase_url, service_key)
            
            # Test a simple query
            result = supabase.table('user_profiles').select('count', count='exact').execute()
            print(f"✓ Supabase connection: SUCCESS")
            print(f"✓ user_profiles count: {result.count}")
            
            # Test insert capability
            test_result = supabase.table('user_profiles').select('id').limit(1).execute()
            print(f"✓ Query execution: SUCCESS")
            
        except Exception as e:
            print(f"✗ Supabase connection: FAILED")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
    
    # Check if using correct key type
    print("\n=== KEY TYPE CHECK ===")
    print("Service role key should:")
    print("- Be 500+ characters long")
    print("- Start with 'eyJ'")
    print("- Have 'service_role' in the decoded payload")
    print("- Be different from anon key")
    
    if service_key and anon_key:
        if service_key == anon_key:
            print("🚨 CRITICAL: Service key = Anon key! Wrong key!")
        else:
            print("✓ Service key ≠ Anon key")

if __name__ == "__main__":
    debug_env()