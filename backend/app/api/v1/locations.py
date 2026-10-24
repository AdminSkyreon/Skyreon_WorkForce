from uuid import UUID

from fastapi import APIRouter

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.schemas.location import LocationCreate, LocationOut, LocationUpdate
from app.services import locations as location_service

router = APIRouter(prefix="/admin/locations", tags=["locations"])
public_router = APIRouter(prefix="/locations", tags=["locations"])


@public_router.get("", response_model=list[LocationOut])
async def list_locations(_user: CurrentUser, db: DbSession) -> list[LocationOut]:
    return await location_service.list_locations(db, active_only=True)


@router.get("", response_model=list[LocationOut])
async def admin_list_locations(_admin: AdminUser, db: DbSession) -> list[LocationOut]:
    return await location_service.list_locations(db)


@router.post("", response_model=LocationOut, status_code=201)
async def create_location(payload: LocationCreate, _admin: AdminUser, db: DbSession) -> LocationOut:
    return await location_service.create_location(db, payload)


@router.patch("/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: UUID, payload: LocationUpdate, _admin: AdminUser, db: DbSession
) -> LocationOut:
    return await location_service.update_location(db, location_id, payload)


@router.delete("/{location_id}", status_code=204)
async def delete_location(location_id: UUID, _admin: AdminUser, db: DbSession) -> None:
    await location_service.delete_location(db, location_id)
