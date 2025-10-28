# File: backend/api/routes/__init__.py
# This file should only contain imports, NOT route registration
from .wallet_recovery import router as wallet_recovery_router

# Export all routers for main.py to register
__all__ = ['wallet_recovery_router']