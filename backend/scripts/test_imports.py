# File Location: backend/scripts/test_imports.py
import sys
from pathlib import Path

# Add the project root to the Python path (two levels up from this script)
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

print(f"Added project root to path: {project_root}")
print(f"Current Python path: {sys.path}")

try:
    # Test the imports
    from backend.config import Settings, get_settings
    from backend.services.wallet_service import WalletService
    from backend.services.notification_service import NotificationService
    from backend.services.audit_service import AuditService
    from backend.services.kyc_service import KYCService
    from backend.services.database_service import DatabaseService
    from backend.models import UserRole
    
    print("✅ All imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    # Try to debug by checking what's in the backend directory
    backend_path = project_root / "backend"
    print(f"Contents of backend directory: {list(backend_path.iterdir())}")