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
            
        except (ImportError, NameError, AttributeError) as e:
            logger.error(f"❌ fastapi-mail import failed: {e}")
            logger.warning("📧 Email service running in MOCK mode - emails will be logged only")
            self.enabled = False
        except Exception as e:
            logger.error(f"❌ Email service initialization failed: {e}")
            self.enabled = False
    
    async def send_email(
        self, 
        subject: str, 
        to_emails: List[str],  # ✅ FIXED: Changed from 'recipients'
        html_content: str  # ✅ FIXED: Changed from 'body'
    ) -> bool:
        """
        Send email with fallback to logging if service unavailable
        
        Args:
            subject: Email subject line
            to_emails: List of recipient email addresses
            html_content: HTML email body content
        """
        
        if not self.enabled:
            # Mock mode - just log
            logger.info(f"📧 [MOCK EMAIL] To: {to_emails}")
            logger.info(f"📧 [MOCK EMAIL] Subject: {subject}")
            logger.debug(f"📧 [MOCK EMAIL] Body: {html_content[:200]}...")
            return True
        
        try:
            from fastapi_mail import MessageSchema, MessageType
            
            message = MessageSchema(
                subject=subject,
                recipients=to_emails,  # ✅ fastapi_mail uses 'recipients' internally
                body=html_content,
                subtype=MessageType.html
            )
            
            await self.mail_client.send_message(message)
            logger.info(f"✅ Email sent successfully to {to_emails}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email send failed: {e}")
            # Fallback to logging (non-critical failure)
            logger.info(f"📧 [FALLBACK LOG] To: {to_emails}, Subject: {subject}")
            return False
    
    async def send_meter_application_confirmation(
    self,
    to_email: str,
    customer_name: str,
    application_id: str,
    application_type: str,
    map_vendor: str,
    phase_type: str,
    district: str,
    total_amount: float
):
    """Send meter application confirmation email"""
    try:
        # Load template
        template_path = Path(__file__).parent.parent / "templates" / "emails" / "meter_application_received.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Replace placeholders
        html_content = html_content.replace('{{ customer_name }}', customer_name)
        html_content = html_content.replace('{{ application_id }}', application_id)
        html_content = html_content.replace('{{ application_type }}', application_type.replace('_', ' ').title())
        html_content = html_content.replace('{{ map_vendor }}', map_vendor)
        html_content = html_content.replace('{{ phase_type }}', 'Single Phase' if phase_type == '1phase' else 'Three Phase')
        html_content = html_content.replace('{{ district }}', district)
        html_content = html_content.replace('{{ total_amount }}', f"{total_amount:,.0f}")
        
        # Send email
        await self.send_email(
            to_email=to_email,
            subject="⚡ Your Meter Application Has Been Received - Seamount",
            html_content=html_content
        )
        
        logger.info(f"✅ Meter application confirmation sent to {to_email}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send meter confirmation email: {e}")