import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

COMP_OFF_CODE = "CO"


class ExtraWorkKind(str, enum.Enum):
    WEEKEND = "weekend"
    HOLIDAY = "holiday"


class ExtraWorkStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExtraWorkSettlement(str, enum.Enum):
    COMP_OFF = "comp_off"
    EXTRA_PAY = "extra_pay"


class ExtraWorkDay(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "extra_work_days"
    __table_args__ = (UniqueConstraint("employee_id", "work_date", name="uq_extra_work_day"),)

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    work_date: Mapped[date] = mapped_column(Date)
    hours: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    kind: Mapped[ExtraWorkKind] = mapped_column(
        Enum(ExtraWorkKind, name="extraworkkind", values_callable=lambda obj: [e.value for e in obj])
    )
    timesheet_week_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("timesheet_weeks.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ExtraWorkStatus] = mapped_column(
        Enum(ExtraWorkStatus, name="extraworkstatus", values_callable=lambda obj: [e.value for e in obj]),
        default=ExtraWorkStatus.PENDING,
    )
    settlement: Mapped[ExtraWorkSettlement | None] = mapped_column(
        Enum(ExtraWorkSettlement, name="extraworksettlement", values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
    )
    comp_off_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"))
    extra_pay_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    payroll_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payroll_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewer_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")

    employee: Mapped["Employee"] = relationship(foreign_keys=[employee_id])


class LeaveCredit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leave_credits"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    leave_type_id: Mapped[UUID] = mapped_column(ForeignKey("leave_types.id", ondelete="CASCADE"), index=True)
    days: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    extra_work_day_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("extra_work_days.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    note: Mapped[str] = mapped_column(Text, default="")


from app.models.employee import Employee  # noqa: E402
