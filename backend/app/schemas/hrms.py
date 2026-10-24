from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.hrms import ApplicantStage, AssetStatus, AttendanceMark, BillStatus, VendorCategory
from app.schemas.common import ORMModel


class PaymentIn(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    amount: Decimal = Field(ge=0)
    received_date: date
    note: str = ""


class ProjectPaymentOut(ORMModel):
    id: UUID
    project_id: UUID
    project_name: str | None = None
    year: int
    month: int
    amount: Decimal
    received_date: date
    note: str


class SalaryPayIn(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    paid_date: date
    reference: str = ""
    amount: Decimal | None = None


class SalaryPaymentOut(ORMModel):
    id: UUID
    employee_id: UUID
    employee_name: str | None = None
    year: int
    month: int
    amount: Decimal
    paid_date: date
    reference: str
    paid: bool = True


class ContractorLine(ORMModel):
    employee_id: UUID
    name: str
    employee_code: str
    department: str
    pay_type: str
    hours: Decimal
    calculated: Decimal
    amount: Decimal
    deduction: Decimal
    paid: bool
    paid_date: date | None = None
    reference: str = ""


class ContractorRegister(ORMModel):
    year: int
    month: int
    period_label: str
    lines: list[ContractorLine]
    total_calculated: Decimal
    total_paid: Decimal


class ContractorPayIn(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    amount: Decimal | None = None
    paid_date: date
    reference: str = ""
    deduction: Decimal = Decimal("0.00")


class VendorBillIn(BaseModel):
    vendor_name: str = Field(min_length=1, max_length=255)
    category: VendorCategory
    amount: Decimal = Field(gt=0)
    gst_percent: Decimal | None = Field(default=None, ge=0, le=100)
    gst_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    bill_date: date
    year: int | None = None
    month: int | None = None
    project_id: UUID | None = None
    note: str = ""
    recurring: bool = False


class VendorBillUpdate(BaseModel):
    vendor_name: str | None = Field(default=None, min_length=1, max_length=255)
    category: VendorCategory | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    gst_percent: Decimal | None = Field(default=None, ge=0, le=100)
    gst_amount: Decimal | None = Field(default=None, ge=0)
    bill_date: date | None = None
    note: str | None = None
    recurring: bool | None = None


class VendorBillOut(ORMModel):
    id: UUID
    vendor_name: str
    category: VendorCategory
    amount: Decimal
    gst_amount: Decimal
    bill_date: date
    paid_date: date | None = None
    year: int
    month: int
    project_id: UUID | None = None
    note: str
    recurring: bool
    status: BillStatus


class CompanyMonthOut(ORMModel):
    year: int
    month: int
    period_label: str
    received: Decimal
    staff_paid: Decimal
    contractors_paid: Decimal
    claims_paid: Decimal
    compliance: Decimal
    other_opex: Decimal
    leftover: Decimal
    invoiced_not_cash: Decimal
    receipts_against_earlier: Decimal = Decimal("0.00")
    salaries_calculated: Decimal
    contractors_calculated: Decimal


class JobIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    department: str = ""
    location_id: UUID | None = None
    hiring_manager_id: UUID | None = None
    opened_on: date
    note: str = ""


class ApplicantIn(BaseModel):
    name: str = Field(min_length=1)
    email: str
    note: str = ""


class ApplicantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    email: str | None = None
    note: str | None = None


class ApplicantOut(ORMModel):
    id: UUID
    job_id: UUID
    name: str
    email: str
    stage: ApplicantStage
    note: str


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    department: str | None = None
    location_id: UUID | None = None
    hiring_manager_id: UUID | None = None
    opened_on: date | None = None
    note: str | None = None


class JobOut(ORMModel):
    id: UUID
    title: str
    department: str
    location_id: UUID | None = None
    hiring_manager_id: UUID | None = None
    is_open: bool
    opened_on: date
    note: str
    applicants: list[ApplicantOut] = []


class DocumentRequirementOut(ORMModel):
    id: UUID
    name: str
    is_active: bool


class EmployeeDocumentOut(ORMModel):
    requirement_id: UUID
    name: str
    provided: bool
    note: str


class AttendanceIn(BaseModel):
    work_date: date
    mark: AttendanceMark
    note: str = ""


class AttendanceOut(ORMModel):
    id: UUID
    employee_id: UUID
    employee_name: str | None = None
    work_date: date
    mark: AttendanceMark
    note: str


class ReviewCycleIn(BaseModel):
    name: str
    start_date: date
    end_date: date


class ReviewCycleOut(ORMModel):
    id: UUID
    name: str
    start_date: date
    end_date: date
    is_open: bool


class ReviewIn(BaseModel):
    employee_id: UUID
    summary: str = ""


class ReviewOut(ORMModel):
    id: UUID
    cycle_id: UUID
    employee_id: UUID
    employee_name: str | None = None
    manager_id: UUID | None = None
    summary: str
    acknowledged: bool


class AssetIn(BaseModel):
    name: str
    asset_tag: str
    category: str = "laptop"
    note: str = ""


class AssetUpdate(BaseModel):
    name: str | None = None
    asset_tag: str | None = None
    category: str | None = None
    note: str | None = None


class AssetOut(ORMModel):
    id: UUID
    name: str
    asset_tag: str
    category: str
    status: AssetStatus
    assigned_to_id: UUID | None = None
    assigned_to_name: str | None = None
    acknowledged: bool
    note: str


class DirectoryPerson(ORMModel):
    id: UUID
    name: str
    designation: str
    department: str
    location_name: str | None = None
    email: str
    engagement: str
    status: str
