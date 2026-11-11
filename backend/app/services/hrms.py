from calendar import monthrange
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from uuid import UUID

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequest, Conflict, Forbidden, NotFound
from app.models.billing import ProjectInvoice
from app.models.employee import Employee, EmployeeStatus, Engagement, PayType
from app.models.hrms import (
    Applicant,
    ApplicantStage,
    AssetStatus,
    AttendanceDay,
    AttendanceMark,
    BillStatus,
    CompanyAsset,
    ContractorPayment,
    DocumentRequirement,
    EmployeeDocument,
    Job,
    PerformanceReview,
    ProjectPayment,
    ReviewCycle,
    SalaryPayment,
    VendorBill,
    VendorCategory,
)
from app.models.payroll import PayrollPeriod, PayrollPeriodStatus
from app.models.project import Project
from app.models.reimbursement import Reimbursement, ReimbursementStatus
from app.models.user import User, is_staff, is_super_admin
from app.schemas.hrms import (
    ApplicantIn,
    ApplicantOut,
    ApplicantUpdate,
    AssetIn,
    AssetOut,
    AssetUpdate,
    AttendanceIn,
    AttendanceOut,
    CompanyMonthOut,
    ContractorLine,
    ContractorPayIn,
    ContractorRegister,
    DocumentRequirementOut,
    EmployeeDocumentOut,
    JobIn,
    JobOut,
    JobUpdate,
    PaymentIn,
    ProjectPaymentOut,
    ReviewCycleIn,
    ReviewCycleOut,
    ReviewIn,
    ReviewOut,
    SalaryPayIn,
    SalaryPaymentOut,
    VendorBillIn,
    VendorBillOut,
    VendorBillUpdate,
)
from app.services.audit import log_audit
from app.services.payroll import _approved_hours, _compute_register, _get_period


def _month_label(year: int, month: int) -> str:
    return date(year, month, 1).strftime("%B %Y")


