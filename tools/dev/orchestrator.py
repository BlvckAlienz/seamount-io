"""
Service Orchestrator for Seamount.io API Gateway
Handles transaction coordination, error recovery, and service communication
File Location: /backend/services/orchestrator.py
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class TransactionStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"

@dataclass
class TransactionStep:
    """Represents a single step in a multi-service transaction"""
    service: str
    action: str
    params: Dict[str, Any]
    rollback_action: Optional[str] = None
    rollback_params: Optional[Dict[str, Any]] = None
    completed: bool = False
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

@dataclass
class Transaction:
    """Represents a complete multi-service transaction"""
    id: str
    user_id: str
    transaction_type: str
    steps: List[TransactionStep] = field(default_factory=list)
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3
    retry_delay: int = 1

class ServiceOrchestrator:
    """
    Coordinates multi-service transactions with proper error handling and rollback
    This is the heart of your API Gateway - it ensures atomicity across services
    """
    
    def __init__(self):
        self.active_transactions: Dict[str, Transaction] = {}
        self.service_registry: Dict[str, Any] = {}
        self.compliance_checks: List[str] = ["aml_check", "kyc_check", "sanctions_check"]
        
    def register_service(self, service_name: str, service_instance: Any):
        """Register a service with the orchestrator"""
        self.service_registry[service_name] = service_instance
        logger.info(f"Registered service: {service_name}")
    
    async def create_transaction(self, 
                               transaction_id: str, 
                               user_id: str, 
                               transaction_type: str,
                               metadata: Dict[str, Any] = None) -> Transaction:
        """Create a new transaction with proper initialization"""
        transaction = Transaction(
            id=transaction_id,
            user_id=user_id,
            transaction_type=transaction_type,
            metadata=metadata or {}
        )
        
        self.active_transactions[transaction_id] = transaction
        logger.info(f"Created transaction {transaction_id} for user {user_id}")
        return transaction
    
    async def add_step(self, 
                      transaction_id: str, 
                      service: str, 
                      action: str,
                      params: Dict[str, Any],
                      rollback_action: str = None,
                      rollback_params: Dict[str, Any] = None):
        """Add a step to a transaction"""
        if transaction_id not in self.active_transactions:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        step = TransactionStep(
            service=service,
            action=action,
            params=params,
            rollback_action=rollback_action,
            rollback_params=rollback_params
        )
        
        self.active_transactions[transaction_id].steps.append(step)
        logger.info(f"Added step {action} to transaction {transaction_id}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    async def execute_step(self, transaction_id: str, step_index: int) -> Dict[str, Any]:
        """Execute a single transaction step with retry logic"""
        transaction = self.active_transactions[transaction_id]
        step = transaction.steps[step_index]
        
        try:
            # Get the service instance
            service = self.service_registry.get(step.service)
            if not service:
                raise HTTPException(status_code=500, detail=f"Service {step.service} not registered")
            
            # Execute the action
            action_method = getattr(service, step.action, None)
            if not action_method:
                raise HTTPException(status_code=500, detail=f"Action {step.action} not found in {step.service}")
            
            logger.info(f"Executing {step.service}.{step.action} for transaction {transaction_id}")
            
            # Call the service method
            if asyncio.iscoroutinefunction(action_method):
                result = await action_method(**step.params)
            else:
                result = action_method(**step.params)
            
            # Mark step as completed
            step.completed = True
            step.result = result
            step.timestamp = datetime.utcnow()
            
            logger.info(f"Step {step.action} completed successfully")
            return result
            
        except Exception as e:
            step.error = str(e)
            step.timestamp = datetime.utcnow()
            logger.error(f"Step {step.action} failed: {str(e)}")
            raise
    
    async def execute_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Execute all steps in a transaction with proper error handling"""
        transaction = self.active_transactions[transaction_id]
        transaction.status = TransactionStatus.PROCESSING
        
        try:
            results = []
            
            # Execute each step in sequence
            for i, step in enumerate(transaction.steps):
                result = await self.execute_step(transaction_id, i)
                results.append(result)
                
                # Update transaction status
                transaction.updated_at = datetime.utcnow()
            
            # Mark transaction as completed
            transaction.status = TransactionStatus.COMPLETED
            transaction.updated_at = datetime.utcnow()
            
            logger.info(f"Transaction {transaction_id} completed successfully")
            return {
                "transaction_id": transaction_id,
                "status": transaction.status.value,
                "results": results,
                "completed_at": transaction.updated_at.isoformat()
            }
            
        except Exception as e:
            transaction.status = TransactionStatus.FAILED
            transaction.updated_at = datetime.utcnow()
            
            logger.error(f"Transaction {transaction_id} failed: {str(e)}")
            
            # Attempt rollback
            await self.rollback_transaction(transaction_id)
            
            raise HTTPException(
                status_code=500,
                detail=f"Transaction failed: {str(e)}"
            )
    
    async def rollback_transaction(self, transaction_id: str):
        """Rollback a failed transaction"""
        transaction = self.active_transactions[transaction_id]
        transaction.status = TransactionStatus.ROLLING_BACK
        
        logger.info(f"Rolling back transaction {transaction_id}")
        
        # Rollback completed steps in reverse order
        for step in reversed(transaction.steps):
            if step.completed and step.rollback_action:
                try:
                    service = self.service_registry.get(step.service)
                    if service:
                        rollback_method = getattr(service, step.rollback_action, None)
                        if rollback_method:
                            rollback_params = step.rollback_params or {}
                            
                            if asyncio.iscoroutinefunction(rollback_method):
                                await rollback_method(**rollback_params)
                            else:
                                rollback_method(**rollback_params)
                            
                            logger.info(f"Rolled back step {step.action}")
                        
                except Exception as e:
                    logger.error(f"Rollback failed for step {step.action}: {str(e)}")
        
        transaction.status = TransactionStatus.ROLLED_BACK
        transaction.updated_at = datetime.utcnow()
    
    async def process_usds_payment(self, 
                                 user_id: str, 
                                 sender_wallet: str, 
                                 recipient_wallet: str, 
                                 amount: float,
                                 compliance_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a USDS payment with full transaction coordination
        This is your core payment flow - everything else builds on this
        """
        transaction_id = f"usds_pay_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        # Create transaction
        transaction = await self.create_transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            transaction_type="usds_payment",
            metadata={
                "sender_wallet": sender_wallet,
                "recipient_wallet": recipient_wallet,
                "amount": amount,
                "compliance_data": compliance_data or {}
            }
        )
        
        # Add compliance check step
        await self.add_step(
            transaction_id=transaction_id,
            service="compliance_service",
            action="check_transaction",
            params={
                "user_id": user_id,
                "sender_wallet": sender_wallet,
                "recipient_wallet": recipient_wallet,
                "amount": amount
            }
        )
        
        # Add balance validation step
        await self.add_step(
            transaction_id=transaction_id,
            service="balance_service",
            action="validate_balance",
            params={
                "user_id": user_id,
                "wallet": sender_wallet,
                "amount": amount
            }
        )
        
        # Add database update step
        await self.add_step(
            transaction_id=transaction_id,
            service="db_service",
            action="create_payment_record",
            params={
                "user_id": user_id,
                "transaction_id": transaction_id,
                "sender_wallet": sender_wallet,
                "recipient_wallet": recipient_wallet,
                "amount": amount,
                "status": "processing"
            },
            rollback_action="delete_payment_record",
            rollback_params={"transaction_id": transaction_id}
        )
        
        # Add blockchain transaction step
        await self.add_step(
            transaction_id=transaction_id,
            service="blockchain_service",
            action="send_usds_transaction",
            params={
                "sender": sender_wallet,
                "recipient": recipient_wallet,
                "amount": amount,
                "metadata": {"transaction_id": transaction_id}
            },
            rollback_action="cancel_transaction",
            rollback_params={"transaction_id": transaction_id}
        )
        
        # Add final database update step
        await self.add_step(
            transaction_id=transaction_id,
            service="db_service",
            action="update_payment_status",
            params={
                "transaction_id": transaction_id,
                "status": "completed"
            }
        )
        
        # Execute the transaction
        return await self.execute_transaction(transaction_id)
    
    async def process_marketData_rebalance(self, 
                                        user_id: str, 
                                        marketData_id: str, 
                                        target_allocation: Dict[str, float]) -> Dict[str, Any]:
        """
        Process marketData rebalancing with transaction coordination
        Shows how to handle complex multi-step operations
        """
        transaction_id = f"rebalance_{user_id}_{marketData_id}_{int(datetime.utcnow().timestamp())}"
        
        # Create transaction
        await self.create_transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            transaction_type="marketData_rebalance",
            metadata={
                "marketData_id": marketData_id,
                "target_allocation": target_allocation
            }
        )
        
        # Add marketData analysis step
        await self.add_step(
            transaction_id=transaction_id,
            service="marketData_service",
            action="analyze_rebalance",
            params={
                "user_id": user_id,
                "marketData_id": marketData_id,
                "target_allocation": target_allocation
            }
        )
        
        # Add trade execution step
        await self.add_step(
            transaction_id=transaction_id,
            service="trading_service",
            action="execute_rebalance",
            params={
                "user_id": user_id,
                "marketData_id": marketData_id,
                "target_allocation": target_allocation
            },
            rollback_action="reverse_trades",
            rollback_params={"transaction_id": transaction_id}
        )
        
        # Add marketData update step
        await self.add_step(
            transaction_id=transaction_id,
            service="marketData_service",
            action="update_allocation",
            params={
                "marketData_id": marketData_id,
                "new_allocation": target_allocation
            }
        )
        
        return await self.execute_transaction(transaction_id)
    
    def get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get the current status of a transaction"""
        if transaction_id not in self.active_transactions:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        transaction = self.active_transactions[transaction_id]
        return {
            "transaction_id": transaction_id,
            "status": transaction.status.value,
            "created_at": transaction.created_at.isoformat(),
            "updated_at": transaction.updated_at.isoformat(),
            "steps": len(transaction.steps),
            "completed_steps": sum(1 for step in transaction.steps if step.completed),
            "metadata": transaction.metadata
        }
    
    async def cleanup_old_transactions(self, max_age_hours: int = 24):
        """Clean up old transactions to prevent memory leaks"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for transaction_id, transaction in self.active_transactions.items():
            if transaction.updated_at < cutoff_time and transaction.status in [
                TransactionStatus.COMPLETED, 
                TransactionStatus.FAILED, 
                TransactionStatus.ROLLED_BACK
            ]:
                to_remove.append(transaction_id)
        
        for transaction_id in to_remove:
            del self.active_transactions[transaction_id]
            logger.info(f"Cleaned up old transaction {transaction_id}")
    
    def get_service(self, service_name: str) -> Any:
        """Get a registered service instance"""
        service = self.service_registry.get(service_name)
        if not service:
            raise HTTPException(status_code=500, detail=f"Service {service_name} not registered")
        return service
    
    def get_all_transactions(self) -> List[Dict[str, Any]]:
        """Get all active transactions (admin only)"""
        transactions = []
        for transaction_id, transaction in self.active_transactions.items():
            transactions.append({
                "transaction_id": transaction_id,
                "user_id": transaction.user_id,
                "type": transaction.transaction_type,
                "status": transaction.status.value,
                "created_at": transaction.created_at.isoformat(),
                "updated_at": transaction.updated_at.isoformat(),
                "steps": len(transaction.steps),
                "completed_steps": sum(1 for step in transaction.steps if step.completed)
            })
        return transactions
    
    async def retry_failed_transactions(self):
        """Retry failed transactions - background task"""
        logger.info("Starting failed transaction retry process")
        
        failed_transactions = [
            tx for tx in self.active_transactions.values() 
            if tx.status == TransactionStatus.FAILED
        ]
        
        for transaction in failed_transactions:
            try:
                logger.info(f"Retrying transaction {transaction.id}")
                await self.execute_transaction(transaction.id)
                logger.info(f"Transaction {transaction.id} retry successful")
            except Exception as e:
                logger.error(f"Transaction {transaction.id} retry failed: {str(e)}")
    
    async def process_payment_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment provider webhook"""
        try:
            # Extract transaction ID from webhook
            transaction_id = webhook_data.get("transaction_id")
            status = webhook_data.get("status")
            
            if not transaction_id:
                raise HTTPException(status_code=400, detail="Transaction ID missing from webhook")
            
            # Update transaction status
            if transaction_id in self.active_transactions:
                transaction = self.active_transactions[transaction_id]
                
                if status == "success":
                    transaction.status = TransactionStatus.COMPLETED
                elif status == "failed":
                    transaction.status = TransactionStatus.FAILED
                
                transaction.updated_at = datetime.utcnow()
                
                logger.info(f"Updated transaction {transaction_id} status to {status}")
            
            return {
                "transaction_id": transaction_id,
                "status": status,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            raise
            
async def process_blockchain_confirmation(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process blockchain confirmation webhook"""
    try:
        # Extract blockchain transaction data
        tx_hash = webhook_data.get("tx_hash")
        confirmations = webhook_data.get("confirmations", 0)
        status = webhook_data.get("status")
        
        if not tx_hash:
            raise HTTPException(status_code=400, detail="Transaction hash missing from webhook")
        
        # Find transaction by tx_hash in metadata
        matching_transaction = None
        for transaction in self.active_transactions.values():
            if transaction.metadata.get("tx_hash") == tx_hash:
                matching_transaction = transaction
                break
        
        if matching_transaction:
            # Update transaction based on confirmations
            if confirmations >= 1 and status == "confirmed":
                matching_transaction.status = TransactionStatus.COMPLETED
            elif status == "failed":
                matching_transaction.status = TransactionStatus.FAILED
            
            matching_transaction.updated_at = datetime.utcnow()
            matching_transaction.metadata["confirmations"] = confirmations
            
            logger.info(f"Updated blockchain transaction {tx_hash} with {confirmations} confirmations")
        
        return {
            "tx_hash": tx_hash,
            "confirmations": confirmations,
            "status": status,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Blockchain confirmation processing failed: {str(e)}")
        raise

# Add service health monitoring
async def health_check(self) -> Dict[str, Any]:
    """Check health of all registered services"""
    health_status = {
        "orchestrator": "healthy",
        "services": {},
        "active_transactions": len(self.active_transactions),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    for service_name, service in self.service_registry.items():
        try:
            # Check if service has health check method
            if hasattr(service, 'health_check'):
                if asyncio.iscoroutinefunction(service.health_check):
                    result = await service.health_check()
                else:
                    result = service.health_check()
                health_status["services"][service_name] = result
            else:
                health_status["services"][service_name] = "no_health_check"
        except Exception as e:
            health_status["services"][service_name] = f"error: {str(e)}"
    
    return health_status

# Add transaction metrics
def get_transaction_metrics(self) -> Dict[str, Any]:
    """Get transaction metrics for monitoring"""
    total_transactions = len(self.active_transactions)
    
    status_counts = {}
    for status in TransactionStatus:
        status_counts[status.value] = sum(
            1 for tx in self.active_transactions.values() 
            if tx.status == status
        )
    
    # Average transaction time for completed transactions
    completed_transactions = [
        tx for tx in self.active_transactions.values() 
        if tx.status == TransactionStatus.COMPLETED
    ]
    
    avg_completion_time = 0
    if completed_transactions:
        total_time = sum(
            (tx.updated_at - tx.created_at).total_seconds() 
            for tx in completed_transactions
        )
        avg_completion_time = total_time / len(completed_transactions)
    
    return {
        "total_transactions": total_transactions,
        "status_distribution": status_counts,
        "average_completion_time_seconds": avg_completion_time,
        "timestamp": datetime.utcnow().isoformat()
    }

# Add async payment processing with callbacks
async def process_async_payment(self, 
                               user_id: str, 
                               payment_data: Dict[str, Any],
                               callback_url: Optional[str] = None) -> Dict[str, Any]:
    """Process payment asynchronously with optional callback"""
    transaction_id = f"async_pay_{user_id}_{int(datetime.utcnow().timestamp())}"
    
    # Create transaction
    transaction = await self.create_transaction(
        transaction_id=transaction_id,
        user_id=user_id,
        transaction_type="async_payment",
        metadata={
            **payment_data,
            "callback_url": callback_url,
            "async": True
        }
    )
    
    # Add async processing steps
    await self.add_step(
        transaction_id=transaction_id,
        service="compliance_service",
        action="async_compliance_check",
        params={
            "user_id": user_id,
            "payment_data": payment_data
        }
    )
    
    await self.add_step(
        transaction_id=transaction_id,
        service="payment_processor",
        action="process_payment",
        params=payment_data
    )
    
    # Execute in background
    asyncio.create_task(self._execute_async_payment(transaction_id, callback_url))
    
    return {
        "transaction_id": transaction_id,
        "status": "processing",
        "estimated_completion": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    }

async def _execute_async_payment(self, transaction_id: str, callback_url: Optional[str] = None):
    """Execute async payment and send callback"""
    try:
        result = await self.execute_transaction(transaction_id)
        
        if callback_url:
            await self._send_callback(callback_url, result)
            
    except Exception as e:
        logger.error(f"Async payment {transaction_id} failed: {str(e)}")
        
        if callback_url:
            await self._send_callback(callback_url, {
                "transaction_id": transaction_id,
                "status": "failed",
                "error": str(e)
            })

async def _send_callback(self, callback_url: str, data: Dict[str, Any]):
    """Send callback to external system"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                callback_url,
                json=data,
                timeout=30.0
            )
            logger.info(f"Callback sent to {callback_url}: {response.status_code}")
    except Exception as e:
        logger.error(f"Callback failed to {callback_url}: {str(e)}")

# Add batch transaction processing
async def process_batch_transactions(self, 
                                   user_id: str, 
                                   transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process multiple transactions as a batch"""
    batch_id = f"batch_{user_id}_{int(datetime.utcnow().timestamp())}"
    
    # Create batch transaction
    await self.create_transaction(
        transaction_id=batch_id,
        user_id=user_id,
        transaction_type="batch_processing",
        metadata={
            "batch_size": len(transactions),
            "transaction_ids": []
        }
    )
    
    results = []
    failed_count = 0
    
    # Process each transaction
    for i, tx_data in enumerate(transactions):
        try:
            tx_id = f"{batch_id}_item_{i}"
            
            # Create individual transaction
            await self.create_transaction(
                transaction_id=tx_id,
                user_id=user_id,
                transaction_type=tx_data.get("type", "payment"),
                metadata=tx_data
            )
            
            # Add to batch metadata
            self.active_transactions[batch_id].metadata["transaction_ids"].append(tx_id)
            
            # Execute transaction
            result = await self.execute_transaction(tx_id)
            results.append(result)
            
        except Exception as e:
            failed_count += 1
            results.append({
                "transaction_id": f"{batch_id}_item_{i}",
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"Batch item {i} failed: {str(e)}")
    
    # Update batch status
    batch_transaction = self.active_transactions[batch_id]
    batch_transaction.status = TransactionStatus.COMPLETED if failed_count == 0 else TransactionStatus.FAILED
    batch_transaction.updated_at = datetime.utcnow()
    
    return {
        "batch_id": batch_id,
        "total_transactions": len(transactions),
        "successful": len(transactions) - failed_count,
        "failed": failed_count,
        "results": results,
        "completed_at": datetime.utcnow().isoformat()
    }

# Add transaction search and filtering
def search_transactions(self, 
                       user_id: Optional[str] = None,
                       transaction_type: Optional[str] = None,
                       status: Optional[str] = None,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Search and filter transactions"""
    filtered_transactions = []
    
    for transaction in self.active_transactions.values():
        # Apply filters
        if user_id and transaction.user_id != user_id:
            continue
            
        if transaction_type and transaction.transaction_type != transaction_type:
            continue
            
        if status and transaction.status.value != status:
            continue
            
        if start_date and transaction.created_at < start_date:
            continue
            
        if end_date and transaction.created_at > end_date:
            continue
        
        # Add to results
        filtered_transactions.append({
            "transaction_id": transaction.id,
            "user_id": transaction.user_id,
            "type": transaction.transaction_type,
            "status": transaction.status.value,
            "created_at": transaction.created_at.isoformat(),
            "updated_at": transaction.updated_at.isoformat(),
            "metadata": transaction.metadata
        })
    
    return filtered_transactions
    
# Global orchestrator instance
orchestrator = ServiceOrchestrator()