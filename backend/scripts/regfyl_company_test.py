#!/usr/bin/env python3
"""
Regfyl API Company Details Extractor
Run this script to get company details using secret key from .env file
"""

import asyncio
import aiohttp
import json
import hashlib
import hmac
import os
from pathlib import Path
from typing import Dict, Any

class RegfylAPITester:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.base_url = "https://api.portal.regfyl.com"  # Based on library docs
        
    def _generate_signature(self, payload: str) -> str:
        """Generate HMAC-SHA256 signature as specified in the implementation guide"""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _get_headers(self, payload: str = "") -> Dict[str, str]:
        """Get headers with API key and signature as per implementation guide"""
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.secret_key,
        }
        
        # Add signature only if payload is provided (for POST requests)
        if payload:
            headers['x-Signature'] = self._generate_signature(payload)
            
        return headers
    
    async def get_company_details(self) -> Dict[str, Any]:
        """
        Call the getCompany endpoint to extract companyName and rcNumber
        As specified in the implementation guide step (c)
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                endpoint = "/getCompany"
                url = f"{self.base_url}{endpoint}"
                
                # For GET requests, signature might not be required or use empty payload
                headers = self._get_headers()
                
                print(f"🔍 Calling getCompany endpoint: {url}")
                
                async with session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    response_status = response.status
                    
                    print(f"📊 Response Status: {response_status}")
                    
                    if response_status == 200:
                        try:
                            json_data = json.loads(response_text)
                            
                            # Extract company details from the companies array
                            if 'companies' in json_data and isinstance(json_data['companies'], list):
                                if len(json_data['companies']) > 0:
                                    company_data = json_data['companies'][0]
                                    company_name = company_data.get('companyName', '').strip()
                                    rc_number = company_data.get('rcNumber', '').strip()
                                    
                                    if company_name and rc_number:
                                        print("✅ Company details extracted successfully!")
                                        return {
                                            "success": True,
                                            "companyName": company_name,
                                            "rcNumber": rc_number,
                                            "accountBalance": json_data.get('accountBalance', ''),
                                            "full_response": json_data
                                        }
                                    else:
                                        return {
                                            "success": False,
                                            "error": "Company details found but empty",
                                            "response": json_data
                                        }
                                else:
                                    return {
                                        "success": False,
                                        "error": "No companies found in response",
                                        "response": json_data
                                    }
                            else:
                                return {
                                    "success": False,
                                    "error": "Invalid response format - 'companies' array not found",
                                    "response": json_data
                                }
                                
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON decode error: {str(e)}")
                            return {
                                "success": False,
                                "error": f"JSON decode error: {str(e)}",
                                "response": response_text
                            }
                    else:
                        print(f"❌ HTTP Error {response_status}")
                        return {
                            "success": False,
                            "error": f"HTTP Error {response_status}",
                            "response": response_text
                        }
                        
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    async def test_transaction_endpoint(self, company_name: str, rc_number: str) -> Dict[str, Any]:
        """Test the postTransaction endpoint with extracted company details"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                
                # Minimal payload as specified in the implementation guide
                test_payload = {
                    "companyName": company_name,
                    "rcNumber": rc_number,
                    "customerID": "test_customer_001",
                    "transactionAmount": 100,
                    "currency": "NGN",
                    "transactionStatus": "SUCCESSFUL",
                    "transactionChannel": "ONLINE",
                    "authenticated": "NO",
                    "customerType": "INDIVIDUAL",
                    "transactionType": "OUTFLOW",
                    "environment": "SANDBOX",
                    "customerName": "Test Customer",
                    "transactionReference": "TEST_REF_001"
                }
                
                payload_str = json.dumps(test_payload)
                headers = self._get_headers(payload_str)
                
                endpoint = "/postTransaction"
                url = f"{self.base_url}{endpoint}"
                
                print(f"🔍 Testing transaction endpoint with company details...")
                
                async with session.post(url, headers=headers, data=payload_str) as response:
                    response_text = await response.text()
                    
                    return {
                        "status": response.status,
                        "response": response_text,
                        "payload_sent": test_payload
                    }
                    
        except Exception as e:
            return {"error": f"POST request failed: {str(e)}"}

