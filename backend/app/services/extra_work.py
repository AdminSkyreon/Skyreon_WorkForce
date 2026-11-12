from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequest, Forbidden, NotFound
from app.models.employee import Employee, PayType
from app.models.extra_work import (
    COMP_OFF_CODE,
    ExtraWorkDay,
    ExtraWorkKind,
    ExtraWorkSettlement,
    ExtraWorkStatus,
    LeaveCredit,
)
from app.models.leave import LeaveType
from app.models.payroll import PayrollAdjustment
from app.models.time_entry import TaskTimeEntry
from app.models.timesheet import TimesheetWeek
from app.models.user import User, is_staff
from app.schemas.extra_work import ExtraWorkApprove, ExtraWorkDefaults, ExtraWorkOut
from app.services.audit import log_audit
from app.services.dates import is_weekend, monday_of, week_days
from app.services.holidays import holiday_dates
from app.services.payroll import STANDARD_DAY_HOURS, _working_days_in_month, is_closed

UTC = ZoneInfo("UTC")
HOLIDAY_MULTIPLIER = Decimal("2.00")


def _money(value: Decimal | int | float) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _comp_days(hours: Decimal) -> Decimal:
    return _money(hours / STANDARD_DAY_HOURS)


def to_out(row: ExtraWorkDay) -> ExtraWorkOut:
    return ExtraWorkOut(
        id=row.id,
        employee_id=row.employee_id,
        employee_name=row.employee.name if row.employee else None,
        work_date=row.work_date,
        hours=row.hours,
        kind=row.kind,
        status=row.status,
        settlement=row.settlement,
        comp_off_days=row.comp_off_days,
        extra_pay_amount=row.extra_pay_amount,
        payroll_year=row.payroll_year,
        payroll_month=row.payroll_month,
        comment=row.comment,
    )


async def _load(db: AsyncSession, row_id: UUID, *, for_update: bool = False) -> ExtraWorkDay:
    stmt = (
        select(ExtraWorkDay)
        .options(selectinload(ExtraWorkDay.employee))
        .where(ExtraWorkDay.id == row_id)
    )
    if for_update:
        stmt = stmt.with_for_update()
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFound("Extra work record not found")
    return row


async def comp_off_type(db: AsyncSession) -> LeaveType:
    row = (await db.execute(select(LeaveType).where(LeaveType.code == COMP_OFF_CODE))).scalar_one_or_none()
    if row is None:
        raise BadRequest("Comp Off leave type is not configured")
    return row


async def credit_balance(db: AsyncSession, employee_id: UUID, leave_type_id: UUID) -> Decimal:
    total = (
        await db.execute(
            select(func.coalesce(func.sum(LeaveCredit.days), 0)).where(
                LeaveCredit.employee_id == employee_id,
                LeaveCredit.leave_type_id == leave_type_id,
            )
        )
    ).scalar()
    return _money(total)


