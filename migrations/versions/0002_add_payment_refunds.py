"""add payment refunds"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_payment_refunds"
down_revision = "0001_create_payments"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payments", sa.Column("refund_reason", sa.String(length=500), nullable=True))
    op.add_column(
        "payments", sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("payments", "refunded_at")
    op.drop_column("payments", "refund_reason")
