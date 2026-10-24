from uuid import UUID

from fastapi import APIRouter

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.schemas.holiday import HolidayCreate, HolidayOut, HolidayUpdate
from app.services import holidays as holiday_service

public_router = APIRouter(prefix="/holidays", tags=["holidays"])
admin_router = APIRouter(prefix="/admin/holidays", tags=["holidays"])


@public_router.get("", response_model=list[HolidayOut])
async def list_holidays(
    _user: CurrentUser,
    db: DbSession,
    year: int | None = None,
    location_id: UUID | None = None,
) -> list[HolidayOut]:
    return await holiday_service.list_holidays(db, year, location_id)


@admin_router.post("", response_model=HolidayOut, status_code=201)
async def create_holiday(
    payload: HolidayCreate, _admin: AdminUser, db: DbSession
) -> HolidayOut:
    return await holiday_service.create_holiday(db, payload)


@admin_router.patch("/{holiday_id}", response_model=HolidayOut)
async def update_holiday(
    holiday_id: UUID, payload: HolidayUpdate, _admin: AdminUser, db: DbSession
) -> HolidayOut:
    return await holiday_service.update_holiday(db, holiday_id, payload)


@admin_router.delete("/{holiday_id}", status_code=204)
async def delete_holiday(holiday_id: UUID, _admin: AdminUser, db: DbSession) -> None:
    await holiday_service.delete_holiday(db, holiday_id)
