# File Location: tools/generate_webhook_secret.py
import secrets
import string

def generate_webhook_secret(length=32):
    """Generate a secure webhook secret for Paystack"""
    alphabet = string.ascii_letters + string.digits
    secret = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f"whsec_seamount_{secret}"

if __name__ == "__main__":
    secret = generate_webhook_secret()
    print(f"Your Paystack Webhook Secret: {secret}")
    print("\nAdd this to your .env file:")
    print(f"PAYSTACK_WEBHOOK_SECRET={secret}")
    print("\nUse this SAME secret when setting up webhook in Paystack dashboard!")