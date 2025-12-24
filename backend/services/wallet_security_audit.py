"""
Wallet Security Audit Script
Checks for common security issues in wallet management
"""

import re
import logging
from typing import Dict, List
from supabase import create_client
import os

logger = logging.getLogger(__name__)

class WalletSecurityAuditor:
    """Audit wallet security practices"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []
    
    def audit_database_storage(self, supabase):
        """Check if private keys are properly encrypted in DB"""
        try:
            # Sample 5 wallets to check encryption
            result = supabase.table('user_wallets')\
                .select('algorand_private_key, algorand_mnemonic')\
                .limit(5)\
                .execute()
            
            for wallet in result.data:
                # Check if keys look encrypted (Fernet format)
                private_key = wallet.get('algorand_private_key', '')
                mnemonic = wallet.get('algorand_mnemonic', '')
                
                # Encrypted data should NOT be readable as 25-word mnemonic
                if len(private_key.split()) == 25:
                    self.issues.append("🚨 CRITICAL: Unencrypted private key in database")
                elif len(private_key) == 64 and re.match(r'^[0-9a-fA-F]{64}$', private_key):
                    self.issues.append("🚨 CRITICAL: Plain hex private key in database")
                else:
                    self.passed.append("✅ Private keys appear encrypted")
                
                if len(mnemonic.split()) == 25 and all(w.isalpha() for w in mnemonic.split()):
                    self.issues.append("🚨 CRITICAL: Plain text mnemonic in database")
                else:
                    self.passed.append("✅ Mnemonics appear encrypted")
            
        except Exception as e:
            self.warnings.append(f"⚠️  Could not audit database: {e}")
    
    def audit_code_for_key_leaks(self, code_directory: str):
        """Scan code for potential key leaks"""
        
        dangerous_patterns = [
            (r'print\(.*private.*key.*\)', "Printing private keys"),
            (r'logger\.info\(.*private.*key.*\)', "Logging private keys"),
            (r'console\.log\(.*private.*key.*\)', "Console logging private keys (frontend)"),
            (r'decrypt_seed.*print', "Printing decrypted seeds"),
        ]
        
        # Scan Python files
        for root, dirs, files in os.walk(code_directory):
            for file in files:
                if file.endswith('.py') or file.endswith('.ts') or file.endswith('.tsx'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            for pattern, description in dangerous_patterns:
                                if re.search(pattern, content, re.IGNORECASE):
                                    self.issues.append(
                                        f"🚨 POTENTIAL LEAK: {description} in {filepath}"
                                    )
                    except:
                        pass  # Skip files we can't read
    
    def audit_encryption_key_storage(self):
        """Check if SEED_ENCRYPTION_KEY is properly secured"""
        
        encryption_key = os.getenv('SEED_ENCRYPTION_KEY')
        
        if not encryption_key:
            self.issues.append("🚨 CRITICAL: SEED_ENCRYPTION_KEY not set")
        elif len(encryption_key) < 32:
            self.issues.append("🚨 CRITICAL: SEED_ENCRYPTION_KEY too short (needs 32+ chars)")
        else:
            self.passed.append("✅ SEED_ENCRYPTION_KEY properly configured")
        
        # Check if key is hardcoded in .env (should be in env vars only)
        try:
            with open('.env', 'r') as f:
                env_content = f.read()
                if 'SEED_ENCRYPTION_KEY' in env_content:
                    self.warnings.append(
                        "⚠️  SEED_ENCRYPTION_KEY in .env file - should be in environment only"
                    )
        except:
            pass
    
    def generate_report(self) -> str:
        """Generate security audit report"""
        
        report = "\n" + "="*70 + "\n"
        report += "  🔐 WALLET SECURITY AUDIT REPORT\n"
        report += "="*70 + "\n\n"
        
        if self.issues:
            report += "🚨 CRITICAL ISSUES:\n"
            for issue in self.issues:
                report += f"  {issue}\n"
            report += "\n"
        
        if self.warnings:
            report += "⚠️  WARNINGS:\n"
            for warning in self.warnings:
                report += f"  {warning}\n"
            report += "\n"
        
        if self.passed:
            report += "✅ PASSED CHECKS:\n"
            for check in self.passed:
                report += f"  {check}\n"
            report += "\n"
        
        # Overall status
        if not self.issues:
            report += "🎉 NO CRITICAL SECURITY ISSUES FOUND\n"
        else:
            report += f"⛔ FOUND {len(self.issues)} CRITICAL SECURITY ISSUES - FIX IMMEDIATELY\n"
        
        report += "="*70 + "\n"
        
        return report

def run_audit():
    """Run full security audit"""
    from dotenv import load_dotenv
    load_dotenv()
    
    auditor = WalletSecurityAuditor()
    
    # Initialize Supabase
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY")
    )
    
    print("🔍 Running wallet security audit...")
    
    # Run checks
    auditor.audit_database_storage(supabase)
    auditor.audit_encryption_key_storage()
    auditor.audit_code_for_key_leaks("backend")
    
    # Generate report
    print(auditor.generate_report())
    
    # Return status code
    return 0 if not auditor.issues else 1

if __name__ == "__main__":
    exit(run_audit())