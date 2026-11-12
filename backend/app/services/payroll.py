import asyncio
from calendar import monthrange
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from uuid import UUID
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequest, Forbidden, NotFound
from app.models.employee import Employee, EmployeeStatus, Engagement, PayType
from app.models.leave import LeaveRequest, LeaveStatus, LeaveType
from app.models.location import Location
from app.models.payroll import EmployeePayroll, PayrollAdjustment, PayrollPeriod, PayrollPeriodStatus
from app.models.time_entry import TaskTimeEntry
from app.models.timesheet import TimesheetStatus, TimesheetWeek
from app.models.user import User, is_super_admin
from app.schemas.payroll import PayrollDetailsIn, PayrollDetailsOut, PayrollLine, PayrollRegister
from app.services.audit import log_audit
from app.services.company import get_profile
from app.services.dates import monday_of
from app.services.leave import working_days
from app.services.reimbursements import approved_for_month

UTC_TZ = ZoneInfo("UTC")
NAVY = colors.HexColor("#081020")
BLUE = colors.HexColor("#0060A8")
CYAN = colors.HexColor("#00A3DC")
MIST = colors.HexColor("#E8F1F8")
INK = colors.HexColor("#081020")
LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "skyreon-logo.png"
STANDARD_DAY_HOURS = Decimal("8.00")


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


async def _get_period(db: AsyncSession, year: int, month: int) -> PayrollPeriod | None:
    return (
        await db.execute(
            select(PayrollPeriod).where(PayrollPeriod.year == year, PayrollPeriod.month == month)
        )
    ).scalar_one_or_none()


async def is_closed(db: AsyncSession, year: int, month: int) -> bool:
    period = await _get_period(db, year, month)
    return bool(period and period.status == PayrollPeriodStatus.CLOSED)


async def _leave_split(
    db: AsyncSession, employee: Employee, start: date, end: date
) -> tuple[Decimal, Decimal]:
    result = await db.execute(
        select(LeaveRequest)
        .options(selectinload(LeaveRequest.leave_type))
        .where(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        )
    )
    paid = Decimal("0.00")
    unpaid = Decimal("0.00")
    for req in result.scalars().all():
        overlap_start = max(req.start_date, start)
        overlap_end = min(req.end_date, end)
        days = await working_days(db, overlap_start, overlap_end, req.is_half_day, employee.location_id)
        if req.leave_type and req.leave_type.is_unpaid:
            unpaid += days
        else:
            paid += days
    return paid, unpaid


async def _approved_hours(db: AsyncSession, employee_id: UUID, start: date, end: date) -> Decimal:
    weeks = list(
        (
            await db.execute(
                select(TimesheetWeek).where(
                    TimesheetWeek.employee_id == employee_id,
                    TimesheetWeek.status == TimesheetStatus.APPROVED,
                    TimesheetWeek.week_start <= end,
                    TimesheetWeek.week_start >= start - timedelta(days=6),
                )
            )
        ).scalars().all()
    )
    if not weeks:
        return Decimal("0.00")
    approved_weeks = {w.week_start for w in weeks}
    start_dt = datetime.combine(start, time.min, tzinfo=UTC_TZ)
    end_dt = datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC_TZ)
    total = Decimal("0.00")
    entries = (
        await db.execute(
            select(TaskTimeEntry).where(
                TaskTimeEntry.employee_id == employee_id,
                TaskTimeEntry.end_time.is_not(None),
                TaskTimeEntry.start_time >= start_dt,
                TaskTimeEntry.start_time < end_dt,
            )
        )
    ).scalars().all()
    for entry in entries:
        if monday_of(entry.start_time.astimezone(UTC_TZ).date()) in approved_weeks:
            total += Decimal(entry.duration_seconds) / Decimal(3600)
    return _money(total)


async def _working_days_in_month(db: AsyncSession, employee: Employee, start: date, end: date) -> Decimal:
    return await working_days(db, start, end, False, employee.location_id)


