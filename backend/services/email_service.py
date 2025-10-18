# File: backend/services/email_service.py
"""
Email service with graceful fallback for fastapi-mail issues
"""

import logging
from typing import List, Optional
from backend.config import Settings

logger = logging.getLogger(__name__)

class EmailService:
    """Email service with robust error handling"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = False
        self.mail_client = None
        
        # Check if mail server configured
        if not settings.MAIL_SERVER:
            logger.warning("⚠️ Mail server not configured - email disabled")
            return
            
        # Try to import fastapi-mail with fallback
        try:
            from fastapi_mail import ConnectionConfig, FastMail
            
            self.conf = ConnectionConfig(
                MAIL_USERNAME=settings.MAIL_USERNAME,
                MAIL_PASSWORD=settings.MAIL_PASSWORD.get_secret_value(),
                MAIL_FROM=settings.MAIL_FROM,
                MAIL_PORT=settings.MAIL_PORT,
                MAIL_SERVER=settings.MAIL_SERVER,
                MAIL_STARTTLS=settings.MAIL_STARTTLS,
                MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
                USE_CREDENTIALS=True,
                VALIDATE_CERTS=False
            )
            
            self.mail_client = FastMail(self.conf)
            self.enabled = True
            logger.info("✅ Email service initialized successfully")
            
        except ImportError as e:
            logger.error(f"❌ fastapi-mail import failed: {e}")
            logger.warning("📧 Email service running in MOCK mode - emails will be logged only")
            self.enabled = False
        except Exception as e:
            logger.error(f"❌ Email service initialization failed: {e}")
            self.enabled = False
    
    async def send_email(
        self, 
        subject: str, 
        recipients: List[str], 
        body: str
    ) -> bool:
        """Send email with fallback to logging if service unavailable"""
        
        if not self.enabled:
            # Mock mode - just log
            logger.info(f"📧 [MOCK EMAIL] To: {recipients}")
            logger.info(f"📧 [MOCK EMAIL] Subject: {subject}")
            logger.debug(f"📧 [MOCK EMAIL] Body: {body[:200]}...")
            return True
        
        try:
            from fastapi_mail import MessageSchema
            
            message = MessageSchema(
                subject=subject,
                recipients=recipients,
                body=body,
                subtype="html"
            )
            
            await self.mail_client.send_message(message)
            logger.info(f"✅ Email sent to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email send failed: {e}")
            # Fallback to logging
            logger.info(f"📧 [FALLBACK LOG] To: {recipients}, Subject: {subject}")
            return False