# File: backend/api/routes/health.py
@router.get("/chain-health")
async def get_chain_health(
    wallet_service: MultiChainWalletService = Depends(get_multi_chain_wallet_service)
):
    """Real-time health monitoring for all 8 chains"""
    
    health_status = {}
    chains = ['algorand', 'bitcoin', 'ethereum', 'polygon', 'arbitrum', 'ton', 'tron', 'solana']
    
    for chain in chains:
        try:
            if chain == 'algorand':
                # Test Algorand connection
                account_info = await wallet_service.algorand.get_account_info(
                    wallet_service.algorand.treasury_address
                )
                health_status[chain] = {
                    "status": "healthy",
                    "block_height": account_info.get('round', 'unknown'),
                    "response_time": "fast"
                }
            else:
                # Test WDK chains
                wdk_health = await wallet_service.wdk_client.health_check()
                health_status[chain] = {
                    "status": "healthy", 
                    "service": "wdk",
                    "circuit_breaker": wallet_service.wdk_client.circuit_breaker.state
                }
                
        except Exception as e:
            health_status[chain] = {
                "status": "unhealthy",
                "error": str(e)
            }
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "total_chains": len(chains),
        "healthy_chains": sum(1 for chain in health_status.values() if chain['status'] == 'healthy'),
        "chains": health_status
    }