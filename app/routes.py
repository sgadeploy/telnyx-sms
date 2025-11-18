import logging
from flask import Blueprint, request, jsonify
from app import db, Contact
from app.__init__ import TELNYX_API_KEY, TELNYX_NUMBER, MESSAGE
import requests
from datetime import datetime

bp = Blueprint('routes', __name__)

logging.basicConfig(level=logging.DEBUG)

@bp.route('/email/inbound', methods=['POST'])
def inbound_email():
    # Handle both JSON and form payloads
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    logging.debug(f"Webhook received: {data}")

    # Extract message from email body
    message = data.get('body-plain', '').strip()
    if not message:
        logging.warning("No message found in email body.")
        return jsonify({"error": "No message content"}), 400

    # Get all contacts from the database
    contacts = Contact.query.all()
    phone_numbers = [c.number for c in contacts]

    logging.debug(f"Sending message to {len(phone_numbers)} contacts: {phone_numbers}")

    for number in phone_numbers:
        logging.debug(f"Sending SMS to {number}")
        send_sms(number, message)

    return jsonify({"status": f"SMS sent to {len(phone_numbers)} contacts"}), 200

def send_sms(to, message):
    # Generate timestamp in local readable format
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    url = "https://api.telnyx.com/v2/messages"
    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }

    # SMS text with message and timestamp
    payload = {
        "from": TELNYX_NUMBER,
        "to": to,
        "text": (
            f"🆘 {timestamp} \n" 
            f"{MESSAGE}"
        )
    }

    logging.debug(f"Payload for Telnyx: {payload}")

    try:
        response = requests.post(url, json=payload, headers=headers)
        logging.debug(f"Telnyx response status: {response.status_code}")
        logging.debug(f"Telnyx response body: {response.text}")
    except Exception as e:
        logging.error(f"Error sending SMS to {to}: {e}")