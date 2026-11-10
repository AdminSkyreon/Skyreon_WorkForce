import re
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, inspect, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequest, Conflict, NotFound
from app.models.hrms import AssetStatus, CompanyAsset
from app.core.security import hash_password

from app.models.employee import Employee, EmployeeStatus, Engagement, PayType
from app.models.payroll import EmployeePayroll
from app.models.user import User, UserRole, is_staff
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeeUpdate


def _package(employee: Employee) -> tuple[Decimal, Decimal]:
    details = inspect(employee).dict.get("payroll")
    if details is None:
        return Decimal("0.00"), Decimal("0.00")
    return details.basic_salary + details.hra + details.allowances, details.hourly_pay_rate


def to_employee_out(employee: Employee) -> EmployeeOut:
    monthly_salary, hourly_pay_rate = _package(employee)
    return EmployeeOut(
        id=employee.id,
        user_id=employee.user_id,
        name=employee.name,
        phone=employee.phone or "",
        address=employee.address or "",
        email=employee.user.email,
        reporting_manager_name=employee.reporting_manager.name if employee.reporting_manager else None,
        employee_code=employee.employee_code,
        designation=employee.designation,
        department=employee.department,
        joining_date=employee.joining_date,
        reporting_manager_id=employee.reporting_manager_id,
        location_id=employee.location_id,
        location_name=employee.location.name if employee.location else None,
        hourly_cost_rate=employee.hourly_cost_rate,
        monthly_salary=monthly_salary,
        hourly_pay_rate=hourly_pay_rate,
        pay_type=employee.pay_type,
        engagement=employee.engagement,
        allow_leave=employee.allow_leave,
        contract_monthly_fee=employee.contract_monthly_fee,
        status=employee.status,
        is_active_user=employee.user.is_active,
    )


async def list_employees(
    db: AsyncSession,
    *,
    search: str | None = None,
    status: EmployeeStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Employee], int]:
    stmt = select(Employee).options(
        selectinload(Employee.user),
        selectinload(Employee.location),
        selectinload(Employee.payroll),
        selectinload(Employee.reporting_manager),
    )
    count_stmt = select(func.count()).select_from(Employee)
    if search:
        pattern = f"%{search}%"
        filt = or_(
            Employee.name.ilike(pattern),
            Employee.employee_code.ilike(pattern),
            Employee.department.ilike(pattern),
        )
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)
    if status:
        stmt = stmt.where(Employee.status == status)
        count_stmt = count_stmt.where(Employee.status == status)
    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(
        stmt.order_by(Employee.name).offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total


async def list_reports(db: AsyncSession, manager_id: UUID) -> list[Employee]:
    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.user),
            selectinload(Employee.location),
            selectinload(Employee.payroll),
            selectinload(Employee.reporting_manager),
        )
        .where(Employee.reporting_manager_id == manager_id)
        .order_by(Employee.name)
    )
    return list(result.scalars().all())


async def get_employee(db: AsyncSession, employee_id: UUID) -> Employee:
    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.user),
            selectinload(Employee.location),
            selectinload(Employee.payroll),
            selectinload(Employee.reporting_manager),
        )
        .where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if employee is None:
        raise NotFound("Employee not found")
    return employee


async def next_employee_code(db: AsyncSession) -> str:
    codes = (await db.execute(select(Employee.employee_code))).scalars().all()
    highest = 0
    for code in codes:
        match = re.search(r"(\d+)$", code)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"SKY-{highest + 1:04d}"


