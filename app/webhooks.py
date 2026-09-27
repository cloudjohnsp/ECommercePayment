import hashlib
import hmac
import json

import requests
from flask import current_app

from .models import Payment


def deliver_payment_webhook(payment: Payment) -> dict:
    if not payment.callback_url:
        return {"attempted": False, "delivered": False}

    event = {
        "event": f"payment.{payment.status.value}",
        "data": payment.to_dict(),
    }
    body = json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(
        current_app.config["WEBHOOK_SECRET"].encode(), body, hashlib.sha256
    ).hexdigest()

    try:
        response = requests.post(
            payment.callback_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Payment-Signature": signature,
            },
            timeout=current_app.config["WEBHOOK_TIMEOUT_SECONDS"],
            allow_redirects=False,
        )
        return {
            "attempted": True,
            "delivered": 200 <= response.status_code < 300,
            "statusCode": response.status_code,
        }
    except requests.RequestException as exc:
        current_app.logger.warning("Payment webhook delivery failed: %s", exc)
        return {"attempted": True, "delivered": False}
