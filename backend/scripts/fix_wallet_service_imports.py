#!/usr/bin/env python3
"""
Automated script to replace all wallet_service imports with multi_chain_wallet_service
Run from project root: python backend/scripts/fix_wallet_service_imports.py
"""

import os
import re
from pathlib import Path

# Files to update (with old import → new import mappings)
REPLACEMENTS = {
    # Simple import replacements
    'from backend.services.wallet_service import WalletService': 
        'from backend.services.multi_chain_wallet_service import MultiChainWalletService as WalletService',
    
    'from .wallet_service import WalletService':
        'from .multi_chain_wallet_service import MultiChainWalletService as WalletService',
    
    'from backend.services.wallet_service import WalletService as ActualWalletService':
        'from backend.services.multi_chain_wallet_service import MultiChainWalletService as ActualWalletService',
    
    # Dependency injection replacements
    'get_wallet_service':
        'get_multi_chain_wallet_service',
    
    # Service initialization
    'WalletService(database_service, algorand_service)':
        'MultiChainWalletService(database_service, algorand_service, fee_calculator_service, oracle_service)',
}

def fix_file(filepath: Path):
    """Fix wallet_service imports in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply replacements
        for old, new in REPLACEMENTS.items():
            content = content.replace(old, new)
        
        # Only write if changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed: {filepath}")
            return True
        else:
            print(f"⏭️  Skipped (no changes): {filepath}")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")
        return False

def main():
    """Main execution"""
    backend_dir = Path('backend')
    
    if not backend_dir.exists():
        print("❌ Error: Run this script from project root")
        return
    
    # Files to fix
    files_to_fix = [
        'backend/api/main.py',
        'backend/api/routes/transactions.py',
        'backend/api/routes/users.py',
        'backend/api/routes/webhooks.py',
        'backend/dependencies.py',
        'backend/services/onboarding_service.py',
        'backend/services/swap_service.py',
        'backend/scripts/test_imports.py',
    ]
    
    fixed_count = 0
    
    print("🔧 Starting wallet_service import fixes...\n")
    
    for filepath in files_to_fix:
        path = Path(filepath)
        if path.exists():
            if fix_file(path):
                fixed_count += 1
        else:
            print(f"⚠️  File not found: {filepath}")
    
    print(f"\n✅ Fixed {fixed_count} files")
    print("\n⚠️  MANUAL FIXES NEEDED:")
    print("1. backend/dependencies.py - Remove old get_wallet_service() function")
    print("2. Verify all Depends() calls updated to get_multi_chain_wallet_service")
    print("\n🧪 Next: Test with 'uvicorn backend.api.main:app --reload'")

if __name__ == '__main__':
    main()