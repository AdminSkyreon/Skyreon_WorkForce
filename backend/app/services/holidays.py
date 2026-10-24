from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import Conflict, NotFound
from app.models.holiday import Holiday
from app.schemas.holiday import HolidayCreate, HolidayOut, HolidayUpdate


def to_holiday_out(holiday: Holiday) -> HolidayOut:
    return HolidayOut(
        id=holiday.id,
        name=holiday.name,
        date=holiday.date,
        location_id=holiday.location_id,
        location_name=holiday.location.name if holiday.location else None,
    )


async def list_holidays(
    db: AsyncSession, year: int | None = None, location_id: UUID | None = None
) -> list[HolidayOut]:
    stmt = select(Holiday).options(selectinload(Holiday.location)).order_by(Holiday.date)
    if year:
        stmt = stmt.where(Holiday.date >= date(year, 1, 1), Holiday.date <= date(year, 12, 31))
    if location_id:
        stmt = stmt.where(or_(Holiday.location_id == location_id, Holiday.location_id.is_(None)))
    return [to_holiday_out(item) for item in (await db.execute(stmt)).scalars().all()]


async def holiday_dates(
    db: AsyncSession, start: date, end: date, location_id: UUID | None = None
) -> set[date]:
    stmt = select(Holiday.date).where(Holiday.date >= start, Holiday.date <= end)
    if location_id:
        stmt = stmt.where(or_(Holiday.location_id == location_id, Holiday.location_id.is_(None)))
    else:
        stmt = stmt.where(Holiday.location_id.is_(None))
    return set((await db.execute(stmt)).scalars().all())


async def create_holiday(db: AsyncSession, data: HolidayCreate) -> HolidayOut:
    holiday = Holiday(name=data.name, date=data.date, location_id=data.location_id)
    db.add(holiday)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise Conflict("A holiday already exists on this date for this location") from exc
    loaded = (
        await db.execute(select(Holiday).options(selectinload(Holiday.location)).where(Holiday.id == holiday.id))
    ).scalar_one()
    return to_holiday_out(loaded)


async def update_holiday(db: AsyncSession, holiday_id: UUID, data: HolidayUpdate) -> HolidayOut:
    holiday = await db.get(Holiday, holiday_id)
    if holiday is None:
        raise NotFound("Holiday not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(holiday, key, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise Conflict("A holiday already exists on this date for this location") from exc
    loaded = (
        await db.execute(select(Holiday).options(selectinload(Holiday.location)).where(Holiday.id == holiday_id))
    ).scalar_one()
    return to_holiday_out(loaded)


async def delete_holiday(db: AsyncSession, holiday_id: UUID) -> None:
    holiday = await db.get(Holiday, holiday_id)
    if holiday is None:
        raise NotFound("Holiday not found")
    await db.delete(holiday)
    await db.commit()
