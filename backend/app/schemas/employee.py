from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator, model_validator

from app.models.employee import EmployeeStatus, Engagement, PayType
from app.schemas.common import ORMModel

Name255 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Label120 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Phone80 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]


class EmployeeCreate(BaseModel):
    name: Name255
    phone: Phone80 = ""
    address: str = ""
    email: EmailStr
    employee_code: str | None = Field(default=None, max_length=50)
    designation: Label120
    department: Label120
    joining_date: date
    reporting_manager_id: UUID | None = None
    location_id: UUID | None = None
    hourly_cost_rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    monthly_salary: Decimal = Field(default=Decimal("0.00"), ge=0)
    hourly_pay_rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    pay_type: PayType = PayType.FIXED
    engagement: Engagement = Engagement.STAFF
    allow_leave: bool = True
    contract_monthly_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    temporary_password: str = Field(min_length=8)

    @field_validator("temporary_password")
    @classmethod
    def check_temp_password(cls, value: str) -> str:
        if len(value.strip()) < 8:
            raise ValueError("Temporary password must contain at least 8 non-space characters")
        return value


class EmployeeUpdate(BaseModel):
    name: Name255 | None = None
    phone: Phone80 | None = None
    address: str | None = None
    designation: Label120 | None = None
    department: Label120 | None = None
    joining_date: date | None = None
    reporting_manager_id: UUID | None = None
    location_id: UUID | None = None
    hourly_cost_rate: Decimal | None = Field(default=None, ge=0)
    monthly_salary: Decimal | None = Field(default=None, ge=0)
    hourly_pay_rate: Decimal | None = Field(default=None, ge=0)
    pay_type: PayType | None = None
    engagement: Engagement | None = None
    allow_leave: bool | None = None
    contract_monthly_fee: Decimal | None = Field(default=None, ge=0)
    status: EmployeeStatus | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "EmployeeUpdate":
        for field in (
            "name",
            "phone",
            "address",
            "designation",
            "department",
            "joining_date",
            "hourly_cost_rate",
            "monthly_salary",
            "hourly_pay_rate",
            "pay_type",
            "engagement",
            "allow_leave",
            "contract_monthly_fee",
            "status",
        ):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ResetPasswordRequest(BaseModel):
    temporary_password: str = Field(min_length=8)

    @field_validator("temporary_password")
    @classmethod
    def check_temp_password(cls, value: str) -> str:
        if len(value.strip()) < 8:
            raise ValueError("Temporary password must contain at least 8 non-space characters")
        return value


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
