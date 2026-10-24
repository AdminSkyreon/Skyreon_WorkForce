from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.extra_work import ExtraWorkKind, ExtraWorkSettlement, ExtraWorkStatus
from app.schemas.common import ORMModel


class ExtraWorkApprove(BaseModel):
    settlement: ExtraWorkSettlement
    comp_off_days: Decimal | None = Field(default=None, ge=0, le=30)
    extra_pay_amount: Decimal | None = Field(default=None, ge=0)
    comment: str = ""


class ExtraWorkReject(BaseModel):
    comment: str = ""


class ExtraWorkOut(ORMModel):
    id: UUID
    employee_id: UUID
    employee_name: str | None = None
    work_date: date
    hours: Decimal
    kind: ExtraWorkKind
    status: ExtraWorkStatus
    settlement: ExtraWorkSettlement | None = None
    comp_off_days: Decimal
    extra_pay_amount: Decimal
    payroll_year: int | None = None
    payroll_month: int | None = None
    comment: str


class ExtraWorkDefaults(BaseModel):
    comp_off_days: Decimal
    extra_pay_amount: Decimal
