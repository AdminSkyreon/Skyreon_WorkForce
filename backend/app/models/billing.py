from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ProjectBilling(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_billings"
    __table_args__ = (UniqueConstraint("project_id", "year", "month", name="uq_project_billing_month"),)

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    note: Mapped[str] = mapped_column(Text, default="")
    entered_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    project: Mapped["Project"] = relationship()


class ProjectInvoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_invoices"

    invoice_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    invoice_date: Mapped[date] = mapped_column(Date)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    gst_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18.00"))
    gst_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    note: Mapped[str] = mapped_column(Text, default="")
    entered_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    project: Mapped["Project"] = relationship()


from app.models.project import Project  # noqa: E402
