import logging
from typing import Dict, Any, List
from datetime import datetime
from decimal import Decimal

# --- Core Dependencies ---
from .email_service import EmailService

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Handles all user notifications and alerts by orchestrating different delivery methods.
    It is a modern, dependency-injected service.
    """
    
    def __init__(self, email_service: EmailService):
        """
        Initializes the service with a pre-configured EmailService client,
        following a clean dependency injection pattern.
        """
        if not email_service:
            raise ValueError("EmailService dependency is required.")
            
        self.email_service = email_service
        # In a real app, you would also inject SMS and Push notification services here.
        logger.info("NotificationService initialized successfully.")
        
    async def send_deposit_confirmation(self, user_email: str, amount: Decimal, usds_balance: Decimal) -> None:
        """Sends a deposit confirmation email to the user."""
        try:
            subject = f"Deposit Confirmed: Your Seamount.io Wallet has been Funded"
            body = f"""
            <html>
                <body>
                    <p>Dear Seamount User,</p>
                    <p>We are pleased to inform you that your deposit of <strong>{amount:.2f} USD</strong> has been successfully processed.</p>
                    <p>An equivalent amount of <strong>{amount:.2f} USDS</strong> has been minted to your wallet.</p>
                    <p>Your new USDS balance is: <strong>{usds_balance:.6f} USDS</strong>.</p>
                    <p>Thank you for using Seamount.io.</p>
                </body>
            </html>
            """
            await self.email_service.send_email(subject, [user_email], body)
            logger.info(f"Deposit confirmation sent to user {user_email}")
            
        except Exception as e:
            logger.error(f"Failed to send deposit notification to {user_email}: {e}")
            # In a production system, this failure would be added to a retry queue.

    async def send_transfer_notifications(self, sender_email: str, recipient_email: str, amount: Decimal, fee: Decimal) -> None:
        """Sends transfer notification emails to both the sender and recipient."""
        try:
            # Sender notification
            sender_subject = f"Transfer Sent: You sent {amount:.2f} USDS"
            sender_body = f"""
            <html>
                <body>
                    <p>Dear Seamount User,</p>
                    <p>You have successfully sent <strong>{amount:.2f} USDS</strong>.</p>
                    <p>A transaction fee of <strong>{fee:.2f} USDS</strong> was applied.</p>
                    <p>Thank you for using Seamount.io.</p>
                </body>
            </html>
            """
            await self.email_service.send_email(sender_subject, [sender_email], sender_body)

            # Recipient notification
            recipient_subject = f"Transfer Received: You have received {amount:.2f} USDS"
            recipient_body = f"""
            <html>
                <body>
                    <p>Dear Seamount User,</p>
                    <p>You have received a new payment of <strong>{amount:.2f} USDS</strong>.</p>
                    <p>The funds are now available in your Seamount.io wallet.</p>
                    <p>Thank you for using Seamount.io.</p>
                </body>
            </html>
            """
            await self.email_service.send_email(recipient_subject, [recipient_email], recipient_body)
            
            logger.info(f"Transfer notifications sent: {sender_email} -> {recipient_email}, {amount} USDS")
            
        except Exception as e:
            logger.error(f"Failed to send transfer notifications: {e}")

    async def send_withdrawal_confirmation(self, user_email: str, amount: Decimal, method: str, estimated_arrival: str) -> None:
        """Sends a withdrawal confirmation email to the user."""
        try:
            subject = f"Withdrawal Processed: {amount:.2f} USD is on its way"
            body = f"""
            <html>
                <body>
                    <p>Dear Seamount User,</p>
                    <p>Your withdrawal request for <strong>{amount:.2f} USD</strong> via {method} has been processed.</p>
                    <p>The estimated arrival time for your funds is: <strong>{estimated_arrival}</strong>.</p>
                    <p>Thank you for using Seamount.io.</p>
                </body>
            </html>
            """
            await self.email_service.send_email(subject, [user_email], body)
            logger.info(f"Withdrawal confirmation sent to user {user_email}: {amount} USD via {method}")

        except Exception as e:
            logger.error(f"Failed to send withdrawal notification to {user_email}: {e}")
            
    async def send_kyc_update(self, user_email: str, status: str, message: str) -> None:
        """Sends a KYC status update email to the user."""
        try:
            subject = f"Your Identity Verification Status has been Updated"
            body = f"""
            <html>
                <body>
                    <p>Dear Seamount User,</p>
                    <p>Your KYC verification status has been updated to: <strong>{status.upper()}</strong>.</p>
                    <p>{message}</p>
                    <p>If you have any questions, please contact our support team.</p>
                    <p>Thank you for using Seamount.io.</p>
                </body>
            </html>
            """
            await self.email_service.send_email(subject, [user_email], body)
            logger.info(f"KYC update sent to user {user_email}: {status}")

        except Exception as e:
            logger.error(f"Failed to send KYC notification to {user_email}: {e}")