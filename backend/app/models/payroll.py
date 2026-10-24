import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PayrollPeriodStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class EmployeePayroll(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employee_payroll"

    employee_id: Mapped[UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), unique=True, index=True
    )
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    hra: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    allowances: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    hourly_pay_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    pf_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    professional_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    employee: Mapped["Employee"] = relationship(back_populates="payroll")


class PayrollAdjustment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payroll_adjustments"
    __table_args__ = (UniqueConstraint("employee_id", "year", "month", name="uq_payroll_adjustment_month"),)

    employee_id: Mapped[UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    bonus: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    extra_work_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))


class PayrollPeriod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payroll_periods"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_payroll_period"),)

    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    status: Mapped[PayrollPeriodStatus] = mapped_column(
        Enum(PayrollPeriodStatus, name="payrollperiodstatus", values_callable=lambda obj: [e.value for e in obj]),
        default=PayrollPeriodStatus.OPEN,
    )
    closed_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot_json: Mapped[str] = mapped_column(Text, default="")


from app.models.employee import Employee  # noqa: E402
