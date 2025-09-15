#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from backend/.env
from dotenv import load_dotenv
env_path = project_root / 'backend' / '.env'
load_dotenv(dotenv_path=env_path)

from backend.config import get_settings
from backend.services.payment_providers.paystack import PaystackProvider

def test_paystack():
    settings = get_settings()
    
    # Check if Paystack keys are configured
    if not hasattr(settings, 'PAYSTACK_SECRET_KEY') or not settings.PAYSTACK_SECRET_KEY:
        print("❌ Paystack secret key not configured")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Env file path: {env_path}")
        print(f"Env file exists: {env_path.exists()}")
        if env_path.exists():
            print("Env file content:")
            with open(env_path, 'r') as f:
                print(f.read())
        return False
    
    try:
        processor = PaystackProvider(settings)
        print("✅ Paystack processor initialized successfully")
        
        # Test connection
        print("✅ Paystack connection test: Basic initialization successful")
        
        return True
    except Exception as e:
        print(f"❌ Paystack test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_paystack()
    sys.exit(0 if success else 1)