async def create_employee(db: AsyncSession, data: EmployeeCreate) -> Employee:
    existing = (await db.execute(select(User).options(selectinload(User.employee)).where(User.email == data.email.lower()))).scalar_one_or_none()
    if existing and existing.employee:
        raise Conflict("Email already in use")
    if existing and not is_staff(existing):
        raise Conflict("Email already in use")
    code = (data.employee_code or "").strip() or await next_employee_code(db)
    taken = await db.execute(select(Employee).where(Employee.employee_code == code))
    if taken.scalar_one_or_none():
        raise Conflict("Employee code already in use")
    if data.reporting_manager_id:
        await get_employee(db, data.reporting_manager_id)

    if existing:
        user = existing
    else:
        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.temporary_password),
            role=UserRole.EMPLOYEE,
            is_active=True,
            must_change_password=True,
        )
        db.add(user)
        await db.flush()
    employee = Employee(
        user_id=user.id,
        name=data.name,
        phone=(data.phone or "").strip(),
        address=(data.address or "").strip(),
        employee_code=code,
        designation=data.designation,
        department=data.department,
        joining_date=data.joining_date,
        reporting_manager_id=data.reporting_manager_id,
        location_id=data.location_id,
        hourly_cost_rate=data.hourly_cost_rate,
        pay_type=data.pay_type,
        engagement=data.engagement,
        allow_leave=True if data.engagement == Engagement.STAFF else data.allow_leave,
        contract_monthly_fee=data.contract_monthly_fee if data.engagement == Engagement.CONTRACTOR else Decimal("0.00"),
        status=EmployeeStatus.ACTIVE,
    )
    db.add(employee)
    await db.flush()
    hourly_pay = data.hourly_pay_rate if data.pay_type == PayType.HOURLY else Decimal("0.00")
    monthly = data.monthly_salary if data.pay_type == PayType.FIXED else Decimal("0.00")
    if hourly_pay == 0 and data.pay_type == PayType.HOURLY:
        hourly_pay = data.hourly_cost_rate
    db.add(
        EmployeePayroll(
            employee_id=employee.id,
            basic_salary=monthly,
            hourly_pay_rate=hourly_pay,
        )
    )
    await db.commit()
    return await get_employee(db, employee.id)


async def update_employee(db: AsyncSession, employee_id: UUID, data: EmployeeUpdate) -> Employee:
    employee = await get_employee(db, employee_id)
    payload = data.model_dump(exclude_unset=True)
    monthly = payload.pop("monthly_salary", None)
    hourly_pay = payload.pop("hourly_pay_rate", None)
    if "reporting_manager_id" in payload and payload["reporting_manager_id"]:
        if payload["reporting_manager_id"] == employee.id:
            raise BadRequest("Employee cannot report to themselves")
        await get_employee(db, payload["reporting_manager_id"])
    if payload.get("engagement") == Engagement.STAFF:
        payload.setdefault("allow_leave", True)
        payload.setdefault("contract_monthly_fee", Decimal("0.00"))
    for key, value in payload.items():
        setattr(employee, key, value)
    if monthly is not None or hourly_pay is not None or "hourly_cost_rate" in payload or "pay_type" in payload:
        payroll = employee.payroll
        if payroll is None:
            payroll = EmployeePayroll(employee_id=employee.id)
            db.add(payroll)
        if monthly is not None:
            extras = Decimal(str(payroll.hra or 0)) + Decimal(str(payroll.allowances or 0))
            payroll.basic_salary = max(Decimal(str(monthly)) - extras, Decimal("0.00"))
        if employee.pay_type == PayType.HOURLY:
            rate = hourly_pay if hourly_pay is not None else payload.get("hourly_cost_rate")
            if rate is not None:
                payroll.hourly_pay_rate = rate
                if "hourly_cost_rate" not in payload:
                    employee.hourly_cost_rate = rate
        elif "pay_type" in payload:
            payroll.hourly_pay_rate = Decimal("0.00")
            employee.hourly_cost_rate = Decimal("0.00")
    await db.commit()
    return await get_employee(db, employee.id)


async def _assert_no_assigned_assets(db: AsyncSession, employee_id: UUID) -> None:
    held = (
        await db.execute(
            select(CompanyAsset.id)
            .where(
                CompanyAsset.assigned_to_id == employee_id,
                CompanyAsset.status == AssetStatus.ASSIGNED,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if held is not None:
        raise BadRequest("Return assigned assets before deactivating this person")


async def _set_employee_active(db: AsyncSession, employee: Employee, active: bool) -> Employee:
    target_status = EmployeeStatus.ACTIVE if active else EmployeeStatus.INACTIVE
    if employee.status == target_status and employee.user.is_active is active:
        return employee  # Idempotent no-op: avoids unnecessary DB writes

    if not active:
        await _assert_no_assigned_assets(db, employee.id)

    employee.status = target_status
    employee.user.is_active = active
    await db.commit()
    return employee


async def activate_employee(db: AsyncSession, employee_id: UUID) -> Employee:
    employee = await get_employee(db, employee_id)
    return await _set_employee_active(db, employee, True)


async def deactivate_employee(db: AsyncSession, employee_id: UUID) -> Employee:
    employee = await get_employee(db, employee_id)
    return await _set_employee_active(db, employee, False)


async def reset_password(db: AsyncSession, employee_id: UUID, temporary_password: str) -> Employee:
    employee = await get_employee(db, employee_id)
    employee.user.password_hash = hash_password(temporary_password)
    employee.user.must_change_password = True
    await db.commit()
    return employee
