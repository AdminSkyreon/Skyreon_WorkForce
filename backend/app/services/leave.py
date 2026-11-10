from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequest, Forbidden, NotFound
from app.models.employee import Employee
from app.models.extra_work import COMP_OFF_CODE, LeaveCredit
from app.models.leave import LeaveAccrualMode, LeaveRequest, LeaveStatus, LeaveType
from app.models.user import User, is_staff
from app.schemas.leave import (
    AdminLeaveCreate,
    LeaveBalanceOut,
    LeaveCreate,
    LeaveRequestOut,
    LeaveTypeCreate,
    LeaveTypeUpdate,
)
from app.services.dates import is_weekend
from app.services.holidays import holiday_dates

LWP_CODE = "LWP"


def _money(value: Decimal | int | float) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _allocated_for_year(leave_type: LeaveType, year: int, as_of: date | None = None) -> Decimal:
    today = as_of or date.today()
    if leave_type.accrual_mode == LeaveAccrualMode.MONTHLY:
        months = today.month if year == today.year else 12
        earned = _money(leave_type.days_per_month * months)
        cap = Decimal(leave_type.annual_allocation_days)
        return _money(min(earned, cap))
    return Decimal(leave_type.annual_allocation_days)


def _validate_accrual(annual: int, mode: LeaveAccrualMode, days_per_month: Decimal) -> None:
    if mode == LeaveAccrualMode.MONTHLY and days_per_month > Decimal(annual):
        raise BadRequest("Days per month cannot exceed the annual cap")


async def working_days(
    db: AsyncSession,
    start: date,
    end: date,
    half_day: bool,
    location_id: UUID | None = None,
) -> Decimal:
    if end < start:
        raise BadRequest("End date must be on or after start date")
    holidays = await holiday_dates(db, start, end, location_id)
    days = 0
    cursor = start
    while cursor <= end:
        if not is_weekend(cursor) and cursor not in holidays:
            days += 1
        cursor += timedelta(days=1)
    if half_day:
        if start != end:
            raise BadRequest("Half-day leave must be a single date")
        return Decimal("0.5") if days > 0 else Decimal("0")
    return Decimal(days)


def to_leave_out(req: LeaveRequest, days: Decimal) -> LeaveRequestOut:
    return LeaveRequestOut(
        id=req.id,
        employee_id=req.employee_id,
        employee_name=req.employee.name if req.employee else None,
        leave_type_id=req.leave_type_id,
        leave_type_name=req.leave_type.name if req.leave_type else None,
        start_date=req.start_date,
        end_date=req.end_date,
        is_half_day=req.is_half_day,
        days=days,
        reason=req.reason,
        status=req.status,
        reviewer_id=req.reviewer_id,
        comment=req.comment,
    )


async def list_leave_types(db: AsyncSession) -> list[LeaveType]:
    result = await db.execute(select(LeaveType).order_by(LeaveType.name))
    return list(result.scalars().all())


async def create_leave_type(db: AsyncSession, data: LeaveTypeCreate) -> LeaveType:
    existing = await db.execute(select(LeaveType).where(LeaveType.code == data.code.upper()))
    if existing.scalar_one_or_none():
        raise BadRequest("Leave type code already exists")
    code = data.code.upper()
    if code == COMP_OFF_CODE:
        raise BadRequest("Comp Off is managed by the system")
    mode = data.accrual_mode
    days_per_month = _money(data.days_per_month)
    if code == LWP_CODE:
        mode = LeaveAccrualMode.LUMP
        days_per_month = Decimal("0.00")
    _validate_accrual(data.annual_allocation_days, mode, days_per_month)
    leave_type = LeaveType(
        name=data.name,
        code=code,
        annual_allocation_days=data.annual_allocation_days,
        is_unpaid=data.is_unpaid or code == LWP_CODE,
        accrual_mode=mode,
        days_per_month=days_per_month,
    )
    db.add(leave_type)
    await db.commit()
    await db.refresh(leave_type)
    return leave_type


async def update_leave_type(db: AsyncSession, type_id: UUID, data: LeaveTypeUpdate) -> LeaveType:
    leave_type = await db.get(LeaveType, type_id)
    if leave_type is None:
        raise NotFound("Leave type not found")
    if data.name is not None:
        leave_type.name = data.name
    if leave_type.code == COMP_OFF_CODE:
        if any(
            v is not None
            for v in (
                data.annual_allocation_days,
                data.accrual_mode,
                data.days_per_month,
                data.is_unpaid,
            )
        ):
            raise BadRequest("Comp Off accrual settings cannot be changed")
    elif leave_type.code == LWP_CODE:
        leave_type.is_unpaid = True
        leave_type.annual_allocation_days = 0
        leave_type.accrual_mode = LeaveAccrualMode.LUMP
        leave_type.days_per_month = Decimal("0.00")
    else:
        if data.annual_allocation_days is not None:
            leave_type.annual_allocation_days = data.annual_allocation_days
        if data.is_unpaid is not None:
            leave_type.is_unpaid = data.is_unpaid
        if data.accrual_mode is not None:
            leave_type.accrual_mode = data.accrual_mode
        if data.days_per_month is not None:
            leave_type.days_per_month = _money(data.days_per_month)
        _validate_accrual(
            leave_type.annual_allocation_days,
            leave_type.accrual_mode,
            leave_type.days_per_month,
        )
    await db.commit()
    await db.refresh(leave_type)
    return leave_type


