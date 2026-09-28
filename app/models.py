import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .extensions import db


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    REFUNDED = "refunded"


class Payment(db.Model):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "amount > 0 AND amount <= 9999999999999999.99",
            name="ck_payments_amount_range",
        ),
        CheckConstraint(
            "length(trim(reference)) > 0",
            name="ck_payments_reference_required",
        ),
        CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="ck_payments_idempotency_key_required",
        ),
        CheckConstraint(
            "length(currency) = 3 AND currency = upper(currency)",
            name="ck_payments_currency_format",
        ),
        CheckConstraint(
            "substr(external_id, 1, 4) = 'pay_'",
            name="ck_payments_external_id_format",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'DECLINED', 'REFUNDED')",
            name="ck_payments_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    reference: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=False),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    callback_url: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    refund_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @staticmethod
    def new_external_id() -> str:
        return f"pay_{uuid.uuid4().hex}"

    def approve(self) -> bool:
        if self.status == PaymentStatus.APPROVED:
            return False
        if self.status == PaymentStatus.DECLINED:
            raise ValueError("A declined payment cannot be approved.")
        if self.status == PaymentStatus.REFUNDED:
            raise ValueError("A refunded payment cannot be approved.")
        self.status = PaymentStatus.APPROVED
        self.processed_at = datetime.now(timezone.utc)
        return True

    def decline(self, reason: str | None = None) -> bool:
        if self.status == PaymentStatus.DECLINED:
            return False
        if self.status == PaymentStatus.APPROVED:
            raise ValueError("An approved payment cannot be declined.")
        if self.status == PaymentStatus.REFUNDED:
            raise ValueError("A refunded payment cannot be declined.")
        self.status = PaymentStatus.DECLINED
        self.failure_reason = reason
        self.processed_at = datetime.now(timezone.utc)
        return True

    def refund(self, reason: str | None = None) -> bool:
        if self.status == PaymentStatus.REFUNDED:
            return False
        if self.status != PaymentStatus.APPROVED:
            raise ValueError("Only an approved payment can be refunded.")
        self.status = PaymentStatus.REFUNDED
        self.refund_reason = reason
        self.refunded_at = datetime.now(timezone.utc)
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.external_id,
            "reference": self.reference,
            "amount": str(self.amount),
            "currency": self.currency,
            "status": self.status.value,
            "failureReason": self.failure_reason,
            "refundReason": self.refund_reason,
            "createdAt": self.created_at.isoformat(),
            "processedAt": self.processed_at.isoformat() if self.processed_at else None,
            "refundedAt": self.refunded_at.isoformat() if self.refunded_at else None,
        }
