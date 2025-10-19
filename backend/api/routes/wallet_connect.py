# File: backend/api/routes/wallet_connect.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.dependencies import get_current_user, get_db_service, get_audit_service
from backend.services.wallet_connect_service import WalletConnectService
from algosdk.v2client import algod, indexer
from backend.config import settings

router = APIRouter(prefix="/wallet", tags=["Wallet Connect"])

# Initialize Algorand clients
algod_client = algod.AlgodClient("", settings.ALGORAND_ALGOD_ADDRESS)
indexer_client = indexer.IndexerClient("", settings.ALGORAND_INDEXER_ADDRESS)

class DepositAddressRequest(BaseModel):
    asset: str = "USDT"

class WithdrawalAddressRequest(BaseModel):
    destination_address: str
    asset: str

@router.post("/deposit/address")
async def get_deposit_address(
    request: DepositAddressRequest,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Generate deposit address for receiving from exchanges"""
    
    service = WalletConnectService(db_service, audit_service, algod_client, indexer_client)
    
    return await service.generate_deposit_address(
        user_id=current_user["id"],
        asset=request.asset
    )

@router.post("/withdrawal/validate")
async def validate_withdrawal_address(
    request: WithdrawalAddressRequest,
    current_user: dict = Depends(get_current_user),
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Validate destination address for sending to exchanges"""
    
    service = WalletConnectService(db_service, audit_service, algod_client, indexer_client)
    
    return await service.get_withdrawal_address_info(
        user_id=current_user["id"],
        destination_address=request.destination_address,
        asset=request.asset
    )

@router.get("/exchanges")
async def get_supported_exchanges(
    db_service = Depends(get_db_service),
    audit_service = Depends(get_audit_service)
):
    """Get list of supported exchanges"""
    
    service = WalletConnectService(db_service, audit_service, algod_client, indexer_client)
    
    return await service.get_supported_exchanges()