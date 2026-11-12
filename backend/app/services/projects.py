from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequest, Conflict, Forbidden, NotFound
from app.models.employee import Employee
from app.models.project import Project, ProjectMember, ProjectStatus
from app.models.task import Task
from app.models.time_entry import TaskTimeEntry
from app.schemas.employee import EmployeeOut
from app.schemas.project import ProjectCreate, ProjectFinancials, ProjectOut, ProjectUpdate
from app.services.employees import get_active_employee, to_employee_out


def _project_load_options():
    return (
        selectinload(Project.manager).selectinload(Employee.user),
        selectinload(Project.members).selectinload(ProjectMember.employee).selectinload(Employee.user),
        selectinload(Project.members).selectinload(ProjectMember.employee).selectinload(Employee.location),
        selectinload(Project.members).selectinload(ProjectMember.employee).selectinload(Employee.reporting_manager),
        selectinload(Project.members).selectinload(ProjectMember.employee).selectinload(Employee.payroll),
    )


def _member_outs(project: Project) -> list[EmployeeOut]:
    return [to_employee_out(member.employee) for member in project.members if member.employee]


def to_project_out(project: Project, financials: ProjectFinancials | None = None) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        name=project.name,
        client_name=project.client_name,
        project_code=project.project_code,
        description=project.description,
        manager_id=project.manager_id,
        manager_name=project.manager.name if project.manager else None,
        start_date=project.start_date,
        end_date=project.end_date,
        status=project.status,
        contract_type=project.contract_type,
        revenue_amount=project.revenue_amount,
        revenue_currency=project.revenue_currency,
        budgeted_hours=project.budgeted_hours,
        members=_member_outs(project),
        financials=financials,
    )


async def _load_project(db: AsyncSession, project_id: UUID) -> Project:
    result = await db.execute(
        select(Project)
        .options(*_project_load_options())
        .execution_options(populate_existing=True)
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFound("Project not found")
    return project


async def compute_financials(db: AsyncSession, project_id: UUID) -> ProjectFinancials:
    stmt = (
        select(
            TaskTimeEntry.employee_id,
            func.coalesce(func.sum(TaskTimeEntry.duration_seconds), 0),
        )
        .join(Task, Task.id == TaskTimeEntry.task_id)
        .where(Task.project_id == project_id, TaskTimeEntry.end_time.is_not(None))
        .group_by(TaskTimeEntry.employee_id)
    )
    rows = (await db.execute(stmt)).all()
    total_seconds = 0
    cost = Decimal("0.00")
    if rows:
        emp_ids = [row[0] for row in rows]
        employees = (
            await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))
        ).scalars()
        rates = {emp.id: emp.hourly_cost_rate for emp in employees}
        for emp_id, seconds in rows:
            total_seconds += int(seconds)
            hours = Decimal(int(seconds)) / Decimal(3600)
            cost += hours * Decimal(rates.get(emp_id, Decimal("0")))

    project = await db.get(Project, project_id)
    if project is None:
        raise NotFound("Project not found")
    total_hours = (Decimal(total_seconds) / Decimal(3600)).quantize(Decimal("0.01"))
    cost = cost.quantize(Decimal("0.01"))
    revenue = Decimal(project.revenue_amount)
    profit = (revenue - cost).quantize(Decimal("0.01"))
    margin = (profit / revenue * Decimal(100)).quantize(Decimal("0.01")) if revenue else Decimal("0")
    budget = Decimal(project.budgeted_hours)
    consumed = (total_hours / budget * Decimal(100)).quantize(Decimal("0.01")) if budget else Decimal("0")
    return ProjectFinancials(
        total_hours=total_hours,
        cost=cost,
        revenue=revenue,
        profit=profit,
        margin_percent=margin,
        budget_consumed_percent=consumed,
    )