def _line_for(
    employee: Employee,
    hours: Decimal,
    paid_leave: Decimal,
    lwp_days: Decimal,
    working_days_count: Decimal,
    reimbursements: Decimal,
    bonus: Decimal = Decimal("0.00"),
    extra_work_pay: Decimal = Decimal("0.00"),
) -> PayrollLine:
    details = employee.payroll
    basic = details.basic_salary if details else Decimal("0.00")
    hra = details.hra if details else Decimal("0.00")
    allowances = details.allowances if details else Decimal("0.00")
    hourly_pay = details.hourly_pay_rate if details else Decimal("0.00")
    tax_percent = details.tax_percent if details else Decimal("0.00")
    pf_percent = details.pf_percent if details else Decimal("0.00")
    professional_tax = details.professional_tax if details else Decimal("0.00")
    other = details.other_deductions if details else Decimal("0.00")
    currency = details.currency if details else "INR"
    pay_type = employee.pay_type.value if employee.pay_type else PayType.FIXED.value
    lwp_amount = Decimal("0.00")
    time_pay = Decimal("0.00")
    paid_leave_pay = Decimal("0.00")

    if pay_type == PayType.HOURLY.value:
        time_pay = _money(hours * hourly_pay)
        paid_leave_pay = _money(paid_leave * STANDARD_DAY_HOURS * hourly_pay)
        package = time_pay + paid_leave_pay
        pf_base = time_pay
    else:
        package = basic + hra + allowances
        if working_days_count > 0 and lwp_days > 0:
            lwp_amount = _money(package * lwp_days / working_days_count)
        package = _money(package - lwp_amount)
        pf_base = basic

    bonus = _money(bonus)
    extra_work_pay = _money(extra_work_pay)
    gross = _money(package + bonus + extra_work_pay + reimbursements)
    tax_amount = _money(gross * tax_percent / Decimal("100"))
    pf_amount = _money(pf_base * pf_percent / Decimal("100"))
    deductions = _money(tax_amount + pf_amount + professional_tax + other)
    return PayrollLine(
        employee_id=employee.id,
        name=employee.name,
        employee_code=employee.employee_code,
        location_name=employee.location.name if employee.location else None,
        department=employee.department,
        currency=currency,
        pay_type=pay_type,
        hourly_rate=hourly_pay if pay_type == PayType.HOURLY.value else employee.hourly_cost_rate,
        hours=hours,
        leave_days=paid_leave + lwp_days,
        lwp_days=lwp_days,
        basic_salary=basic,
        hra=hra,
        allowances=allowances,
        time_pay=time_pay,
        paid_leave_pay=paid_leave_pay,
        reimbursements=reimbursements,
        bonus=bonus,
        extra_work_pay=extra_work_pay,
        lwp_amount=lwp_amount,
        tax_percent=tax_percent,
        tax_amount=tax_amount,
        pf_amount=pf_amount,
        professional_tax=professional_tax,
        other_deductions=other,
        gross_pay=gross,
        total_deductions=deductions,
        net_pay=_money(gross - deductions),
        has_details=details is not None,
    )


async def _compute_register(
    db: AsyncSession, year: int, month: int, location_id: UUID | None = None
) -> PayrollRegister:
    start, end = _month_bounds(year, month)
    emp_stmt = (
        select(Employee)
        .options(
            selectinload(Employee.user),
            selectinload(Employee.location),
            selectinload(Employee.payroll),
        )
        .where(Employee.status == EmployeeStatus.ACTIVE, Employee.engagement == Engagement.STAFF)
        .order_by(Employee.name)
    )
    location_name = None
    if location_id:
        location = await db.get(Location, location_id)
        if location is None:
            raise NotFound("Location not found")
        location_name = location.name
        emp_stmt = emp_stmt.where(Employee.location_id == location_id)

    employees = list((await db.execute(emp_stmt)).scalars().all())
    adjustments = list(
        (
            await db.execute(
                select(PayrollAdjustment).where(
                    PayrollAdjustment.year == year, PayrollAdjustment.month == month
                )
            )
        ).scalars().all()
    )
    bonuses = {row.employee_id: row.bonus for row in adjustments}
    extra_pays = {row.employee_id: row.extra_work_pay for row in adjustments}
    lines: list[PayrollLine] = []
    for employee in employees:
        hours = await _approved_hours(db, employee.id, start, end)
        paid_leave, lwp_days = await _leave_split(db, employee, start, end)
        working = await _working_days_in_month(db, employee, start, end)
        claims = await approved_for_month(db, employee.id, year, month)
        lines.append(
            _line_for(
                employee,
                hours,
                paid_leave,
                lwp_days,
                working,
                claims,
                bonuses.get(employee.id, Decimal("0.00")),
                extra_pays.get(employee.id, Decimal("0.00")),
            )
        )

    return PayrollRegister(
        year=year,
        month=month,
        period_label=start.strftime("%B %Y"),
        location_name=location_name,
        lines=lines,
        total_hours=sum((line.hours for line in lines), Decimal("0.00")),
        total_leave_days=sum((line.leave_days for line in lines), Decimal("0.00")),
        total_gross=sum((line.gross_pay for line in lines), Decimal("0.00")),
        total_tax=sum((line.tax_amount for line in lines), Decimal("0.00")),
        total_pay=sum((line.net_pay for line in lines), Decimal("0.00")),
        closed=False,
    )


