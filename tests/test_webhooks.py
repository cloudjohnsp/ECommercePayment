import hashlib
import hmac
import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

import requests

from app.models import Payment, PaymentStatus
from app.webhooks import deliver_payment_webhook


def build_payment(callback_url="http://ecommerce-api/api/webhooks/payments"):
    now = datetime.now(timezone.utc)
    return Payment(
        external_id="pay_contract",
        reference="4c6bd984-e0aa-45df-aaf5-f932755c20d8",
        idempotency_key="payment-contract",
        amount=Decimal("299.90"),
        currency="BRL",
        status=PaymentStatus.APPROVED,
        callback_url=callback_url,
        created_at=now,
        updated_at=now,
        processed_at=now,
    )


@patch("app.webhooks.requests.post")
def test_delivery_signs_exact_canonical_payload_with_payment_identity(post, app):
    post.return_value = Mock(ok=True, status_code=204)

    with app.app_context():
        result = deliver_payment_webhook(build_payment())

    assert result == {"attempted": True, "delivered": True, "statusCode": 204}
    post.assert_called_once()
    _, kwargs = post.call_args
    body = kwargs["data"]
    payload = json.loads(body)
    assert payload["event"] == "payment.approved"
    assert payload["data"]["id"] == "pay_contract"
    assert payload["data"]["reference"] == "4c6bd984-e0aa-45df-aaf5-f932755c20d8"
    assert payload["data"]["amount"] == "299.90"
    assert payload["data"]["currency"] == "BRL"
    assert body == json.dumps(
        payload, separators=(",", ":"), sort_keys=True
    ).encode()

    expected_signature = hmac.new(
        app.config["WEBHOOK_SECRET"].encode(), body, hashlib.sha256
    ).hexdigest()
    assert kwargs["headers"] == {
        "Content-Type": "application/json",
        "X-Payment-Signature": expected_signature,
    }
    assert kwargs["timeout"] == app.config["WEBHOOK_TIMEOUT_SECONDS"]


@patch("app.webhooks.requests.post")
def test_delivery_without_callback_does_not_issue_http_request(post, app):
    with app.app_context():
        result = deliver_payment_webhook(build_payment(callback_url=None))

    assert result == {"attempted": False, "delivered": False}
    post.assert_not_called()


@patch("app.webhooks.requests.post")
def test_non_success_response_is_reported_without_rolling_back_state(post, app):
    post.return_value = Mock(ok=False, status_code=503)

    with app.app_context():
        result = deliver_payment_webhook(build_payment())

    assert result == {"attempted": True, "delivered": False, "statusCode": 503}


@patch("app.webhooks.requests.post")
def test_network_failure_is_reported_as_failed_best_effort_delivery(post, app):
    post.side_effect = requests.Timeout("gateway callback timed out")

    with app.app_context():
        result = deliver_payment_webhook(build_payment())

    assert result == {"attempted": True, "delivered": False}
