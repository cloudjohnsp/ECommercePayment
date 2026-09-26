from unittest.mock import patch

import pytest


def create_payment(client, key="order-123", callback_url=None):
    payload = {"amount": "299.90", "currency": "BRL", "reference": "order-123"}
    if callback_url:
        payload["callbackUrl"] = callback_url
    return client.post("/payments", json=payload, headers={"Idempotency-Key": key})


def test_create_payment_returns_pending_payment(client):
    response = create_payment(client)
    assert response.status_code == 201
    assert response.json["id"].startswith("pay_")
    assert response.json["status"] == "pending"
    assert response.json["amount"] == "299.90"


def test_create_payment_requires_idempotency_key(client):
    response = client.post("/payments", json={"amount": 10, "reference": "order"})
    assert response.status_code == 400


@pytest.mark.parametrize(
    "amount",
    ["1.001", "10000000000000000.00", "NaN", "Infinity"],
)
def test_create_payment_rejects_amount_outside_numeric_contract(client, amount):
    response = client.post(
        "/payments",
        json={"amount": amount, "currency": "BRL", "reference": "order-123"},
        headers={"Idempotency-Key": f"amount-{amount}"},
    )

    assert response.status_code == 400


def test_repeated_identical_request_returns_same_payment(client):
    first = create_payment(client)
    second = create_payment(client)
    assert second.status_code == 200
    assert second.json["id"] == first.json["id"]


def test_reusing_key_with_different_payload_returns_conflict(client):
    create_payment(client)
    response = client.post(
        "/payments",
        json={"amount": 100, "currency": "BRL", "reference": "another-order"},
        headers={"Idempotency-Key": "order-123"},
    )
    assert response.status_code == 409


def test_get_payment(client):
    created = create_payment(client).json
    response = client.get(f"/payments/{created['id']}")
    assert response.status_code == 200
    assert response.json["reference"] == "order-123"


@patch("app.routes.deliver_payment_webhook")
def test_approve_payment_is_idempotent(deliver, client):
    deliver.return_value = {"attempted": True, "delivered": True, "statusCode": 200}
    created = create_payment(client, callback_url="http://api/webhook").json
    first = client.post(f"/payments/{created['id']}/approve")
    second = client.post(f"/payments/{created['id']}/approve")
    assert first.status_code == 200
    assert first.json["status"] == "approved"
    assert second.status_code == 200
    deliver.assert_called_once()


def test_declined_payment_cannot_be_approved(client):
    created = create_payment(client).json
    client.post(f"/payments/{created['id']}/decline", json={"reason": "card_declined"})
    response = client.post(f"/payments/{created['id']}/approve")
    assert response.status_code == 409


@patch("app.routes.deliver_payment_webhook")
def test_refund_approved_payment_is_idempotent(deliver, client):
    deliver.return_value = {"attempted": True, "delivered": True, "statusCode": 200}
    created = create_payment(client, callback_url="http://api/webhook").json
    client.post(f"/payments/{created['id']}/approve")

    first = client.post(
        f"/payments/{created['id']}/refund", json={"reason": "customer_request"}
    )
    second = client.post(f"/payments/{created['id']}/refund")

    assert first.status_code == 200
    assert first.json["status"] == "refunded"
    assert first.json["refundReason"] == "customer_request"
    assert first.json["refundedAt"] is not None
    assert second.status_code == 200
    assert second.json["webhook"]["attempted"] is False
    assert deliver.call_count == 2


def test_refund_pending_payment_returns_conflict(client):
    created = create_payment(client).json

    response = client.post(f"/payments/{created['id']}/refund")

    assert response.status_code == 409


def test_refund_unknown_payment_returns_not_found(client):
    response = client.post("/payments/pay_unknown/refund")

    assert response.status_code == 404
