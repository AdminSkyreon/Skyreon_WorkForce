from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.employee import Employee, EmployeeStatus
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.project import Project, ProjectStatus, ProjectMember
from app.models.reimbursement import Reimbursement, ReimbursementStatus
from app.models.time_entry import TaskTimeEntry
from app.models.timesheet import TimesheetStatus, TimesheetWeek
from app.schemas.dashboard import AdminDashboard, EmployeeDashboard
from app.services.billing import missing_projects
from app.services.dates import monday_of
from app.models.task import Task, TaskStatus
from app.services.leave import balances_for
from app.services.timer import get_open_entry


def _week_bounds() -> tuple[datetime, datetime]:
    start = monday_of(date.today())
    start_dt = datetime.combine(start, time.min, tzinfo=UTC)
    end_dt = start_dt + timedelta(days=7)
    return start_dt, end_dt


async def admin_dashboard(db: AsyncSession) -> AdminDashboard:
    start_dt, end_dt = _week_bounds()
    today = date.today()
    prev = date(today.year, today.month, 1) - timedelta(days=1)

    active_employees = (
        await db.execute(
            select(func.count()).select_from(Employee).where(Employee.status == EmployeeStatus.ACTIVE)
        )
    ).scalar_one()
    active_projects = (
        await db.execute(
            select(func.count()).select_from(Project).where(Project.status == ProjectStatus.ACTIVE)
        )
    ).scalar_one()
    pending_timesheets = (
        await db.execute(
            select(func.count())
            .select_from(TimesheetWeek)
            .where(TimesheetWeek.status == TimesheetStatus.SUBMITTED)
        )
    ).scalar_one()
    pending_leaves = (
        await db.execute(
            select(func.count()).select_from(LeaveRequest).where(LeaveRequest.status == LeaveStatus.PENDING)
        )
    ).scalar_one()
    pending_claims = (
        await db.execute(
            select(func.count())
            .select_from(Reimbursement)
            .where(Reimbursement.status == ReimbursementStatus.SUBMITTED)
        )
    ).scalar_one()
    missing = await missing_projects(db, prev.year, prev.month)

    projects = list(
        (
            await db.execute(
                select(Project).where(Project.status.in_([ProjectStatus.ACTIVE, ProjectStatus.PLANNED]))
            )
        )
        .scalars()
        .all()
    )
    hour_rows = (
        await db.execute(
            select(
                TaskTimeEntry.employee_id,
                func.coalesce(func.sum(TaskTimeEntry.duration_seconds), 0),
            )
            .where(
                TaskTimeEntry.end_time.is_not(None),
                TaskTimeEntry.start_time >= start_dt,
                TaskTimeEntry.start_time < end_dt,
            )
            .group_by(TaskTimeEntry.employee_id)
        )
    ).all()

    hours = Decimal("0.00")
    cost = Decimal("0.00")
    if hour_rows:
        emp_ids = [row[0] for row in hour_rows]
        rates = {
            emp.id: emp.hourly_cost_rate
            for emp in (await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))).scalars()
        }
        for emp_id, seconds in hour_rows:
            h = Decimal(int(seconds)) / Decimal(3600)
            hours += h
            cost += h * Decimal(rates.get(emp_id, 0))

    financials = []
    revenue = sum((p.revenue_amount for p in projects), Decimal("0.00"))
    if projects:
        project_ids = [p.id for p in projects]

        fin_stmt = (
            select(
                Task.project_id,
                TaskTimeEntry.employee_id,
                func.coalesce(func.sum(TaskTimeEntry.duration_seconds), 0),
            )
            .join(Task, Task.id == TaskTimeEntry.task_id)
            .where(
                Task.project_id.in_(project_ids),
                TaskTimeEntry.end_time.is_not(None),
            )
            .group_by(Task.project_id, TaskTimeEntry.employee_id)
        )
        fin_rows = (await db.execute(fin_stmt)).all()
        # Load rates for employees involved in these projects
        fin_emp_ids = {row[1] for row in fin_rows}
        if fin_emp_ids:
            rates_map = {
                emp.id: emp.hourly_cost_rate
                for emp in (await db.execute(select(Employee).where(Employee.id.in_(fin_emp_ids)))).scalars()
            }
        else:
            rates_map = {}
        
        project_data: dict[UUID, dict[str, Decimal]] = {
            p.id: {"hours": Decimal("0.00"), "cost": Decimal("0.00")} for p in projects
        }
        for proj_id, emp_id, seconds in fin_rows:
            h = Decimal(int(seconds)) / Decimal(3600)
            project_data[proj_id]["hours"] += h
            project_data[proj_id]["cost"] += h * Decimal(rates_map.get(emp_id, Decimal("0.00")))
        for project in projects:
            p_hours = project_data[project.id]["hours"].quantize(Decimal("0.01"))
            p_cost = project_data[project.id]["cost"].quantize(Decimal("0.01"))
            p_revenue = Decimal(project.revenue_amount)
            p_profit = (p_revenue - p_cost).quantize(Decimal("0.01"))
            financials.append(
                {
                    "id": str(project.id),
                    "name": project.name,
                    "hours": float(p_hours),
                    "cost": float(p_cost),
                    "revenue": float(p_revenue),
                    "profit": float(p_profit),
                }
            )
    return AdminDashboard(
        active_employees=active_employees,
        active_projects=active_projects,
        pending_timesheets=pending_timesheets,
        pending_leaves=pending_leaves,
        hours_this_week=hours.quantize(Decimal("0.01")),
        cost_this_week=cost.quantize(Decimal("0.01")),
        revenue_active_projects=Decimal(revenue),
        project_financials=financials,
        pending_claims=pending_claims,
        missing_billing=len(missing),
    )



