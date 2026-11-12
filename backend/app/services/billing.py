import re
from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequest, Conflict, Forbidden, NotFound
from app.models.billing import ProjectInvoice
from app.models.employee import Employee
from app.models.hrms import ProjectPayment
from app.models.project import ContractType, Project, ProjectStatus
from app.models.task import Task
from app.models.time_entry import TaskTimeEntry
from app.models.timesheet import TimesheetStatus, TimesheetWeek
from app.models.user import User, is_staff
from app.schemas.billing import (
    InvoiceCreate,
    InvoiceOut,
    InvoicePaymentIn,
    InvoicePaymentOut,
    InvoicePaymentUpdate,
    InvoiceSuggestOut,
    InvoiceUpdate,
)
from app.services.audit import log_audit
from app.services.dates import monday_of


def _money(value: Decimal | int | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.00"))


DEFAULT_GST_PERCENT = Decimal("18.00")


def compute_gst(taxable: Decimal, gst_percent: Decimal) -> tuple[Decimal, Decimal]:
    taxable = _money(taxable)
    gst_amount = _money(taxable * gst_percent / Decimal("100"))
    return gst_amount, _money(taxable + gst_amount)


def can_edit_billing(user: User, project: Project) -> bool:
    if is_staff(user):
        return True
    return bool(user.employee and project.manager_id == user.employee.id)


def invoice_status(amount: Decimal, received: Decimal) -> str:
    if received <= 0:
        return "open"
    if received < amount:
        return "partial"
    return "paid"


async def next_invoice_no(db: AsyncSession) -> str:
    codes = (await db.execute(select(ProjectInvoice.invoice_no))).scalars().all()
    highest = 0
    for code in codes:
        match = re.search(r"(\d+)$", code)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"INV-{highest + 1:04d}"


async def _received_map(db: AsyncSession, invoice_ids: list[UUID]) -> dict[UUID, Decimal]:
    if not invoice_ids:
        return {}
    rows = (
        await db.execute(
            select(ProjectPayment.invoice_id, func.coalesce(func.sum(ProjectPayment.amount), 0)).where(
                ProjectPayment.invoice_id.in_(invoice_ids)
            ).group_by(ProjectPayment.invoice_id)
        )
    ).all()
    return {invoice_id: _money(total) for invoice_id, total in rows}


async def _to_invoice_out(row: ProjectInvoice, received: Decimal) -> InvoiceOut:
    amount = _money(row.amount)
    received = _money(received)
    outstanding = max(amount - received, Decimal("0.00"))
    return InvoiceOut(
        id=row.id,
        invoice_no=row.invoice_no,
        project_id=row.project_id,
        project_name=row.project.name if row.project else None,
        invoice_date=row.invoice_date,
        year=row.year,
        month=row.month,
        taxable_amount=_money(row.taxable_amount),
        gst_percent=_money(row.gst_percent),
        gst_amount=_money(row.gst_amount),
        amount=amount,
        received=min(received, amount) if received else Decimal("0.00"),
        outstanding=outstanding,
        status=invoice_status(amount, received),
        note=row.note,
    )


async def create_invoice(db: AsyncSession, user: User, data: InvoiceCreate) -> InvoiceOut:
    project = await db.get(Project, data.project_id)
    if project is None:
        raise NotFound("Project not found")
    if not can_edit_billing(user, project):
        raise Forbidden("You can only raise invoices for your own projects")
    invoice_no = (data.invoice_no or "").strip() or await next_invoice_no(db)
    taken = await db.execute(select(ProjectInvoice).where(ProjectInvoice.invoice_no == invoice_no))
    if taken.scalar_one_or_none():
        raise Conflict("That invoice number is already in use")
    gst_amount, total = compute_gst(data.taxable_amount, data.gst_percent)
    row = ProjectInvoice(
        invoice_no=invoice_no,
        project_id=data.project_id,
        invoice_date=data.invoice_date,
        year=data.invoice_date.year,
        month=data.invoice_date.month,
        taxable_amount=_money(data.taxable_amount),
        gst_percent=_money(data.gst_percent),
        gst_amount=gst_amount,
        amount=total,
        note=data.note,
        entered_by_id=user.id,
    )
    db.add(row)
    await log_audit(
        db,
        user,
        "created",
        "project_invoice",
        data.project_id,
        summary=f"{row.invoice_no} {project.name} {total} (incl. GST) on {data.invoice_date}",
    )
    await db.commit()
    loaded = (
        await db.execute(
            select(ProjectInvoice).options(selectinload(ProjectInvoice.project)).where(ProjectInvoice.id == row.id)
        )
    ).scalar_one()
    return await _to_invoice_out(loaded, Decimal("0.00"))


async def list_invoices(
    db: AsyncSession,
    user: User,
    year: int | None = None,
    month: int | None = None,
    outstanding_only: bool = False,
) -> list[InvoiceOut]:
    stmt = select(ProjectInvoice).options(selectinload(ProjectInvoice.project)).order_by(
        ProjectInvoice.invoice_date.desc(), ProjectInvoice.invoice_no.desc()
    )
    if year and month:
        stmt = stmt.where(ProjectInvoice.year == year, ProjectInvoice.month == month)
    if not is_staff(user):
        if user.employee is None:
            return []
        stmt = stmt.join(Project, Project.id == ProjectInvoice.project_id).where(Project.manager_id == user.employee.id)
    rows = list((await db.execute(stmt)).scalars().all())
    received = await _received_map(db, [row.id for row in rows])
    outs = [await _to_invoice_out(row, received.get(row.id, Decimal("0.00"))) for row in rows]
    if outstanding_only:
        return [row for row in outs if row.status != "paid"]
    return outs


async def update_invoice(db: AsyncSession, user: User, invoice_id: UUID, data: InvoiceUpdate) -> InvoiceOut:
    invoice = (
        await db.execute(
            select(ProjectInvoice).options(selectinload(ProjectInvoice.project)).where(ProjectInvoice.id == invoice_id).with_for_update()
        )
    ).scalar_one_or_none()
    if invoice is None or invoice.project is None:
        raise NotFound("Invoice not found")
    if not can_edit_billing(user, invoice.project):
        raise Forbidden("You can only edit invoices for your own projects")
    payload = data.model_dump(exclude_unset=True)
    if "invoice_no" in payload:
        invoice_no = (payload["invoice_no"] or "").strip()
        if not invoice_no:
            raise BadRequest("Invoice number cannot be blank")
        taken = await db.execute(
            select(ProjectInvoice).where(ProjectInvoice.invoice_no == invoice_no, ProjectInvoice.id != invoice.id)
        )
        if taken.scalar_one_or_none():
            raise Conflict("That invoice number is already in use")
        invoice.invoice_no = invoice_no
        payload.pop("invoice_no")
    if "project_id" in payload:
        project = await db.get(Project, payload["project_id"])
        if project is None:
            raise NotFound("Project not found")
        if not can_edit_billing(user, project):
            raise Forbidden("You can only raise invoices for your own projects")
        if payload["project_id"] != invoice.project_id:
            payments = (
                await db.execute(select(ProjectPayment).where(ProjectPayment.invoice_id == invoice.id))
            ).scalars().all()
            for payment in payments:
                payment.project_id = payload["project_id"]
    if "invoice_date" in payload and payload["invoice_date"]:
        invoice.year = payload["invoice_date"].year
        invoice.month = payload["invoice_date"].month
    taxable = invoice.taxable_amount
    gst_percent = invoice.gst_percent
    if "taxable_amount" in payload and payload["taxable_amount"] is not None:
        taxable = _money(payload["taxable_amount"])
        payload.pop("taxable_amount")
    if "gst_percent" in payload and payload["gst_percent"] is not None:
        gst_percent = _money(payload["gst_percent"])
        payload.pop("gst_percent")
    if "taxable_amount" in data.model_dump(exclude_unset=True) or "gst_percent" in data.model_dump(exclude_unset=True):
        gst_amount, total = compute_gst(taxable, gst_percent)
        received = (await _received_map(db, [invoice.id])).get(invoice.id, Decimal("0.00"))

        if total < received:
            raise BadRequest(f"Invoice total cannot be less than {received} already received")
        invoice.taxable_amount = taxable
        invoice.gst_percent = gst_percent
        invoice.gst_amount = gst_amount
        invoice.amount = total
    for key, value in payload.items():
        setattr(invoice, key, value)
    await log_audit(
        db,
        user,
        "updated",
        "project_invoice",
        invoice.project_id,
        summary=f"Edited {invoice.invoice_no}",
    )
    await db.commit()
    loaded = (
        await db.execute(
            select(ProjectInvoice).options(selectinload(ProjectInvoice.project)).where(ProjectInvoice.id == invoice.id)
        )
    ).scalar_one()
    received = (await _received_map(db, [loaded.id])).get(loaded.id, Decimal("0.00"))
    return await _to_invoice_out(loaded, received)


async def apply_payment(db: AsyncSession, user: User, invoice_id: UUID, data: InvoicePaymentIn) -> InvoicePaymentOut:
    if not is_staff(user):
        raise Forbidden("Only Admin can record payment received")
    invoice = (
        await db.execute(
            select(ProjectInvoice).options(selectinload(ProjectInvoice.project)).where(ProjectInvoice.id == invoice_id).with_for_update()
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise NotFound("Invoice not found")
    received = (await _received_map(db, [invoice.id])).get(invoice.id, Decimal("0.00"))

    outstanding = _money(invoice.amount) - received
    if data.amount > outstanding:
        raise BadRequest(f"This invoice has only {outstanding} outstanding")
    if data.received_date < invoice.invoice_date:
        raise BadRequest("Received date cannot be earlier than invoice date")
    row = ProjectPayment(
        project_id=invoice.project_id,
        invoice_id=invoice.id,
        year=data.received_date.year,
        month=data.received_date.month,
        amount=data.amount,
        received_date=data.received_date,
        note=data.note,
        entered_by_id=user.id,
    )
    db.add(row)
    await log_audit(
        db,
        user,
        "created",
        "project_payment",
        invoice.project_id,
        summary=f"Received {data.amount} against {invoice.invoice_no} on {data.received_date}",
    )
    await db.commit()
    await db.refresh(row)
    return InvoicePaymentOut(
        id=row.id,
        invoice_id=invoice.id,
        invoice_no=invoice.invoice_no,
        project_id=invoice.project_id,
        project_name=invoice.project.name if invoice.project else None,
        year=row.year,
        month=row.month,
        amount=row.amount,
        received_date=row.received_date,
        note=row.note,
        against_earlier_invoice=invoice.year != row.year or invoice.month != row.month,
    )


def _to_payment_out(payment: ProjectPayment, invoice: ProjectInvoice | None, project_name: str | None) -> InvoicePaymentOut:
    return InvoicePaymentOut(
        id=payment.id,
        invoice_id=payment.invoice_id,
        invoice_no=invoice.invoice_no if invoice else None,
        project_id=payment.project_id,
        project_name=project_name,
        year=payment.year,
        month=payment.month,
        amount=payment.amount,
        received_date=payment.received_date,
        note=payment.note,
        against_earlier_invoice=bool(invoice and (invoice.year != payment.year or invoice.month != payment.month)),
    )


async def update_payment(db: AsyncSession, user: User, payment_id: UUID, data: InvoicePaymentUpdate) -> InvoicePaymentOut:
    if not is_staff(user):
        raise Forbidden("Only Admin can edit payment received")
    payment = await db.get(ProjectPayment, payment_id)
    if payment is None:
        raise NotFound("Payment not found")
    payload = data.model_dump(exclude_unset=True)
    invoice_id = payload.get("invoice_id", payment.invoice_id)
    invoice = None
    if invoice_id:
        invoice = (
            await db.execute(
                select(ProjectInvoice).options(selectinload(ProjectInvoice.project)).where(ProjectInvoice.id == invoice_id).with_for_update()
            )
        ).scalar_one_or_none()
        if invoice is None:
            raise NotFound("Invoice not found")
        new_amount = _money(payload.get("amount", payment.amount))
        received = (await _received_map(db, [invoice.id])).get(invoice.id, Decimal("0.00"))

        if payment.invoice_id == invoice.id:
            received = received - _money(payment.amount)
        outstanding = _money(invoice.amount) - received
        if new_amount > outstanding:
            raise BadRequest(f"This invoice has only {outstanding} outstanding")
        payment.invoice_id = invoice.id
        payment.project_id = invoice.project_id
    if "received_date" in payload and payload["received_date"]:
        next_received = payload["received_date"]
    else:
        next_received = payment.received_date
    if invoice is not None and next_received < invoice.invoice_date:
        raise BadRequest("Received date cannot be earlier than invoice date")
    if "received_date" in payload and payload["received_date"]:
        payment.year = payload["received_date"].year
        payment.month = payload["received_date"].month
        payment.received_date = payload["received_date"]
        payload.pop("received_date")
    payload.pop("invoice_id", None)
    for key, value in payload.items():
        setattr(payment, key, value)
    await log_audit(
        db,
        user,
        "updated",
        "project_payment",
        payment.project_id,
        summary=f"Edited receipt {payment.amount} on {payment.received_date}",
    )
    await db.commit()
    await db.refresh(payment)
    if invoice is None and payment.invoice_id:
        invoice = (
            await db.execute(
                select(ProjectInvoice).options(selectinload(ProjectInvoice.project)).where(ProjectInvoice.id == payment.invoice_id)
            )
        ).scalar_one_or_none()
    project = await db.get(Project, payment.project_id)
    return _to_payment_out(payment, invoice, project.name if project else None)


async def list_payments(db: AsyncSession, user: User, year: int, month: int) -> list[InvoicePaymentOut]:
    stmt = (
        select(ProjectPayment, ProjectInvoice, Project.name)
        .outerjoin(ProjectInvoice, ProjectInvoice.id == ProjectPayment.invoice_id)
        .join(Project, Project.id == ProjectPayment.project_id)
        .where(ProjectPayment.year == year, ProjectPayment.month == month)
        .order_by(ProjectPayment.received_date.desc())
    )
    if not is_staff(user):
        return []
    rows = (await db.execute(stmt)).all()
    return [
        InvoicePaymentOut(
            id=payment.id,
            invoice_id=payment.invoice_id,
            invoice_no=invoice.invoice_no if invoice else None,
            project_id=payment.project_id,
            project_name=name,
            year=payment.year,
            month=payment.month,
            amount=payment.amount,
            received_date=payment.received_date,
            note=payment.note,
            against_earlier_invoice=bool(invoice and (invoice.year != payment.year or invoice.month != payment.month)),
        )
        for payment, invoice, name in rows
    ]


async def missing_projects(db: AsyncSession, year: int, month: int) -> list[Project]:
    last_day = monthrange(year, month)[1]
    period_end = date(year, month, last_day)
    projects = list(
        (
            await db.execute(
                select(Project)
                .options(selectinload(Project.manager).selectinload(Employee.user))
                .where(
                    Project.status == ProjectStatus.ACTIVE,
                    Project.start_date <= period_end,
                )
            )
        ).scalars().all()
    )
    billed_ids = set(
        (
            await db.execute(
                select(ProjectInvoice.project_id).where(ProjectInvoice.year == year, ProjectInvoice.month == month)
            )
        ).scalars().all()
    )
    return [project for project in projects if project.id not in billed_ids]


async def invoiced_in_month(db: AsyncSession, year: int, month: int) -> Decimal:
    return _money(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProjectInvoice.amount), 0)).where(
                    ProjectInvoice.year == year, ProjectInvoice.month == month
                )
            )
        ).scalar()
    )


