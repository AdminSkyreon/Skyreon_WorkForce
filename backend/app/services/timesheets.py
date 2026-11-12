from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequest, Forbidden, NotFound
from app.models.employee import Employee, EmployeeStatus
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.models.time_entry import TaskTimeEntry, TimeEntrySource
from app.models.timesheet import TimesheetStatus, TimesheetWeek
from app.models.user import User, is_staff
from app.schemas.timesheet import DayCell, ManualEntryRequest, SetDayHoursRequest, TimesheetOut, TimesheetRow
from app.services.dates import is_weekend, monday_of, week_days
from app.services import extra_work as extra_work_service
from app.services.holidays import holiday_dates
from app.services.leave import approved_leave_dates

UTC = ZoneInfo("UTC")


def _hours(seconds: int) -> Decimal:
    return (Decimal(seconds) / Decimal(3600)).quantize(Decimal("0.01"))


async def _get_or_none(
    db: AsyncSession, employee_id: UUID, week_start: date
) -> TimesheetWeek | None:
    result = await db.execute(
        select(TimesheetWeek).where(
            TimesheetWeek.employee_id == employee_id,
            TimesheetWeek.week_start == week_start,
        )
    )
    return result.scalar_one_or_none()


async def _ensure_week(db: AsyncSession, employee_id: UUID, week_start: date) -> TimesheetWeek:
    existing = await _get_or_none(db, employee_id, week_start)
    if existing:
        return existing
    week = TimesheetWeek(
        employee_id=employee_id, week_start=week_start, status=TimesheetStatus.DRAFT
    )
    db.add(week)
    await db.flush()
    return week


def _can_review(
    user: User, project_ids: set[UUID], manager_ids: set[UUID], reporting_manager_id: UUID | None = None
) -> bool:
    if is_staff(user):
        return True
    if user.employee and (
        user.employee.id in manager_ids or user.employee.id == reporting_manager_id
    ):
        return True
    return False


async def build_timesheet(
    db: AsyncSession, employee: Employee, week_start: date
) -> TimesheetOut:
    start = monday_of(week_start)
    days = week_days(start)
    end = days[-1]
    week = await _get_or_none(db, employee.id, start)

    entries = (
        await db.execute(
            select(TaskTimeEntry)
            .options(selectinload(TaskTimeEntry.task).selectinload(Task.project))
            .where(
                TaskTimeEntry.employee_id == employee.id,
                TaskTimeEntry.end_time.is_not(None),
                TaskTimeEntry.start_time >= datetime.combine(start, time.min, tzinfo=UTC),
                TaskTimeEntry.start_time < datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC),
            )
        )
    ).scalars().all()

    holidays = await holiday_dates(db, start, end, employee.location_id)
    leave_days = await approved_leave_dates(db, employee.id, start, end)

    grouped: dict[UUID, dict[date, list[TaskTimeEntry]]] = defaultdict(lambda: defaultdict(list))
    for entry in entries:
        work_date = entry.start_time.astimezone(UTC).date()
        grouped[entry.task_id][work_date].append(entry)

    rows: list[TimesheetRow] = []
    daily = [Decimal("0.00")] * 7
    warnings: list[str] = []

    for task_id, by_date in grouped.items():
        sample = next(iter(next(iter(by_date.values()))))
        task = sample.task
        cells: list[DayCell] = []
        for i, day in enumerate(days):
            day_entries = by_date.get(day, [])
            seconds = sum(e.duration_seconds for e in day_entries)
            hours = _hours(seconds)
            daily[i] += hours
            is_manual = any(e.source == TimeEntrySource.MANUAL for e in day_entries)
            cells.append(
                DayCell(
                    date=day,
                    hours=hours,
                    is_manual=is_manual,
                    is_holiday=day in holidays,
                    is_weekend=is_weekend(day),
                    is_leave=day in leave_days,
                    exceeds_12h=False,
                )
            )
        rows.append(
            TimesheetRow(
                task_id=task_id,
                project_id=task.project_id,
                project_name=task.project.name if task.project else "",
                task_title=task.title,
                days=cells,
            )
        )

    for i, total in enumerate(daily):
        if total > Decimal("12"):
            warnings.append(f"{days[i].isoformat()} exceeds 12 hours ({total}h)")
            for row in rows:
                row.days[i].exceeds_12h = True
        if days[i] in holidays and total > 0:
            warnings.append(f"{days[i].isoformat()} is a holiday")
        if days[i] in leave_days and total > 0:
            warnings.append(f"{days[i].isoformat()} is on approved leave")

    status = week.status if week else TimesheetStatus.DRAFT
    return TimesheetOut(
        id=week.id if week else None,
        employee_id=employee.id,
        employee_name=employee.name,
        week_start=start,
        status=status,
        comment=week.comment if week else "",
        reviewer_id=week.reviewer_id if week else None,
        rows=rows,
        daily_totals=daily,
        weekly_total=sum(daily, Decimal("0.00")),
        warnings=warnings,
        locked=status == TimesheetStatus.APPROVED,
    )

