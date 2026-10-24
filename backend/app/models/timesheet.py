import enum
from datetime import date
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TimesheetStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class TimesheetWeek(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "timesheet_weeks"
    __table_args__ = (UniqueConstraint("employee_id", "week_start", name="uq_timesheet_week"),)

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[TimesheetStatus] = mapped_column(
        Enum(TimesheetStatus, name="timesheetstatus", values_callable=lambda obj: [e.value for e in obj]),
        default=TimesheetStatus.DRAFT,
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")

    employee: Mapped["Employee"] = relationship(foreign_keys=[employee_id])
    reviewer: Mapped["Employee | None"] = relationship(foreign_keys=[reviewer_id])


from app.models.employee import Employee  # noqa: E402