async def build_register(
    db: AsyncSession, year: int, month: int, location_id: UUID | None = None
) -> PayrollRegister:
    period = await _get_period(db, year, month)
    if period and period.status == PayrollPeriodStatus.CLOSED and period.snapshot_json:
        register = PayrollRegister.model_validate_json(period.snapshot_json)
        register.closed = True
        if location_id:
            location = await db.get(Location, location_id)
            if location is None:
                raise NotFound("Location not found")
            register.location_name = location.name
            register.lines = [line for line in register.lines if line.location_name == location.name]
            register.total_hours = sum((line.hours for line in register.lines), Decimal("0.00"))
            register.total_leave_days = sum((line.leave_days for line in register.lines), Decimal("0.00"))
            register.total_gross = sum((line.gross_pay for line in register.lines), Decimal("0.00"))
            register.total_tax = sum((line.tax_amount for line in register.lines), Decimal("0.00"))
            register.total_pay = sum((line.net_pay for line in register.lines), Decimal("0.00"))
        return register
    register = await _compute_register(db, year, month, location_id)
    register.closed = bool(period and period.status == PayrollPeriodStatus.CLOSED)
    return register


def to_details_out(
    row: EmployeePayroll,
    name: str | None = None,
    bonus: Decimal = Decimal("0.00"),
    reimbursements: Decimal = Decimal("0.00"),
) -> PayrollDetailsOut:
    return PayrollDetailsOut(
        employee_id=row.employee_id,
        employee_name=name,
        currency=row.currency,
        basic_salary=row.basic_salary,
        hra=row.hra,
        allowances=row.allowances,
        hourly_pay_rate=row.hourly_pay_rate,
        tax_percent=row.tax_percent,
        pf_percent=row.pf_percent,
        professional_tax=row.professional_tax,
        other_deductions=row.other_deductions,
        bonus=bonus,
        reimbursements=reimbursements,
    )


async def _month_bonus(db: AsyncSession, employee_id: UUID, year: int | None, month: int | None) -> Decimal:
    if year is None or month is None:
        return Decimal("0.00")
    row = (
        await db.execute(
            select(PayrollAdjustment).where(
                PayrollAdjustment.employee_id == employee_id,
                PayrollAdjustment.year == year,
                PayrollAdjustment.month == month,
            )
        )
    ).scalar_one_or_none()
    return row.bonus if row else Decimal("0.00")


async def _upsert_bonus(
    db: AsyncSession, employee_id: UUID, year: int, month: int, bonus: Decimal
) -> Decimal:
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
    row.bonus = bonus
    return row.bonus


async def _month_claims(db: AsyncSession, employee_id: UUID, year: int | None, month: int | None) -> Decimal:
    if year is None or month is None:
        return Decimal("0.00")
    return await approved_for_month(db, employee_id, year, month)


