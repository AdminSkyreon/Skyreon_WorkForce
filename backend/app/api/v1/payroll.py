from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.deps import AdminUser, CurrentEmployee, CurrentUser, DbSession, SuperAdminUser
from app.core.exceptions import Forbidden, NotFound
from app.models.user import is_staff
from app.schemas.payroll import PayrollDetailsIn, PayrollDetailsOut, PayrollRegister
from app.services import payroll as payroll_service

router = APIRouter(tags=["payroll"])


@router.get("/admin/payroll/details/{employee_id}", response_model=PayrollDetailsOut)
async def get_payroll_details(
    employee_id: UUID,
    _admin: AdminUser,
    db: DbSession,
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
) -> PayrollDetailsOut:
    return await payroll_service.get_details(db, employee_id, year, month)


@router.put("/admin/payroll/details/{employee_id}", response_model=PayrollDetailsOut)
async def save_payroll_details(
    employee_id: UUID,
    payload: PayrollDetailsIn,
    user: AdminUser,
    db: DbSession,
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
) -> PayrollDetailsOut:
    return await payroll_service.upsert_details(db, employee_id, payload, user, year, month)


@router.get("/admin/payroll", response_model=PayrollRegister)
async def payroll_register(
    _admin: AdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    location_id: UUID | None = None,
) -> PayrollRegister:
    return await payroll_service.build_register(db, year, month, location_id)


@router.post("/admin/payroll/close", response_model=PayrollRegister)
async def close_payroll(
    user: AdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> PayrollRegister:
    return await payroll_service.close_month(db, user, year, month)


@router.post("/admin/payroll/reopen", response_model=PayrollRegister)
async def reopen_payroll(
    user: SuperAdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> PayrollRegister:
    return await payroll_service.reopen_month(db, user, year, month)


@router.get("/admin/payroll/pdf")
async def payroll_pdf(
    _admin: AdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    location_id: UUID | None = None,
) -> Response:
    register = await payroll_service.build_register(db, year, month, location_id)
    filename = f"payroll-{year}-{month:02d}.pdf"
    return Response(
        content=await payroll_service.render_register_pdf(register, db),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/admin/payroll/{employee_id}/pdf")
async def payslip_pdf(
    employee_id: UUID,
    _admin: AdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> Response:
    register = await payroll_service.build_register(db, year, month)
    line = next((item for item in register.lines if item.employee_id == employee_id), None)
    if line is None:
        raise NotFound("Employee not found in this payroll period")
    filename = f"payslip-{line.employee_code}-{year}-{month:02d}.pdf"
    return Response(
        content=await payroll_service.render_payslip_pdf(register, line, db),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/me/payslips/{year}/{month}/pdf")
async def my_payslip_pdf(
    year: int,
    month: int,
    employee: CurrentEmployee,
    db: DbSession,
) -> Response:
    register = await payroll_service.build_register(db, year, month)
    if not register.closed:
        raise Forbidden("Payslip is available after payroll is closed")
    line = next((item for item in register.lines if item.employee_id == employee.id), None)
    if line is None:
        raise NotFound("No payslip for this month")
    filename = f"payslip-{line.employee_code}-{year}-{month:02d}.pdf"
    return Response(
        content=await payroll_service.render_payslip_pdf(register, line, db),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/me/payslips/{year}/{month}", response_model=PayrollRegister)
async def my_payslip_meta(
    year: int, month: int, employee: CurrentEmployee, db: DbSession
) -> PayrollRegister:
    register = await payroll_service.build_register(db, year, month)
    if not register.closed:
        raise Forbidden("Payslip is available after payroll is closed")
    register.lines = [line for line in register.lines if line.employee_id == employee.id]
    return register


_ = CurrentUser, is_staff