def _money(value: Decimal | int | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.00"))


async def record_payment(db: AsyncSession, user: User, project_id: UUID, data: PaymentIn) -> ProjectPaymentOut:
    project = await db.get(Project, project_id)
    if project is None:
        raise NotFound("Project not found")
    row = ProjectPayment(
        project_id=project_id,
        year=data.year,
        month=data.month,
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
        project_id,
        summary=f"Received {data.amount} for {project.name} {_month_label(data.year, data.month)}",
    )
    await db.commit()
    await db.refresh(row)
    return ProjectPaymentOut(
        id=row.id,
        project_id=row.project_id,
        project_name=project.name,
        year=row.year,
        month=row.month,
        amount=row.amount,
        received_date=row.received_date,
        note=row.note,
    )


async def list_payments(db: AsyncSession, year: int, month: int) -> list[ProjectPaymentOut]:
    rows = (
        await db.execute(
            select(ProjectPayment, Project.name)
            .join(Project, Project.id == ProjectPayment.project_id)
            .where(ProjectPayment.year == year, ProjectPayment.month == month)
            .order_by(Project.name)
        )
    ).all()
    return [
        ProjectPaymentOut(
            id=row.id,
            project_id=row.project_id,
            project_name=name,
            year=row.year,
            month=row.month,
            amount=row.amount,
            received_date=row.received_date,
            note=row.note,
        )
        for row, name in rows
    ]


async def mark_salary_paid(db: AsyncSession, user: User, employee_id: UUID, data: SalaryPayIn) -> SalaryPaymentOut:
    employee = await db.get(Employee, employee_id)
    if employee is None:
        raise NotFound("Employee not found")
    if employee.engagement != Engagement.STAFF:
        raise BadRequest("Use the contractor register for this person")
    if user.employee and user.employee.id == employee_id:
        raise Forbidden("You cannot mark your own salary paid")
    period = await _get_period(db, data.year, data.month)
    if period is None or period.status != PayrollPeriodStatus.CLOSED:
        raise BadRequest("Close the staff payroll month before marking salary paid")
    register = await _compute_register(db, data.year, data.month)
    line = next((item for item in register.lines if item.employee_id == employee_id), None)
    if line is None:
        raise BadRequest("This person is not on the closed staff register")
    amount = data.amount if data.amount is not None else line.net_pay
    existing = (
        await db.execute(
            select(SalaryPayment).where(
                SalaryPayment.employee_id == employee_id,
                SalaryPayment.year == data.year,
                SalaryPayment.month == data.month,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.amount = amount
        existing.paid_date = data.paid_date
        existing.reference = data.reference
        existing.marked_by_id = user.id
        row = existing
    else:
        row = SalaryPayment(
            employee_id=employee_id,
            year=data.year,
            month=data.month,
            amount=amount,
            paid_date=data.paid_date,
            reference=data.reference,
            marked_by_id=user.id,
        )
        db.add(row)
    await log_audit(
        db,
        user,
        "created",
        "salary_payment",
        employee_id,
        summary=f"Salary paid {employee.name} {_month_label(data.year, data.month)} = {amount}",
    )
    await db.commit()
    await db.refresh(row)
    return SalaryPaymentOut(
        id=row.id,
        employee_id=row.employee_id,
        employee_name=employee.name,
        year=row.year,
        month=row.month,
        amount=row.amount,
        paid_date=row.paid_date,
        reference=row.reference,
        paid=True,
    )


async def list_salary_payments(db: AsyncSession, year: int, month: int) -> list[SalaryPaymentOut]:
    rows = (
        await db.execute(
            select(SalaryPayment, Employee.name)
            .join(Employee, Employee.id == SalaryPayment.employee_id)
            .where(SalaryPayment.year == year, SalaryPayment.month == month)
        )
    ).all()
    return [
        SalaryPaymentOut(
            id=row.id,
            employee_id=row.employee_id,
            employee_name=name,
            year=row.year,
            month=row.month,
            amount=row.amount,
            paid_date=row.paid_date,
            reference=row.reference,
            paid=True,
        )
        for row, name in rows
    ]


async def contractor_register(db: AsyncSession, year: int, month: int) -> ContractorRegister:
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    people = list(
        (
            await db.execute(
                select(Employee)
                .options(selectinload(Employee.payroll), selectinload(Employee.user))
                .where(Employee.engagement == Engagement.CONTRACTOR, Employee.status == EmployeeStatus.ACTIVE)
                .order_by(Employee.name)
            )
        ).scalars().all()
    )
    paid = {
        row.employee_id: row
        for row in (
            await db.execute(
                select(ContractorPayment).where(ContractorPayment.year == year, ContractorPayment.month == month)
            )
        ).scalars().all()
    }
    lines: list[ContractorLine] = []
    for person in people:
        hours = await _approved_hours(db, person.id, start, end)
        rate = person.payroll.hourly_pay_rate if person.payroll else Decimal("0.00")
        if person.pay_type == PayType.HOURLY:
            calculated = (hours * rate).quantize(Decimal("0.00"))
        else:
            calculated = person.contract_monthly_fee
        row = paid.get(person.id)
        lines.append(
            ContractorLine(
                employee_id=person.id,
                name=person.name,
                employee_code=person.employee_code,
                department=person.department,
                pay_type=person.pay_type.value,
                hours=hours,
                calculated=calculated,
                amount=row.amount if row else calculated,
                deduction=row.deduction if row else Decimal("0.00"),
                paid=row is not None and row.paid_date is not None,
                paid_date=row.paid_date if row else None,
                reference=row.reference if row else "",
            )
        )
    return ContractorRegister(
        year=year,
        month=month,
        period_label=_month_label(year, month),
        lines=lines,
        total_calculated=sum((line.calculated for line in lines), Decimal("0.00")),
        total_paid=sum((line.amount for line in lines if line.paid), Decimal("0.00")),
    )


async def mark_contractor_paid(
    db: AsyncSession, user: User, employee_id: UUID, data: ContractorPayIn
) -> ContractorLine:
    if user.employee and user.employee.id == employee_id:
        raise Forbidden("You cannot mark your own contractor payment")
    register = await contractor_register(db, data.year, data.month)
    line = next((item for item in register.lines if item.employee_id == employee_id), None)
    if line is None:
        raise NotFound("Contractor not found")
    amount = data.amount if data.amount is not None else line.calculated
    existing = (
        await db.execute(
            select(ContractorPayment).where(
                ContractorPayment.employee_id == employee_id,
                ContractorPayment.year == data.year,
                ContractorPayment.month == data.month,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.calculated = line.calculated
        existing.amount = amount
        existing.paid_date = data.paid_date
        existing.reference = data.reference
        existing.deduction = data.deduction
        existing.marked_by_id = user.id
    else:
        db.add(
            ContractorPayment(
                employee_id=employee_id,
                year=data.year,
                month=data.month,
                calculated=line.calculated,
                amount=amount,
                paid_date=data.paid_date,
                reference=data.reference,
                deduction=data.deduction,
                marked_by_id=user.id,
            )
        )
    await log_audit(
        db,
        user,
        "created",
        "contractor_payment",
        employee_id,
        summary=f"Contractor paid {line.name} {_month_label(data.year, data.month)} = {amount}",
    )
    await db.commit()
    updated = await contractor_register(db, data.year, data.month)
    return next(item for item in updated.lines if item.employee_id == employee_id)


def contractor_statement_pdf(line: ContractorLine, year: int, month: int) -> bytes:
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm)
    story = [
        Paragraph("Skyreon contractor payment", styles["Title"]),
        Paragraph(_month_label(year, month), styles["Normal"]),
        Spacer(1, 8 * mm),
        Table(
            [
                ["Name", line.name],
                ["Code", line.employee_code],
                ["Hours", str(line.hours)],
                ["Calculated", str(line.calculated)],
                ["Paid", str(line.amount)],
                ["Deduction", str(line.deduction)],
                ["Reference", line.reference or "—"],
                ["Paid date", str(line.paid_date or "—")],
            ],
            colWidths=[50 * mm, 110 * mm],
        ),
    ]
    story[-1].setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke)]))
    doc.build(story)
    return buffer.getvalue()


def _vendor_gst(amount: Decimal, gst_percent: Decimal | None, gst_amount: Decimal | None) -> Decimal:
    if gst_percent is not None:
        return (amount * gst_percent / Decimal("100")).quantize(Decimal("0.00"))
    return (gst_amount or Decimal("0.00")).quantize(Decimal("0.00"))


async def create_bill(db: AsyncSession, user: User, data: VendorBillIn) -> VendorBillOut:
    year = data.bill_date.year
    month = data.bill_date.month
    gst_amount = _vendor_gst(data.amount, data.gst_percent, data.gst_amount)
    row = VendorBill(
        vendor_name=data.vendor_name,
        category=data.category,
        amount=data.amount,
        gst_amount=gst_amount,
        bill_date=data.bill_date,
        year=year,
        month=month,
        project_id=data.project_id,
        note=data.note,
        recurring=data.recurring,
        status=BillStatus.APPROVED,
        entered_by_id=user.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _bill_out(row)


async def list_bills(db: AsyncSession, year: int, month: int) -> list[VendorBillOut]:
    rows = (
        await db.execute(
            select(VendorBill)
            .where(VendorBill.year == year, VendorBill.month == month)
            .order_by(VendorBill.bill_date.desc())
        )
    ).scalars().all()
    return [_bill_out(row) for row in rows]


async def update_bill(db: AsyncSession, bill_id: UUID, data: VendorBillUpdate) -> VendorBillOut:
    row = await db.get(VendorBill, bill_id)
    if row is None:
        raise NotFound("Bill not found")
    payload = data.model_dump(exclude_unset=True)
    if "bill_date" in payload and payload["bill_date"]:
        row.year = payload["bill_date"].year
        row.month = payload["bill_date"].month
    amount = row.amount
    if "amount" in payload and payload["amount"] is not None:
        amount = payload["amount"]
    gst_percent = payload.pop("gst_percent", None)
    if gst_percent is not None or "amount" in payload:
        row.gst_amount = _vendor_gst(amount, gst_percent, payload.get("gst_amount", row.gst_amount))
    payload.pop("gst_amount", None)
    for key, value in payload.items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return _bill_out(row)


async def mark_bill_paid(db: AsyncSession, bill_id: UUID, paid_date: date) -> VendorBillOut:
    row = await db.get(VendorBill, bill_id)
    if row is None:
        raise NotFound("Bill not found")
    if row.status == BillStatus.PAID:
        raise BadRequest("Bill is already marked paid")
    if paid_date < row.bill_date:
        raise BadRequest("Paid date cannot be earlier than bill date")
    row.status = BillStatus.PAID
    row.paid_date = paid_date
    await db.commit()
    await db.refresh(row)
    return _bill_out(row)


def _bill_out(row: VendorBill) -> VendorBillOut:
    return VendorBillOut(
        id=row.id,
        vendor_name=row.vendor_name,
        category=row.category,
        amount=row.amount,
        gst_amount=row.gst_amount,
        bill_date=row.bill_date,
        paid_date=row.paid_date,
        year=row.year,
        month=row.month,
        project_id=row.project_id,
        note=row.note,
        recurring=row.recurring,
        status=row.status,
    )


async def company_month(db: AsyncSession, year: int, month: int) -> CompanyMonthOut:
    received = _money(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProjectPayment.amount), 0)).where(
                    ProjectPayment.year == year, ProjectPayment.month == month
                )
            )
        ).scalar()
    )
    staff_paid = _money(
        (
            await db.execute(
                select(func.coalesce(func.sum(SalaryPayment.amount), 0)).where(
                    SalaryPayment.year == year, SalaryPayment.month == month
                )
            )
        ).scalar()
    )
    contractors_paid = _money(
        (
            await db.execute(
                select(func.coalesce(func.sum(ContractorPayment.amount), 0)).where(
                    ContractorPayment.year == year,
                    ContractorPayment.month == month,
                    ContractorPayment.paid_date.is_not(None),
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
                    Reimbursement.payroll_month == month,
                )
            )
        ).scalar()
    )
    bills = list(
        (
            await db.execute(select(VendorBill).where(VendorBill.year == year, VendorBill.month == month, VendorBill.status == BillStatus.PAID))
        ).scalars().all()
    )
    compliance_cats = {VendorCategory.GST_FILING, VendorCategory.CA_AUDIT, VendorCategory.LEGAL}
    compliance = sum((row.amount + row.gst_amount for row in bills if row.category in compliance_cats), Decimal("0.00"))
    other_opex = sum((row.amount + row.gst_amount for row in bills if row.category not in compliance_cats), Decimal("0.00"))
    invoiced = _money(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProjectInvoice.amount), 0)).where(
                    ProjectInvoice.year == year, ProjectInvoice.month == month
                )
            )
        ).scalar()
    )
    receipts_against_earlier = _money(
        (
            await db.execute(
                select(func.coalesce(func.sum(ProjectPayment.amount), 0))
                .join(ProjectInvoice, ProjectInvoice.id == ProjectPayment.invoice_id)
                .where(
                    ProjectPayment.year == year,
                    ProjectPayment.month == month,
                    or_(ProjectInvoice.year != year, ProjectInvoice.month != month),
                )
            )
        ).scalar()
    )
    salaries_calculated = Decimal("0.00")
    period = await _get_period(db, year, month)
    if period and period.snapshot_json:
        try:
            import json

            salaries_calculated = _money(json.loads(period.snapshot_json).get("total_pay"))
        except (TypeError, ValueError):
            salaries_calculated = Decimal("0.00")
    contractors = await contractor_register(db, year, month)
    leftover = received - staff_paid - contractors_paid - claims_paid - compliance - other_opex
    return CompanyMonthOut(
        year=year,
        month=month,
        period_label=_month_label(year, month),
        received=received,
        staff_paid=staff_paid,
        contractors_paid=contractors_paid,
        claims_paid=claims_paid,
        compliance=compliance,
        other_opex=other_opex,
        leftover=leftover,
        invoiced_not_cash=invoiced,
        receipts_against_earlier=receipts_against_earlier,
        salaries_calculated=salaries_calculated,
        contractors_calculated=contractors.total_calculated,
    )


