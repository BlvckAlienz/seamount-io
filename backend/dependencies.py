# File Location: backend/dependencies.py
from fastapi import HTTPException
from supabase import Client
from services.wallet_service import WalletService
from services.notification_service import NotificationService
from config import get_settings  # Add this import

# Global instances (will be set in main.py)
_supabase_client: Client = None
_wallet_service: WalletService = None
_notification_service: NotificationService = None

def get_supabase_client() -> Client:
    if _supabase_client is None: 
        raise HTTPException(status_code=503, detail="Database client not initialized")
    return _supabase_client

def get_wallet_service() -> WalletService:
    if _wallet_service is None: 
        raise HTTPException(status_code=503, detail="Wallet service not initialized")
    return _wallet_service

def get_notification_service() -> NotificationService:
    if _notification_service is None: 
        raise HTTPException(status_code=503, detail="Notification service not initialized")
    return _notification_service

# Re-export get_settings from config
get_settings = get_settings