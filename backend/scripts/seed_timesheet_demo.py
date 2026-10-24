"""Idempotent demo data: 11 employees, 3 projects, mixed timesheet statuses."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.employee import Employee, EmployeeStatus
from app.models.project import ContractType, Project, ProjectMember, ProjectStatus
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.time_entry import TaskTimeEntry, TimeEntrySource
from app.models.timesheet import TimesheetStatus, TimesheetWeek
from app.models.user import User, UserRole

UTC = ZoneInfo("UTC")
PASSWORD = "DemoPass123!"
WEEK = date(2026, 10, 19)

PEOPLE = [
    ("Alan Turing", "alan@skyreon.com", "EMP-ALAN", "Engineer", "Engineering", "90"),
    ("Ada Lovelace", "ada@skyreon.com", "EMP-ADA", "Engineer", "Engineering", "95"),
    ("Katherine Johnson", "katherine@skyreon.com", "EMP-KATH", "Analyst", "Delivery", "88"),
    ("Margaret Hamilton", "margaret@skyreon.com", "EMP-MARG", "Lead", "Engineering", "110"),
    ("Tim Berners-Lee", "tim@skyreon.com", "EMP-TIM", "Engineer", "Engineering", "92"),
    ("Linus Torvalds", "linus@skyreon.com", "EMP-LINUS", "Engineer", "Engineering", "105"),
    ("Barbara Liskov", "barbara@skyreon.com", "EMP-BARB", "Architect", "Engineering", "108"),
    ("Donald Knuth", "donald@skyreon.com", "EMP-DON", "Engineer", "Engineering", "100"),
    ("Radia Perlman", "radia@skyreon.com", "EMP-RADIA", "Engineer", "Networking", "96"),
    ("Vint Cerf", "vint@skyreon.com", "EMP-VINT", "Engineer", "Networking", "98"),
]

PROJECTS = [
    ("Portal", "Skyreon", "PRJ-PORTAL", ["alan@skyreon.com", "tim@skyreon.com", "donald@skyreon.com", "grace@skyreon.com"]),
    ("Atlas CRM", "Northwind", "PRJ-ATLAS", ["ada@skyreon.com", "katherine@skyreon.com", "barbara@skyreon.com", "radia@skyreon.com", "alan@skyreon.com"]),
    ("Helix Mobile", "Contoso", "PRJ-HELIX", ["margaret@skyreon.com", "linus@skyreon.com", "donald@skyreon.com", "vint@skyreon.com", "katherine@skyreon.com"]),
]


async def get_or_create_employee(db, name: str, email: str, code: str, designation: str, department: str, rate: str) -> Employee:
    existing = (await db.execute(select(Employee).where(Employee.employee_code == code))).scalar_one_or_none()
    if existing:
        return existing
    user = User(
        email=email,
        password_hash=hash_password(PASSWORD),
        role=UserRole.EMPLOYEE,
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.flush()
    employee = Employee(
        user_id=user.id,
        name=name,
        employee_code=code,
        designation=designation,
        department=department,
        joining_date=date(2024, 1, 8),
        hourly_cost_rate=Decimal(rate),
        status=EmployeeStatus.ACTIVE,
    )
    db.add(employee)
    await db.flush()
    return employee


async def get_or_create_project(db, name: str, client: str, code: str, manager_id, member_ids: list) -> Project:
    existing = (await db.execute(select(Project).where(Project.project_code == code))).scalar_one_or_none()
    if existing:
        return existing
    project = Project(
        name=name,
        client_name=client,
        project_code=code,
        description=f"{name} delivery",
        manager_id=manager_id,
        start_date=date(2026, 9, 1),
        status=ProjectStatus.ACTIVE,
        contract_type=ContractType.TIME_AND_MATERIAL,
        revenue_amount=Decimal("120000"),
        budgeted_hours=Decimal("800"),
    )
    db.add(project)
    await db.flush()
    for employee_id in {manager_id, *member_ids}:
        db.add(ProjectMember(project_id=project.id, employee_id=employee_id))
    await db.flush()
    return project


async def ensure_task(db, project: Project, employee: Employee, title: str) -> Task:
    existing = (
        await db.execute(
            select(Task).where(Task.project_id == project.id, Task.assignee_id == employee.id, Task.title == title)
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    task = Task(
        project_id=project.id,
        title=title,
        description="",
        priority=TaskPriority.MEDIUM,
        estimated_hours=Decimal("40"),
        assignee_id=employee.id,
        status=TaskStatus.IN_PROGRESS,
    )
    db.add(task)
    await db.flush()
    return task


async def add_hours(db, task: Task, employee: Employee, work_date: date, hours: float) -> None:
    start = datetime.combine(work_date, time(9, 0), tzinfo=UTC)
    seconds = int(hours * 3600)
    exists = (
        await db.execute(
            select(TaskTimeEntry).where(
                TaskTimeEntry.task_id == task.id,
                TaskTimeEntry.employee_id == employee.id,
                TaskTimeEntry.start_time == start,
            )
        )
    ).scalar_one_or_none()
    if exists:
        return
    db.add(
        TaskTimeEntry(
            task_id=task.id,
            employee_id=employee.id,
            start_time=start,
            end_time=start + timedelta(seconds=seconds),
            duration_seconds=seconds,
            source=TimeEntrySource.MANUAL,
            manual_reason="Demo week",
            note="Demo week",
        )
    )


async def ensure_week(db, employee: Employee, week_start: date, status: TimesheetStatus, comment: str = "") -> None:
    week = (
        await db.execute(
            select(TimesheetWeek).where(TimesheetWeek.employee_id == employee.id, TimesheetWeek.week_start == week_start)
        )
    ).scalar_one_or_none()
    if week:
        week.status = status
        week.comment = comment
        return
    db.add(TimesheetWeek(employee_id=employee.id, week_start=week_start, status=status, comment=comment))


async def main() -> None:
    async with SessionLocal() as db:
        people: dict[str, Employee] = {}
        grace = (await db.execute(select(Employee).where(Employee.employee_code == "EMP-GRACE"))).scalar_one_or_none()
        if grace:
            people["grace@skyreon.com"] = grace
        for name, email, code, designation, department, rate in PEOPLE:
            people[email] = await get_or_create_employee(db, name, email, code, designation, department, rate)

        manager_id = next(iter(people.values())).id
        projects: dict[str, Project] = {}
        for name, client, code, members in PROJECTS:
            member_ids = [people[email].id for email in members if email in people]
            projects[code] = await get_or_create_project(db, name, client, code, manager_id, member_ids)

        assignments = [
            ("grace@skyreon.com", "PRJ-PORTAL", "Build UI", [(WEEK, 6), (WEEK + timedelta(days=1), 7.5)], TimesheetStatus.APPROVED, "Looks good for this week."),
            ("alan@skyreon.com", "PRJ-PORTAL", "Auth module", [(WEEK, 8), (WEEK + timedelta(days=1), 8), (WEEK + timedelta(days=2), 4)], TimesheetStatus.SUBMITTED, ""),
            ("alan@skyreon.com", "PRJ-ATLAS", "CRM search", [(WEEK + timedelta(days=3), 6)], TimesheetStatus.SUBMITTED, ""),
            ("ada@skyreon.com", "PRJ-ATLAS", "Pipeline board", [(WEEK, 7), (WEEK + timedelta(days=1), 7), (WEEK + timedelta(days=2), 7)], TimesheetStatus.SUBMITTED, ""),
            ("katherine@skyreon.com", "PRJ-ATLAS", "Forecast model", [(WEEK, 8), (WEEK + timedelta(days=1), 6)], TimesheetStatus.SUBMITTED, ""),
            ("katherine@skyreon.com", "PRJ-HELIX", "Metrics sync", [(WEEK + timedelta(days=2), 5)], TimesheetStatus.SUBMITTED, ""),
            ("margaret@skyreon.com", "PRJ-HELIX", "Release checklist", [(WEEK, 8), (WEEK + timedelta(days=1), 8), (WEEK + timedelta(days=2), 8)], TimesheetStatus.APPROVED, "On track."),
            ("tim@skyreon.com", "PRJ-PORTAL", "Content API", [(WEEK, 6), (WEEK + timedelta(days=2), 6), (WEEK + timedelta(days=3), 6)], TimesheetStatus.SUBMITTED, ""),
            ("linus@skyreon.com", "PRJ-HELIX", "Native build", [(WEEK, 8), (WEEK + timedelta(days=1), 8)], TimesheetStatus.REJECTED, "Split the weekend hours."),
            ("barbara@skyreon.com", "PRJ-ATLAS", "Domain model", [(WEEK, 7.5), (WEEK + timedelta(days=1), 7.5), (WEEK + timedelta(days=4), 4)], TimesheetStatus.SUBMITTED, ""),
            ("donald@skyreon.com", "PRJ-PORTAL", "Docs site", [(WEEK, 4), (WEEK + timedelta(days=1), 4)], TimesheetStatus.SUBMITTED, ""),
            ("donald@skyreon.com", "PRJ-HELIX", "Perf pass", [(WEEK + timedelta(days=3), 8)], TimesheetStatus.SUBMITTED, ""),
            ("radia@skyreon.com", "PRJ-ATLAS", "Network layer", [(WEEK, 8), (WEEK + timedelta(days=2), 8), (WEEK + timedelta(days=3), 8)], TimesheetStatus.APPROVED, ""),
            ("vint@skyreon.com", "PRJ-HELIX", "Protocol tests", [(WEEK, 5), (WEEK + timedelta(days=1), 5), (WEEK + timedelta(days=4), 6)], TimesheetStatus.SUBMITTED, ""),
        ]

        week_status: dict[tuple[str, date], tuple[TimesheetStatus, str]] = {}
        for email, project_code, title, days, status, comment in assignments:
            employee = people[email]
            task = await ensure_task(db, projects[project_code], employee, title)
            for work_date, hours in days:
                await add_hours(db, task, employee, work_date, hours)
            week_status[(email, WEEK)] = (status, comment)

        for (email, week_start), (status, comment) in week_status.items():
            await ensure_week(db, people[email], week_start, status, comment)

        await db.commit()
        print(f"Seeded {len(people)} employees across {len(projects)} projects for week {WEEK.isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
