from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import ProjectInvoice
from app.models.employee import Employee
from app.models.hrms import BillStatus, ContractorPayment, ProjectPayment, SalaryPayment, VendorBill
from app.models.project import Project
from app.models.reimbursement import Reimbursement, ReimbursementStatus
from app.models.task import Task
from app.models.time_entry import TaskTimeEntry
from app.schemas.finance import (
    FinanceMonth,
    FinanceProjectRow,
    FinanceTrendPoint,
    FinanceYear,
    FinanceYearManager,
    FinanceYearMonth,
    FinanceYearProject,
)
from app.services.billing import invoiced_by_project
from app.services.company import get_profile
from app.services.reimbursements import approved_for_project_month

UTC = ZoneInfo("UTC")
NAVY = colors.HexColor("#081020")
BLUE = colors.HexColor("#0060A8")
MIST = colors.HexColor("#E8F1F8")
INK = colors.HexColor("#081020")
LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "skyreon-logo.png"


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    last = monthrange(year, month)[1]
    start = datetime.combine(date(year, month, 1), time.min, tzinfo=UTC)
    end = datetime.combine(date(year, month, last) + timedelta(days=1), time.min, tzinfo=UTC)
    return start, end


def _year_bounds(year: int) -> tuple[datetime, datetime]:
    start = datetime.combine(date(year, 1, 1), time.min, tzinfo=UTC)
    end = datetime.combine(date(year + 1, 1, 1), time.min, tzinfo=UTC)
    return start, end


def _money(value: Decimal | int | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _in_period(project: Project, start: date, end: date) -> bool:
    if project.start_date > end:
        return False
    if project.end_date and project.end_date < start:
        return False
    return True


async def _list_projects(db: AsyncSession, start: date, end: date) -> list[Project]:
    rows = list(
        (
            await db.execute(
                select(Project)
                .options(selectinload(Project.manager))
                .order_by(Project.name)
            )
        ).scalars().all()
    )
    return [project for project in rows if _in_period(project, start, end)]


async def _project_cost(db: AsyncSession, project_id: UUID, year: int, month: int) -> Decimal:
    start, end = _month_bounds(year, month)
    rows = (
        await db.execute(
            select(TaskTimeEntry.employee_id, TaskTimeEntry.duration_seconds)
            .join(Task, Task.id == TaskTimeEntry.task_id)
            .where(
                Task.project_id == project_id,
                TaskTimeEntry.end_time.is_not(None),
                TaskTimeEntry.start_time >= start,
                TaskTimeEntry.start_time < end,
            )
        )
    ).all()
    if not rows:
        claims = await approved_for_project_month(db, project_id, year, month)
        return _money(claims)
    emp_ids = {row[0] for row in rows}
    rates = {
        emp.id: emp.hourly_cost_rate
        for emp in (await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))).scalars()
    }
    cost = Decimal("0.00")
    for emp_id, seconds in rows:
        cost += (Decimal(int(seconds)) / Decimal(3600)) * Decimal(rates.get(emp_id, 0))
    cost += await approved_for_project_month(db, project_id, year, month)
    return _money(cost)


async def _cost_map(db: AsyncSession, project_ids: list[UUID], start: datetime, end: datetime, year: int) -> dict[UUID, Decimal]:
    costs: dict[UUID, Decimal] = {project_id: Decimal("0.00") for project_id in project_ids}
    if not project_ids:
        return costs
    time_rows = (
        await db.execute(
            select(Task.project_id, TaskTimeEntry.employee_id, TaskTimeEntry.duration_seconds)
            .join(Task, Task.id == TaskTimeEntry.task_id)
            .where(
                Task.project_id.in_(project_ids),
                TaskTimeEntry.end_time.is_not(None),
                TaskTimeEntry.start_time >= start,
                TaskTimeEntry.start_time < end,
            )
        )
    ).all()
    emp_ids = {row[1] for row in time_rows}
    rates = {}
    if emp_ids:
        rates = {
            emp.id: emp.hourly_cost_rate
            for emp in (await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))).scalars()
        }
    for project_id, emp_id, seconds in time_rows:
        costs[project_id] += (Decimal(int(seconds)) / Decimal(3600)) * Decimal(rates.get(emp_id, 0))
    claim_rows = (
        await db.execute(
            select(Reimbursement.project_id, func.coalesce(func.sum(Reimbursement.amount), 0)).where(
                Reimbursement.project_id.in_(project_ids),
                Reimbursement.status == ReimbursementStatus.APPROVED,
                Reimbursement.payroll_year == year,
            ).group_by(Reimbursement.project_id)
        )
    ).all()
    for project_id, total in claim_rows:
        if project_id:
            costs[project_id] += _money(total)
    return {project_id: _money(amount) for project_id, amount in costs.items()}