async def employee_dashboard(db: AsyncSession, employee: Employee) -> EmployeeDashboard:
    start_dt, end_dt = _week_bounds()
    open_tasks = (
        await db.execute(
            select(func.count())
            .select_from(Task)
            .where(
                Task.assignee_id == employee.id,
                Task.status != TaskStatus.COMPLETED,
            )
        )
    ).scalar_one()
    seconds = (
        await db.execute(
            select(func.coalesce(func.sum(TaskTimeEntry.duration_seconds), 0)).where(
                TaskTimeEntry.employee_id == employee.id,
                TaskTimeEntry.end_time.is_not(None),
                TaskTimeEntry.start_time >= start_dt,
                TaskTimeEntry.start_time < end_dt,
            )
        )
    ).scalar_one()
    running = await get_open_entry(db, employee.id)
    balances = await balances_for(db, employee.id, date.today().year)
    project_count = (
        await db.execute(
            select(func.count()).select_from(ProjectMember).where(ProjectMember.employee_id == employee.id)
        )
    ).scalar_one()
    week = (
        await db.execute(
            select(TimesheetWeek).where(
                TimesheetWeek.employee_id == employee.id,
                TimesheetWeek.week_start == monday_of(date.today()),
            )
        )
    ).scalar_one_or_none()
    people = (
        await db.execute(
            select(func.count())
            .select_from(Employee)
            .where(Employee.reporting_manager_id == employee.id, Employee.status == EmployeeStatus.ACTIVE)
        )
    ).scalar_one() > 0
    project_hat = (
        await db.execute(select(func.count()).select_from(Project).where(Project.manager_id == employee.id))
    ).scalar_one() > 0
    pending_team_leaves = 0
    pending_team_claims = 0
    pending_team_timesheets = 0
    missing_count = 0
    if people:
        pending_team_leaves = (
            await db.execute(
                select(func.count())
                .select_from(LeaveRequest)
                .join(Employee, Employee.id == LeaveRequest.employee_id)
                .where(
                    Employee.reporting_manager_id == employee.id,
                    LeaveRequest.status == LeaveStatus.PENDING,
                )
            )
        ).scalar_one()
        pending_team_claims = (
            await db.execute(
                select(func.count())
                .select_from(Reimbursement)
                .join(Employee, Employee.id == Reimbursement.employee_id)
                .where(
                    Employee.reporting_manager_id == employee.id,
                    Reimbursement.status == ReimbursementStatus.SUBMITTED,
                )
            )
        ).scalar_one()
    if project_hat:
        managed_member_ids = (
            select(ProjectMember.employee_id)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(Project.manager_id == employee.id)
        )
        pending_team_timesheets = (
            await db.execute(
                select(func.count())
                .select_from(TimesheetWeek)
                .where(
                    TimesheetWeek.status == TimesheetStatus.SUBMITTED,
                    TimesheetWeek.employee_id.in_(managed_member_ids),
                )
            )
        ).scalar_one()
        today = date.today()
        prev = date(today.year, today.month, 1) - timedelta(days=1)
        missing_count = len(
            [p for p in await missing_projects(db, prev.year, prev.month) if p.manager_id == employee.id]
        )
    return EmployeeDashboard(
        open_tasks=open_tasks,
        hours_this_week=(Decimal(int(seconds)) / Decimal(3600)).quantize(Decimal("0.01")),
        leave_balances=[b.model_dump(mode="json") for b in balances],
        running_task_id=running.task_id if running else None,
        running_task_title=running.task.title if running else None,
        timesheet_status=week.status.value if week else TimesheetStatus.DRAFT.value,
        project_count=project_count,
        is_people_manager=people,
        is_project_manager=project_hat,
        pending_team_leaves=pending_team_leaves,
        pending_team_claims=pending_team_claims,
        pending_team_timesheets=pending_team_timesheets,
        missing_billing=missing_count,
    )