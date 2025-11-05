# File: backend/scripts/cleanup_usds.py
"""
Remove all USDS references from codebase
Run with: python backend/scripts/cleanup_usds.py
"""

import os
import re
from pathlib import Path

def remove_usds_references():
    """Remove USDS from all Python files"""
    
    # Root directory
    root = Path(__file__).parent.parent
    
    files_modified = []
    
    # Files to check
    python_files = list(root.rglob("*.py"))
    
    for file_path in python_files:
        if "venv" in str(file_path) or "__pycache__" in str(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Remove USDS from SUPPORTED_ASSETS dict
            content = re.sub(
                r':\s*\{[^}]+\},?\s*',
                '',
                content,
                flags=re.MULTILINE | re.DOTALL
            )
            
            # Remove USDS references in lists
            content = content.replace('', '')
            content = content.replace("", '')
            content = content.replace('', '')
            content = content.replace("", '')
            
            # Remove USDS-specific methods
            patterns_to_remove = [
                r'async def mint_usds\([^)]*\):[^}]+\n',
                r'async def burn_usds\([^)]*\):[^}]+\n',
                r'def get_usds_balance\([^)]*\):[^}]+\n',
            ]
            
            for pattern in patterns_to_remove:
                content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)
            
            # Write back if changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_modified.append(str(file_path))
                print(f"✅ Cleaned: {file_path.name}")
        
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    print(f"\n✅ CLEANUP COMPLETE: {len(files_modified)} files modified")
    for file in files_modified:
        print(f"   - {file}")

if __name__ == "__main__":
    print("🧹 Starting USDS cleanup...")
    remove_usds_references()