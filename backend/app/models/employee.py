import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PayType(str, enum.Enum):
    FIXED = "fixed"
    HOURLY = "hourly"


class Engagement(str, enum.Enum):
    STAFF = "staff"
    CONTRACTOR = "contractor"


class Employee(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employees"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(80), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    designation: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(120))
    joining_date: Mapped[date] = mapped_column(Date)
    reporting_manager_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("locations.id"), nullable=True, index=True
    )
    hourly_cost_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    engagement: Mapped[Engagement] = mapped_column(
        Enum(Engagement, name="engagement", values_callable=lambda obj: [e.value for e in obj]),
        default=Engagement.STAFF,
    )
    allow_leave: Mapped[bool] = mapped_column(default=True)
    contract_monthly_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    pay_type: Mapped[PayType] = mapped_column(
        Enum(PayType, name="paytype", values_callable=lambda obj: [e.value for e in obj]),
        default=PayType.FIXED,
    )
    status: Mapped[EmployeeStatus] = mapped_column(
        Enum(EmployeeStatus, name="employeestatus", values_callable=lambda obj: [e.value for e in obj]),
        default=EmployeeStatus.ACTIVE,
    )

    user: Mapped["User"] = relationship(back_populates="employee")
    reporting_manager: Mapped["Employee | None"] = relationship(
        remote_side="Employee.id", foreign_keys=[reporting_manager_id]
    )
    location: Mapped["Location | None"] = relationship()
    payroll: Mapped["EmployeePayroll | None"] = relationship(back_populates="employee", uselist=False)


from app.models.location import Location  # noqa: E402
from app.models.payroll import EmployeePayroll  # noqa: E402
from app.models.user import User  # noqa: E402