async def _hours_by_date(db: AsyncSession, employee_id: UUID, start: date, end: date) -> dict[date, Decimal]:
    entries = (
        await db.execute(
            select(TaskTimeEntry)
            .where(
                TaskTimeEntry.employee_id == employee_id,
                TaskTimeEntry.end_time.is_not(None),
                TaskTimeEntry.start_time >= datetime.combine(start, time.min, tzinfo=UTC),
                TaskTimeEntry.start_time < datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC),
            )
        )
    ).scalars().all()
    totals: dict[date, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for entry in entries:
        day = entry.start_time.astimezone(UTC).date()
        totals[day] += Decimal(entry.duration_seconds) / Decimal(3600)
    return {day: _money(hours) for day, hours in totals.items()}


async def sync_from_timesheet_week(db: AsyncSession, employee: Employee, week_start: date, week: TimesheetWeek) -> int:
    start = monday_of(week_start)
    days = week_days(start)
    end = days[-1]
    hours_map = await _hours_by_date(db, employee.id, start, end)
    holidays = await holiday_dates(db, start, end, employee.location_id)
    created = 0
    for day in days:
        hours = hours_map.get(day, Decimal("0.00"))
        if hours <= 0:
            continue
        on_weekend = is_weekend(day)
        on_holiday = day in holidays
        if not on_weekend and not on_holiday:
            continue
        kind = ExtraWorkKind.HOLIDAY if on_holiday else ExtraWorkKind.WEEKEND
        existing = (
            await db.execute(
                select(ExtraWorkDay).where(ExtraWorkDay.employee_id == employee.id, ExtraWorkDay.work_date == day)
            )
        ).scalar_one_or_none()
        if existing and existing.status == ExtraWorkStatus.APPROVED:
            continue
        if existing is None:
            db.add(
                ExtraWorkDay(
                    employee_id=employee.id,
                    work_date=day,
                    hours=hours,
                    kind=kind,
                    timesheet_week_id=week.id,
                    status=ExtraWorkStatus.PENDING,
                )
            )
            created += 1
        else:
            existing.hours = hours
            existing.kind = kind
            existing.timesheet_week_id = week.id
            existing.status = ExtraWorkStatus.PENDING
            existing.settlement = None
            existing.comp_off_days = Decimal("0.00")
            existing.extra_pay_amount = Decimal("0.00")
            existing.payroll_year = None
            existing.payroll_month = None
            existing.reviewer_id = None
            existing.comment = ""
    await db.flush()
    return created


async def suggest_settlement(db: AsyncSession, row: ExtraWorkDay) -> ExtraWorkDefaults:
    employee = (
        await db.execute(
            select(Employee).options(selectinload(Employee.payroll)).where(Employee.id == row.employee_id)
        )
    ).scalar_one()
    comp_days = _comp_days(row.hours)
    year, month = row.work_date.year, row.work_date.month
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    if employee.pay_type == PayType.HOURLY:
        rate = employee.payroll.hourly_pay_rate if employee.payroll else Decimal("0.00")
        pay = _money(row.hours * rate * HOLIDAY_MULTIPLIER)
    else:
        basic = employee.payroll.basic_salary if employee.payroll else Decimal("0.00")
        hra = employee.payroll.hra if employee.payroll else Decimal("0.00")
        allowances = employee.payroll.allowances if employee.payroll else Decimal("0.00")
        package = basic + hra + allowances
        working = await _working_days_in_month(db, employee, start, end)
        daily = _money(package / working) if working > 0 else Decimal("0.00")
        pay = _money(daily * comp_days)
    return ExtraWorkDefaults(comp_off_days=comp_days, extra_pay_amount=pay)


def can_review(user: User, row: ExtraWorkDay) -> bool:
    if is_staff(user):
        return True
    return bool(user.employee and row.employee.reporting_manager_id == user.employee.id)


async def list_queue(
    db: AsyncSession, user: User, status: ExtraWorkStatus | None = None
) -> list[ExtraWorkOut]:
    stmt = (
        select(ExtraWorkDay)
        .options(selectinload(ExtraWorkDay.employee))
        .order_by(ExtraWorkDay.work_date.desc())
    )
    if status:
        stmt = stmt.where(ExtraWorkDay.status == status)
    if is_staff(user):
        pass
    elif user.employee:
        stmt = stmt.join(Employee, Employee.id == ExtraWorkDay.employee_id).where(
            Employee.reporting_manager_id == user.employee.id
        )
    else:
        return []
    rows = list((await db.execute(stmt)).scalars().unique().all())
    return [to_out(row) for row in rows]


async def defaults_for(db: AsyncSession, user: User, row_id: UUID) -> ExtraWorkDefaults:
    row = await _load(db, row_id)
    if user.employee and row.employee_id == user.employee.id:
        raise Forbidden("You cannot review your own extra work")
    if not can_review(user, row):
        raise Forbidden("You cannot view this extra work")
    return await suggest_settlement(db, row)


async def list_mine(db: AsyncSession, employee_id: UUID) -> list[ExtraWorkOut]:
    rows = list(
        (
            await db.execute(
                select(ExtraWorkDay)
                .options(selectinload(ExtraWorkDay.employee))
                .where(ExtraWorkDay.employee_id == employee_id)
                .order_by(ExtraWorkDay.work_date.desc())
            )
        ).scalars().all()
    )
    return [to_out(row) for row in rows]


async def _add_extra_work_pay(db: AsyncSession, employee_id: UUID, year: int, month: int, amount: Decimal) -> None:
    row = (
        await db.execute(
            select(PayrollAdjustment).where(
                PayrollAdjustment.employee_id == employee_id,
                PayrollAdjustment.year == year,
                PayrollAdjustment.month == month,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = PayrollAdjustment(employee_id=employee_id, year=year, month=month)
        db.add(row)
    row.extra_work_pay = _money(row.extra_work_pay + amount)


async def approve(
    db: AsyncSession, user: User, row_id: UUID, data: ExtraWorkApprove
) -> ExtraWorkOut:
    row = await _load(db, row_id, for_update=True)
    if row.status != ExtraWorkStatus.PENDING:
        raise BadRequest("Only pending extra work can be approved")
    if user.employee and row.employee_id == user.employee.id:
        raise Forbidden("You cannot approve your own extra work")
    if not can_review(user, row):
        raise Forbidden("You cannot approve this extra work")
    defaults = await suggest_settlement(db, row)
    if data.settlement == ExtraWorkSettlement.COMP_OFF:
        comp_days = _money(data.comp_off_days if data.comp_off_days is not None else defaults.comp_off_days)
        if comp_days <= 0:
            raise BadRequest("Comp-off days must be greater than zero")
        leave_type = await comp_off_type(db)
        db.add(
            LeaveCredit(
                employee_id=row.employee_id,
                leave_type_id=leave_type.id,
                days=comp_days,
                extra_work_day_id=row.id,
                note=f"Extra work on {row.work_date.isoformat()}",
            )
        )
        row.comp_off_days = comp_days
        row.extra_pay_amount = Decimal("0.00")
    else:
        amount = _money(data.extra_pay_amount if data.extra_pay_amount is not None else defaults.extra_pay_amount)
        if amount <= 0:
            raise BadRequest("Extra pay amount must be greater than zero")
        year, month = row.work_date.year, row.work_date.month
        if await is_closed(db, year, month):
            raise BadRequest("Payroll for that month is closed. Re-open it before approving extra pay.")
        await _add_extra_work_pay(db, row.employee_id, year, month, amount)
        row.extra_pay_amount = amount
        row.payroll_year = year
        row.payroll_month = month
        row.comp_off_days = Decimal("0.00")
    row.status = ExtraWorkStatus.APPROVED
    row.settlement = data.settlement
    row.comment = data.comment
    row.reviewer_id = user.employee.id if user.employee else None
    await log_audit(
        db,
        user,
        "approved",
        "extra_work_day",
        str(row.id),
        summary=f"{data.settlement.value} for {row.work_date}",
    )
    await db.commit()
    return to_out(await _load(db, row_id))


async def reject(db: AsyncSession, user: User, row_id: UUID, comment: str) -> ExtraWorkOut:
    row = await _load(db, row_id)
    if row.status != ExtraWorkStatus.PENDING:
        raise BadRequest("Only pending extra work can be rejected")
    if user.employee and row.employee_id == user.employee.id:
        raise Forbidden("You cannot reject your own extra work")
    if not can_review(user, row):
        raise Forbidden("You cannot reject this extra work")
    row.status = ExtraWorkStatus.REJECTED
    row.comment = comment
    row.reviewer_id = user.employee.id if user.employee else None
    await db.commit()
    return to_out(await _load(db, row_id))