async def get_details(
    db: AsyncSession, employee_id: UUID, year: int | None = None, month: int | None = None
) -> PayrollDetailsOut:
    employee = (
        await db.execute(
            select(Employee).options(selectinload(Employee.payroll)).where(Employee.id == employee_id)
        )
    ).scalar_one_or_none()
    if employee is None:
        raise NotFound("Employee not found")
    bonus = await _month_bonus(db, employee_id, year, month)
    claims = await _month_claims(db, employee_id, year, month)
    if employee.payroll is None:
        return PayrollDetailsOut(
            employee_id=employee.id,
            employee_name=employee.name,
            currency="INR",
            basic_salary=Decimal("0.00"),
            hra=Decimal("0.00"),
            allowances=Decimal("0.00"),
            hourly_pay_rate=Decimal("0.00"),
            tax_percent=Decimal("0.00"),
            pf_percent=Decimal("0.00"),
            professional_tax=Decimal("0.00"),
            other_deductions=Decimal("0.00"),
            bonus=bonus,
            reimbursements=claims,
        )
    return to_details_out(employee.payroll, employee.name, bonus, claims)


async def upsert_details(
    db: AsyncSession,
    employee_id: UUID,
    data: PayrollDetailsIn,
    user: User | None = None,
    year: int | None = None,
    month: int | None = None,
) -> PayrollDetailsOut:
    employee = (
        await db.execute(
            select(Employee).options(selectinload(Employee.payroll)).where(Employee.id == employee_id)
        )
    ).scalar_one_or_none()
    if employee is None:
        raise NotFound("Employee not found")
    row = employee.payroll
    if row is None:
        row = EmployeePayroll(employee_id=employee.id)
        db.add(row)
    row.currency = data.currency.upper()
    row.basic_salary = data.basic_salary
    row.hra = data.hra
    row.allowances = data.allowances
    row.hourly_pay_rate = data.hourly_pay_rate
    row.tax_percent = data.tax_percent
    row.pf_percent = data.pf_percent
    row.professional_tax = data.professional_tax
    row.other_deductions = data.other_deductions
    bonus = Decimal("0.00")
    if year is not None and month is not None:
        if await is_closed(db, year, month):
            raise BadRequest("This payroll month is closed. Re-open it before changing bonus.")
        bonus = await _upsert_bonus(db, employee.id, year, month, data.bonus)
    if user:
        await log_audit(db, user, "updated", "employee_payroll", employee_id, summary=f"Payroll details for {employee.name}")
    await db.commit()
    await db.refresh(row)
    claims = await _month_claims(db, employee.id, year, month)
    return to_details_out(row, employee.name, bonus, claims)


async def close_month(db: AsyncSession, user: User, year: int, month: int) -> PayrollRegister:
    register = await _compute_register(db, year, month)
    if (
        user.employee
        and len(register.lines) == 1
        and register.lines[0].employee_id == user.employee.id
        and not is_super_admin(user)
    ):
        raise Forbidden("Super admin must confirm a payroll month that only contains you")
    period = await _get_period(db, year, month)
    if period is None:
        period = PayrollPeriod(year=year, month=month)
        db.add(period)
    if period.status == PayrollPeriodStatus.CLOSED:
        raise BadRequest("This payroll month is already closed")
    period.status = PayrollPeriodStatus.CLOSED
    period.closed_by_id = user.id
    period.closed_at = datetime.now(UTC)
    period.snapshot_json = register.model_dump_json()
    register.closed = True
    await log_audit(db, user, "closed", "payroll_period", f"{year}-{month:02d}", summary=f"Closed payroll {register.period_label}")
    await db.commit()
    return register


async def reopen_month(db: AsyncSession, user: User, year: int, month: int) -> PayrollRegister:
    if not is_super_admin(user):
        raise Forbidden("Only a super admin can re-open a closed payroll month")
    period = await _get_period(db, year, month)
    if period is None or period.status != PayrollPeriodStatus.CLOSED:
        raise BadRequest("This payroll month is not closed")
    period.status = PayrollPeriodStatus.OPEN
    period.snapshot_json = ""
    period.closed_at = None
    await log_audit(db, user, "reopened", "payroll_period", f"{year}-{month:02d}", summary=f"Re-opened payroll {year}-{month:02d}")
    await db.commit()
    return await _compute_register(db, year, month)


def _styles():
    styles = getSampleStyleSheet()
    styles["Title"].textColor = NAVY
    styles["Heading2"].textColor = BLUE
    styles["Normal"].textColor = INK
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, textColor=colors.Color(0.25, 0.28, 0.32)))
    styles.add(ParagraphStyle(name="Net", parent=styles["Heading2"], fontSize=14, textColor=NAVY))
    return styles