def load_secret_key_from_env() -> str:
    """
    Load the secret key from the .env file in the backend directory
    """
    # Path to the backend directory
    backend_dir = Path(__file__).parent / "backend"
    env_file = backend_dir / ".env"
    
    print(f"🔍 Looking for .env file at: {env_file}")
    
    if not env_file.exists():
        raise FileNotFoundError(f".env file not found at {env_file}")
    
    # Read the .env file
    with open(env_file, 'r') as file:
        env_content = file.read()
    
    # Parse the .env file (simple key=value parsing)
    env_vars = {}
    for line in env_content.splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key.strip()] = value.strip().strip('"').strip("'")
    
    # Look for the secret key - common variable names
    secret_key = None
    possible_keys = [
        'REGFYL_SECRET_KEY', 
        'REGIFYL_SECRET_KEY',
        'SECRET_KEY',
        'API_SECRET',
        'REGFYL_API_KEY',
        'REGIFYL_API_KEY'
    ]
    
    for key in possible_keys:
        if key in env_vars:
            secret_key = env_vars[key]
            print(f"✅ Found secret key using variable: {key}")
            break
    
    if not secret_key:
        # If not found, show available keys for debugging
        available_keys = list(env_vars.keys())
        print(f"🔍 Available environment variables: {available_keys}")
        raise KeyError(f"Secret key not found in .env file. Tried: {possible_keys}")
    
    return secret_key

async def main():
    """Main function to extract company details using secret key from .env file"""
    print("🔍 Regfyl API Company Details Extractor")
    print("=" * 50)
    print("Loading secret key from backend/.env file...")
    print()
    
    try:
        # Load secret key from .env file
        secret_key = load_secret_key_from_env()
        
        if not secret_key:
            print("❌ Secret key is empty")
            return
        
        print("✅ Secret key loaded successfully")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\n📁 Directory structure should be:")
        print("   project_root/")
        print("   ├── backend/")
        print("   │   └── .env          <-- Your .env file here")
        print("   └── this_script.py    <-- This script")
        return
        
    except KeyError as e:
        print(f"❌ Error: {e}")
        print("\n💡 Please ensure your .env file contains one of these variables:")
        print("   REGFYL_SECRET_KEY=your_secret_key_here")
        print("   SECRET_KEY=your_secret_key_here")
        print("   API_SECRET=your_secret_key_here")
        return
        
    except Exception as e:
        print(f"❌ Unexpected error loading .env file: {e}")
        return
    
    tester = RegfylAPITester(secret_key)
    
    # Step 1: Get company details as specified in the implementation guide
    print("\n🔄 Calling getCompany endpoint to extract companyName and rcNumber...")
    company_result = await tester.get_company_details()
    
    if company_result["success"]:
        print("\n🎯 COMPANY DETAILS EXTRACTED:")
        print(f"   📛 Company Name: {company_result['companyName']}")
        print(f"   🔢 RC Number: {company_result['rcNumber']}")
        print(f"   💰 Account Balance: {company_result.get('accountBalance', 'N/A')}")
        
        print("\n💡 Use these values in your API requests as required parameters:")
        print(f"   - companyName: '{company_result['companyName']}'")
        print(f"   - rcNumber: '{company_result['rcNumber']}'")
        
        # Optional: Test the transaction endpoint with the extracted values
        print("\n🔄 Testing transaction endpoint with extracted company details...")
        transaction_result = await tester.test_transaction_endpoint(
            company_result['companyName'], 
            company_result['rcNumber']
        )
        
        print(f"📊 Transaction Test Result:")
        print(f"   Status: {transaction_result.get('status', 'N/A')}")
        if 'response' in transaction_result:
            try:
                response_data = json.loads(transaction_result['response'])
                print(f"   API Response: {json.dumps(response_data, indent=2)}")
            except:
                print(f"   Response: {transaction_result['response'][:200]}...")
        
    else:
        print("\n❌ Failed to extract company details")
        print(f"   Error: {company_result.get('error', 'Unknown error')}")
        
        # Provide troubleshooting tips
        print("\n🔧 Troubleshooting Tips:")
        print("1. Verify your account has company details set up in the Regfyl portal")
        print("2. Check that your API key has proper permissions")
        print("3. Contact Regfyl support if issues persist")

if __name__ == "__main__":
    asyncio.run(main())