# File: backend/api/routes/__init__.py
from .wallet_recovery import router as wallet_recovery_router

# Include in main FastAPI app
app.include_router(wallet_recovery_router, prefix="/api/wallet-recovery", tags=["wallet-recovery"])