async def _received_by_project(db: AsyncSession, year: int, month: int | None = None) -> dict[UUID, Decimal]:
    stmt = select(ProjectPayment.project_id, func.coalesce(func.sum(ProjectPayment.amount), 0)).where(
        ProjectPayment.year == year
    )
    if month:
        stmt = stmt.where(ProjectPayment.month == month)
    rows = (await db.execute(stmt.group_by(ProjectPayment.project_id))).all()
    return {project_id: _money(total) for project_id, total in rows}


async def _invoiced_by_project_year(db: AsyncSession, year: int) -> dict[UUID, Decimal]:
    rows = (
        await db.execute(
            select(ProjectInvoice.project_id, func.coalesce(func.sum(ProjectInvoice.amount), 0)).where(
                ProjectInvoice.year == year
            ).group_by(ProjectInvoice.project_id)
        )
    ).all()
    return {project_id: _money(total) for project_id, total in rows}


async def year_cash_leftover(db: AsyncSession, year: int) -> Decimal:
    received = _money(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProjectPayment.amount), 0)).where(ProjectPayment.year == year)
            )
        ).scalar()
    )
    staff_paid = _money(
        (
            await db.execute(
                select(func.coalesce(func.sum(SalaryPayment.amount), 0)).where(SalaryPayment.year == year)
            )
        ).scalar()
    )
    contractors_paid = _money(
        (
            await db.execute(
                select(func.coalesce(func.sum(ContractorPayment.amount), 0)).where(
                    ContractorPayment.year == year, ContractorPayment.paid_date.is_not(None)
                )
            )
        ).scalar()
    )
    claims_paid = _money(
        (
            await db.execute(
                select(func.coalesce(func.sum(Reimbursement.amount), 0)).where(
                    Reimbursement.status == ReimbursementStatus.APPROVED,
                    Reimbursement.paid_separately.is_(True),
                    Reimbursement.payroll_year == year,
                )
            )
        ).scalar()
    )
    bills = list(
        (
            await db.execute(
                select(VendorBill).where(VendorBill.year == year, VendorBill.status == BillStatus.PAID)
            )
        ).scalars().all()
    )
    opex = sum((row.amount + row.gst_amount for row in bills), Decimal("0.00"))
    return _money(received - staff_paid - contractors_paid - claims_paid - opex)


async def month_report(db: AsyncSession, year: int, month: int) -> FinanceMonth:
    last = monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, last)
    projects = await _list_projects(db, month_start, month_end)
    bills = await invoiced_by_project(db, year, month)
    rows: list[FinanceProjectRow] = []
    total_billing = Decimal("0.00")
    total_cost = Decimal("0.00")
    for project in projects:
        revenue = _money(bills.get(project.id, Decimal("0.00")))
        cost = await _project_cost(db, project.id, year, month)
        margin = _money(revenue - cost)
        total_billing += revenue
        total_cost += cost
        rows.append(
            FinanceProjectRow(
                project_id=project.id,
                project_name=project.name,
                client_name=project.client_name,
                manager_id=project.manager_id,
                manager_name=project.manager.name if project.manager else None,
                billing=revenue,
                cost=cost,
                margin=margin,
            )
        )
    return FinanceMonth(
        year=year,
        month=month,
        period_label=month_start.strftime("%B %Y"),
        total_billing=_money(total_billing),
        total_cost=_money(total_cost),
        total_margin=_money(total_billing - total_cost),
        projects=rows,
    )


async def trend(db: AsyncSession, year: int, month: int, months: int = 12) -> list[FinanceTrendPoint]:
    points: list[FinanceTrendPoint] = []
    cursor = date(year, month, 1)
    for _ in range(months):
        report = await month_report(db, cursor.year, cursor.month)
        points.append(
            FinanceTrendPoint(
                year=cursor.year,
                month=cursor.month,
                label=cursor.strftime("%b %Y"),
                billing=report.total_billing,
                cost=report.total_cost,
                margin=report.total_margin,
            )
        )
        if cursor.month == 1:
            cursor = date(cursor.year - 1, 12, 1)
        else:
            cursor = date(cursor.year, cursor.month - 1, 1)
    points.reverse()
    return points


