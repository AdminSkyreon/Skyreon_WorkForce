from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentEmployee, CurrentUser, DbSession
from app.models.extra_work import ExtraWorkStatus
from app.schemas.extra_work import ExtraWorkApprove, ExtraWorkDefaults, ExtraWorkOut, ExtraWorkReject
from app.services import extra_work as extra_work_service

router = APIRouter(tags=["extra-work"])


@router.get("/me/extra-work", response_model=list[ExtraWorkOut])
async def my_extra_work(employee: CurrentEmployee, db: DbSession) -> list[ExtraWorkOut]:
    return await extra_work_service.list_mine(db, employee.id)


@router.get("/extra-work", response_model=list[ExtraWorkOut])
async def list_extra_work(
    user: CurrentUser,
    db: DbSession,
    status: ExtraWorkStatus | None = Query(default=None),
) -> list[ExtraWorkOut]:
    return await extra_work_service.list_queue(db, user, status)


@router.get("/extra-work/{row_id}/defaults", response_model=ExtraWorkDefaults)
async def extra_work_defaults(row_id: UUID, user: CurrentUser, db: DbSession) -> ExtraWorkDefaults:
    return await extra_work_service.defaults_for(db, user, row_id)


@router.post("/extra-work/{row_id}/approve", response_model=ExtraWorkOut)
async def approve_extra_work(
    row_id: UUID, payload: ExtraWorkApprove, user: CurrentUser, db: DbSession
) -> ExtraWorkOut:
    return await extra_work_service.approve(db, user, row_id, payload)


@router.post("/extra-work/{row_id}/reject", response_model=ExtraWorkOut)
async def reject_extra_work(
    row_id: UUID, payload: ExtraWorkReject, user: CurrentUser, db: DbSession
) -> ExtraWorkOut:
    return await extra_work_service.reject(db, user, row_id, payload.comment)