async def mark_claim_paid(db: AsyncSession, user: User, claim_id: UUID) -> Reimbursement:
    row = await db.get(Reimbursement, claim_id)
    if row is None:
        raise NotFound("Reimbursement not found")
    if row.status != ReimbursementStatus.APPROVED:
        raise BadRequest("Only approved claims can be marked paid")
    if user.employee and row.employee_id == user.employee.id:
        raise Forbidden("You cannot mark your own claim paid")
    row.paid_separately = True
    row.paid_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(row)
    return row


async def create_job(db: AsyncSession, data: JobIn) -> JobOut:
    row = Job(
        title=data.title,
        department=data.department,
        location_id=data.location_id,
        hiring_manager_id=data.hiring_manager_id,
        opened_on=data.opened_on,
        note=data.note,
        is_open=True,
    )
    db.add(row)
    await db.commit()
    return await get_job(db, row.id)


async def list_jobs(db: AsyncSession) -> list[JobOut]:
    rows = list((await db.execute(select(Job).options(selectinload(Job.applicants)).order_by(Job.opened_on.desc()))).scalars().all())
    return [_job_out(row) for row in rows]


async def get_job(db: AsyncSession, job_id: UUID) -> JobOut:
    row = (
        await db.execute(select(Job).options(selectinload(Job.applicants)).where(Job.id == job_id))
    ).scalar_one_or_none()
    if row is None:
        raise NotFound("Job not found")
    return _job_out(row)