async def year_report(db: AsyncSession, year: int) -> FinanceYear:
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    projects = await _list_projects(db, year_start, year_end)
    invoiced_map = await _invoiced_by_project_year(db, year)
    received_map = await _received_by_project(db, year)
    start_dt, end_dt = _year_bounds(year)
    cost_map = await _cost_map(db, [project.id for project in projects], start_dt, end_dt, year)

    grouped: dict[UUID | None, list[FinanceYearProject]] = defaultdict(list)
    names: dict[UUID | None, str] = {}
    for project in projects:
        invoiced = invoiced_map.get(project.id, Decimal("0.00"))
        received = received_map.get(project.id, Decimal("0.00"))
        cost = cost_map.get(project.id, Decimal("0.00"))
        grouped[project.manager_id].append(
            FinanceYearProject(
                project_id=project.id,
                project_name=project.name,
                client_name=project.client_name,
                invoiced=invoiced,
                received=received,
                cost=cost,
                profit=_money(invoiced - cost),
            )
        )
        names[project.manager_id] = project.manager.name if project.manager else "Unassigned"

    managers: list[FinanceYearManager] = []
    total_invoiced = Decimal("0.00")
    total_received = Decimal("0.00")
    total_cost = Decimal("0.00")
    for manager_id, items in grouped.items():
        invoiced = sum((item.invoiced for item in items), Decimal("0.00"))
        received = sum((item.received for item in items), Decimal("0.00"))
        cost = sum((item.cost for item in items), Decimal("0.00"))
        total_invoiced += invoiced
        total_received += received
        total_cost += cost
        managers.append(
            FinanceYearManager(
                manager_id=manager_id,
                manager_name=names.get(manager_id, "Unassigned"),
                invoiced=_money(invoiced),
                received=_money(received),
                cost=_money(cost),
                profit=_money(invoiced - cost),
                projects=sorted(items, key=lambda item: item.project_name),
            )
        )
    managers.sort(key=lambda row: row.invoiced, reverse=True)

    months: list[FinanceYearMonth] = []
    for month in range(1, 13):
        month_row = await month_report(db, year, month)
        received = sum((await _received_by_project(db, year, month)).values(), Decimal("0.00"))
        months.append(
            FinanceYearMonth(
                month=month,
                label=date(year, month, 1).strftime("%b"),
                invoiced=month_row.total_billing,
                received=_money(received),
                cost=month_row.total_cost,
                profit=month_row.total_margin,
            )
        )

    return FinanceYear(
        year=year,
        invoiced=_money(total_invoiced),
        received=_money(total_received),
        cost=_money(total_cost),
        profit=_money(total_invoiced - total_cost),
        cash_leftover=await year_cash_leftover(db, year),
        managers=managers,
        months=months,
    )


def _styles():
    styles = getSampleStyleSheet()
    styles["Title"].textColor = NAVY
    styles["Heading2"].textColor = BLUE
    styles["Normal"].textColor = INK
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, textColor=colors.Color(0.25, 0.28, 0.32)))
    return styles


def _logo_flowable(width=42 * mm):
    if not LOGO_PATH.exists():
        return Paragraph("SKYREON", getSampleStyleSheet()["Title"])
    return Image(str(LOGO_PATH), width=width, height=width * 67 / 235)


async def render_year_pdf(report: FinanceYear, db: AsyncSession) -> bytes:
    profile = await get_profile(db)
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
    company = profile.legal_name if profile else "Skyreon"
    header = [_logo_flowable(36 * mm), Paragraph(f"<b>{company}</b><br/>Year report · {report.year}", styles["Heading2"])]
    story = [Table([header], colWidths=[50 * mm, 220 * mm]), Spacer(1, 8)]
    summary = Table(
        [
            ["Invoiced", "Received", "Cost", "Profit", "Cash leftover"],
            [
                f"{report.invoiced:.2f}",
                f"{report.received:.2f}",
                f"{report.cost:.2f}",
                f"{report.profit:.2f}",
                f"{report.cash_leftover:.2f}",
            ],
        ],
        colWidths=[52 * mm] * 5,
    )
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, 1), MIST),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("ALIGN", (0, 1), (-1, 1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(summary)
    story.append(Spacer(1, 10))
    story.append(Paragraph("By project manager", styles["Heading2"]))
    rows = [["Manager / project", "Client", "Invoiced", "Received", "Cost", "Profit"]]
    for manager in report.managers:
        rows.append(
            [
                manager.manager_name,
                "",
                f"{manager.invoiced:.2f}",
                f"{manager.received:.2f}",
                f"{manager.cost:.2f}",
                f"{manager.profit:.2f}",
            ]
        )
        for project in manager.projects:
            rows.append(
                [
                    f"    {project.project_name}",
                    project.client_name,
                    f"{project.invoiced:.2f}",
                    f"{project.received:.2f}",
                    f"{project.cost:.2f}",
                    f"{project.profit:.2f}",
                ]
            )
    table = Table(rows, repeatRows=1, colWidths=[70 * mm, 50 * mm, 35 * mm, 35 * mm, 35 * mm, 35 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.Color(0.8, 0.85, 0.9)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, MIST]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 10))
    story.append(Paragraph("Month by month", styles["Heading2"]))
    month_rows = [["Month", "Invoiced", "Received", "Cost", "Profit"]]
    for row in report.months:
        month_rows.append([row.label, f"{row.invoiced:.2f}", f"{row.received:.2f}", f"{row.cost:.2f}", f"{row.profit:.2f}"])
    month_table = Table(month_rows, repeatRows=1)
    month_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.Color(0.8, 0.85, 0.9)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, MIST]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(month_table)
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Invoiced uses invoice date. Received uses cash date. Profit is invoiced minus time-cost. Cash leftover is company cash in minus salaries, contractor pay, separately paid claims and vendor bills.",
            styles["Small"],
        )
    )
    doc.build(story)
    return buffer.getvalue()
