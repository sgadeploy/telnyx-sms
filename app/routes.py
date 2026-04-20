import hmac
import hashlib
import logging
import time
from flask import Blueprint, request, jsonify
from app import db, Contact
from app.__init__ import TELNYX_API_KEY, TELNYX_NUMBER, MESSAGE, MAILGUN_SIGNING_KEY
import requests
from datetime import datetime

bp = Blueprint('routes', __name__)

# Write to a dedicated log file so output is captured regardless of Gunicorn's logging setup
_log_handler = logging.FileHandler("/var/log/telnyx-sms/app.log")
_log_handler.setLevel(logging.DEBUG)
_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(_log_handler)

# Maximum age of a webhook timestamp before it is rejected (5 minutes)
MAX_TIMESTAMP_AGE = 300


def verify_mailgun_signature(timestamp, token, signature):
    """
    Verify the Mailgun webhook HMAC-SHA256 signature.
    Concatenate timestamp + token, sign with the Webhook Signing Key,
    and compare to the provided signature.
    Also rejects requests where the timestamp is more than MAX_TIMESTAMP_AGE
    seconds old to prevent replay attacks.
    """
    # Reject stale timestamps
    try:
        age = abs(time.time() - int(timestamp))
        if age > MAX_TIMESTAMP_AGE:
            logger.warning(f"Webhook timestamp too old: {age:.0f}s")
            return False
    except (ValueError, TypeError):
        logger.warning("Invalid webhook timestamp.")
        return False

    # Compute expected signature
    expected = hmac.new(
        MAILGUN_SIGNING_KEY.encode(),
        msg=f"{timestamp}{token}".encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        logger.warning("Mailgun signature verification failed.")
        return False

    logger.debug("Mailgun signature verified successfully.")
    return True


@bp.route('/email/inbound', methods=['POST'])
def inbound_email():
    # Handle both JSON and form payloads
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    logger.debug(f"Webhook received: {data}")

    # Extract signature fields
    timestamp = data.get('timestamp', '')
    token = data.get('token', '')
    signature = data.get('signature', '')

    if not all([timestamp, token, signature]):
        logger.warning("Missing signature fields in webhook payload.")
        return jsonify({"error": "Unauthorized"}), 403

    if not verify_mailgun_signature(timestamp, token, signature):
        return jsonify({"error": "Unauthorized"}), 403

    # Get all contacts from the database
    contacts = Contact.query.all()
    phone_numbers = [c.number for c in contacts]

    logger.debug(f"Sending SMS to {len(phone_numbers)} contacts: {phone_numbers}")

    for number in phone_numbers:
        logger.debug(f"Sending SMS to {number}")
        send_sms(number)

    return jsonify({"status": f"SMS sent to {len(phone_numbers)} contacts"}), 200


def send_sms(to):
    # Generate timestamp in local readable format
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    url = "https://api.telnyx.com/v2/messages"
    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }

    # SMS text with fixed message from config and timestamp
    payload = {
        "from": TELNYX_NUMBER,
        "to": to,
        "text": (
            f"🆘 {timestamp} \n"
            f"{MESSAGE}"
        )
    }

    logger.debug(f"Payload for Telnyx: {payload}")

    try:
        response = requests.post(url, json=payload, headers=headers)
        logger.debug(f"Telnyx response status: {response.status_code}")
        logger.debug(f"Telnyx response body: {response.text}")
    except Exception as e:
        logger.error(f"Error sending SMS to {to}: {e}")