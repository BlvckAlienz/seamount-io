# File Location: backend/scripts/simple_server.py
from fastapi import FastAPI
import uvicorn
from pathlib import Path
import sys

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

app = FastAPI()

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "version": "test"}

@app.post("/api/payments/deposit/initialize")
async def initialize_deposit_test():
    return {
        "success": True,
        "transaction_id": "test_txn_123",
        "provider": "paystack",
        "payment_url": "https://checkout.paystack.com/test",
        "reference": "test_ref_123"
    }

@app.get("/api/payments/transaction/{transaction_id}")
async def get_transaction_status_test(transaction_id: str):
    return {
        "id": transaction_id,
        "status": "pending",
        "amount": 1000.00,
        "currency": "NGN",
        "created_at": "2023-09-12T19:43:35.656Z"
    }

if __name__ == "__main__":
    # Use a different port
    uvicorn.run(app, host="127.0.0.1", port=8001)