def _logo_flowable(width=42 * mm):
    if not LOGO_PATH.exists():
        return Paragraph("SKYREON", getSampleStyleSheet()["Title"])
    return Image(str(LOGO_PATH), width=width, height=width * 67 / 235)


def _signature_flowable(image_b64: str):
    if not image_b64:
        return Paragraph("________________", getSampleStyleSheet()["Normal"])
    raw = image_b64.split(",", 1)[-1]
    if len(raw) > 2_800_000:
        return Paragraph("________________", getSampleStyleSheet()["Normal"])
    try:
        import base64

        data = base64.b64decode(raw, validate=True)
        if len(data) > 2_000_000:
            return Paragraph("________________", getSampleStyleSheet()["Normal"])
        return Image(BytesIO(data), width=40 * mm, height=16 * mm, kind="proportional")
    except Exception:
        return Paragraph("________________", getSampleStyleSheet()["Normal"])


def _amount_words(amount: Decimal, currency: str) -> str:
    ones = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
        "Seventeen", "Eighteen", "Nineteen",
    ]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def two(n: int) -> str:
        if n < 20:
            return ones[n]
        return f"{tens[n // 10]} {ones[n % 10]}".strip()

    def three(n: int) -> str:
        if n < 100:
            return two(n)
        return f"{ones[n // 100]} Hundred {two(n % 100)}".strip()

    def indian_words(n: int) -> str:
        if n == 0:
            return "Zero"
        crore, rem = divmod(n, 10000000)
        lakh, rem = divmod(rem, 100000)
        thousand, rem = divmod(rem, 1000)
        parts = []
        if crore:
            crore_text = indian_words(crore) if crore >= 1000 else three(crore)
            parts.append(f"{crore_text} Crore")
        if lakh:
            parts.append(f"{three(lakh)} Lakh")
        if thousand:
            parts.append(f"{three(thousand)} Thousand")
        if rem:
            parts.append(three(rem))
        return " ".join(parts)

    negative = amount < 0
    abs_amount = abs(amount)
    whole = int(abs_amount)
    words = indian_words(whole)
    paise = min(99, max(0, int(((abs_amount - Decimal(whole)) * 100).quantize(Decimal("1")))))
    suffix = f" and {two(paise)} Paise" if paise else ""
    prefix = "Minus " if negative else ""
    return f"{currency} {prefix}{words}{suffix} Only"


async def render_register_pdf(register: PayrollRegister, db: AsyncSession | None = None) -> bytes:
    profile = await get_profile(db) if db else None
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = _styles()
    company = escape(profile.legal_name if profile and profile.legal_name else "Skyreon")
    scope = escape(register.location_name or "All locations")
    header = [_logo_flowable(36 * mm), Paragraph(f"<b>{company}</b><br/>Payroll register · {escape(register.period_label)} · {scope}", styles["Heading2"])]
    story = [Table([header], colWidths=[50 * mm, 220 * mm]), Spacer(1, 8)]
    rows = [["Employee", "Code", "Type", "Hours", "Bonus", "Gross", "Tax", "Claims", "Net"]]
    for line in register.lines:
        rows.append(
            [
                line.name,
                line.employee_code,
                line.pay_type,
                f"{line.hours:.2f}",
                f"{line.bonus:.2f}",
                f"{line.gross_pay:.2f}",
                f"{line.tax_amount:.2f}",
                f"{line.reimbursements:.2f}",
                f"{line.net_pay:.2f}",
            ]
        )
    rows.append(
        [
            "Total", "", "",
            f"{register.total_hours:.2f}",
            "",
            f"{register.total_gross:.2f}",
            f"{register.total_tax:.2f}",
            "",
            f"{register.total_pay:.2f}",
        ]
    )
    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, -1), (-1, -1), MIST),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.Color(0.8, 0.85, 0.9)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, MIST]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    await asyncio.to_thread(doc.build, story)
    return buffer.getvalue()


