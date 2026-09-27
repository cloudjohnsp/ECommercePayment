"""add payment integrity constraints"""

from alembic import op

revision = "0003_add_payment_constraints"
down_revision = "0002_add_payment_refunds"
branch_labels = None
depends_on = None


def upgrade():
    op.create_check_constraint(
        "ck_payments_amount_range",
        "payments",
        "amount > 0 AND amount <= 9999999999999999.99",
    )
    op.create_check_constraint(
        "ck_payments_reference_required",
        "payments",
        "length(trim(reference)) > 0",
    )
    op.create_check_constraint(
        "ck_payments_idempotency_key_required",
        "payments",
        "length(trim(idempotency_key)) > 0",
    )
    op.create_check_constraint(
        "ck_payments_currency_format",
        "payments",
        "length(currency) = 3 AND currency = upper(currency)",
    )
    op.create_check_constraint(
        "ck_payments_external_id_format",
        "payments",
        "substr(external_id, 1, 4) = 'pay_'",
    )
    op.create_check_constraint(
        "ck_payments_status",
        "payments",
        "status IN ('PENDING', 'APPROVED', 'DECLINED', 'REFUNDED')",
    )


def downgrade():
    op.drop_constraint("ck_payments_status", "payments", type_="check")
    op.drop_constraint("ck_payments_external_id_format", "payments", type_="check")
    op.drop_constraint("ck_payments_currency_format", "payments", type_="check")
    op.drop_constraint(
        "ck_payments_idempotency_key_required", "payments", type_="check"
    )
    op.drop_constraint("ck_payments_reference_required", "payments", type_="check")
    op.drop_constraint("ck_payments_amount_range", "payments", type_="check")
