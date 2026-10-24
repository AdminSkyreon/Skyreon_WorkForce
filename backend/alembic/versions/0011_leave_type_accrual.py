"""leave type monthly accrual

Revision ID: 0011_leave_type_accrual
Revises: 0010_extra_work
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_leave_type_accrual"
down_revision: str | None = "0010_extra_work"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN CREATE TYPE leaveaccrualmode AS ENUM ('lump', 'monthly'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.add_column(
        "leave_types",
        sa.Column(
            "accrual_mode",
            sa.Enum("lump", "monthly", name="leaveaccrualmode", create_type=False),
            nullable=False,
            server_default="lump",
        ),
    )
    op.add_column(
        "leave_types",
        sa.Column("days_per_month", sa.Numeric(4, 2), nullable=False, server_default="0"),
    )
    # CL/SL/EL: 1 day per calendar month, capped by existing annual_allocation_days
    op.execute(
        """
        UPDATE leave_types
        SET accrual_mode = 'monthly', days_per_month = 1
        WHERE code IN ('CL', 'SL', 'EL')
        """
    )
    op.execute(
        """
        UPDATE leave_types
        SET accrual_mode = 'lump', days_per_month = 0
        WHERE code IN ('LWP', 'CO')
        """
    )


def downgrade() -> None:
    op.drop_column("leave_types", "days_per_month")
    op.drop_column("leave_types", "accrual_mode")
    op.execute("DROP TYPE IF EXISTS leaveaccrualmode")
