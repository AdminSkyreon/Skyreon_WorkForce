"""monthly bonus adjustments

Revision ID: 0005_payroll_adjustments
Revises: 0004_operating_model
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_payroll_adjustments"
down_revision: str | None = "0004_operating_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payroll_adjustments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_id", sa.Uuid(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("bonus", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", "year", "month", name="uq_payroll_adjustment_month"),
    )
    op.create_index("ix_payroll_adjustments_employee_id", "payroll_adjustments", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_payroll_adjustments_employee_id", table_name="payroll_adjustments")
    op.drop_table("payroll_adjustments")
