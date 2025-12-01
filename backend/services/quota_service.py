# File: backend/services/quota_service.py
# Smart API Quota Management - Production Grade

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from backend.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class QuotaService:
    """
    Intelligent API quota management system
    - Tracks usage across all external APIs
    - Automatically skips exhausted services
    - Resets quotas monthly
    - Provides health status for monitoring
    """
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self._quota_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamp = None
        
    async def can_use_service(self, service_name: str, reserve_calls: int = 10) -> bool:
        """
        Check if service has available quota
        
        Args:
            service_name: API service identifier
            reserve_calls: Reserve this many calls for emergencies
            
        Returns:
            True if service can be used, False if quota exhausted
        """
        try:
            quota_data = await self._get_quota_data(service_name)
            
            if not quota_data:
                logger.warning(f"No quota data for {service_name}, allowing by default")
                return True
            
            calls_used = quota_data.get('calls_used_this_month', 0)
            monthly_limit = quota_data.get('monthly_limit', 999999)
            status = quota_data.get('status', 'active')
            
            # Check status
            if status == 'exhausted':
                return False
            
            # Check if we're within safe limits
            available = monthly_limit - calls_used
            
            if available <= reserve_calls:
                logger.warning(
                    f"⚠️ {service_name} approaching limit: "
                    f"{calls_used}/{monthly_limit} used, reserving last {reserve_calls} calls"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Quota check failed for {service_name}: {e}")
            return True  # Fail open - allow service
    
    async def record_api_call(self, service_name: str, success: bool = True):
        """
        Record an API call for quota tracking
        
        Args:
            service_name: API service identifier
            success: Whether the call succeeded
        """
        try:
            # Increment counter
            query = """
                UPDATE api_quota_tracking
                SET 
                    calls_used_this_month = calls_used_this_month + 1,
                    last_call_timestamp = NOW(),
                    status = CASE 
                        WHEN calls_used_this_month + 1 >= monthly_limit THEN 'exhausted'
                        WHEN calls_used_this_month + 1 >= monthly_limit * 0.9 THEN 'degraded'
                        ELSE 'active'
                    END
                WHERE service_name = $1
                RETURNING calls_used_this_month, monthly_limit, status
            """
            
            result = await self.db_service.execute_query(query, service_name)
            
            if result and len(result) > 0:
                row = result[0]
                calls_used = row['calls_used_this_month']
                limit = row['monthly_limit']
                status = row['status']
                
                # Log warnings at key thresholds
                usage_percent = (calls_used / limit) * 100
                
                if usage_percent >= 90:
                    logger.warning(
                        f"🚨 {service_name} CRITICAL: {calls_used}/{limit} "
                        f"({usage_percent:.1f}%) - Status: {status}"
                    )
                elif usage_percent >= 75:
                    logger.warning(
                        f"⚠️ {service_name} HIGH: {calls_used}/{limit} "
                        f"({usage_percent:.1f}%)"
                    )
                
                # Clear cache to force refresh
                self._quota_cache.pop(service_name, None)
            
        except Exception as e:
            logger.error(f"Failed to record API call for {service_name}: {e}")
    
    async def get_quota_status(self, service_name: str) -> Dict[str, Any]:
        """Get current quota status for a service"""
        try:
            quota_data = await self._get_quota_data(service_name)
            
            if not quota_data:
                return {
                    'service': service_name,
                    'status': 'unknown',
                    'available': False
                }
            
            calls_used = quota_data.get('calls_used_this_month', 0)
            limit = quota_data.get('monthly_limit', 999999)
            
            return {
                'service': service_name,
                'calls_used': calls_used,
                'monthly_limit': limit,
                'remaining': limit - calls_used,
                'usage_percent': round((calls_used / limit) * 100, 2),
                'status': quota_data.get('status', 'active'),
                'last_call': quota_data.get('last_call_timestamp'),
                'available': await self.can_use_service(service_name)
            }
            
        except Exception as e:
            logger.error(f"Failed to get quota status for {service_name}: {e}")
            return {'service': service_name, 'status': 'error', 'available': False}
    
    async def get_all_quotas(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tracked services"""
        try:
            query = "SELECT * FROM api_quota_tracking ORDER BY service_name"
            results = await self.db_service.execute_query(query)
            
            quotas = {}
            for row in results:
                service = row['service_name']
                quotas[service] = await self.get_quota_status(service)
            
            return quotas
            
        except Exception as e:
            logger.error(f"Failed to get all quotas: {e}")
            return {}
    
    async def reset_monthly_quotas(self):
        """Manually trigger monthly quota reset"""
        try:
            query = """
                UPDATE api_quota_tracking
                SET 
                    calls_used_this_month = 0,
                    last_reset_date = NOW(),
                    status = 'active'
            """
            
            await self.db_service.execute_query(query)
            logger.info("✅ Monthly quotas reset successfully")
            
            # Clear cache
            self._quota_cache.clear()
            
        except Exception as e:
            logger.error(f"Failed to reset monthly quotas: {e}")
    
    async def _get_quota_data(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Internal method to get quota data with caching"""
        try:
            # Check cache (5 minute TTL)
            from datetime import datetime, timedelta
            
            if service_name in self._quota_cache:
                cached = self._quota_cache[service_name]
                if datetime.now() - cached['cached_at'] < timedelta(minutes=5):
                    return cached['data']
            
            # Fetch from database
            query = """
                SELECT * FROM api_quota_tracking 
                WHERE service_name = $1
            """
            
            result = await self.db_service.execute_query(query, service_name)
            
            if result and len(result) > 0:
                data = dict(result[0])
                
                # Cache it
                self._quota_cache[service_name] = {
                    'data': data,
                    'cached_at': datetime.now()
                }
                
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get quota data for {service_name}: {e}")
            return None