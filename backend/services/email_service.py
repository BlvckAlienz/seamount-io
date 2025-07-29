import asyncio
from typing import List
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# This import will now work correctly because config.py has get_settings and logger.
from config import get_settings, logger

class EmailService:
    def __init__(self):
        settings = get_settings()
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
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

async def send_test_email():
    email_service = EmailService()
    try:
        await email_service.send_email(
            subject="Test Email from Seamount.io",
            recipients=["upskillwithai9@gmail.com"], # Change to a recipient for testing
            body="<p>This is a test from the robust Seamount.io email service. If you received this, it works.</p>"
        )
    except Exception as e:
        logger.critical(f"Email sending failed after all retries. Final error: {e}")

if __name__ == "__main__":
    asyncio.run(send_test_email())