async def _assert_daily_total_within_24h(
    db: AsyncSession, employee_id: UUID, work_date: date, delta_seconds: int
) -> None:
    if delta_seconds <= 0:
        return
    day_start = datetime.combine(work_date, time.min, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)
    total_seconds = (
        await db.execute(
            select(func.coalesce(func.sum(TaskTimeEntry.duration_seconds), 0)).where(
                TaskTimeEntry.employee_id == employee_id,
                TaskTimeEntry.end_time.is_not(None),
                TaskTimeEntry.start_time >= day_start,
                TaskTimeEntry.start_time < day_end,
            )
        )
    ).scalar_one()
    if int(total_seconds) + delta_seconds > 24 * 3600:
        raise BadRequest(f"Total logged hours for {work_date.isoformat()} cannot exceed 24 hours")
    

async def add_manual_entry(
    db: AsyncSession, employee: Employee, data: ManualEntryRequest
) -> TimesheetOut:
    week_start = monday_of(data.work_date)
    week = await _ensure_week(db, employee.id, week_start)
    if week.status == TimesheetStatus.APPROVED:
        raise BadRequest("Approved timesheets are locked")
    if week.status == TimesheetStatus.SUBMITTED:
        raise BadRequest("Submitted timesheets cannot be edited")

    task = await db.get(Task, data.task_id)
    if task is None:
        raise NotFound("Task not found")
    if task.assignee_id != employee.id:
        raise Forbidden("You can only log time on your own tasks")

    start_dt = datetime.combine(data.work_date, time(9, 0), tzinfo=UTC)
    seconds = int(data.hours * 3600)

    await _assert_daily_total_within_24h(db, employee.id, data.work_date, seconds)

    end_dt = start_dt + timedelta(seconds=seconds)
    db.add(
        TaskTimeEntry(
            task_id=task.id,
            employee_id=employee.id,
            start_time=start_dt,
            end_time=end_dt,
            duration_seconds=seconds,
            source=TimeEntrySource.MANUAL,
            manual_reason=data.reason,
            note=data.reason,
        )
    )
    await db.commit()
    return await build_timesheet(db, employee, week_start)


async def set_day_hours(
    db: AsyncSession, employee: Employee, data: SetDayHoursRequest
) -> TimesheetOut:
    week_start = monday_of(data.work_date)
    week = await _ensure_week(db, employee.id, week_start)
    if week.status == TimesheetStatus.APPROVED:
        raise BadRequest("Approved timesheets are locked")
    if week.status == TimesheetStatus.SUBMITTED:
        raise BadRequest("Submitted timesheets cannot be edited")

    task = await db.get(Task, data.task_id)
    if task is None:
        raise NotFound("Task not found")
    if task.assignee_id != employee.id:
        raise Forbidden("You can only log time on your own tasks")

    day_start = datetime.combine(data.work_date, time.min, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)
    entries = list(
        (
            await db.execute(
                select(TaskTimeEntry)
                .where(
                    TaskTimeEntry.employee_id == employee.id,
                    TaskTimeEntry.task_id == task.id,
                    TaskTimeEntry.end_time.is_not(None),
                    TaskTimeEntry.start_time >= day_start,
                    TaskTimeEntry.start_time < day_end,
                )
                .order_by(TaskTimeEntry.created_at.desc())
            )
        ).scalars().all()
    )
    timer_seconds = sum(e.duration_seconds for e in entries if e.source == TimeEntrySource.TIMER)
    current_seconds = sum(e.duration_seconds for e in entries)
    target_seconds = int(data.hours * 3600)
    if target_seconds < timer_seconds:
        raise BadRequest(
            f"Timer already logged {_hours(timer_seconds)}h. Pause/stop or lower only the typed hours."
        )

    manuals = [e for e in entries if e.source == TimeEntrySource.MANUAL]
    if target_seconds > current_seconds:
        extra = target_seconds - current_seconds
        await _assert_daily_total_within_24h(db, employee.id, data.work_date, extra)
        start_dt = datetime.combine(data.work_date, time(9, 0), tzinfo=UTC) + timedelta(minutes=len(entries))
        db.add(
            TaskTimeEntry(
                task_id=task.id,
                employee_id=employee.id,
                start_time=start_dt,
                end_time=start_dt + timedelta(seconds=extra),
                duration_seconds=extra,
                source=TimeEntrySource.MANUAL,
                manual_reason="Timesheet grid",
                note="Timesheet grid",
            )
        )
    elif target_seconds < current_seconds:
        remaining = current_seconds - target_seconds
        for entry in manuals:
            if remaining <= 0:
                break
            if entry.duration_seconds <= remaining:
                remaining -= entry.duration_seconds
                await db.delete(entry)
            else:
                entry.duration_seconds -= remaining
                if entry.start_time:
                    entry.end_time = entry.start_time + timedelta(seconds=entry.duration_seconds)
                remaining = 0

    await db.commit()
    return await build_timesheet(db, employee, week_start)


