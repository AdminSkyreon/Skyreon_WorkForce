from datetime import date
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentEmployee, CurrentUser, DbSession
from app.schemas.dashboard import EmployeeDashboard
from app.schemas.employee import EmployeeOut
from app.schemas.leave import LeaveBalanceOut, LeaveCreate, LeaveRequestOut
from app.schemas.notification import NotificationOut
from app.schemas.project import ProjectOut
from app.schemas.task import TaskCreate, TaskOut
from app.schemas.timer import RunningTimer, TimerStartRequest, TimerStopRequest
from app.schemas.timesheet import ManualEntryRequest, SetDayHoursRequest, TimesheetOut
from app.services import dashboard as dashboard_service
from app.services import employees as employee_service
from app.services import leave as leave_service
from app.services import notifications as notification_service
from app.services import projects as project_service
from app.services import tasks as task_service
from app.services import timer as timer_service
from app.services import timesheets as timesheet_service

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/projects", response_model=list[ProjectOut])
async def my_projects(employee: CurrentEmployee, db: DbSession) -> list[ProjectOut]:
    projects = await project_service.list_my_projects(db, employee.id)
    return [project_service.to_project_out(project) for project in projects]


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def my_project(project_id: UUID, employee: CurrentEmployee, db: DbSession) -> ProjectOut:
    project = await project_service.assert_project_member(db, project_id, employee.id)
    return project_service.to_project_out(project)


@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
async def my_project_tasks(project_id: UUID, employee: CurrentEmployee, db: DbSession) -> list[TaskOut]:
    await project_service.assert_project_member(db, project_id, employee.id)
    return await task_service.list_project_tasks(db, project_id)


@router.post("/projects/{project_id}/tasks", response_model=TaskOut, status_code=201)
async def create_my_project_task(
    project_id: UUID, payload: TaskCreate, employee: CurrentEmployee, db: DbSession
) -> TaskOut:
    return await task_service.create_my_task(db, project_id, employee.id, payload)


@router.get("/tasks", response_model=list[TaskOut])
async def my_tasks(employee: CurrentEmployee, db: DbSession) -> list[TaskOut]:
    return await task_service.list_my_tasks(db, employee.id)


@router.get("/timer", response_model=RunningTimer)
async def my_timer(employee: CurrentEmployee, db: DbSession) -> RunningTimer:
    return await timer_service.running_timer(db, employee.id)


@router.post("/tasks/{task_id}/timer/start", response_model=RunningTimer)
async def start_timer(
    task_id: UUID, payload: TimerStartRequest, employee: CurrentEmployee, db: DbSession
) -> RunningTimer:
    return await timer_service.start_timer(db, employee.id, task_id, payload.pause_current)


@router.post("/tasks/{task_id}/timer/pause", response_model=RunningTimer)
async def pause_timer(task_id: UUID, employee: CurrentEmployee, db: DbSession) -> RunningTimer:
    return await timer_service.pause_timer(db, employee.id, task_id)


@router.post("/tasks/{task_id}/timer/resume", response_model=RunningTimer)
async def resume_timer(
    task_id: UUID, payload: TimerStartRequest, employee: CurrentEmployee, db: DbSession
) -> RunningTimer:
    return await timer_service.resume_timer(db, employee.id, task_id, payload.pause_current)


@router.post("/tasks/{task_id}/timer/stop", response_model=RunningTimer)
async def stop_timer(
    task_id: UUID, payload: TimerStopRequest, employee: CurrentEmployee, db: DbSession
) -> RunningTimer:
    return await timer_service.stop_timer(db, employee.id, task_id, payload.note)


@router.get("/timesheets", response_model=TimesheetOut)
async def my_timesheet(
    employee: CurrentEmployee,
    db: DbSession,
    week_start: date | None = None,
) -> TimesheetOut:
    return await timesheet_service.build_timesheet(db, employee, week_start or date.today())


