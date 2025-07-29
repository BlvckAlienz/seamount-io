from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from config import get_config

async def test_email():
    config = get_config()
    conf = ConnectionConfig(
        MAIL_USERNAME=config["MAIL_USERNAME"],
        MAIL_PASSWORD=config["MAIL_PASSWORD"],
        MAIL_FROM=config["MAIL_FROM"],
        MAIL_PORT=config["MAIL_PORT"],
        MAIL_SERVER=config["MAIL_SERVER"],
        MAIL_USE_SSL=config["MAIL_USE_SSL"]
    )
    
    message = MessageSchema(
        subject="Test Email",
        recipients=["upskillwithai9@gmail.com"],
        body="This is a test from Seamount"
    )
    
    fm = FastMail(conf)
    await fm.send_message(message)