from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequest, Conflict
from app.models.task import Task, TaskStatus
from app.models.time_entry import TaskTimeEntry, TimeEntrySource
from app.models.timesheet import TimesheetStatus, TimesheetWeek
from app.schemas.timer import RunningTimer
from app.services.tasks import assert_task_owner, get_task


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _estimate_cap_seconds(task: Task) -> int | None:
    est = Decimal(task.estimated_hours or 0)
    if est <= 0:
        return None
    return int(est * 3600)


async def _closed_seconds(db: AsyncSession, task_id: UUID, employee_id: UUID) -> int:
    result = await db.execute(
        select(func.coalesce(func.sum(TaskTimeEntry.duration_seconds), 0)).where(
            TaskTimeEntry.task_id == task_id,
            TaskTimeEntry.employee_id == employee_id,
            TaskTimeEntry.end_time.is_not(None),
        )
    )
    return int(result.scalar_one())


async def get_open_entry(db: AsyncSession, employee_id: UUID) -> TaskTimeEntry | None:
    result = await db.execute(
        select(TaskTimeEntry)
        .options(selectinload(TaskTimeEntry.task).selectinload(Task.project))
        .where(TaskTimeEntry.employee_id == employee_id, TaskTimeEntry.end_time.is_(None))
    )
    return result.scalar_one_or_none()


async def running_timer(db: AsyncSession, employee_id: UUID) -> RunningTimer:
    now = datetime.now(UTC)
    entry = await get_open_entry(db, employee_id)
    if entry is None:
        return RunningTimer(running=False, server_time=now)
    elapsed = max(0, int((now - _aware(entry.start_time)).total_seconds()))
    logged = await _closed_seconds(db, entry.task_id, employee_id)
    cap = _estimate_cap_seconds(entry.task)
    estimated = cap if cap is not None else 0
    remaining = (cap - logged - elapsed) if cap is not None else 0
    if cap is not None and logged + elapsed >= cap:
        await _close_entry(db, entry, employee_id)
        entry.task.status = TaskStatus.PAUSED
        await db.commit()
        return RunningTimer(running=False, server_time=now)
    return RunningTimer(
        running=True,
        task_id=entry.task_id,
        task_title=entry.task.title,
        project_name=entry.task.project.name if entry.task.project else None,
        entry_id=entry.id,
        started_at=entry.start_time,
        remaining_seconds=remaining,
        estimated_seconds=estimated,
        logged_seconds=logged + elapsed,
        server_time=now,
        is_overtime=cap is not None and remaining <= 0,
    )


async def _week_locked(db: AsyncSession, employee_id: UUID, on: datetime) -> None:
    week_start = on.date()
    week_start = week_start.fromordinal(week_start.toordinal() - week_start.weekday())
    result = await db.execute(
        select(TimesheetWeek).where(
            TimesheetWeek.employee_id == employee_id,
            TimesheetWeek.week_start == week_start,
            TimesheetWeek.status == TimesheetStatus.APPROVED,
        )
    )
    if result.scalar_one_or_none():
        raise BadRequest("This week is locked after approval")


async def _close_entry(
    db: AsyncSession, entry: TaskTimeEntry, employee_id: UUID, note: str = ""
) -> None:
    now = datetime.now(UTC)
    elapsed = max(0, int((now - _aware(entry.start_time)).total_seconds()))
    cap = _estimate_cap_seconds(entry.task)
    if cap is not None:
        closed_before = await _closed_seconds(db, entry.task_id, employee_id)
        elapsed = min(elapsed, max(0, cap - closed_before))
    entry.end_time = _aware(entry.start_time) + timedelta(seconds=elapsed)
    entry.duration_seconds = elapsed
    if note:
        entry.note = note


async def start_timer(
    db: AsyncSession, employee_id: UUID, task_id: UUID, pause_current: bool
) -> RunningTimer:
    task = await get_task(db, task_id)
    assert_task_owner(task, employee_id)
    await _week_locked(db, employee_id, datetime.now(UTC))
    cap = _estimate_cap_seconds(task)
    if cap is not None:
        logged = await _closed_seconds(db, task.id, employee_id)
        if logged >= cap:
            raise BadRequest("Task estimate reached; no more timer time available")
    current = await get_open_entry(db, employee_id)
    if current:
        if current.task_id == task_id:
            return await running_timer(db, employee_id)
        if not pause_current:
            raise Conflict("Another timer is already running")
        await _close_entry(db, current, employee_id)
        if current.task and current.task.status == TaskStatus.IN_PROGRESS:
            current.task.status = TaskStatus.PAUSED

    entry = TaskTimeEntry(
        task_id=task.id,
        employee_id=employee_id,
        start_time=datetime.now(UTC),
        source=TimeEntrySource.TIMER,
    )
    db.add(entry)
    task.status = TaskStatus.IN_PROGRESS
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise Conflict("Another timer is already running") from exc
    return await running_timer(db, employee_id)


async def pause_timer(db: AsyncSession, employee_id: UUID, task_id: UUID) -> RunningTimer:
    entry = await get_open_entry(db, employee_id)
    if entry is None or entry.task_id != task_id:
        raise BadRequest("No running timer for this task")
    await _close_entry(db, entry, employee_id)
    entry.task.status = TaskStatus.PAUSED
    await db.commit()
    return await running_timer(db, employee_id)


async def resume_timer(
    db: AsyncSession, employee_id: UUID, task_id: UUID, pause_current: bool
) -> RunningTimer:
    return await start_timer(db, employee_id, task_id, pause_current)


async def stop_timer(
    db: AsyncSession, employee_id: UUID, task_id: UUID, note: str
) -> RunningTimer:
    entry = await get_open_entry(db, employee_id)
    if entry is None or entry.task_id != task_id:
        raise BadRequest("No running timer for this task")
    await _close_entry(db, entry, employee_id, note)
    await db.commit()
    return await running_timer(db, employee_id)