@router.get("/timesheets/month", response_model=list[TimesheetOut])
async def my_timesheet_month(
    employee: CurrentEmployee,
    db: DbSession,
    year: int,
    month: int,
) -> list[TimesheetOut]:
    return await timesheet_service.my_month(db, employee, year, month)


@router.post("/timesheets/entries", response_model=TimesheetOut)
async def add_manual_entry(
    payload: ManualEntryRequest, employee: CurrentEmployee, db: DbSession
) -> TimesheetOut:
    return await timesheet_service.add_manual_entry(db, employee, payload)


@router.put("/timesheets/day", response_model=TimesheetOut)
async def set_timesheet_day(
    payload: SetDayHoursRequest, employee: CurrentEmployee, db: DbSession
) -> TimesheetOut:
    return await timesheet_service.set_day_hours(db, employee, payload)


@router.post("/timesheets/submit", response_model=TimesheetOut)
async def submit_timesheet(
    employee: CurrentEmployee,
    db: DbSession,
    week_start: date | None = None,
) -> TimesheetOut:
    result = await timesheet_service.submit_week(db, employee, week_start or date.today())
    await notification_service.notify_admins(
        db,
        "timesheet_submitted",
        "Timesheet submitted",
        f"{employee.name} submitted the week of {result.week_start}.",
        "/admin/timesheets",
    )
    await db.commit()
    return result


@router.get("/leave", response_model=list[LeaveRequestOut])
async def my_leave(employee: CurrentEmployee, db: DbSession) -> list[LeaveRequestOut]:
    return await leave_service.list_my_leave(db, employee.id)


@router.post("/leave", response_model=LeaveRequestOut, status_code=201)
async def apply_leave(
    payload: LeaveCreate, employee: CurrentEmployee, db: DbSession
) -> LeaveRequestOut:
    result = await leave_service.apply_leave(db, employee, payload)
    if employee.reporting_manager_id:
        manager = await employee_service.get_employee(db, employee.reporting_manager_id)
        await notification_service.notify(
            db,
            manager.user_id,
            "leave_submitted",
            "Leave to review",
            f"{employee.name} requested leave from {result.start_date}.",
            "/employee/team",
        )
    else:
        await notification_service.notify_admins(
            db,
            "leave_submitted",
            "New leave request",
            f"{employee.name} requested leave from {result.start_date}.",
            "/admin/leave",
        )
    await db.commit()
    return result


@router.post("/leave/{request_id}/cancel", response_model=LeaveRequestOut)
async def cancel_leave(
    request_id: UUID, employee: CurrentEmployee, db: DbSession
) -> LeaveRequestOut:
    return await leave_service.cancel_leave(db, employee.id, request_id)


@router.get("/leave/balances", response_model=list[LeaveBalanceOut])
async def my_balances(
    employee: CurrentEmployee,
    db: DbSession,
    year: int | None = None,
) -> list[LeaveBalanceOut]:
    return await leave_service.balances_for(db, employee.id, year or date.today().year)


@router.get("/notifications", response_model=list[NotificationOut])
async def my_notifications(user: CurrentUser, db: DbSession) -> list[NotificationOut]:
    return await notification_service.list_notifications(db, user.id)


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
async def read_notification(
    notification_id: UUID, user: CurrentUser, db: DbSession
) -> NotificationOut:
    return await notification_service.mark_read(db, user.id, notification_id)


@router.get("/team", response_model=list[EmployeeOut])
async def my_team(employee: CurrentEmployee, db: DbSession) -> list[EmployeeOut]:
    reports = await employee_service.list_reports(db, employee.id)
    return [employee_service.to_employee_out(item) for item in reports]


@router.get("/dashboard", response_model=EmployeeDashboard)
async def my_dashboard(employee: CurrentEmployee, db: DbSession) -> EmployeeDashboard:
    return await dashboard_service.employee_dashboard(db, employee)
