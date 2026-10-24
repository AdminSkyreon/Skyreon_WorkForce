"""invoice GST breakdown

Revision ID: 0012_invoice_gst
Revises: 0011_leave_type_accrual
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_invoice_gst"
down_revision: str | None = "0011_leave_type_accrual"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "project_invoices",
        sa.Column("taxable_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "project_invoices",
        sa.Column("gst_percent", sa.Numeric(5, 2), nullable=False, server_default="18"),
    )
    op.add_column(
        "project_invoices",
        sa.Column("gst_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
    )
    op.execute(
        "UPDATE project_invoices SET taxable_amount = amount, gst_amount = 0, gst_percent = 18 WHERE taxable_amount = 0"
    )


def downgrade() -> None:
    op.drop_column("project_invoices", "gst_amount")
    op.drop_column("project_invoices", "gst_percent")
    op.drop_column("project_invoices", "taxable_amount")
