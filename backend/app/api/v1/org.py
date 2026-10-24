from fastapi import APIRouter

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.schemas.org import NamedCreate, NamedOut
from app.services import org as org_service

router = APIRouter(tags=["org"])


@router.get("/departments", response_model=list[NamedOut])
async def list_departments(_user: CurrentUser, db: DbSession) -> list[NamedOut]:
    return await org_service.list_departments(db)


@router.post("/departments", response_model=NamedOut, status_code=201)
async def create_department(payload: NamedCreate, _admin: AdminUser, db: DbSession) -> NamedOut:
    return await org_service.create_department(db, payload)


@router.get("/designations", response_model=list[NamedOut])
async def list_designations(_user: CurrentUser, db: DbSession) -> list[NamedOut]:
    return await org_service.list_designations(db)


@router.post("/designations", response_model=NamedOut, status_code=201)
async def create_designation(payload: NamedCreate, _admin: AdminUser, db: DbSession) -> NamedOut:
    return await org_service.create_designation(db, payload)
