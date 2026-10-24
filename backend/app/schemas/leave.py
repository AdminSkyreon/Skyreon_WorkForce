from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.leave import LeaveAccrualMode, LeaveStatus
from app.schemas.common import ORMModel


class LeaveTypeCreate(BaseModel):
    name: str
    code: str = Field(min_length=1, max_length=20)
    annual_allocation_days: int = Field(ge=0)
    is_unpaid: bool = False
    accrual_mode: LeaveAccrualMode = LeaveAccrualMode.LUMP
    days_per_month: Decimal = Field(default=Decimal("0.00"), ge=0)

    @model_validator(mode="after")
    def default_monthly_for_paid(self) -> "LeaveTypeCreate":
        if (
            not self.is_unpaid
            and self.annual_allocation_days > 0
            and self.accrual_mode == LeaveAccrualMode.LUMP
            and self.days_per_month == 0
        ):
            self.accrual_mode = LeaveAccrualMode.MONTHLY
            self.days_per_month = Decimal("1.00")
        return self


class LeaveTypeUpdate(BaseModel):
    name: str | None = None
    annual_allocation_days: int | None = Field(default=None, ge=0)
    is_unpaid: bool | None = None
    accrual_mode: LeaveAccrualMode | None = None
    days_per_month: Decimal | None = Field(default=None, ge=0)


class LeaveTypeOut(ORMModel):
    id: UUID
    name: str
    code: str
    annual_allocation_days: int
    is_unpaid: bool = False
    accrual_mode: LeaveAccrualMode = LeaveAccrualMode.LUMP
    days_per_month: Decimal = Decimal("0.00")


class LeaveCreate(BaseModel):
    leave_type_id: UUID
    start_date: date
    end_date: date
    is_half_day: bool = False
    reason: str = ""


class AdminLeaveCreate(LeaveCreate):
    employee_id: UUID
    approve: bool = True


class LeaveReviewRequest(BaseModel):
    comment: str = ""


class LeaveBalanceOut(BaseModel):
    leave_type_id: UUID
    leave_type_name: str
    allocated: Decimal
    used: Decimal
    pending: Decimal
    available: Decimal


class LeaveRequestOut(ORMModel):
    id: UUID
    employee_id: UUID
    employee_name: str | None = None
    leave_type_id: UUID
    leave_type_name: str | None = None
    start_date: date
    end_date: date
    is_half_day: bool
    days: Decimal
    reason: str
    status: LeaveStatus
    reviewer_id: UUID | None
    comment: str