async def list_projects(
    db: AsyncSession,
    *,
    search: str | None = None,
    status: ProjectStatus | None = None,
    manager_id: UUID | None = None,
    start_from: object | None = None,
    start_to: object | None = None,
    sort: str = "name",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Project], int]:
    stmt: Select[tuple[Project]] = select(Project).options(*_project_load_options())
    count_stmt = select(func.count()).select_from(Project)
    if search:
        pattern = f"%{search}%"
        filt = or_(
            Project.name.ilike(pattern),
            Project.client_name.ilike(pattern),
            Project.project_code.ilike(pattern),
        )
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)
    if status:
        stmt = stmt.where(Project.status == status)
        count_stmt = count_stmt.where(Project.status == status)
    if manager_id:
        stmt = stmt.where(Project.manager_id == manager_id)
        count_stmt = count_stmt.where(Project.manager_id == manager_id)
    if start_from:
        stmt = stmt.where(Project.start_date >= start_from)
        count_stmt = count_stmt.where(Project.start_date >= start_from)
    if start_to:
        stmt = stmt.where(Project.start_date <= start_to)
        count_stmt = count_stmt.where(Project.start_date <= start_to)

    sort_map = {
        "name": Project.name,
        "start_date": Project.start_date,
        "status": Project.status,
        "client_name": Project.client_name,
    }
    descending = sort.startswith("-")
    key = sort[1:] if descending else sort
    col = sort_map.get(key, Project.name)
    stmt = stmt.order_by(col.desc() if descending else col.asc())

    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    return list(result.scalars().unique().all()), total


async def get_project(db: AsyncSession, project_id: UUID) -> Project:
    return await _load_project(db, project_id)


async def assert_project_member(db: AsyncSession, project_id: UUID, employee_id: UUID) -> Project:
    project = await _load_project(db, project_id)
    member_ids = {member.employee_id for member in project.members}
    if employee_id != project.manager_id and employee_id not in member_ids:
        raise Forbidden("You are not on this project")
    return project


async def list_my_projects(db: AsyncSession, employee_id: UUID) -> list[Project]:
    stmt = (
        select(Project)
        .options(*_project_load_options())
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.employee_id == employee_id)
        .order_by(Project.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def _set_members(db: AsyncSession, project: Project, member_ids: list[UUID]) -> None:
    unique_ids = list(dict.fromkeys([*member_ids, project.manager_id]))
    existing = (
        await db.execute(select(ProjectMember).where(ProjectMember.project_id == project.id))
    ).scalars().all()
    existing_ids = {m.employee_id for m in existing}
    desired = set(unique_ids)
    for emp_id in desired - existing_ids:
        await get_active_employee(db, emp_id, "Team member")
        db.add(ProjectMember(project_id=project.id, employee_id=emp_id))
    for member in existing:
        if member.employee_id not in desired:
            await db.delete(member)


async def create_project(db: AsyncSession, data: ProjectCreate) -> Project:
    dup = await db.execute(select(Project).where(Project.project_code == data.project_code))
    if dup.scalar_one_or_none():
        raise Conflict("Project code already in use")
    await get_active_employee(db, data.manager_id, "Project manager")
    project = Project(
        name=data.name,
        client_name=data.client_name,
        project_code=data.project_code,
        description=data.description,
        manager_id=data.manager_id,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
        contract_type=data.contract_type,
        revenue_amount=data.revenue_amount,
        revenue_currency=data.revenue_currency,
        budgeted_hours=data.budgeted_hours,
    )
    db.add(project)
    await db.flush()
    await _set_members(db, project, data.member_ids)
    await db.commit()
    return await _load_project(db, project.id)


async def update_project(db: AsyncSession, project_id: UUID, data: ProjectUpdate) -> Project:
    project = await _load_project(db, project_id)
    payload = data.model_dump(exclude_unset=True)
    member_ids = payload.pop("member_ids", None)
    if "manager_id" in payload:
        await get_active_employee(db, payload["manager_id"], "Project manager")
    for key, value in payload.items():
        setattr(project, key, value)
    if project.end_date is not None and project.end_date < project.start_date:
        raise BadRequest("End date cannot be earlier than start date")
    if member_ids is not None:
        await _set_members(db, project, member_ids)
    await db.commit()
    return await _load_project(db, project.id)


def grouped_financials(
    rows: list[tuple[UUID, int, Decimal]],
) -> dict[UUID, tuple[Decimal, Decimal]]:
    hours: dict[UUID, Decimal] = defaultdict(lambda: Decimal("0"))
    cost: dict[UUID, Decimal] = defaultdict(lambda: Decimal("0"))
    for project_id, seconds, rate in rows:
        h = Decimal(seconds) / Decimal(3600)
        hours[project_id] += h
        cost[project_id] += h * rate
    return {pid: (hours[pid], cost[pid]) for pid in hours}
