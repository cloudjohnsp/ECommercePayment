from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import Payment
from .webhooks import deliver_payment_webhook

payments = Blueprint("payments", __name__)
MAX_PAYMENT_AMOUNT = Decimal("9999999999999999.99")
MAX_AMOUNT_DECIMAL_PLACES = 2


def error(message: str, status: int):
    return jsonify(error=message), status


def matches_creation_request(
    payment: Payment,
    reference: str,
    amount: Decimal,
    currency: str,
    callback_url: str | None,
) -> bool:
    return (
        payment.reference == reference
        and payment.amount == amount
        and payment.currency == currency
        and payment.callback_url == callback_url
    )


@payments.post("/payments")
def create_payment():
    payload = request.get_json(silent=True) or {}
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key:
        return error("Idempotency-Key header is required.", 400)
    if len(key) > 100:
        return error("Idempotency-Key cannot exceed 100 characters.", 400)

    try:
        amount = Decimal(str(payload.get("amount")))
    except (InvalidOperation, TypeError):
        return error("Amount must be a valid decimal.", 400)

    reference = str(payload.get("reference", "")).strip()
    currency = str(payload.get("currency", "BRL")).strip().upper()
    callback_url = payload.get("callbackUrl")
    if not amount.is_finite():
        return error("Amount must be a finite decimal.", 400)
    if amount <= 0:
        return error("Amount must be greater than zero.", 400)
    if amount.as_tuple().exponent < -MAX_AMOUNT_DECIMAL_PLACES:
        return error("Amount cannot have more than two decimal places.", 400)
    if amount > MAX_PAYMENT_AMOUNT:
        return error(f"Amount cannot exceed {MAX_PAYMENT_AMOUNT}.", 400)
    if not reference or len(reference) > 100:
        return error("Reference is required and cannot exceed 100 characters.", 400)
    if len(currency) != 3 or not currency.isalpha():
        return error("Currency must be a three-letter ISO code.", 400)
    if callback_url and not str(callback_url).lower().startswith(("http://", "https://")):
        return error("Callback URL must use HTTP or HTTPS.", 400)

    existing = db.session.execute(
        db.select(Payment).where(Payment.idempotency_key == key)
    ).scalar_one_or_none()
    if existing:
        return (jsonify(existing.to_dict()), 200) if matches_creation_request(
            existing, reference, amount, currency, callback_url
        ) else error(
            "Idempotency-Key was already used with different data.", 409
        )

    payment = Payment(
        external_id=Payment.new_external_id(),
        reference=reference,
        idempotency_key=key,
        amount=amount,
        currency=currency,
        callback_url=callback_url,
    )
    db.session.add(payment)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        concurrent = db.session.execute(
            db.select(Payment).where(Payment.idempotency_key == key)
        ).scalar_one_or_none()
        if concurrent and matches_creation_request(
            concurrent, reference, amount, currency, callback_url
        ):
            return jsonify(concurrent.to_dict()), 200
        return error("Idempotency-Key was already used.", 409)
    return jsonify(payment.to_dict()), 201


@payments.get("/payments/<external_id>")
def get_payment(external_id: str):
    payment = db.session.execute(
        db.select(Payment).where(Payment.external_id == external_id)
    ).scalar_one_or_none()
    return error("Payment not found.", 404) if payment is None else jsonify(payment.to_dict())


@payments.post("/payments/<external_id>/approve")
def approve_payment(external_id: str):
    return transition_payment(external_id, approved=True)


@payments.post("/payments/<external_id>/decline")
def decline_payment(external_id: str):
    return transition_payment(external_id, approved=False)


@payments.post("/payments/<external_id>/refund")
def refund_payment(external_id: str):
    payment = db.session.execute(
        db.select(Payment).where(Payment.external_id == external_id).with_for_update()
    ).scalar_one_or_none()
    if payment is None:
        return error("Payment not found.", 404)

    payload = request.get_json(silent=True) or {}
    reason = payload.get("reason")
    if reason is not None:
        reason = str(reason).strip() or None
    if reason and len(reason) > 500:
        return error("Refund reason cannot exceed 500 characters.", 400)

    try:
        changed = payment.refund(reason)
    except ValueError as exc:
        return error(str(exc), 409)

    if changed:
        db.session.commit()
        delivery = deliver_payment_webhook(payment)
    else:
        delivery = {"attempted": False, "delivered": False}

    response = payment.to_dict()
    response["webhook"] = delivery
    return jsonify(response)


def transition_payment(external_id: str, approved: bool):
    payment = db.session.execute(
        db.select(Payment).where(Payment.external_id == external_id).with_for_update()
    ).scalar_one_or_none()
    if payment is None:
        return error("Payment not found.", 404)

    payload = request.get_json(silent=True) or {}
    try:
        changed = payment.approve() if approved else payment.decline(payload.get("reason"))
    except ValueError as exc:
        return error(str(exc), 409)

    if changed:
        db.session.commit()
        delivery = deliver_payment_webhook(payment)
    else:
        delivery = {"attempted": False, "delivered": False}

    response = payment.to_dict()
    response["webhook"] = delivery
    return jsonify(response)