async def invoiced_by_project(db: AsyncSession, year: int, month: int) -> dict[UUID, Decimal]:
    rows = (
        await db.execute(
            select(ProjectInvoice.project_id, func.coalesce(func.sum(ProjectInvoice.amount), 0)).where(
                ProjectInvoice.year == year, ProjectInvoice.month == month
            ).group_by(ProjectInvoice.project_id)
        )
    ).all()
    return {project_id: _money(total) for project_id, total in rows}


async def _approved_week(db: AsyncSession, employee_id: UUID, week_start: date) -> bool:
    row = (
        await db.execute(
            select(TimesheetWeek.status).where(
                TimesheetWeek.employee_id == employee_id,
                TimesheetWeek.week_start == week_start,
            )
        )
    ).scalar_one_or_none()
    return row == TimesheetStatus.APPROVED


async def _approved_seconds_for_project_month(
    db: AsyncSession, project_id: UUID, year: int, month: int
) -> int:
    last_day = monthrange(year, month)[1]
    start = datetime.combine(date(year, month, 1), time.min, tzinfo=UTC)
    end = datetime.combine(date(year, month, last_day) + timedelta(days=1), time.min, tzinfo=UTC)
    rows = (
        await db.execute(
            select(
                TaskTimeEntry.employee_id,
                TaskTimeEntry.duration_seconds,
                TaskTimeEntry.start_time,
            )
            .join(Task, Task.id == TaskTimeEntry.task_id)
            .where(
                Task.project_id == project_id,
                TaskTimeEntry.end_time.is_not(None),
                TaskTimeEntry.start_time >= start,
                TaskTimeEntry.start_time < end,
            )
        )
    ).all()
    week_cache: dict[tuple[UUID, date], bool] = {}
    total = 0
    for employee_id, seconds, started in rows:
        week_start = monday_of(started.astimezone(UTC).date())
        key = (employee_id, week_start)
        if key not in week_cache:
            week_cache[key] = await _approved_week(db, employee_id, week_start)
        if week_cache[key]:
            total += int(seconds)
    return total


