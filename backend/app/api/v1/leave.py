from uuid import UUID

from fastapi import APIRouter

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.models.leave import LeaveStatus
from app.schemas.leave import (
    AdminLeaveCreate,
    LeaveRequestOut,
    LeaveReviewRequest,
    LeaveTypeCreate,
    LeaveTypeOut,
    LeaveTypeUpdate,
)
from app.services import leave as leave_service
from app.services import notifications as notification_service

router = APIRouter(tags=["leave"])


@router.get("/leave-types", response_model=list[LeaveTypeOut])
async def list_leave_types(_user: CurrentUser, db: DbSession) -> list[LeaveTypeOut]:
    return await leave_service.list_leave_types(db)


@router.post("/admin/leave-types", response_model=LeaveTypeOut, status_code=201)
async def create_leave_type(
    payload: LeaveTypeCreate, _admin: AdminUser, db: DbSession
) -> LeaveTypeOut:
    return await leave_service.create_leave_type(db, payload)


@router.patch("/admin/leave-types/{type_id}", response_model=LeaveTypeOut)
async def update_leave_type(
    type_id: UUID, payload: LeaveTypeUpdate, _admin: AdminUser, db: DbSession
) -> LeaveTypeOut:
    return await leave_service.update_leave_type(db, type_id, payload)


@router.get("/leave", response_model=list[LeaveRequestOut])
async def list_leave(user: CurrentUser, db: DbSession) -> list[LeaveRequestOut]:
    return await leave_service.list_manageable_leave(db, user)


@router.post("/admin/leave", response_model=LeaveRequestOut, status_code=201)
async def admin_add_leave(
    payload: AdminLeaveCreate, user: AdminUser, db: DbSession
) -> LeaveRequestOut:
    result = await leave_service.admin_add_leave(db, user, payload)
    user_id = await _user_id_for_employee(db, result.employee_id)
    await notification_service.notify(
        db,
        user_id,
        "leave_added",
        "Leave added",
        f"Leave from {result.start_date} was added by admin.",
        "/employee/leave",
    )
    await db.commit()
    return result


@router.post("/leave/{request_id}/approve", response_model=LeaveRequestOut)
async def approve_leave(
    request_id: UUID, payload: LeaveReviewRequest, user: CurrentUser, db: DbSession
) -> LeaveRequestOut:
    result = await leave_service.review_leave(
        db, user, request_id, LeaveStatus.APPROVED, payload.comment
    )
    user_id = await _user_id_for_employee(db, result.employee_id)
    await notification_service.notify(
        db,
        user_id,
        "leave_approved",
        "Leave approved",
        f"Your leave from {result.start_date} was approved.",
        "/employee/leave",
    )
    await db.commit()
    return result


@router.post("/leave/{request_id}/reject", response_model=LeaveRequestOut)
async def reject_leave(
    request_id: UUID, payload: LeaveReviewRequest, user: CurrentUser, db: DbSession
) -> LeaveRequestOut:
    result = await leave_service.review_leave(
        db, user, request_id, LeaveStatus.REJECTED, payload.comment
    )
    user_id = await _user_id_for_employee(db, result.employee_id)
    await notification_service.notify(
        db,
        user_id,
        "leave_rejected",
        "Leave rejected",
        f"Your leave from {result.start_date} was rejected.",
        "/employee/leave",
    )
    await db.commit()
    return result


async def _user_id_for_employee(db: DbSession, employee_id: UUID):
    from app.services.employees import get_employee

    employee = await get_employee(db, employee_id)
    return employee.user_id
