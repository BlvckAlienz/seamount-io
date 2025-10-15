#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path.cwd()))

# Load environment variables from the .env file in the backend directory
from dotenv import load_dotenv
env_path = Path.cwd() / 'backend' / '.env'
load_dotenv(dotenv_path=env_path)

from backend.config import get_settings
from backend.services.payment_providers.flutterwave import FlutterwaveProvider

def test_flutterwave():
    settings = get_settings()
    
    # Check if Flutterwave keys are configured
    if not hasattr(settings, 'FLUTTERWAVE_SECRET_KEY') or not settings.FLUTTERWAVE_SECRET_KEY:
        print("❌ Flutterwave secret key not configured")
        return False
    
    try:
        processor = FlutterwaveProvider(settings)
        print("✅ Flutterwave processor initialized successfully")
        print("✅ Flutterwave connection test: Basic initialization successful")
        return True
    except Exception as e:
        print(f"❌ Flutterwave test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_flutterwave()
    sys.exit(0 if success else 1)