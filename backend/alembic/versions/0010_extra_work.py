"""extra work and comp-off credits

Revision ID: 0010_extra_work
Revises: 0009_employee_contact
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_extra_work"
down_revision: str | None = "0009_employee_contact"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN CREATE TYPE extraworkkind AS ENUM ('weekend', 'holiday'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE extraworkstatus AS ENUM ('pending', 'approved', 'rejected'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE extraworksettlement AS ENUM ('comp_off', 'extra_pay'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.create_table(
        "extra_work_days",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("hours", sa.Numeric(6, 2), nullable=False),
        sa.Column("kind", sa.Enum("weekend", "holiday", name="extraworkkind", create_type=False), nullable=False),
        sa.Column("timesheet_week_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "rejected", name="extraworkstatus", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "settlement",
            sa.Enum("comp_off", "extra_pay", name="extraworksettlement", create_type=False),
            nullable=True,
        ),
        sa.Column("comp_off_days", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("extra_pay_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("payroll_year", sa.Integer(), nullable=True),
        sa.Column("payroll_month", sa.Integer(), nullable=True),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["timesheet_week_id"], ["timesheet_weeks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "work_date", name="uq_extra_work_day"),
    )
    op.create_index("ix_extra_work_days_employee_id", "extra_work_days", ["employee_id"])
    op.create_table(
        "leave_credits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("leave_type_id", sa.Uuid(), nullable=False),
        sa.Column("days", sa.Numeric(6, 2), nullable=False),
        sa.Column("extra_work_day_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["leave_type_id"], ["leave_types.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extra_work_day_id"], ["extra_work_days.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("extra_work_day_id"),
    )
    op.create_index("ix_leave_credits_employee_id", "leave_credits", ["employee_id"])
    op.add_column(
        "payroll_adjustments",
        sa.Column("extra_work_pay", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("payroll_adjustments", "extra_work_pay")
    op.drop_table("leave_credits")
    op.drop_table("extra_work_days")
    op.execute("DROP TYPE IF EXISTS extraworksettlement")
    op.execute("DROP TYPE IF EXISTS extraworkstatus")
    op.execute("DROP TYPE IF EXISTS extraworkkind")
