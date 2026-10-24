"""employee payroll details

Revision ID: 0003_payroll_details
Revises: 0002_locations
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_payroll_details"
down_revision: str | None = "0002_locations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "employee_payroll",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "employee_id",
            sa.Uuid(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("currency", sa.String(8), nullable=False, server_default="INR"),
        sa.Column("basic_salary", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("hra", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("allowances", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("pf_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("professional_tax", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("other_deductions", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_employee_payroll_employee_id", "employee_payroll", ["employee_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_employee_payroll_employee_id", table_name="employee_payroll")
    op.drop_table("employee_payroll")
