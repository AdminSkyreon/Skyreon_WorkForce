"""operating model: roles, pay, claims, billing, audit

Revision ID: 0004_operating_model
Revises: 0003_payroll_details
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_operating_model"
down_revision: str | None = "0003_payroll_details"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'super_admin'")
    op.execute("DO $$ BEGIN CREATE TYPE paytype AS ENUM ('fixed', 'hourly'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute(
        "DO $$ BEGIN CREATE TYPE reimbursementstatus AS ENUM ('submitted', 'approved', 'rejected', 'cancelled'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE payrollperiodstatus AS ENUM ('open', 'closed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    op.add_column(
        "employees",
        sa.Column("pay_type", sa.Enum("fixed", "hourly", name="paytype", create_type=False), nullable=False, server_default="fixed"),
    )
    op.add_column(
        "employee_payroll",
        sa.Column("hourly_pay_rate", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "leave_types",
        sa.Column("is_unpaid", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "reimbursements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_id", sa.Uuid(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("category", sa.String(40), nullable=False, server_default="other"),
        sa.Column("spend_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "status",
            sa.Enum("submitted", "approved", "rejected", "cancelled", name="reimbursementstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("reviewer_id", sa.Uuid(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("payroll_year", sa.Integer(), nullable=True),
        sa.Column("payroll_month", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reimbursements_employee_id", "reimbursements", ["employee_id"])
    op.create_index("ix_reimbursements_project_id", "reimbursements", ["project_id"])

    op.create_table(
        "project_billings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("entered_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", "year", "month", name="uq_project_billing_month"),
    )
    op.create_index("ix_project_billings_project_id", "project_billings", ["project_id"])

    op.create_table(
        "payroll_periods",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "closed", name="payrollperiodstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("closed_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_json", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("year", "month", name="uq_payroll_period"),
    )

    op.create_table(
        "company_profile",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("legal_name", sa.String(255), nullable=False, server_default="Skyreon"),
        sa.Column("address", sa.Text(), nullable=False, server_default=""),
        sa.Column("phone", sa.String(80), nullable=False, server_default=""),
        sa.Column("website", sa.String(255), nullable=False, server_default="https://www.skyreon.com"),
        sa.Column("signatory_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("signatory_title", sa.String(120), nullable=False, server_default=""),
        sa.Column("signature_image", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=False, server_default=""),
        sa.Column("actor_role", sa.String(40), nullable=False, server_default=""),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("summary", sa.String(500), nullable=False, server_default=""),
        sa.Column("before_json", sa.Text(), nullable=False, server_default=""),
        sa.Column("after_json", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("company_profile")
    op.drop_table("payroll_periods")
    op.drop_index("ix_project_billings_project_id", table_name="project_billings")
    op.drop_table("project_billings")
    op.drop_index("ix_reimbursements_project_id", table_name="reimbursements")
    op.drop_index("ix_reimbursements_employee_id", table_name="reimbursements")
    op.drop_table("reimbursements")
    op.drop_column("leave_types", "is_unpaid")
    op.drop_column("employee_payroll", "hourly_pay_rate")
    op.drop_column("employees", "pay_type")
    op.execute("DROP TYPE IF EXISTS payrollperiodstatus")
    op.execute("DROP TYPE IF EXISTS reimbursementstatus")
    op.execute("DROP TYPE IF EXISTS paytype")
