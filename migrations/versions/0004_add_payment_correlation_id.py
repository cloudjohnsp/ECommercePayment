"""add payment correlation id

Revision ID: 0004_add_payment_correlation_id
Revises: 0003_add_payment_constraints
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_add_payment_correlation_id"
down_revision = "0003_add_payment_constraints"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "payments",
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
    )
    op.execute("UPDATE payments SET correlation_id = replace(external_id, 'pay_', '')")
    op.alter_column("payments", "correlation_id", nullable=False)


def downgrade():
    op.drop_column("payments", "correlation_id")
