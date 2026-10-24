import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class VendorCategory(str, enum.Enum):
    GST_FILING = "gst_filing"
    CA_AUDIT = "ca_audit"
    LEGAL = "legal"
    RENT_OFFICE = "rent_office"
    TOOLS = "tools"
    OTHER = "other"


class BillStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    PAID = "paid"


class ApplicantStage(str, enum.Enum):
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    JOINED = "joined"
    REJECTED = "rejected"


class AttendanceMark(str, enum.Enum):
    PRESENT = "present"
    WORK_FROM = "work_from"
    LEAVE = "leave"
    ABSENT = "absent"


class AssetStatus(str, enum.Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    RETURNED = "returned"
    LOST = "lost"


class ProjectPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_payments"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    invoice_id: Mapped[UUID | None] = mapped_column(ForeignKey("project_invoices.id", ondelete="SET NULL"), nullable=True, index=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    received_date: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(Text, default="")
    entered_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class SalaryPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "salary_payments"
    __table_args__ = (UniqueConstraint("employee_id", "year", "month", name="uq_salary_payment_month"),)

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    paid_date: Mapped[date] = mapped_column(Date)
    reference: Mapped[str] = mapped_column(String(80), default="")
    marked_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class ContractorPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contractor_payments"
    __table_args__ = (UniqueConstraint("employee_id", "year", "month", name="uq_contractor_payment_month"),)

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    calculated: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference: Mapped[str] = mapped_column(String(80), default="")
    deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    marked_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class VendorBill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vendor_bills"

    vendor_name: Mapped[str] = mapped_column(String(255))
    category: Mapped[VendorCategory] = mapped_column(
        Enum(VendorCategory, name="vendorcategory", values_callable=lambda obj: [e.value for e in obj])
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    gst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    bill_date: Mapped[date] = mapped_column(Date)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    recurring: Mapped[bool] = mapped_column(default=False)
    status: Mapped[BillStatus] = mapped_column(
        Enum(BillStatus, name="billstatus", values_callable=lambda obj: [e.value for e in obj]),
        default=BillStatus.APPROVED,
    )
    entered_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "jobs"

    title: Mapped[str] = mapped_column(String(255))
    department: Mapped[str] = mapped_column(String(120), default="")
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    hiring_manager_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    is_open: Mapped[bool] = mapped_column(default=True)
    opened_on: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(Text, default="")

    applicants: Mapped[list["Applicant"]] = relationship(back_populates="job")


class Applicant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "applicants"

    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    stage: Mapped[ApplicantStage] = mapped_column(
        Enum(ApplicantStage, name="applicantstage", values_callable=lambda obj: [e.value for e in obj]),
        default=ApplicantStage.APPLIED,
    )
    note: Mapped[str] = mapped_column(Text, default="")

    job: Mapped["Job"] = relationship(back_populates="applicants")


class DocumentRequirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_requirements"

    name: Mapped[str] = mapped_column(String(120), unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class EmployeeDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "employee_documents"
    __table_args__ = (UniqueConstraint("employee_id", "requirement_id", name="uq_employee_document"),)

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    requirement_id: Mapped[UUID] = mapped_column(ForeignKey("document_requirements.id", ondelete="CASCADE"))
    provided: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str] = mapped_column(Text, default="")


class AttendanceDay(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "attendance_days"
    __table_args__ = (UniqueConstraint("employee_id", "work_date", name="uq_attendance_day"),)

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    work_date: Mapped[date] = mapped_column(Date)
    mark: Mapped[AttendanceMark] = mapped_column(
        Enum(AttendanceMark, name="attendancemark", values_callable=lambda obj: [e.value for e in obj])
    )
    note: Mapped[str] = mapped_column(Text, default="")


class ReviewCycle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review_cycles"

    name: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_open: Mapped[bool] = mapped_column(default=True)


class PerformanceReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "performance_reviews"
    __table_args__ = (UniqueConstraint("cycle_id", "employee_id", name="uq_review_cycle_employee"),)

    cycle_id: Mapped[UUID] = mapped_column(ForeignKey("review_cycles.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    manager_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    acknowledged: Mapped[bool] = mapped_column(default=False)


class CompanyAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "company_assets"

    name: Mapped[str] = mapped_column(String(255))
    asset_tag: Mapped[str] = mapped_column(String(80), unique=True)
    category: Mapped[str] = mapped_column(String(40), default="laptop")
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="assetstatus", values_callable=lambda obj: [e.value for e in obj]),
        default=AssetStatus.AVAILABLE,
    )
    assigned_to_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    acknowledged: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str] = mapped_column(Text, default="")
