"""create payments table"""
from alembic import op
import sqlalchemy as sa

revision = "0001_create_payments"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=40), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "APPROVED", "DECLINED", name="payment_status", native_enum=False), nullable=False),
        sa.Column("callback_url", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_payments_external_id", "payments", ["external_id"])
    op.create_index("ix_payments_reference", "payments", ["reference"])


def downgrade():
    op.drop_index("ix_payments_reference", table_name="payments")
    op.drop_index("ix_payments_external_id", table_name="payments")
    op.drop_table("payments")
