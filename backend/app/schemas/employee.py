from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.employee import EmployeeStatus, Engagement, PayType
from app.schemas.common import ORMModel


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(default="", max_length=80)
    address: str = ""
    email: EmailStr
    employee_code: str | None = Field(default=None, max_length=50)
    designation: str
    department: str
    joining_date: date
    reporting_manager_id: UUID | None = None
    location_id: UUID | None = None
    hourly_cost_rate: Decimal = Decimal("0.00")
    monthly_salary: Decimal = Field(default=Decimal("0.00"), ge=0)
    hourly_pay_rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    pay_type: PayType = PayType.FIXED
    engagement: Engagement = Engagement.STAFF
    allow_leave: bool = True
    contract_monthly_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    temporary_password: str = Field(min_length=8)


class EmployeeUpdate(BaseModel):
    name: str | None = None
    phone: str | None = Field(default=None, max_length=80)
    address: str | None = None
    designation: str | None = None
    department: str | None = None
    joining_date: date | None = None
    reporting_manager_id: UUID | None = None
    location_id: UUID | None = None
    hourly_cost_rate: Decimal | None = None
    monthly_salary: Decimal | None = Field(default=None, ge=0)
    hourly_pay_rate: Decimal | None = Field(default=None, ge=0)
    pay_type: PayType | None = None
    engagement: Engagement | None = None
    allow_leave: bool | None = None
    contract_monthly_fee: Decimal | None = Field(default=None, ge=0)
    status: EmployeeStatus | None = None


class ResetPasswordRequest(BaseModel):
    temporary_password: str = Field(min_length=8)


class EmployeeOut(ORMModel):
    id: UUID
    user_id: UUID
    name: str
    phone: str = ""
    address: str = ""
    email: str
    employee_code: str
    reporting_manager_name: str | None = None
    designation: str
    department: str
    joining_date: date
    reporting_manager_id: UUID | None
    location_id: UUID | None = None
    location_name: str | None = None
    hourly_cost_rate: Decimal
    monthly_salary: Decimal = Decimal("0.00")
    hourly_pay_rate: Decimal = Decimal("0.00")
    pay_type: PayType = PayType.FIXED
    engagement: Engagement = Engagement.STAFF
    allow_leave: bool = True
    contract_monthly_fee: Decimal = Decimal("0.00")
    status: EmployeeStatus
    is_active_user: bool
