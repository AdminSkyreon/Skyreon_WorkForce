from datetime import date as Date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.timesheet import TimesheetStatus
from app.schemas.common import ORMModel


class ManualEntryRequest(BaseModel):
    task_id: UUID
    work_date: Date
    hours: Decimal = Field(gt=0, le=24)
    reason: str = Field(min_length=1, max_length=500)


class SetDayHoursRequest(BaseModel):
    task_id: UUID
    work_date: Date
    hours: Decimal = Field(ge=0, le=24)


class TimesheetReviewRequest(BaseModel):
    comment: str = ""


class DayCell(BaseModel):
    date: Date
    hours: Decimal
    is_manual: bool = False
    is_holiday: bool = False
    is_weekend: bool = False
    is_leave: bool = False
    exceeds_12h: bool = False


class TimesheetRow(BaseModel):
    task_id: UUID
    project_id: UUID
    project_name: str
    task_title: str
    days: list[DayCell]


class TimesheetOut(ORMModel):
    id: UUID | None = None
    employee_id: UUID
    employee_name: str | None = None
    week_start: Date
    status: TimesheetStatus
    comment: str = ""
    reviewer_id: UUID | None = None
    rows: list[TimesheetRow] = Field(default_factory=list)
    daily_totals: list[Decimal] = Field(default_factory=list)
    weekly_total: Decimal = Decimal("0.00")
    warnings: list[str] = Field(default_factory=list)
    locked: bool = False
    extra_work_pending_count: int = 0