async def suggest_invoice(
    db: AsyncSession, user: User, project_id: UUID, year: int, month: int, gst_percent: Decimal | None = None
) -> InvoiceSuggestOut:
    project = await db.get(Project, project_id)
    if project is None:
        raise NotFound("Project not found")
    if not can_edit_billing(user, project):
        raise Forbidden("You can only bill your own projects")
    pct = _money(gst_percent if gst_percent is not None else DEFAULT_GST_PERCENT)
    seconds = await _approved_seconds_for_project_month(db, project_id, year, month)
    hours = _money(Decimal(seconds) / Decimal(3600))
    bill_rate: Decimal | None = None
    detail = ""
    if project.contract_type == ContractType.FIXED and project.revenue_amount > 0:
        taxable = _money(project.revenue_amount)
        detail = "Fixed contract: project revenue amount"
    elif project.budgeted_hours > 0 and project.revenue_amount > 0:
        bill_rate = _money(project.revenue_amount / project.budgeted_hours)
        taxable = _money(hours * bill_rate)
        detail = f"{hours}h approved × {bill_rate}/h from project budget"
    else:
        rows = (
            await db.execute(
                select(TaskTimeEntry.employee_id, TaskTimeEntry.duration_seconds, TaskTimeEntry.start_time)
                .join(Task, Task.id == TaskTimeEntry.task_id)
                .where(
                    Task.project_id == project_id,
                    TaskTimeEntry.end_time.is_not(None),
                    TaskTimeEntry.start_time
                    >= datetime.combine(date(year, month, 1), time.min, tzinfo=UTC),
                    TaskTimeEntry.start_time
                    < datetime.combine(
                        date(year, month, monthrange(year, month)[1]) + timedelta(days=1),
                        time.min,
                        tzinfo=UTC,
                    ),
                )
            )
        ).all()
        week_cache: dict[tuple[UUID, date], bool] = {}
        cost = Decimal("0.00")
        approved_h = Decimal("0.00")
        emp_ids = {row[0] for row in rows}
        rates: dict[UUID, Decimal] = {}
        if emp_ids:
            rates = {
                emp.id: emp.hourly_cost_rate
                for emp in (await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))).scalars()
            }
        for employee_id, secs, started in rows:
            week_start = monday_of(started.astimezone(UTC).date())
            key = (employee_id, week_start)
            if key not in week_cache:
                week_cache[key] = await _approved_week(db, employee_id, week_start)
            if not week_cache[key]:
                continue
            h = Decimal(int(secs)) / Decimal(3600)
            approved_h += h
            cost += h * Decimal(rates.get(employee_id, 0))
        hours = _money(approved_h)
        taxable = _money(cost)
        detail = f"{hours}h approved at internal cost rates (set budget/revenue for client rate)"

    gst_amount, total = compute_gst(taxable, pct)
    return InvoiceSuggestOut(
        project_id=project_id,
        project_name=project.name,
        year=year,
        month=month,
        approved_hours=hours,
        bill_rate=bill_rate,
        taxable_amount=taxable,
        gst_percent=pct,
        gst_amount=gst_amount,
        total_amount=total,
        detail=detail,
    )
