from calendar import monthrange
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequest, Forbidden, NotFound
from app.models.employee import Employee
from app.models.payroll import PayrollPeriod, PayrollPeriodStatus
from app.models.project import Project
from app.models.reimbursement import Reimbursement, ReimbursementStatus
from app.models.user import User, is_staff
from app.schemas.reimbursement import ReimbursementCreate, ReimbursementOut
from app.services.audit import log_audit


def to_out(row: Reimbursement) -> ReimbursementOut:
    return ReimbursementOut(
        id=row.id,
        employee_id=row.employee_id,
        employee_name=row.employee.name if row.employee else None,
        project_id=row.project_id,
        project_name=None,
        amount=row.amount,
        category=row.category,
        spend_date=row.spend_date,
        note=row.note,
        status=row.status,
        reviewer_id=row.reviewer_id,
        comment=row.comment,
        payroll_year=row.payroll_year,
        payroll_month=row.payroll_month,
        paid_separately=row.paid_separately,
    )


async def _load(db: AsyncSession, claim_id: UUID) -> Reimbursement:
    result = await db.execute(
        select(Reimbursement)
        .options(selectinload(Reimbursement.employee).selectinload(Employee.user))
        .where(Reimbursement.id == claim_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFound("Reimbursement not found")
    return row


async def _period_for_claim(db: AsyncSession, spend: date) -> tuple[int, int]:
    year, month = spend.year, spend.month
    period = (
        await db.execute(
            select(PayrollPeriod).where(PayrollPeriod.year == year, PayrollPeriod.month == month)
        )
    ).scalar_one_or_none()
    if period and period.status == PayrollPeriodStatus.CLOSED:
        if month == 12:
            return year + 1, 1
        return year, month + 1
    return year, month


async def apply_claim(db: AsyncSession, employee: Employee, data: ReimbursementCreate) -> ReimbursementOut:
    if data.project_id:
        project = await db.get(Project, data.project_id)
        if project is None:
            raise NotFound("Project not found")
    row = Reimbursement(
        employee_id=employee.id,
        project_id=data.project_id,
        amount=data.amount,
        category=data.category,
        spend_date=data.spend_date,
        note=data.note,
        status=ReimbursementStatus.SUBMITTED,
    )
    db.add(row)
    await db.commit()
    return to_out(await _load(db, row.id))


async def list_my_claims(db: AsyncSession, employee_id: UUID) -> list[ReimbursementOut]:
    result = await db.execute(
        select(Reimbursement)
        .options(selectinload(Reimbursement.employee))
        .where(Reimbursement.employee_id == employee_id)
        .order_by(Reimbursement.spend_date.desc())
    )
    return [to_out(row) for row in result.scalars().all()]


async def list_manageable_claims(db: AsyncSession, user: User) -> list[ReimbursementOut]:
    stmt = (
        select(Reimbursement)
        .options(selectinload(Reimbursement.employee).selectinload(Employee.user))
        .order_by(Reimbursement.created_at.desc())
    )
    if not is_staff(user):
        if user.employee is None:
            return []
        stmt = stmt.join(Employee, Employee.id == Reimbursement.employee_id).where(
            Employee.reporting_manager_id == user.employee.id
        )
    return [to_out(row) for row in (await db.execute(stmt)).scalars().unique().all()]


def can_review_claim(user: User, row: Reimbursement) -> bool:
    if is_staff(user):
        return True
    return bool(user.employee and row.employee.reporting_manager_id == user.employee.id)


async def review_claim(
    db: AsyncSession, user: User, claim_id: UUID, status: ReimbursementStatus, comment: str
) -> ReimbursementOut:
    row = await _load(db, claim_id)
    if row.status != ReimbursementStatus.SUBMITTED:
        raise BadRequest("Only submitted claims can be reviewed")
    if user.employee and row.employee_id == user.employee.id:
        raise Forbidden("You cannot review your own claim")
    if not can_review_claim(user, row):
        raise Forbidden("You cannot review this reimbursement")
    before = {"status": row.status.value}
    row.status = status
    row.comment = comment
    row.reviewer_id = user.employee.id if user.employee else None
    if status == ReimbursementStatus.APPROVED:
        row.payroll_year, row.payroll_month = await _period_for_claim(db, row.spend_date)
    await log_audit(
        db,
        user,
        "approved" if status == ReimbursementStatus.APPROVED else "rejected",
        "reimbursement",
        row.id,
        summary=f"{row.employee.name} claim {row.amount}",
        before=before,
        after={"status": status.value, "comment": comment},
    )
    await db.commit()
    return to_out(await _load(db, claim_id))


async def cancel_claim(db: AsyncSession, employee_id: UUID, claim_id: UUID) -> ReimbursementOut:
    row = await _load(db, claim_id)
    if row.employee_id != employee_id:
        raise Forbidden("You can only cancel your own claim")
    if row.status != ReimbursementStatus.SUBMITTED:
        raise BadRequest("Only submitted claims can be cancelled")
    row.status = ReimbursementStatus.CANCELLED
    await db.commit()
    return to_out(await _load(db, claim_id))


async def approved_for_month(db: AsyncSession, employee_id: UUID, year: int, month: int) -> Decimal:
    result = await db.execute(
        select(Reimbursement).where(
            Reimbursement.employee_id == employee_id,
            Reimbursement.status == ReimbursementStatus.APPROVED,
            Reimbursement.payroll_year == year,
            Reimbursement.payroll_month == month,
            Reimbursement.paid_separately.is_(False),
        )
    )
    return sum((row.amount for row in result.scalars().all()), Decimal("0.00"))


async def approved_for_project_month(db: AsyncSession, project_id: UUID, year: int, month: int) -> Decimal:
    result = await db.execute(
        select(Reimbursement).where(
            Reimbursement.project_id == project_id,
            Reimbursement.status == ReimbursementStatus.APPROVED,
            Reimbursement.payroll_year == year,
            Reimbursement.payroll_month == month,
        )
    )
    return sum((row.amount for row in result.scalars().all()), Decimal("0.00"))


_ = monthrange
