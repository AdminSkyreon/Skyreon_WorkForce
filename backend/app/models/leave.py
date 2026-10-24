import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LeaveAccrualMode(str, enum.Enum):
    LUMP = "lump"
    MONTHLY = "monthly"


class LeaveType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leave_types"

    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    annual_allocation_days: Mapped[int] = mapped_column(Integer, default=0)
    is_unpaid: Mapped[bool] = mapped_column(default=False)
    accrual_mode: Mapped[LeaveAccrualMode] = mapped_column(
        Enum(LeaveAccrualMode, name="leaveaccrualmode", values_callable=lambda obj: [e.value for e in obj]),
        default=LeaveAccrualMode.LUMP,
    )
    days_per_month: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.00"))


class LeaveRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leave_requests"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    leave_type_id: Mapped[UUID] = mapped_column(ForeignKey("leave_types.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_half_day: Mapped[bool] = mapped_column(default=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[LeaveStatus] = mapped_column(
        Enum(LeaveStatus, name="leavestatus", values_callable=lambda obj: [e.value for e in obj]),
        default=LeaveStatus.PENDING,
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")

    employee: Mapped["Employee"] = relationship(foreign_keys=[employee_id])
    leave_type: Mapped[LeaveType] = relationship()
    reviewer: Mapped["Employee | None"] = relationship(foreign_keys=[reviewer_id])


from app.models.employee import Employee  # noqa: E402
