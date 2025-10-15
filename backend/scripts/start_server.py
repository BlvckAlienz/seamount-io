#!/usr/bin/env python3
import os
import sys
import uvicorn
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Start the server
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["backend"],
    )