async def submit_week(db: AsyncSession, employee: Employee, week_start: date) -> TimesheetOut:
    start = monday_of(week_start)
    week = await _ensure_week(db, employee.id, start)
    if week.status == TimesheetStatus.APPROVED:
        raise BadRequest("Approved timesheets are locked")

    if week.status == TimesheetStatus.SUBMITTED:
        raise BadRequest("Timesheet is already submitted")

    sheet = await build_timesheet(db, employee, start)
    if sheet.weekly_total <= 0:
        raise BadRequest("Cannot submit an empty timesheet")
    week.status = TimesheetStatus.SUBMITTED
    week.comment = ""
    pending_created = await extra_work_service.sync_from_timesheet_week(db, employee, start, week)
    await db.commit()
    sheet = await build_timesheet(db, employee, start)
    sheet.extra_work_pending_count = pending_created
    return sheet


def mondays_for_month(year: int, month: int) -> list[date]:
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    cursor = monday_of(start)
    weeks: list[date] = []
    while cursor <= end:
        weeks.append(cursor)
        cursor += timedelta(days=7)
    return weeks


async def list_period(
    db: AsyncSession,
    user: User,
    week_start: date | None = None,
    year: int | None = None,
    month: int | None = None,
    employee_id: UUID | None = None,
    department: str | None = None,
    location_id: UUID | None = None,
    project_id: UUID | None = None,
    status: TimesheetStatus | None = None,
) -> list[TimesheetOut]:
    if year and month:
        weeks = mondays_for_month(year, month)
    else:
        weeks = [monday_of(week_start or date.today())]
    emp_stmt = (
        select(Employee)
        .options(selectinload(Employee.user), selectinload(Employee.location))
        .where(Employee.status == EmployeeStatus.ACTIVE)
        .order_by(Employee.name)
    )
    if employee_id:
        emp_stmt = emp_stmt.where(Employee.id == employee_id)
    if department:
        emp_stmt = emp_stmt.where(Employee.department == department)
    if location_id:
        emp_stmt = emp_stmt.where(Employee.location_id == location_id)
    if not is_staff(user):
        if user.employee is None:
            return []
        managed_member_ids = (
            select(ProjectMember.employee_id)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(Project.manager_id == user.employee.id)
        )
        emp_stmt = emp_stmt.where(
            or_(
                Employee.id == user.employee.id,
                Employee.reporting_manager_id == user.employee.id,
                Employee.id.in_(managed_member_ids),
            )
        )
    people = list((await db.execute(emp_stmt)).scalars().all())
    outs: list[TimesheetOut] = []
    for person in people:
        for monday in weeks:
            sheet = await build_timesheet(db, person, monday)
            if status and sheet.status != status:
                continue
            if project_id and not any(row.project_id == project_id for row in sheet.rows):
                continue
            outs.append(sheet)
    return outs


async def list_submitted(
    db: AsyncSession,
    user: User,
    week_start: date | None = None,
    year: int | None = None,
    month: int | None = None,
    employee_id: UUID | None = None,
    department: str | None = None,
    location_id: UUID | None = None,
    project_id: UUID | None = None,
    status: TimesheetStatus | None = None,
) -> list[TimesheetOut]:
    return await list_period(
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


async def my_month(db: AsyncSession, employee: Employee, year: int, month: int) -> list[TimesheetOut]:
    return [await build_timesheet(db, employee, monday) for monday in mondays_for_month(year, month)]


async def review_week(
    db: AsyncSession, user: User, week_id: UUID, status: TimesheetStatus, comment: str
) -> TimesheetOut:
    week = await db.get(TimesheetWeek, week_id)
    if week is None:
        raise NotFound("Timesheet not found")
    if week.status != TimesheetStatus.SUBMITTED:
        raise BadRequest("Only submitted timesheets can be reviewed")

    if status == TimesheetStatus.REJECTED and not comment.strip():
        raise BadRequest("Please enter a reason when rejecting a timesheet")
    
    employee = (
        await db.execute(
            select(Employee).options(selectinload(Employee.user)).where(Employee.id == week.employee_id)
        )
    ).scalar_one()
    sheet = await build_timesheet(db, employee, week.week_start)
    project_ids = {row.project_id for row in sheet.rows}
    managers = set()
    if project_ids:
        managers = set(
            (await db.execute(select(Project.manager_id).where(Project.id.in_(project_ids)))).scalars().all()
        )
    if user.employee and user.employee.id == week.employee_id:
        raise Forbidden("You cannot approve your own timesheet")
    if not _can_review(user, project_ids, managers, employee.reporting_manager_id):
        raise Forbidden("You cannot review this timesheet")
    week.status = status
    week.comment = comment
    week.reviewer_id = user.employee.id if user.employee else None
    await db.commit()
    return await build_timesheet(db, employee, week.week_start)
