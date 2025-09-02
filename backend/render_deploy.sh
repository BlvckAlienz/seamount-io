#!/bin/bash

# File Location: backend/render_deploy.sh
# CRITICAL: Render deployment script to fix Python path and module resolution

set -e  # Exit on any error

echo "🚀 Starting Seamount Backend Deployment on Render..."

# Fix Python path issues by ensuring backend directory is properly configured
export PYTHONPATH="/opt/render/project/src:$PYTHONPATH"
export PYTHONPATH="/opt/render/project/src/backend:$PYTHONPATH"

echo "✅ Python path configured: $PYTHONPATH"

# Create __init__.py files to ensure proper module structure
touch /opt/render/project/src/__init__.py
touch /opt/render/project/src/backend/__init__.py
touch /opt/render/project/src/backend/services/__init__.py
touch /opt/render/project/src/backend/api/__init__.py
touch /opt/render/project/src/backend/api/routes/__init__.py

echo "✅ Module structure initialized"

# Verify critical imports work before starting the server
python -c "
import sys
sys.path.insert(0, '/opt/render/project/src')
sys.path.insert(0, '/opt/render/project/src/backend')

print('Testing critical imports...')
try:
    from backend.config import get_settings, settings
    print('✅ Config imports working')
    
    from backend.services.database_service import SuperDatabaseService
    print('✅ Database service import working')
    
    from backend.api.main import app
    print('✅ Main app import working')
    
    # Test settings initialization
    test_settings = get_settings()
    print('✅ Settings initialization working')
    
    print('🎉 All critical imports successful!')
except Exception as e:
    print(f'❌ Import test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

echo "✅ Import verification completed successfully"

# Now start the actual server
echo "🔥 Starting Seamount API server..."
exec gunicorn -k uvicorn.workers.UvicornWorker api.main:app \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info