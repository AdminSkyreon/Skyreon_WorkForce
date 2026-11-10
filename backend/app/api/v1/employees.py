from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import AdminUser, DbSession, HrAdminUser
from app.models.employee import EmployeeStatus
from app.schemas.common import Page
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeeUpdate, ResetPasswordRequest
from app.services import employees as employee_service

router = APIRouter(prefix="/admin/employees", tags=["employees"])


@router.get("", response_model=Page[EmployeeOut])
async def list_employees(
    _admin: AdminUser,
    db: DbSession,
    search: str | None = None,
    status: EmployeeStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[EmployeeOut]:
    items, total = await employee_service.list_employees(
        db, search=search, status=status, page=page, page_size=page_size
    )
    return Page(
        items=[employee_service.to_employee_out(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=EmployeeOut, status_code=201)
async def create_employee(
    payload: EmployeeCreate, _admin: HrAdminUser, db: DbSession
) -> EmployeeOut:
    employee = await employee_service.create_employee(db, payload)
    return employee_service.to_employee_out(employee)


@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(employee_id: UUID, _admin: AdminUser, db: DbSession) -> EmployeeOut:
    employee = await employee_service.get_employee(db, employee_id)
    return employee_service.to_employee_out(employee)


@router.patch("/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: UUID, payload: EmployeeUpdate, _admin: HrAdminUser, db: DbSession
) -> EmployeeOut:
    employee = await employee_service.update_employee(db, employee_id, payload)
    return employee_service.to_employee_out(employee)


@router.post("/{employee_id}/deactivate", response_model=EmployeeOut)
async def deactivate_employee(
    employee_id: UUID, _admin: HrAdminUser, db: DbSession
) -> EmployeeOut:
    employee = await employee_service.deactivate_employee(db, employee_id)
    return employee_service.to_employee_out(employee)

@router.post("/{employee_id}/activate", response_model=EmployeeOut)
async def activate_employee(
    employee_id: UUID, _admin: HrAdminUser, db: DbSession
) -> EmployeeOut:
    employee = await employee_service.activate_employee(db, employee_id)
    return employee_service.to_employee_out(employee)


@router.post("/{employee_id}/reset-password", response_model=EmployeeOut)
async def reset_password(
    employee_id: UUID, payload: ResetPasswordRequest, _admin: HrAdminUser, db: DbSession
) -> EmployeeOut:
    employee = await employee_service.reset_password(db, employee_id, payload.temporary_password)
    return employee_service.to_employee_out(employee)