async def _load_request(db: AsyncSession, request_id: UUID) -> LeaveRequest:
    result = await db.execute(
        select(LeaveRequest)
        .options(
            selectinload(LeaveRequest.employee).selectinload(Employee.user),
            selectinload(LeaveRequest.leave_type),
        )
        .where(LeaveRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if req is None:
        raise NotFound("Leave request not found")
    return req


async def _overlaps(
    db: AsyncSession, employee_id: UUID, start: date, end: date, exclude_id: UUID | None = None
) -> None:
    stmt = select(LeaveRequest).where(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
        LeaveRequest.start_date <= end,
        LeaveRequest.end_date >= start,
    )
    if exclude_id:
        stmt = stmt.where(LeaveRequest.id != exclude_id)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise BadRequest("Leave overlaps an existing pending or approved request")


async def _credit_balance(db: AsyncSession, employee_id: UUID, leave_type_id: UUID) -> Decimal:
    total = (
        await db.execute(
            select(func.coalesce(func.sum(LeaveCredit.days), 0)).where(
                LeaveCredit.employee_id == employee_id,
                LeaveCredit.leave_type_id == leave_type_id,
            )
        )
    ).scalar()
    return Decimal(str(total or 0)).quantize(Decimal("0.01"))


async def _consume_comp_off(db: AsyncSession, employee_id: UUID, leave_type: LeaveType, days: Decimal) -> None:
    if leave_type.code != COMP_OFF_CODE:
        return
    db.add(
        LeaveCredit(
            employee_id=employee_id,
            leave_type_id=leave_type.id,
            days=-days,
            note="Comp-off leave approved",
        )
    )


async def apply_leave(db: AsyncSession, employee: Employee, data: LeaveCreate) -> LeaveRequestOut:
    if not getattr(employee, "allow_leave", True):
        raise BadRequest("This contractor does not have staff leave")

    if data.start_date < date.today():
        raise BadRequest("Cannot apply leave for a past date")
    
    leave_type = await db.get(LeaveType, data.leave_type_id)
    if leave_type is None:
        raise NotFound("Leave type not found")
    days = await working_days(db, data.start_date, data.end_date, data.is_half_day, employee.location_id)
    if days <= 0:
        raise BadRequest("Leave request has no working days")
    await _overlaps(db, employee.id, data.start_date, data.end_date)
    balances = await balances_for(db, employee.id, data.start_date.year)
    match = next((b for b in balances if b.leave_type_id == leave_type.id), None)
    if not leave_type.is_unpaid:
        if match and days > match.available:
            raise BadRequest("Insufficient leave balance")
    req = LeaveRequest(
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=data.start_date,
        end_date=data.end_date,
        is_half_day=data.is_half_day,
        reason=data.reason,
        status=LeaveStatus.PENDING,
    )
    db.add(req)
    await db.commit()
    loaded = await _load_request(db, req.id)
    return to_leave_out(loaded, days)


async def list_my_leave(db: AsyncSession, employee_id: UUID) -> list[LeaveRequestOut]:
    result = await db.execute(
        select(LeaveRequest)
        .options(selectinload(LeaveRequest.employee), selectinload(LeaveRequest.leave_type))
        .where(LeaveRequest.employee_id == employee_id)
        .order_by(LeaveRequest.start_date.desc())
    )
    outs: list[LeaveRequestOut] = []
    for req in result.scalars().all():
        days = await working_days(
            db, req.start_date, req.end_date, req.is_half_day, req.employee.location_id if req.employee else None
        )
        outs.append(to_leave_out(req, days))
    return outs


async def list_manageable_leave(db: AsyncSession, user: User) -> list[LeaveRequestOut]:
    stmt = (
        select(LeaveRequest)
        .options(
            selectinload(LeaveRequest.employee).selectinload(Employee.user),
            selectinload(LeaveRequest.leave_type),
        )
        .order_by(LeaveRequest.created_at.desc())
    )
    if not is_staff(user):
        if user.employee is None:
            return []
        stmt = stmt.join(Employee, Employee.id == LeaveRequest.employee_id).where(
            or_(
                Employee.reporting_manager_id == user.employee.id,
                LeaveRequest.employee_id == user.employee.id,
            )
        )
    outs: list[LeaveRequestOut] = []
    for req in (await db.execute(stmt)).scalars().unique().all():
        days = await working_days(
            db, req.start_date, req.end_date, req.is_half_day, req.employee.location_id if req.employee else None
        )
        outs.append(to_leave_out(req, days))
    return outs


def can_review_leave(user: User, req: LeaveRequest) -> bool:
    if is_staff(user):
        return True
    return bool(user.employee and req.employee.reporting_manager_id == user.employee.id)


async def review_leave(
    db: AsyncSession, user: User, request_id: UUID, status: LeaveStatus, comment: str
) -> LeaveRequestOut:
    req = await _load_request(db, request_id)
    if req.status != LeaveStatus.PENDING:
        raise BadRequest("Only pending requests can be reviewed")
    if user.employee and req.employee_id == user.employee.id:
        raise Forbidden("You cannot review your own leave")
    if not can_review_leave(user, req):
        raise Forbidden("You cannot review this leave request")
    req.status = status
    req.comment = comment
    req.reviewer_id = user.employee.id if user.employee else None
    days = await working_days(db, req.start_date, req.end_date, req.is_half_day, req.employee.location_id)
    if status == LeaveStatus.APPROVED and req.leave_type:
        await _consume_comp_off(db, req.employee_id, req.leave_type, days)
    await db.commit()
    req = await _load_request(db, request_id)
    return to_leave_out(req, days)


async def cancel_leave(db: AsyncSession, employee_id: UUID, request_id: UUID) -> LeaveRequestOut:
    req = await _load_request(db, request_id)
    if req.employee_id != employee_id:
        raise Forbidden("You can only cancel your own leave")
    if req.status != LeaveStatus.PENDING:
        raise BadRequest("Only pending leave can be cancelled")
    req.status = LeaveStatus.CANCELLED
    await db.commit()
    req = await _load_request(db, request_id)
    days = await working_days(db, req.start_date, req.end_date, req.is_half_day, req.employee.location_id)
    return to_leave_out(req, days)


async def admin_add_leave(db: AsyncSession, user: User, data: AdminLeaveCreate) -> LeaveRequestOut:
    employee = (
        await db.execute(
            select(Employee).options(selectinload(Employee.user)).where(Employee.id == data.employee_id)
        )
    ).scalar_one_or_none()
    if employee is None:
        raise NotFound("Employee not found")
    leave_type = await db.get(LeaveType, data.leave_type_id)
    if leave_type is None:
        raise NotFound("Leave type not found")
    days = await working_days(db, data.start_date, data.end_date, data.is_half_day, employee.location_id)
    if days <= 0:
        raise BadRequest("Leave request has no working days")
    await _overlaps(db, employee.id, data.start_date, data.end_date)
    req = LeaveRequest(
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=data.start_date,
        end_date=data.end_date,
        is_half_day=data.is_half_day,
        reason=data.reason or "Added by admin",
        status=LeaveStatus.APPROVED if data.approve else LeaveStatus.PENDING,
        reviewer_id=user.employee.id if data.approve and user.employee else None,
        comment="Added by admin" if data.approve else "",
    )
    db.add(req)
    if data.approve:
        await _consume_comp_off(db, employee.id, leave_type, days)
    await db.commit()
    loaded = await _load_request(db, req.id)
    return to_leave_out(loaded, days)


async def balances_for(db: AsyncSession, employee_id: UUID, year: int) -> list[LeaveBalanceOut]:
    types = await list_leave_types(db)
    employee = await db.get(Employee, employee_id)
    location_id = employee.location_id if employee else None
    result = await db.execute(
        select(LeaveRequest)
        .where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
            LeaveRequest.start_date >= date(year, 1, 1),
            LeaveRequest.start_date <= date(year, 12, 31),
        )
    )
    requests = list(result.scalars().all())
    balances: list[LeaveBalanceOut] = []
    for leave_type in types:
        used = Decimal("0")
        pending = Decimal("0")
        for req in requests:
            if req.leave_type_id != leave_type.id:
                continue
            days = await working_days(db, req.start_date, req.end_date, req.is_half_day, location_id)
            if req.status == LeaveStatus.APPROVED:
                used += days
            elif req.status == LeaveStatus.PENDING:
                pending += days
        if leave_type.code == COMP_OFF_CODE:
            credits = await _credit_balance(db, employee_id, leave_type.id)
            balances.append(
                LeaveBalanceOut(
                    leave_type_id=leave_type.id,
                    leave_type_name=leave_type.name,
                    allocated=credits,
                    used=used,
                    pending=pending,
                    available=credits - used - pending,
                )
            )
        else:
            allocated = _allocated_for_year(leave_type, year)
            balances.append(
                LeaveBalanceOut(
                    leave_type_id=leave_type.id,
                    leave_type_name=leave_type.name,
                    allocated=allocated,
                    used=used,
                    pending=pending,
                    available=allocated - used - pending,
                )
            )
    return balances


async def approved_leave_dates(db: AsyncSession, employee_id: UUID, start: date, end: date) -> set[date]:
    result = await db.execute(
        select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        )
    )
    dates: set[date] = set()
    for req in result.scalars().all():
        cursor = max(req.start_date, start)
        last = min(req.end_date, end)
        while cursor <= last:
            dates.add(cursor)
            cursor += timedelta(days=1)
    return dates
