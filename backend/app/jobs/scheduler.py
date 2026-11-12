import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.employee import Employee, EmployeeStatus
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.timesheet import TimesheetStatus, TimesheetWeek
from app.models.project import Project
from app.models.user import User, UserRole
from app.services.billing import missing_projects
from app.services.dates import monday_of
from app.services.notifications import notify, notify_admins

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="UTC")


async def remind_unsubmitted_timesheets() -> None:
    week_start = monday_of(date.today())
    async with SessionLocal() as db:
        employees = (
            await db.execute(select(Employee).where(Employee.status == EmployeeStatus.ACTIVE))
        ).scalars().all()
        submitted_ids = set(
            (
                await db.execute(
                    select(TimesheetWeek.employee_id).where(
                        TimesheetWeek.week_start == week_start,
                        TimesheetWeek.status.in_(
                            [TimesheetStatus.SUBMITTED, TimesheetStatus.APPROVED]
                        ),
                    )
                )
            ).scalars().all()
        )
        for employee in employees:
            if employee.id in submitted_ids:
                continue
            await notify(
                db,
                employee.user_id,
                "timesheet_reminder",
                "Submit your timesheet",
                f"Please submit your timesheet for the week of {week_start}.",
                "/employee/timesheet",
            )
        await db.commit()


async def remind_pending_approvals() -> None:
    async with SessionLocal() as db:
        ts_count = len(
            list(
                (
                    await db.execute(
                        select(TimesheetWeek).where(TimesheetWeek.status == TimesheetStatus.SUBMITTED)
                    )
                ).scalars().all()
            )
        )
        leave_count = len(
            list(
                (
                    await db.execute(
                        select(LeaveRequest).where(LeaveRequest.status == LeaveStatus.PENDING)
                    )
                ).scalars().all()
            )
        )
        if ts_count == 0 and leave_count == 0:
            return
        admins = (
            await db.execute(
                select(User).where(
                    User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]),
                    User.is_active.is_(True),
                )
            )
        ).scalars().all()
        body = f"{ts_count} timesheet(s) and {leave_count} leave request(s) await review."
        for admin in admins:
            await notify(
                db,
                admin.id,
                "approval_reminder",
                "Pending approvals",
                body,
                "/admin/timesheets",
            )
        await db.commit()


async def remind_missing_billing() -> None:
    today = date.today()
    prev = date(today.year, today.month, 1)
    prev = prev.replace(day=1)
    from datetime import timedelta as _td

    last_month = (date(today.year, today.month, 1) - _td(days=1))
    async with SessionLocal() as db:
        missing = await missing_projects(db, last_month.year, last_month.month)
        if not missing:
            return
        label = last_month.strftime("%B %Y")
        for project in missing:
            title = f"Billing not added for {project.name} — {label}"
            body = f"Enter monthly billing for {project.name}."
            if project.manager and project.manager.user_id:
                await notify(
                    db,
                    project.manager.user_id,
                    "billing_missing",
                    title,
                    body,
                    "/employee/billing",
                )
            await notify_admins(db, "billing_missing", title, body, "/admin/billing")
        await db.commit()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        remind_unsubmitted_timesheets,
        "cron",
        day_of_week="fri",
        hour=16,
        minute=0,
        id="timesheet_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        remind_pending_approvals,
        "cron",
        hour=9,
        minute=0,
        id="approval_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        remind_missing_billing,
        "cron",
        day=1,
        hour=6,
        minute=0,
        id="billing_reminder",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
