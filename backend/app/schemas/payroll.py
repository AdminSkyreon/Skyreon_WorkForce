from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class PayrollDetailsIn(BaseModel):
    currency: str = Field(default="INR", min_length=1, max_length=8)
    basic_salary: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("9999999999.99"))
    hra: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("9999999999.99"))
    allowances: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("9999999999.99"))
    tax_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    pf_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    hourly_pay_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("9999999999.99"))
    professional_tax: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("9999999999.99"))
    other_deductions: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("9999999999.99"))
    bonus: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("9999999999.99"))


class PayrollDetailsOut(ORMModel):
    employee_id: UUID
    employee_name: str | None = None
    currency: str
    basic_salary: Decimal
    hra: Decimal
    allowances: Decimal
    hourly_pay_rate: Decimal = Decimal("0.00")
    tax_percent: Decimal
    pf_percent: Decimal
    professional_tax: Decimal
    other_deductions: Decimal
    bonus: Decimal = Decimal("0.00")
    reimbursements: Decimal = Decimal("0.00")


class PayrollLine(BaseModel):
    employee_id: UUID
    name: str
    employee_code: str
    location_name: str | None = None
    department: str
    currency: str = "INR"
    pay_type: str = "fixed"
    hourly_rate: Decimal
    hours: Decimal
    leave_days: Decimal
    lwp_days: Decimal = Decimal("0.00")
    basic_salary: Decimal = Decimal("0.00")
    hra: Decimal = Decimal("0.00")
    allowances: Decimal = Decimal("0.00")
    time_pay: Decimal = Decimal("0.00")
    paid_leave_pay: Decimal = Decimal("0.00")
    reimbursements: Decimal = Decimal("0.00")
    bonus: Decimal = Decimal("0.00")
    extra_work_pay: Decimal = Decimal("0.00")
    lwp_amount: Decimal = Decimal("0.00")
    tax_percent: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    pf_amount: Decimal = Decimal("0.00")
    professional_tax: Decimal = Decimal("0.00")
    other_deductions: Decimal = Decimal("0.00")
    gross_pay: Decimal
    total_deductions: Decimal = Decimal("0.00")
    net_pay: Decimal
    has_details: bool = False


class PayrollRegister(BaseModel):
    year: int
    month: int
    period_label: str
    location_name: str | None = None
    lines: list[PayrollLine]
    total_hours: Decimal
    total_leave_days: Decimal
    total_gross: Decimal
    total_tax: Decimal
    total_pay: Decimal
    closed: bool = False
