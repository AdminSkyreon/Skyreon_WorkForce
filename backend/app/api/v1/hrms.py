from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.deps import AdminUser, CurrentEmployee, CurrentUser, DbSession
from app.models.hrms import ApplicantStage
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
from app.schemas.org import NamedCreate
from app.services import hrms as hrms_service

router = APIRouter(tags=["hrms"])


@router.get("/company/month", response_model=CompanyMonthOut)
async def company_month(
    _admin: AdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> CompanyMonthOut:
    return await hrms_service.company_month(db, year, month)


@router.get("/salary-payments", response_model=list[SalaryPaymentOut])
async def list_salary_payments(
    _admin: AdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> list[SalaryPaymentOut]:
    return await hrms_service.list_salary_payments(db, year, month)


@router.post("/employees/{employee_id}/salary-paid", response_model=SalaryPaymentOut)
async def mark_salary_paid(employee_id: UUID, payload: SalaryPayIn, user: AdminUser, db: DbSession) -> SalaryPaymentOut:
    return await hrms_service.mark_salary_paid(db, user, employee_id, payload)


@router.get("/contractors", response_model=ContractorRegister)
async def contractor_register(
    _admin: AdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> ContractorRegister:
    return await hrms_service.contractor_register(db, year, month)


@router.post("/employees/{employee_id}/contractor-paid", response_model=ContractorLine)
async def mark_contractor_paid(
    employee_id: UUID, payload: ContractorPayIn, user: AdminUser, db: DbSession
) -> ContractorLine:
    return await hrms_service.mark_contractor_paid(db, user, employee_id, payload)


@router.get("/employees/{employee_id}/contractor-statement")
async def contractor_statement(
    employee_id: UUID,
    _admin: AdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> Response:
    register = await hrms_service.contractor_register(db, year, month)
    line = next((item for item in register.lines if item.employee_id == employee_id and item.paid), None)
    if line is None:
        return Response(status_code=404, content=b"Statement available after payment is marked")
    return Response(
        content=hrms_service.contractor_statement_pdf(line, year, month),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="contractor-{line.employee_code}-{year}-{month:02d}.pdf"'},
    )


@router.get("/bills", response_model=list[VendorBillOut])
async def list_bills(
    _admin: AdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> list[VendorBillOut]:
    return await hrms_service.list_bills(db, year, month)


@router.post("/bills", response_model=VendorBillOut, status_code=201)
async def create_bill(payload: VendorBillIn, user: AdminUser, db: DbSession) -> VendorBillOut:
    return await hrms_service.create_bill(db, user, payload)


@router.patch("/bills/{bill_id}", response_model=VendorBillOut)
async def update_bill(bill_id: UUID, payload: VendorBillUpdate, _admin: AdminUser, db: DbSession) -> VendorBillOut:
    return await hrms_service.update_bill(db, bill_id, payload)


@router.post("/bills/{bill_id}/paid", response_model=VendorBillOut)
async def mark_bill_paid(bill_id: UUID, _admin: AdminUser, db: DbSession, paid_date: date = Query(...)) -> VendorBillOut:
    return await hrms_service.mark_bill_paid(db, bill_id, paid_date)


@router.post("/reimbursements/{claim_id}/paid")
async def mark_claim_paid(claim_id: UUID, user: AdminUser, db: DbSession) -> dict[str, str]:
    await hrms_service.mark_claim_paid(db, user, claim_id)
    return {"status": "ok"}


@router.get("/jobs", response_model=list[JobOut])
async def list_jobs(_admin: AdminUser, db: DbSession) -> list[JobOut]:
    return await hrms_service.list_jobs(db)


@router.post("/jobs", response_model=JobOut, status_code=201)
async def create_job(payload: JobIn, _admin: AdminUser, db: DbSession) -> JobOut:
    return await hrms_service.create_job(db, payload)


@router.patch("/jobs/{job_id}", response_model=JobOut)
async def update_job(job_id: UUID, payload: JobUpdate, _admin: AdminUser, db: DbSession) -> JobOut:
    return await hrms_service.update_job(db, job_id, payload)


@router.post("/jobs/{job_id}/close", response_model=JobOut)
async def close_job(job_id: UUID, _admin: AdminUser, db: DbSession) -> JobOut:
    return await hrms_service.close_job(db, job_id)


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: UUID, _admin: AdminUser, db: DbSession) -> None:
    await hrms_service.delete_job(db, job_id)


@router.post("/jobs/{job_id}/applicants", response_model=ApplicantOut, status_code=201)
async def add_applicant(job_id: UUID, payload: ApplicantIn, _admin: AdminUser, db: DbSession) -> ApplicantOut:
    return await hrms_service.add_applicant(db, job_id, payload)


@router.patch("/applicants/{applicant_id}", response_model=ApplicantOut)
async def update_applicant(
    applicant_id: UUID, payload: ApplicantUpdate, _admin: AdminUser, db: DbSession
) -> ApplicantOut:
    return await hrms_service.update_applicant(db, applicant_id, payload)


@router.post("/applicants/{applicant_id}/stage", response_model=ApplicantOut)
async def move_applicant(
    applicant_id: UUID, _admin: AdminUser, db: DbSession, stage: ApplicantStage = Query(...)
) -> ApplicantOut:
    return await hrms_service.move_applicant(db, applicant_id, stage)


@router.delete("/applicants/{applicant_id}", status_code=204)
async def delete_applicant(applicant_id: UUID, _admin: AdminUser, db: DbSession) -> None:
    await hrms_service.delete_applicant(db, applicant_id)


@router.get("/document-requirements", response_model=list[DocumentRequirementOut])
async def list_requirements(_user: CurrentUser, db: DbSession) -> list[DocumentRequirementOut]:
    return await hrms_service.list_requirements(db)


@router.post("/document-requirements", response_model=DocumentRequirementOut, status_code=201)
async def create_requirement(payload: NamedCreate, _admin: AdminUser, db: DbSession) -> DocumentRequirementOut:
    return await hrms_service.create_requirement(db, payload.name)


@router.get("/employees/{employee_id}/documents", response_model=list[EmployeeDocumentOut])
async def employee_documents(employee_id: UUID, _admin: AdminUser, db: DbSession) -> list[EmployeeDocumentOut]:
    return await hrms_service.employee_documents(db, employee_id)


@router.post("/employees/{employee_id}/documents/{requirement_id}", response_model=list[EmployeeDocumentOut])
async def set_document(
    employee_id: UUID,
    requirement_id: UUID,
    _admin: AdminUser,
    db: DbSession,
    provided: bool = Query(...),
    note: str = "",
) -> list[EmployeeDocumentOut]:
    return await hrms_service.set_document(db, employee_id, requirement_id, provided, note)


@router.get("/me/documents", response_model=list[EmployeeDocumentOut])
async def my_documents(employee: CurrentEmployee, db: DbSession) -> list[EmployeeDocumentOut]:
    return await hrms_service.employee_documents(db, employee.id)


@router.get("/attendance", response_model=list[AttendanceOut])
async def list_attendance(
    _admin: AdminUser,
    db: DbSession,
    start: date = Query(...),
    end: date = Query(...),
    employee_id: UUID | None = None,
) -> list[AttendanceOut]:
    return await hrms_service.list_attendance(db, start, end, employee_id)


@router.post("/employees/{employee_id}/attendance", response_model=AttendanceOut)
async def mark_attendance(employee_id: UUID, payload: AttendanceIn, _admin: AdminUser, db: DbSession) -> AttendanceOut:
    return await hrms_service.mark_attendance(db, employee_id, payload)


@router.get("/me/attendance", response_model=list[AttendanceOut])
async def my_attendance(
    employee: CurrentEmployee,
    db: DbSession,
    start: date = Query(...),
    end: date = Query(...),
) -> list[AttendanceOut]:
    return await hrms_service.list_attendance(db, start, end, employee.id)


@router.get("/review-cycles", response_model=list[ReviewCycleOut])
async def list_cycles(_admin: AdminUser, db: DbSession) -> list[ReviewCycleOut]:
    return await hrms_service.list_cycles(db)


@router.post("/review-cycles", response_model=ReviewCycleOut, status_code=201)
async def create_cycle(payload: ReviewCycleIn, _admin: AdminUser, db: DbSession) -> ReviewCycleOut:
    return await hrms_service.create_cycle(db, payload)


@router.get("/review-cycles/{cycle_id}/reviews", response_model=list[ReviewOut])
async def list_reviews(cycle_id: UUID, _admin: AdminUser, db: DbSession) -> list[ReviewOut]:
    return await hrms_service.list_reviews(db, cycle_id)


@router.post("/review-cycles/{cycle_id}/reviews", response_model=ReviewOut)
async def upsert_review(cycle_id: UUID, payload: ReviewIn, user: AdminUser, db: DbSession) -> ReviewOut:
    return await hrms_service.upsert_review(db, user, cycle_id, payload)


@router.get("/me/reviews", response_model=list[ReviewOut])
async def my_reviews(employee: CurrentEmployee, db: DbSession) -> list[ReviewOut]:
    return await hrms_service.my_reviews(db, employee.id)


@router.post("/me/reviews/{review_id}/acknowledge", response_model=ReviewOut)
async def acknowledge_review(review_id: UUID, employee: CurrentEmployee, db: DbSession) -> ReviewOut:
    return await hrms_service.acknowledge_review(db, employee, review_id)


@router.get("/assets", response_model=list[AssetOut])
async def list_assets(_admin: AdminUser, db: DbSession) -> list[AssetOut]:
    return await hrms_service.list_assets(db)


@router.post("/assets", response_model=AssetOut, status_code=201)
async def create_asset(payload: AssetIn, _admin: AdminUser, db: DbSession) -> AssetOut:
    return await hrms_service.create_asset(db, payload)


@router.patch("/assets/{asset_id}", response_model=AssetOut)
async def update_asset(asset_id: UUID, payload: AssetUpdate, _admin: AdminUser, db: DbSession) -> AssetOut:
    return await hrms_service.update_asset(db, asset_id, payload)


@router.post("/assets/{asset_id}/assign", response_model=AssetOut)
async def assign_asset(asset_id: UUID, _admin: AdminUser, db: DbSession, employee_id: UUID = Query(...)) -> AssetOut:
    return await hrms_service.assign_asset(db, asset_id, employee_id)


@router.post("/assets/{asset_id}/return", response_model=AssetOut)
async def return_asset(asset_id: UUID, _admin: AdminUser, db: DbSession) -> AssetOut:
    return await hrms_service.return_asset(db, asset_id)


@router.get("/me/assets", response_model=list[AssetOut])
async def my_assets(employee: CurrentEmployee, db: DbSession) -> list[AssetOut]:
    return await hrms_service.my_assets(db, employee.id)


@router.post("/me/assets/{asset_id}/acknowledge", response_model=AssetOut)
async def acknowledge_asset(asset_id: UUID, employee: CurrentEmployee, db: DbSession) -> AssetOut:
    return await hrms_service.acknowledge_asset(db, employee, asset_id)
