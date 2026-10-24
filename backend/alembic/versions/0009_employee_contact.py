"""employee phone and address

Revision ID: 0009_employee_contact
Revises: 0008_invoice_no_length
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_employee_contact"
down_revision: str | None = "0008_invoice_no_length"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("phone", sa.String(80), nullable=False, server_default=""))
    op.add_column("employees", sa.Column("address", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("employees", "address")
    op.drop_column("employees", "phone")
