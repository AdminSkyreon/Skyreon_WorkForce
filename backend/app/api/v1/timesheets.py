from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.models.timesheet import TimesheetStatus
from app.schemas.timesheet import TimesheetOut, TimesheetReviewRequest
from app.services import notifications as notification_service
from app.services import timesheets as timesheet_service
from app.services.employees import get_employee

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


@router.get("", response_model=list[TimesheetOut])
async def list_timesheets(
    user: CurrentUser,
    db: DbSession,
    week_start: date | None = None,
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    employee_id: UUID | None = None,
    department: str | None = None,
    location_id: UUID | None = None,
    project_id: UUID | None = None,
    status: TimesheetStatus | None = None,
) -> list[TimesheetOut]:
    return await timesheet_service.list_period(
        db,
        user,
        week_start=week_start,
        year=year,
        month=month,
        employee_id=employee_id,
        department=department,
        location_id=location_id,
        project_id=project_id,
        status=status,
    )


@router.post("/{week_id}/approve", response_model=TimesheetOut)
async def approve_timesheet(
    week_id: UUID, payload: TimesheetReviewRequest, user: CurrentUser, db: DbSession
) -> TimesheetOut:
    result = await timesheet_service.review_week(
        db, user, week_id, TimesheetStatus.APPROVED, payload.comment
    )
    employee = await get_employee(db, result.employee_id)
    await notification_service.notify(
        db,
        employee.user_id,
        "timesheet_approved",
        "Timesheet approved",
        f"Your week of {result.week_start} was approved.",
        "/employee/timesheet",
    )
    await db.commit()
    return result


@router.post("/{week_id}/reject", response_model=TimesheetOut)
async def reject_timesheet(
    week_id: UUID, payload: TimesheetReviewRequest, user: CurrentUser, db: DbSession
) -> TimesheetOut:
    result = await timesheet_service.review_week(
        db, user, week_id, TimesheetStatus.REJECTED, payload.comment
    )
    employee = await get_employee(db, result.employee_id)
    await notification_service.notify(
        db,
        employee.user_id,
        "timesheet_rejected",
        "Timesheet rejected",
        f"Your week of {result.week_start} was rejected.",
        "/employee/timesheet",
    )
    await db.commit()
    return result
