from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Payment, PaymentStatus


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
    ("field", "value"),
    [
        ("reference", None),
        ("currency", "BŔL"),
        ("callbackUrl", "http://"),
        ("callbackUrl", 123),
    ],
)
def test_create_payment_rejects_malformed_identity_and_callback_fields(
    client, field, value
):
    payload = {
        "amount": "299.90",
        "currency": "BRL",
        "reference": "order-123",
        field: value,
    }

    response = client.post(
        "/payments",
        json=payload,
        headers={"Idempotency-Key": f"invalid-{field}-{value}"},
    )

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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("amount", Decimal("0")),
        ("reference", "   "),
        ("idempotency_key", "   "),
        ("currency", "brl"),
        ("external_id", "invalid"),
        ("status", "INVALID"),
    ],
)
def test_database_constraints_reject_invalid_payment_state(app, field, value):
    now = datetime.now(timezone.utc)
    payment = Payment(
        external_id=Payment.new_external_id(),
        reference="order-database-constraint",
        idempotency_key=f"database-constraint-{field}",
        amount=Decimal("10.00"),
        currency="BRL",
        status=PaymentStatus.PENDING,
        callback_url=None,
        created_at=now,
        updated_at=now,
    )
    setattr(payment, field, value)

    with app.app_context():
        db.session.add(payment)

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()


def test_repeated_identical_request_returns_same_payment(client):
    first = create_payment(client)
    second = create_payment(client)
    assert second.status_code == 200
    assert second.json["id"] == first.json["id"]


def test_concurrent_identical_idempotency_key_returns_existing_payment(client):
    now = datetime.now(timezone.utc)
    existing = Payment(
        external_id="pay_concurrent",
        reference="order-123",
        idempotency_key="order-123",
        amount=Decimal("299.90"),
        currency="BRL",
        status=PaymentStatus.PENDING,
        callback_url=None,
        created_at=now,
        updated_at=now,
    )
    missing_result = Mock()
    missing_result.scalar_one_or_none.return_value = None
    concurrent_result = Mock()
    concurrent_result.scalar_one_or_none.return_value = existing
    fake_db = Mock()
    fake_db.session.execute.side_effect = [missing_result, concurrent_result]
    fake_db.session.commit.side_effect = IntegrityError(
        "insert payment", {}, Exception("unique violation")
    )

    with patch("app.routes.db", fake_db):
        response = create_payment(client)

    assert response.status_code == 200
    assert response.json["id"] == "pay_concurrent"
    fake_db.session.rollback.assert_called_once_with()


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


@pytest.mark.parametrize("reason", ["x" * 501, {"unexpected": "object"}])
def test_decline_rejects_invalid_reason_without_changing_payment(client, reason):
    created = create_payment(client).json

    response = client.post(
        f"/payments/{created['id']}/decline", json={"reason": reason}
    )

    assert response.status_code == 400
    persisted = client.get(f"/payments/{created['id']}")
    assert persisted.json["status"] == "pending"


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


@pytest.mark.parametrize("reason", ["x" * 501, ["unexpected", "array"]])
def test_refund_rejects_invalid_reason_without_changing_payment(client, reason):
    created = create_payment(client).json
    client.post(f"/payments/{created['id']}/approve")

    response = client.post(
        f"/payments/{created['id']}/refund", json={"reason": reason}
    )

    assert response.status_code == 400
    persisted = client.get(f"/payments/{created['id']}")
    assert persisted.json["status"] == "approved"


def test_refund_unknown_payment_returns_not_found(client):
    response = client.post("/payments/pay_unknown/refund")

    assert response.status_code == 404
