"""widen invoice numbers

Revision ID: 0008_invoice_no_length
Revises: 0007_project_invoices
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_invoice_no_length"
down_revision: str | None = "0007_project_invoices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "project_invoices",
        "invoice_no",
        existing_type=sa.String(20),
        type_=sa.String(80),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "project_invoices",
        "invoice_no",
        existing_type=sa.String(80),
        type_=sa.String(20),
        existing_nullable=False,
    )
