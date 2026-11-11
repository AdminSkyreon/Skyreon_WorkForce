from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequest, Forbidden, NotFound
from app.models.employee import Employee, EmployeeStatus
from app.models.project import ProjectMember
from app.models.task import Task, TaskStatus
from app.models.time_entry import TaskTimeEntry
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate


async def _logged_seconds(db: AsyncSession, task_id: UUID) -> int:
    result = await db.execute(
        select(func.coalesce(func.sum(TaskTimeEntry.duration_seconds), 0)).where(
            TaskTimeEntry.task_id == task_id,
            TaskTimeEntry.end_time.is_not(None),
        )
    )
    return int(result.scalar_one())


async def _open_seconds(db: AsyncSession, task_id: UUID) -> int:
    result = await db.execute(
        select(TaskTimeEntry).where(
            TaskTimeEntry.task_id == task_id,
            TaskTimeEntry.end_time.is_(None),
        )
    )
    open_entry = result.scalar_one_or_none()
    if open_entry is None:
        return 0
    start = open_entry.start_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return max(0, int((datetime.now(UTC) - start).total_seconds()))


def to_task_out(task: Task, logged_seconds: int, remaining_seconds: int) -> TaskOut:
    return TaskOut(
        id=task.id,
        project_id=task.project_id,
        project_name=task.project.name if task.project else None,
        title=task.title,
        description=task.description,
        priority=task.priority,
        estimated_hours=task.estimated_hours,
        due_date=task.due_date,
        assignee_id=task.assignee_id,
        assignee_name=task.assignee.name if task.assignee else None,
        status=task.status,
        logged_seconds=logged_seconds,
        remaining_seconds=remaining_seconds,
    )


async def _assert_member(db: AsyncSession, project_id: UUID, employee_id: UUID) -> None:
    result = await db.execute(
        select(ProjectMember.id).join(Employee, Employee.id == ProjectMember.employee_id).where(
            ProjectMember.project_id == project_id,
            ProjectMember.employee_id == employee_id,
            Employee.status == EmployeeStatus.ACTIVE,
        )
    )
    if result.scalar_one_or_none() is None:
        raise BadRequest("Assignee must be an active project team member")


async def get_task(db: AsyncSession, task_id: UUID) -> Task:
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.project), selectinload(Task.assignee))
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise NotFound("Task not found")
    return task


async def list_project_tasks(db: AsyncSession, project_id: UUID) -> list[TaskOut]:
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.project), selectinload(Task.assignee))
        .where(Task.project_id == project_id)
        .order_by(Task.created_at)
    )
    tasks = list(result.scalars().all())
    outs: list[TaskOut] = []
    for task in tasks:
        logged = await _logged_seconds(db, task.id)
        open_s = await _open_seconds(db, task.id)
        estimated = int(Decimal(task.estimated_hours) * 3600)
        outs.append(to_task_out(task, logged + open_s, estimated - logged - open_s))
    return outs


async def create_my_task(db: AsyncSession, project_id: UUID, employee_id: UUID, data: TaskCreate) -> TaskOut:
    from app.services.projects import assert_project_member

    await assert_project_member(db, project_id, employee_id)
    payload = data.model_copy(update={"assignee_id": employee_id})
    return await create_task(db, project_id, payload)


async def create_task(db: AsyncSession, project_id: UUID, data: TaskCreate) -> TaskOut:
    if data.assignee_id:
        await _assert_member(db, project_id, data.assignee_id)
    task = Task(project_id=project_id, **data.model_dump())
    db.add(task)
    await db.commit()
    task = await get_task(db, task.id)
    estimated = int(Decimal(task.estimated_hours) * 3600)
    return to_task_out(task, 0, estimated)


async def update_task(db: AsyncSession, task_id: UUID, data: TaskUpdate) -> TaskOut:
    task = await get_task(db, task_id)
    payload = data.model_dump(exclude_unset=True)
    if "assignee_id" in payload and payload["assignee_id"]:
        await _assert_member(db, task.project_id, payload["assignee_id"])
    for key, value in payload.items():
        setattr(task, key, value)
    await db.commit()
    task = await get_task(db, task.id)
    logged = await _logged_seconds(db, task.id)
    open_s = await _open_seconds(db, task.id)
    estimated = int(Decimal(task.estimated_hours) * 3600)
    return to_task_out(task, logged + open_s, estimated - logged - open_s)


async def list_my_tasks(db: AsyncSession, employee_id: UUID) -> list[TaskOut]:
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.project), selectinload(Task.assignee))
        .where(Task.assignee_id == employee_id)
        .order_by(Task.status, Task.due_date)
    )
    tasks = list(result.scalars().all())
    outs: list[TaskOut] = []
    for task in tasks:
        logged = await _logged_seconds(db, task.id)
        open_s = await _open_seconds(db, task.id)
        estimated = int(Decimal(task.estimated_hours) * 3600)
        outs.append(to_task_out(task, logged + open_s, estimated - logged - open_s))
    return outs


def assert_task_owner(task: Task, employee_id: UUID) -> None:
    if task.assignee_id != employee_id:
        raise Forbidden("You can only access your own tasks")


async def set_task_status(db: AsyncSession, task: Task, status: TaskStatus) -> None:
    task.status = status
    await db.flush()
