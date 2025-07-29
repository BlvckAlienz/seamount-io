"""
Notification Service for Seamount.io - User Communication Hub
Handles: Transaction alerts, KYC updates, system notifications
File Location: backend/services/notification_service.py
"""

import logging
from typing import Dict, Any
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

class NotificationService:
    """Handles all user notifications and alerts"""
    
    def __init__(self):
        self.notification_queue = []
        self.email_enabled = True
        self.sms_enabled = True
        self.push_enabled = True
        
    async def send_deposit_confirmation(self, user_id: str, amount: Decimal, usds_balance: Decimal) -> Dict[str, Any]:
        """Send deposit confirmation notification"""
        try:
            notification = {
                'type': 'deposit_confirmation',
                'user_id': user_id,
                'amount': float(amount),
                'usds_balance': float(usds_balance),
                'timestamp': datetime.now(),
                'message': f"Deposit confirmed: {amount} USD converted to {amount} USDS"
            }
            
            self.notification_queue.append(notification)
            
            # Log for monitoring dashboard
            logger.info(f"Deposit confirmation sent to user {user_id}: {amount} USD")
            
            return {'success': True, 'notification_id': f"notif_{user_id}_{int(datetime.now().timestamp())}"}
            
        except Exception as e:
            logger.error(f"Deposit notification failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def send_transfer_notifications(self, sender_id: str, recipient_id: str, amount: Decimal, fee: Decimal) -> Dict[str, Any]:
        """Send transfer notifications to both parties"""
        try:
            # Sender notification
            sender_notification = {
                'type': 'transfer_sent',
                'user_id': sender_id,
                'amount': float(amount),
                'fee': float(fee),
                'recipient_id': recipient_id,
                'timestamp': datetime.now(),
                'message': f"Transfer sent: {amount} USDS (fee: {fee} USDS)"
            }
            
            # Recipient notification
            recipient_notification = {
                'type': 'transfer_received',
                'user_id': recipient_id,
                'amount': float(amount),
                'sender_id': sender_id,
                'timestamp': datetime.now(),
                'message': f"Transfer received: {amount} USDS"
            }
            
            self.notification_queue.extend([sender_notification, recipient_notification])
            
            logger.info(f"Transfer notifications sent: {sender_id} → {recipient_id}, {amount} USDS")
            
            return {'success': True, 'notifications_sent': 2}
            
        except Exception as e:
            logger.error(f"Transfer notifications failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def send_withdrawal_confirmation(self, user_id: str, amount: Decimal, method: str, estimated_arrival: str) -> Dict[str, Any]:
        """Send withdrawal confirmation notification"""
        try:
            notification = {
                'type': 'withdrawal_confirmation',
                'user_id': user_id,
                'amount': float(amount),
                'method': method,
                'estimated_arrival': estimated_arrival,
                'timestamp': datetime.now(),
                'message': f"Withdrawal confirmed: {amount} USD via {method}"
            }
            
            self.notification_queue.append(notification)
            
            logger.info(f"Withdrawal confirmation sent to user {user_id}: {amount} USD via {method}")
            
            return {'success': True, 'notification_id': f"notif_{user_id}_{int(datetime.now().timestamp())}"}
            
        except Exception as e:
            logger.error(f"Withdrawal notification failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def send_kyc_update(self, user_id: str, status: str, message: str) -> Dict[str, Any]:
        """Send KYC status update notification"""
        try:
            notification = {
                'type': 'kyc_update',
                'user_id': user_id,
                'status': status,
                'message': message,
                'timestamp': datetime.now()
            }
            
            self.notification_queue.append(notification)
            
            logger.info(f"KYC update sent to user {user_id}: {status}")
            
            return {'success': True, 'notification_id': f"kyc_{user_id}_{int(datetime.now().timestamp())}"}
            
        except Exception as e:
            logger.error(f"KYC notification failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_user_notifications(self, user_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get user notifications for dashboard"""
        try:
            user_notifications = [
                notif for notif in self.notification_queue
                if notif['user_id'] == user_id
            ]
            
            # Sort by timestamp (newest first)
            user_notifications.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return {
                'success': True,
                'notifications': user_notifications[:limit],
                'total': len(user_notifications)
            }
            
        except Exception as e:
            logger.error(f"Get notifications failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Notification service health check"""
        try:
            return {
                'healthy': True,
                'queue_size': len(self.notification_queue),
                'email_enabled': self.email_enabled,
                'sms_enabled': self.sms_enabled,
                'push_enabled': self.push_enabled,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Notification health check failed: {str(e)}")
            return {'healthy': False, 'error': str(e)}