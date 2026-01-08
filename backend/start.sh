#!/bin/bash
# File: backend/start.sh

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "🔵 Starting Seamount API..."
echo "🔵 PROJECT_ROOT: $PROJECT_ROOT"
echo "🔵 PYTHONPATH: $PYTHONPATH"

# Start server
cd "$SCRIPT_DIR"
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000