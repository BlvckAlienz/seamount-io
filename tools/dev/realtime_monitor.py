# realtime_monitor.py
# Location: /root/seamount/monitoring/realtime_monitor.py

import requests
import time
import json
import os
import sys
import signal
import os
import sys
import signal
from datetime import datetime
import logging
import logging
import threading
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SeamountMonitor:
    def __init__(self, base_url=None):
        # Get base_url from environment or use default
        self.base_url = base_url or os.getenv("SEAMOUNT_API_URL", "http://localhost:8000")
        self.base_url = base_url or os.getenv("SEAMOUNT_API_URL", "http://localhost:8000")
        self.monitoring = True
        self.stats = {
            'webhooks_received': 0,
            'usds_minted': 0,
            'failed_requests': 0,
            'last_activity': None
        }
        self.recent_events = deque(maxlen=10)
    
    def log_event(self, event_type, data):
        """Log events with timestamp"""
        event = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'type': event_type,
            'data': data
        }
        logger.info(f"EVENT: {event_type} - {data}")
        logger.info(f"EVENT: {event_type} - {data}")
        self.recent_events.append(event)
    
    def check_system_health(self):
        """Check if Seamount is responsive"""
        try:
            logger.debug(f"Checking health at {self.base_url}/health")
            
            logger.debug(f"Checking health at {self.base_url}/health")
            
            response = requests.get(f"{self.base_url}/health", timeout=3)
            if response.status_code == 200:
                health_data = response.json()
                self.log_event('HEALTH_CHECK', 'System healthy')
                return True, health_data
            else:
                self.log_event('HEALTH_CHECK', f'Status {response.status_code}')
                return False, None
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            logger.warning(f"Health check failed: {e}")
            self.log_event('HEALTH_CHECK', f'Failed: {str(e)}')
            return False, None
    
    def monitor_usds_supply(self):
        """Monitor USDS token supply changes"""
        logger.debug(f"Checking USDS supply at {self.base_url}/api/usds/balance")
        
        logger.debug(f"Checking USDS supply at {self.base_url}/api/usds/balance")
        
        try:
            response = requests.get(f"{self.base_url}/api/usds/balance", timeout=3)
            if response.status_code == 200:
                balance_data = response.json()
                total_supply = balance_data.get('total_supply', 0)
                
                # Check if supply increased
                if hasattr(self, 'last_supply') and total_supply > self.last_supply:
                    minted = total_supply - self.last_supply
                    self.stats['usds_minted'] += minted
                    self.log_event('USDS_MINT', f'{minted} USDS minted')
                
                self.last_supply = total_supply
                return balance_data
            else:
                self.stats['failed_requests'] += 1
                logger.warning(f"USDS balance check failed with status {response.status_code}")
                logger.warning(f"USDS balance check failed with status {response.status_code}")
                return None
        except Exception as e:
            self.stats['failed_requests'] += 1
            return None
    
    def display_dashboard(self):
        """Display real-time dashboard"""
        while self.monitoring:
            # Clear screen (works on most terminals)
            print('\033[2J\033[H')
            
            # Header
            print("🌊 SEAMOUNT REAL-TIME MONITOR")
            print("=" * 60)
            print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🌐 Monitoring: {self.base_url}")
            
            # System Health
            is_healthy, health_data = self.check_system_health()
            status_icon = "🟢" if is_healthy else "🔴"
            print(f"\n{status_icon} System Status: {'ONLINE' if is_healthy else 'OFFLINE'}")
            
            # USDS Stats
            balance_data = self.monitor_usds_supply()
            if balance_data:
                print(f"💰 USDS Supply: {balance_data.get('total_supply', 0)}")
                print(f"💵 Reserve: ${balance_data.get('reserve_balance', 0):,.2f}")
            
            # Live Stats
            print(f"\n📊 SESSION STATS:")
            print(f"   Webhooks Received: {self.stats['webhooks_received']}")
            print(f"   USDS Minted: {self.stats['usds_minted']}")
            print(f"   Failed Requests: {self.stats['failed_requests']}")
            
            # Recent Events
            print(f"\n📜 RECENT ACTIVITY:")
            if self.recent_events:
                for event in list(self.recent_events)[-5:]:  # Show last 5 events
                    print(f"   {event['timestamp']} | {event['type']}: {event['data']}")
            else:
                print("   No recent activity")
            
            # Instructions
            print(f"\n🧪 TEST INSTRUCTIONS:")
            print(f"   1. Open: {self.base_url}")
            print(f"   2. Create payment ($5 test amount)")
            print(f"   3. Use test card: 4187427415564246")
            print(f"   4. Watch webhook trigger USDS mint")
            print(f"\n💡 Press Ctrl+C to stop monitoring")
            
            time.sleep(2)  # Update every 2 seconds

    def monitor_backend_logs(self):
        """Monitor backend logs if available"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/logs", timeout=3)
            if response.status_code == 200:
                logs_data = response.json()
                for log in logs_data.get('recent_logs', [])[:5]:
                    self.log_event('BACKEND_LOG', log)
        except Exception as e:
            logger.debug(f"Backend logs check failed: {e}")

    def monitor_backend_logs(self):
        """Monitor backend logs if available"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/logs", timeout=3)
            if response.status_code == 200:
                logs_data = response.json()
                for log in logs_data.get('recent_logs', [])[:5]:
                    self.log_event('BACKEND_LOG', log)
        except Exception as e:
            logger.debug(f"Backend logs check failed: {e}")
    
    def webhook_listener(self):
        """Simulate listening for webhook activity"""
        # In a real implementation, this would monitor webhook endpoint
        # For now, we'll poll webhook endpoint status
        pass
    
    def start_monitoring(self):
        """Start the real-time monitoring"""
        print("🚀 Starting Seamount Real-Time Monitor...")
        logger.info(f"Starting monitoring of {self.base_url}")


        try:
            # Register signal handler for graceful exit
            signal.signal(signal.SIGINT, lambda sig, frame: self.stop_monitoring())
            # Register signal handler for graceful exit
            signal.signal(signal.SIGINT, lambda sig, frame: self.stop_monitoring())
            # Start monitoring in main thread
            self.display_dashboard()
        except KeyboardInterrupt:
            print("\n\n⏹️ Monitoring stopped.")
            self.monitoring = False
    
    def quick_test(self):
        """Run a quick system test"""
        print("⚡ Quick System Test")
        print("-" * 30)
        
        # Test health endpoint
        is_healthy, _ = self.check_system_health()
        print(f"Health Check: {'✅ PASS' if is_healthy else '❌ FAIL'}")
        
        # Test USDS balance endpoint
        balance_data = self.monitor_usds_supply()
        print(f"USDS Balance: {'✅ PASS' if balance_data else '❌ FAIL'}")
        
        if balance_data:
            print(f"Current Supply: {balance_data.get('total_supply', 0)} USDS")
        
        return is_healthy and balance_data is not None

    def stop_monitoring(self):
        """Stop monitoring gracefully"""
        print("\n\n⏹️ Monitoring stopped.")
        logger.info("Monitoring stopped by user")
        self.monitoring = False

    def stop_monitoring(self):
        """Stop monitoring gracefully"""
        print("\n\n⏹️ Monitoring stopped.")
        logger.info("Monitoring stopped by user")
        self.monitoring = False

if __name__ == "__main__":
    import sys
    
    # Get base URL from command line args if provided
    base_url = sys.argv[2] if len(sys.argv) > 2 else None
    monitor = SeamountMonitor(base_url)
    
    # Get base URL from command line args if provided
    base_url = sys.argv[2] if len(sys.argv) > 2 else None
    monitor = SeamountMonitor(base_url)
    
    monitor = SeamountMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Quick test mode
        success = monitor.quick_test()
        sys.exit(0 if success else 1)
    else:
        # Full monitoring mode
        monitor.start_monitoring()
