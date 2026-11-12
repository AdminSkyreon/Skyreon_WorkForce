from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints, model_validator

from app.models.hrms import ApplicantStage, AssetStatus, AttendanceMark, BillStatus, VendorCategory
from app.schemas.common import ORMModel

VendorName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
NonEmpty255 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
NonEmpty120 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Tag80 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Category40 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Dept120 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]


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
    reference: str = Field(default="", max_length=255)
    amount: Decimal | None = Field(default=None, ge=0, le=Decimal("9999999999.99"))


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
    amount: Decimal | None = Field(default=None, ge=0, le=Decimal("9999999999.99"))
    paid_date: date
    reference: str = Field(default="", max_length=255)
    deduction: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("9999999999.99"))


class VendorBillIn(BaseModel):
    vendor_name: VendorName
    category: VendorCategory
    amount: Decimal = Field(gt=0)
    gst_percent: Decimal | None = Field(default=None, ge=0, le=100)
    gst_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    bill_date: date
    year: int | None = Field(default=None, ge=2000, le=2100)
    month: int | None = Field(default=None, ge=1, le=12)
    project_id: UUID | None = None
    note: str = Field(default="", max_length=500)
    recurring: bool = False


class VendorBillUpdate(BaseModel):
    vendor_name: VendorName | None = None
    category: VendorCategory | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    gst_percent: Decimal | None = Field(default=None, ge=0, le=100)
    gst_amount: Decimal | None = Field(default=None, ge=0)
    bill_date: date | None = None
    note: str | None = Field(default=None, max_length=500)
    recurring: bool | None = None

    @model_validator(mode="after")
    def reject_nulls(self) -> "VendorBillUpdate":
        for field in ("vendor_name", "category", "amount", "gst_amount", "bill_date", "note", "recurring"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


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
    title: NonEmpty255
    department: Dept120 = ""
    location_id: UUID | None = None
    hiring_manager_id: UUID | None = None
    opened_on: date
    note: str = Field(default="", max_length=1000)


class ApplicantIn(BaseModel):
    name: NonEmpty255
    email: EmailStr
    note: str = Field(default="", max_length=1000)


class ApplicantUpdate(BaseModel):
    name: NonEmpty255 | None = None
    email: EmailStr | None = None
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def reject_nulls(self) -> "ApplicantUpdate":
        for field in ("name", "email", "note"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ApplicantOut(ORMModel):
    id: UUID
    job_id: UUID
    name: str
    email: str
    stage: ApplicantStage
    note: str


class JobUpdate(BaseModel):
    title: NonEmpty255 | None = None
    department: Dept120 | None = None
    location_id: UUID | None = None
    hiring_manager_id: UUID | None = None
    opened_on: date | None = None
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def reject_nulls(self) -> "JobUpdate":
        for field in ("title", "department", "opened_on", "note"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


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
    note: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def validate_work_date(self) -> "AttendanceIn":
        if self.work_date > date.today():
            raise ValueError("Cannot mark attendance for a future date")
        return self


class AttendanceOut(ORMModel):
    id: UUID
    employee_id: UUID
    employee_name: str | None = None
    work_date: date
    mark: AttendanceMark
    note: str


class ReviewCycleIn(BaseModel):
    name: NonEmpty120
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self) -> "ReviewCycleIn":
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date")
        return self


class ReviewCycleOut(ORMModel):
    id: UUID
    name: str
    start_date: date
    end_date: date
    is_open: bool


class ReviewIn(BaseModel):
    employee_id: UUID
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class ReviewOut(ORMModel):
    id: UUID
    cycle_id: UUID
    employee_id: UUID
    employee_name: str | None = None
    manager_id: UUID | None = None
    summary: str
    acknowledged: bool


class AssetIn(BaseModel):
    name: NonEmpty255
    asset_tag: Tag80
    category: Category40 = "laptop"
    note: str = Field(default="", max_length=500)


class AssetUpdate(BaseModel):
    name: NonEmpty255 | None = None
    asset_tag: Tag80 | None = None
    category: Category40 | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def reject_nulls(self) -> "AssetUpdate":
        for field in ("name", "asset_tag", "category", "note"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


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
