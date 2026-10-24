from uuid import UUID

from fastapi import APIRouter

from app.core.deps import DbSession, SuperAdminUser
from app.schemas.admin_user import AdminCreate, AdminOut
from app.services import admins as admin_service

router = APIRouter(prefix="/super/admins", tags=["admins"])


@router.get("", response_model=list[AdminOut])
async def list_admins(_user: SuperAdminUser, db: DbSession) -> list[AdminOut]:
    return await admin_service.list_admins(db)


@router.post("", response_model=AdminOut, status_code=201)
async def create_admin(payload: AdminCreate, user: SuperAdminUser, db: DbSession) -> AdminOut:
    return await admin_service.create_admin(db, user, payload)


@router.post("/{admin_id}/deactivate", response_model=AdminOut)
async def deactivate_admin(admin_id: UUID, user: SuperAdminUser, db: DbSession) -> AdminOut:
    return await admin_service.deactivate_admin(db, user, admin_id)
