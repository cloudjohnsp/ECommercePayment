import hashlib
import hmac
import json
import uuid

import requests
from flask import current_app

from .models import Payment


def deliver_payment_webhook(payment: Payment) -> dict:
    if not payment.callback_url:
        return {"attempted": False, "delivered": False}

    event_type = f"payment.{payment.status.value}"
    occurred_at = payment.refunded_at or payment.processed_at or payment.updated_at
    event = {
        "messageId": str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"ecommerce-payment:{payment.external_id}:{event_type}",
            )
        ),
        "eventType": event_type,
        "version": "1",
        "occurredAt": occurred_at.isoformat(),
        "correlationId": payment.correlation_id,
        "payload": payment.to_dict(),
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
                "X-Correlation-ID": payment.correlation_id,
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
