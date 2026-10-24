"""project invoices and payment link

Revision ID: 0007_project_invoices
Revises: 0006_hrms_operating_model
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_project_invoices"
down_revision: str | None = "0006_hrms_operating_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_invoices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("invoice_no", sa.String(20), nullable=False, unique=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("entered_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_project_invoices_project_id", "project_invoices", ["project_id"])
    op.create_index("ix_project_invoices_invoice_no", "project_invoices", ["invoice_no"], unique=True)

    op.add_column("project_payments", sa.Column("invoice_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_project_payments_invoice_id",
        "project_payments",
        "project_invoices",
        ["invoice_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_project_payments_invoice_id", "project_payments", ["invoice_id"])

    op.execute(
        """
        INSERT INTO project_invoices (id, invoice_no, project_id, invoice_date, year, month, amount, note, entered_by_id, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            'INV-' || LPAD((ROW_NUMBER() OVER (ORDER BY year, month, project_id))::text, 4, '0'),
            project_id,
            make_date(year, month, 1),
            year,
            month,
            amount,
            note,
            entered_by_id,
            NOW(),
            NOW()
        FROM project_billings
        WHERE amount > 0
        """
    )
    op.execute(
        """
        UPDATE project_payments p
        SET invoice_id = i.id
        FROM project_invoices i
        WHERE p.invoice_id IS NULL
          AND p.project_id = i.project_id
          AND p.year = i.year
          AND p.month = i.month
        """
    )


def downgrade() -> None:
    op.drop_index("ix_project_payments_invoice_id", table_name="project_payments")
    op.drop_constraint("fk_project_payments_invoice_id", "project_payments", type_="foreignkey")
    op.drop_column("project_payments", "invoice_id")
    op.drop_index("ix_project_invoices_invoice_no", table_name="project_invoices")
    op.drop_index("ix_project_invoices_project_id", table_name="project_invoices")
    op.drop_table("project_invoices")
