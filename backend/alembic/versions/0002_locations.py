"""locations, employee location, holidays by location

Revision ID: 0002_locations
Revises: 0001_initial
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_locations"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("city", sa.String(120), nullable=False, server_default=""),
        sa.Column("country", sa.String(120), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_locations_code", "locations", ["code"], unique=True)

    op.add_column("employees", sa.Column("location_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_employees_location_id", "employees", "locations", ["location_id"], ["id"])
    op.create_index("ix_employees_location_id", "employees", ["location_id"])

    op.add_column("holidays", sa.Column("location_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_holidays_location_id", "holidays", "locations", ["location_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_holidays_location_id", "holidays", ["location_id"])
    op.drop_constraint("uq_holiday_date", "holidays", type_="unique")
    op.execute(
        "CREATE UNIQUE INDEX uq_holiday_company_date ON holidays (date) WHERE location_id IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_holiday_location_date ON holidays (location_id, date) WHERE location_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_holiday_location_date")
    op.execute("DROP INDEX IF EXISTS uq_holiday_company_date")
    op.create_unique_constraint("uq_holiday_date", "holidays", ["date"])
    op.drop_index("ix_holidays_location_id", table_name="holidays")
    op.drop_constraint("fk_holidays_location_id", "holidays", type_="foreignkey")
    op.drop_column("holidays", "location_id")
    op.drop_index("ix_employees_location_id", table_name="employees")
    op.drop_constraint("fk_employees_location_id", "employees", type_="foreignkey")
    op.drop_column("employees", "location_id")
    op.drop_index("ix_locations_code", table_name="locations")
    op.drop_table("locations")