async def render_payslip_pdf(register: PayrollRegister, line: PayrollLine, db: AsyncSession) -> bytes:
    profile = await get_profile(db)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    styles = _styles()
    addr_parts = [profile.legal_name, profile.address, profile.phone, profile.website] if profile else ["Skyreon"]
    address = "<br/>".join(escape(part).replace("\n", "<br/>") for part in addr_parts if part)
    head = Table(
        [[_logo_flowable(48 * mm), Paragraph(address, styles["Normal"])]],
        colWidths=[70 * mm, 110 * mm],
    )
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    story = [
        head,
        Spacer(1, 6),
        Table([[""]], colWidths=[180 * mm], rowHeights=[3]),
        Spacer(1, 8),
        Paragraph("PAYSLIP", styles["Title"]),
        Paragraph(register.period_label, styles["Heading2"]),
        Spacer(1, 8),
    ]
    info = [
        ["Employee", line.name, "Code", line.employee_code],
        ["Department", line.department, "Location", line.location_name or "—"],
        ["Pay type", line.pay_type.title(), "Currency", line.currency],
    ]
    info_table = Table(info, colWidths=[32 * mm, 58 * mm, 32 * mm, 58 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), MIST),
                ("BACKGROUND", (2, 0), (2, -1), MIST),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.Color(0.8, 0.85, 0.9)),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 10))

    if line.pay_type == "hourly":
        earnings = [
            ["Earnings", "Amount"],
            [f"Hours ({line.hours} × {line.hourly_rate})", f"{line.time_pay:.2f}"],
            ["Paid leave", f"{line.paid_leave_pay:.2f}"],
            ["Reimbursements", f"{line.reimbursements:.2f}"],
        ]
    else:
        earnings = [
            ["Earnings", "Amount"],
            ["Basic / monthly salary", f"{line.basic_salary:.2f}"],
            ["HRA", f"{line.hra:.2f}"],
            ["Allowances", f"{line.allowances:.2f}"],
            ["Reimbursements", f"{line.reimbursements:.2f}"],
        ]
    if line.bonus > 0:
        earnings.insert(-1, ["Bonus", f"{line.bonus:.2f}"])
    if line.extra_work_pay > 0:
        earnings.insert(-1, ["Extra work pay", f"{line.extra_work_pay:.2f}"])
    deductions = [
        ["Deductions", "Amount"],
        [f"Tax ({line.tax_percent}%)", f"{line.tax_amount:.2f}"],
        ["Provident fund", f"{line.pf_amount:.2f}"],
        ["Professional tax", f"{line.professional_tax:.2f}"],
        ["Other", f"{line.other_deductions:.2f}"],
    ]
    if line.lwp_amount > 0:
        deductions.insert(1, [f"Unpaid leave ({line.lwp_days} days)", f"{line.lwp_amount:.2f}"])

    earn_t = Table(earnings, colWidths=[55 * mm, 30 * mm])
    ded_t = Table(deductions, colWidths=[55 * mm, 30 * mm])
    for tbl in (earn_t, ded_t):
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.Color(0.8, 0.85, 0.9)),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
    story.append(Table([[earn_t, ded_t]], colWidths=[90 * mm, 90 * mm]))
    story.append(Spacer(1, 10))
    net = Table(
        [["Net pay", f"{line.currency} {line.net_pay:.2f}"], ["In words", _amount_words(line.net_pay, line.currency)]],
        colWidths=[40 * mm, 140 * mm],
    )
    net.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), MIST),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (1, 0), (1, 0), 13),
                ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(net)
    story.append(Spacer(1, 18))
    signatory = escape((profile.signatory_name if profile and profile.signatory_name else None) or "Authorised signatory")
    title = escape((profile.signatory_title if profile and profile.signatory_title else None) or "")
    sig = _signature_flowable(profile.signature_image if profile else "")
    story.append(
        Table(
            [[Paragraph("For Skyreon", styles["Normal"]), ""], [sig, ""], [Paragraph(f"<b>{signatory}</b><br/>{title}", styles["Small"]), ""]],
            colWidths=[70 * mm, 110 * mm],
        )
    )
    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "Computer-generated from approved hours, leave and reimbursements. This document uses the Skyreon letterhead.",
            styles["Small"],
        )
    )
    await asyncio.to_thread(doc.build, story)
    return buffer.getvalue()


# keep unused import referenced for older call sites
_ = (LeaveType, defaultdict, ImageReader, CYAN)