async def update_job(db: AsyncSession, job_id: UUID, data: JobUpdate) -> JobOut:
    row = await db.get(Job, job_id)
    if row is None:
        raise NotFound("Job not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    await db.commit()
    return await get_job(db, job_id)


async def close_job(db: AsyncSession, job_id: UUID) -> JobOut:
    row = await db.get(Job, job_id)
    if row is None:
        raise NotFound("Job not found")
    row.is_open = False
    await db.commit()
    return await get_job(db, job_id)


def _job_out(row: Job) -> JobOut:
    return JobOut(
        id=row.id,
        title=row.title,
        department=row.department,
        location_id=row.location_id,
        hiring_manager_id=row.hiring_manager_id,
        is_open=row.is_open,
        opened_on=row.opened_on,
        note=row.note,
        applicants=[
            ApplicantOut(id=item.id, job_id=item.job_id, name=item.name, email=item.email, stage=item.stage, note=item.note)
            for item in row.applicants
        ],
    )


async def add_applicant(db: AsyncSession, job_id: UUID, data: ApplicantIn) -> ApplicantOut:
    if await db.get(Job, job_id) is None:
        raise NotFound("Job not found")
    row = Applicant(job_id=job_id, name=data.name, email=data.email, note=data.note)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ApplicantOut(id=row.id, job_id=row.job_id, name=row.name, email=row.email, stage=row.stage, note=row.note)


async def update_applicant(db: AsyncSession, applicant_id: UUID, data: ApplicantUpdate) -> ApplicantOut:
    row = await db.get(Applicant, applicant_id)
    if row is None:
        raise NotFound("Applicant not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return ApplicantOut(id=row.id, job_id=row.job_id, name=row.name, email=row.email, stage=row.stage, note=row.note)


async def move_applicant(db: AsyncSession, applicant_id: UUID, stage: ApplicantStage) -> ApplicantOut:
    row = await db.get(Applicant, applicant_id)
    if row is None:
        raise NotFound("Applicant not found")
    row.stage = stage
    await db.commit()
    await db.refresh(row)
    return ApplicantOut(id=row.id, job_id=row.job_id, name=row.name, email=row.email, stage=row.stage, note=row.note)


async def list_requirements(db: AsyncSession) -> list[DocumentRequirementOut]:
    rows = (await db.execute(select(DocumentRequirement).where(DocumentRequirement.is_active.is_(True)).order_by(DocumentRequirement.name))).scalars().all()
    return [DocumentRequirementOut(id=row.id, name=row.name, is_active=row.is_active) for row in rows]


async def create_requirement(db: AsyncSession, name: str) -> DocumentRequirementOut:
    existing = (await db.execute(select(DocumentRequirement).where(DocumentRequirement.name.ilike(name.strip())))).scalar_one_or_none()
    if existing:
        existing.is_active = True
        await db.commit()
        return DocumentRequirementOut(id=existing.id, name=existing.name, is_active=existing.is_active)
    row = DocumentRequirement(name=name.strip())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return DocumentRequirementOut(id=row.id, name=row.name, is_active=row.is_active)


async def employee_documents(db: AsyncSession, employee_id: UUID) -> list[EmployeeDocumentOut]:
    reqs = (await db.execute(select(DocumentRequirement).where(DocumentRequirement.is_active.is_(True)).order_by(DocumentRequirement.name))).scalars().all()
    have = {
        row.requirement_id: row
        for row in (await db.execute(select(EmployeeDocument).where(EmployeeDocument.employee_id == employee_id))).scalars().all()
    }
    return [
        EmployeeDocumentOut(
            requirement_id=req.id,
            name=req.name,
            provided=have[req.id].provided if req.id in have else False,
            note=have[req.id].note if req.id in have else "",
        )
        for req in reqs
    ]


async def set_document(db: AsyncSession, employee_id: UUID, requirement_id: UUID, provided: bool, note: str = "") -> list[EmployeeDocumentOut]:
    row = (
        await db.execute(
            select(EmployeeDocument).where(
                EmployeeDocument.employee_id == employee_id, EmployeeDocument.requirement_id == requirement_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = EmployeeDocument(employee_id=employee_id, requirement_id=requirement_id)
        db.add(row)
    row.provided = provided
    row.note = note
    await db.commit()
    return await employee_documents(db, employee_id)


async def mark_attendance(db: AsyncSession, employee_id: UUID, data: AttendanceIn) -> AttendanceOut:
    employee = await db.get(Employee, employee_id)
    if employee is None:
        raise NotFound("Employee not found")
    row = (
        await db.execute(
            select(AttendanceDay).where(AttendanceDay.employee_id == employee_id, AttendanceDay.work_date == data.work_date)
        )
    ).scalar_one_or_none()
    if row is None:
        row = AttendanceDay(employee_id=employee_id, work_date=data.work_date)
        db.add(row)
    row.mark = data.mark
    row.note = data.note
    await db.commit()
    await db.refresh(row)
    return AttendanceOut(
        id=row.id,
        employee_id=row.employee_id,
        employee_name=employee.name,
        work_date=row.work_date,
        mark=row.mark,
        note=row.note,
    )


async def list_attendance(db: AsyncSession, start: date, end: date, employee_id: UUID | None = None) -> list[AttendanceOut]:
    if end < start:
        raise BadRequest("End date must be on or after start date")
    stmt = (
        select(AttendanceDay, Employee.name)
        .join(Employee, Employee.id == AttendanceDay.employee_id)
        .where(AttendanceDay.work_date >= start, AttendanceDay.work_date <= end)
        .order_by(AttendanceDay.work_date.desc(), Employee.name)
    )
    if employee_id:
        stmt = stmt.where(AttendanceDay.employee_id == employee_id)
    return [
        AttendanceOut(id=row.id, employee_id=row.employee_id, employee_name=name, work_date=row.work_date, mark=row.mark, note=row.note)
        for row, name in (await db.execute(stmt)).all()
    ]


async def create_cycle(db: AsyncSession, data: ReviewCycleIn) -> ReviewCycleOut:
    row = ReviewCycle(name=data.name, start_date=data.start_date, end_date=data.end_date, is_open=True)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ReviewCycleOut(id=row.id, name=row.name, start_date=row.start_date, end_date=row.end_date, is_open=row.is_open)


async def list_cycles(db: AsyncSession) -> list[ReviewCycleOut]:
    rows = (await db.execute(select(ReviewCycle).order_by(ReviewCycle.start_date.desc()))).scalars().all()
    return [ReviewCycleOut(id=row.id, name=row.name, start_date=row.start_date, end_date=row.end_date, is_open=row.is_open) for row in rows]


async def upsert_review(db: AsyncSession, user: User, cycle_id: UUID, data: ReviewIn) -> ReviewOut:
    if await db.get(ReviewCycle, cycle_id) is None:
        raise NotFound("Review cycle not found")
    employee = await db.get(Employee, data.employee_id)
    if employee is None:
        raise NotFound("Employee not found")
    if user.employee and user.employee.id == data.employee_id and not is_super_admin(user):
        raise Forbidden("You cannot write your own review")
    row = (
        await db.execute(
            select(PerformanceReview).where(
                PerformanceReview.cycle_id == cycle_id, PerformanceReview.employee_id == data.employee_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = PerformanceReview(cycle_id=cycle_id, employee_id=data.employee_id)
        db.add(row)
    row.summary = data.summary
    row.manager_id = user.employee.id if user.employee else None
    await db.commit()
    await db.refresh(row)
    return ReviewOut(
        id=row.id,
        cycle_id=row.cycle_id,
        employee_id=row.employee_id,
        employee_name=employee.name,
        manager_id=row.manager_id,
        summary=row.summary,
        acknowledged=row.acknowledged,
    )


async def list_reviews(db: AsyncSession, cycle_id: UUID) -> list[ReviewOut]:
    rows = (
        await db.execute(
            select(PerformanceReview, Employee.name)
            .join(Employee, Employee.id == PerformanceReview.employee_id)
            .where(PerformanceReview.cycle_id == cycle_id)
        )
    ).all()
    return [
        ReviewOut(
            id=row.id,
            cycle_id=row.cycle_id,
            employee_id=row.employee_id,
            employee_name=name,
            manager_id=row.manager_id,
            summary=row.summary,
            acknowledged=row.acknowledged,
        )
        for row, name in rows
    ]


async def acknowledge_review(db: AsyncSession, employee: Employee, review_id: UUID) -> ReviewOut:
    row = await db.get(PerformanceReview, review_id)
    if row is None or row.employee_id != employee.id:
        raise Forbidden("You can only acknowledge your own review")
    row.acknowledged = True
    await db.commit()
    await db.refresh(row)
    return ReviewOut(
        id=row.id,
        cycle_id=row.cycle_id,
        employee_id=row.employee_id,
        employee_name=employee.name,
        manager_id=row.manager_id,
        summary=row.summary,
        acknowledged=row.acknowledged,
    )


async def my_reviews(db: AsyncSession, employee_id: UUID) -> list[ReviewOut]:
    rows = (
        await db.execute(
            select(PerformanceReview, Employee.name)
            .join(Employee, Employee.id == PerformanceReview.employee_id)
            .where(PerformanceReview.employee_id == employee_id)
        )
    ).all()
    return [
        ReviewOut(
            id=row.id,
            cycle_id=row.cycle_id,
            employee_id=row.employee_id,
            employee_name=name,
            manager_id=row.manager_id,
            summary=row.summary,
            acknowledged=row.acknowledged,
        )
        for row, name in rows
    ]


async def create_asset(db: AsyncSession, data: AssetIn) -> AssetOut:
    taken = (
        await db.execute(select(CompanyAsset.id).where(CompanyAsset.asset_tag == data.asset_tag).limit(1))
    ).scalar_one_or_none()
    if taken is not None:
        raise Conflict("That asset tag is already in use")
    row = CompanyAsset(name=data.name, asset_tag=data.asset_tag, category=data.category, note=data.note)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _asset_out(row, None)


async def list_assets(db: AsyncSession) -> list[AssetOut]:
    rows = (
        await db.execute(
            select(CompanyAsset, Employee.name)
            .outerjoin(Employee, Employee.id == CompanyAsset.assigned_to_id)
            .order_by(CompanyAsset.name)
        )
    ).all()
    return [_asset_out(row, name) for row, name in rows]


async def update_asset(db: AsyncSession, asset_id: UUID, data: AssetUpdate) -> AssetOut:
    row = await db.get(CompanyAsset, asset_id)
    if row is None:
        raise NotFound("Asset not found")
    payload = data.model_dump(exclude_unset=True)
    if "asset_tag" in payload and payload["asset_tag"]:
        taken = (
            await db.execute(
                select(CompanyAsset).where(CompanyAsset.asset_tag == payload["asset_tag"], CompanyAsset.id != row.id)
            )
        ).scalar_one_or_none()
        if taken:
            raise Conflict("That asset tag is already in use")
    for key, value in payload.items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    employee = await db.get(Employee, row.assigned_to_id) if row.assigned_to_id else None
    return _asset_out(row, employee.name if employee else None)


async def assign_asset(db: AsyncSession, asset_id: UUID, employee_id: UUID) -> AssetOut:
    row = await db.get(CompanyAsset, asset_id)
    if row is None:
        raise NotFound("Asset not found")
    employee = await db.get(Employee, employee_id)
    if employee is None:
        raise NotFound("Employee not found")
    row.assigned_to_id = employee_id
    row.status = AssetStatus.ASSIGNED
    row.acknowledged = False
    await db.commit()
    await db.refresh(row)
    return _asset_out(row, employee.name)


async def return_asset(db: AsyncSession, asset_id: UUID) -> AssetOut:
    row = await db.get(CompanyAsset, asset_id)
    if row is None:
        raise NotFound("Asset not found")
    row.status = AssetStatus.RETURNED
    row.assigned_to_id = None
    row.acknowledged = False
    await db.commit()
    await db.refresh(row)
    return _asset_out(row, None)


async def acknowledge_asset(db: AsyncSession, employee: Employee, asset_id: UUID) -> AssetOut:
    row = await db.get(CompanyAsset, asset_id)
    if row is None or row.assigned_to_id != employee.id:
        raise Forbidden("You can only acknowledge assets assigned to you")
    row.acknowledged = True
    await db.commit()
    await db.refresh(row)
    return _asset_out(row, employee.name)


async def my_assets(db: AsyncSession, employee_id: UUID) -> list[AssetOut]:
    rows = (await db.execute(select(CompanyAsset).where(CompanyAsset.assigned_to_id == employee_id))).scalars().all()
    employee = await db.get(Employee, employee_id)
    return [_asset_out(row, employee.name if employee else None) for row in rows]


def _asset_out(row: CompanyAsset, name: str | None) -> AssetOut:
    return AssetOut(
        id=row.id,
        name=row.name,
        asset_tag=row.asset_tag,
        category=row.category,
        status=row.status,
        assigned_to_id=row.assigned_to_id,
        assigned_to_name=name,
        acknowledged=row.acknowledged,
        note=row.note,
    )


async def assigned_assets(db: AsyncSession, employee_id: UUID) -> list[CompanyAsset]:
    return list(
        (
            await db.execute(
                select(CompanyAsset).where(
                    CompanyAsset.assigned_to_id == employee_id, CompanyAsset.status == AssetStatus.ASSIGNED
                )
            )
        ).scalars().all()
    )


_ = (is_staff,)
