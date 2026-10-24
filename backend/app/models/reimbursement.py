import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ReimbursementStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Reimbursement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reimbursements"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    category: Mapped[str] = mapped_column(String(40), default="other")
    spend_date: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[ReimbursementStatus] = mapped_column(
        Enum(ReimbursementStatus, name="reimbursementstatus", values_callable=lambda obj: [e.value for e in obj]),
        default=ReimbursementStatus.SUBMITTED,
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    payroll_year: Mapped[int | None] = mapped_column(nullable=True)
    payroll_month: Mapped[int | None] = mapped_column(nullable=True)
    paid_separately: Mapped[bool] = mapped_column(default=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped["Employee"] = relationship(foreign_keys=[employee_id])
    reviewer: Mapped["Employee | None"] = relationship(foreign_keys=[reviewer_id])


from app.models.employee import Employee  # noqa: E402
