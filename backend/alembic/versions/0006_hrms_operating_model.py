"""hrms operating model tables

Revision ID: 0006_hrms_operating_model
Revises: 0005_payroll_adjustments
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_hrms_operating_model"
down_revision: str | None = "0005_payroll_adjustments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN CREATE TYPE engagement AS ENUM ('staff', 'contractor'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE vendorcategory AS ENUM ('gst_filing', 'ca_audit', 'legal', 'rent_office', 'tools', 'other'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE billstatus AS ENUM ('draft', 'approved', 'paid'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE applicantstage AS ENUM ('applied', 'interview', 'offer', 'joined', 'rejected'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE attendancemark AS ENUM ('present', 'work_from', 'leave', 'absent'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE assetstatus AS ENUM ('available', 'assigned', 'returned', 'lost'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    op.create_table(
        "departments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "designations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "employees",
        sa.Column("engagement", sa.Enum("staff", "contractor", name="engagement", create_type=False), nullable=False, server_default="staff"),
    )
    op.add_column("employees", sa.Column("allow_leave", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("employees", sa.Column("contract_monthly_fee", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("reimbursements", sa.Column("paid_separately", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("reimbursements", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "project_payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("entered_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_project_payments_project_id", "project_payments", ["project_id"])

    op.create_table(
        "salary_payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_id", sa.Uuid(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("paid_date", sa.Date(), nullable=False),
        sa.Column("reference", sa.String(80), nullable=False, server_default=""),
        sa.Column("marked_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", "year", "month", name="uq_salary_payment_month"),
    )
    op.create_table(
        "contractor_payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_id", sa.Uuid(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("calculated", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("reference", sa.String(80), nullable=False, server_default=""),
        sa.Column("deduction", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("marked_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", "year", "month", name="uq_contractor_payment_month"),
    )
    op.create_table(
        "vendor_bills",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("vendor_name", sa.String(255), nullable=False),
        sa.Column("category", sa.Enum("gst_filing", "ca_audit", "legal", "rent_office", "tools", "other", name="vendorcategory", create_type=False), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("gst_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("bill_date", sa.Date(), nullable=False),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("recurring", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.Enum("draft", "approved", "paid", name="billstatus", create_type=False), nullable=False),
        sa.Column("entered_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("department", sa.String(120), nullable=False, server_default=""),
        sa.Column("location_id", sa.Uuid(), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("hiring_manager_id", sa.Uuid(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("opened_on", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "applicants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("stage", sa.Enum("applied", "interview", "offer", "joined", "rejected", name="applicantstage", create_type=False), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "document_requirements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "employee_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_id", sa.Uuid(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), sa.ForeignKey("document_requirements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provided", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", "requirement_id", name="uq_employee_document"),
    )
    op.create_table(
        "attendance_days",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("employee_id", sa.Uuid(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("mark", sa.Enum("present", "work_from", "leave", "absent", name="attendancemark", create_type=False), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", "work_date", name="uq_attendance_day"),
    )
    op.create_table(
        "review_cycles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "performance_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cycle_id", sa.Uuid(), sa.ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.Uuid(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("manager_id", sa.Uuid(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("cycle_id", "employee_id", name="uq_review_cycle_employee"),
    )
    op.create_table(
        "company_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("asset_tag", sa.String(80), nullable=False, unique=True),
        sa.Column("category", sa.String(40), nullable=False, server_default="laptop"),
        sa.Column("status", sa.Enum("available", "assigned", "returned", "lost", name="assetstatus", create_type=False), nullable=False),
        sa.Column("assigned_to_id", sa.Uuid(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "company_assets",
        "performance_reviews",
        "review_cycles",
        "attendance_days",
        "employee_documents",
        "document_requirements",
        "applicants",
        "jobs",
        "vendor_bills",
        "contractor_payments",
        "salary_payments",
        "project_payments",
        "designations",
        "departments",
    ]:
        op.drop_table(table)
    op.drop_column("reimbursements", "paid_at")
    op.drop_column("reimbursements", "paid_separately")
    op.drop_column("employees", "contract_monthly_fee")
    op.drop_column("employees", "allow_leave")
    op.drop_column("employees", "engagement")
