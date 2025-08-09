import asyncio
from typing import List
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- Core Dependencies ---
from config import Settings, logger # Import the base logger and Settings type

class EmailService:
    """
    A modern, dependency-injected service for sending transactional emails.
    """
    def __init__(self, settings: Settings):
        """
        Initializes the service with a pre-configured settings object,
        following a clean dependency injection pattern.
        """
        if not all([settings.MAIL_USERNAME, settings.MAIL_PASSWORD, settings.MAIL_FROM]):
            raise ValueError("Mail credentials are not fully configured.")
            
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD.get_secret_value(), # Use .get_secret_value() for SecretStr
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def send_email(self, subject: str, recipients: List[str], body: str):
        """
        Sends an email with robust error handling and retries.
        """
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype="html"
        )
        fm = FastMail(self.conf)
        try:
            logger.info(f"Attempting to send email to {recipients} with subject: '{subject}'")
            await fm.send_message(message)
            logger.info(f"Successfully sent email to {recipients}")
        except Exception as e:
            logger.error(f"Failed to send email to {recipients}. Error: {e}")
            raise

# Note: The test functions `send_test_email` and the `if __name__ == "__main__"` block
# are removed as they are not needed for the production service and can cause
# circular dependencies or other issues when run as part of the main application.