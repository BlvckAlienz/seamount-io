# Create test_signature.py
import hmac
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

webhook_secret = os.getenv("QUIDAX_WEBHOOK_SECRET")
timestamp = "1766602406"
payload = '{"event":"instant_order.done","id":"evt_1766602425","data":{"id":"qd_test_123"}}'

signed_payload = f"{timestamp}.{payload}"
signature = hmac.new(
    webhook_secret.encode('utf-8'),
    signed_payload.encode('utf-8'),
    hashlib.sha256
).hexdigest()

print(f"Timestamp: {timestamp}")
print(f"Signature: {signature}")
print(f"Full header: t={timestamp},v1={signature}")