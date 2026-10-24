from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.reimbursement import ReimbursementStatus
from app.schemas.common import ORMModel


class ReimbursementCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    category: str = "other"
    spend_date: date
    note: str = ""
    project_id: UUID | None = None


class ReimbursementReview(BaseModel):
    comment: str = ""


class ReimbursementOut(ORMModel):
    id: UUID
    employee_id: UUID
    employee_name: str | None = None
    project_id: UUID | None = None
    project_name: str | None = None
    amount: Decimal
    category: str
    spend_date: date
    note: str
    status: ReimbursementStatus
    reviewer_id: UUID | None = None
    comment: str
    payroll_year: int | None = None
    payroll_month: int | None = None
    paid_separately: bool = False
