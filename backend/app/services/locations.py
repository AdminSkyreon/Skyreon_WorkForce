from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequest, Conflict, NotFound
from app.models.employee import Employee
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate


async def list_locations(db: AsyncSession, active_only: bool = False) -> list[Location]:
    stmt = select(Location).order_by(Location.name)
    if active_only:
        stmt = stmt.where(Location.is_active.is_(True))
    return list((await db.execute(stmt)).scalars().all())


async def get_location(db: AsyncSession, location_id: UUID) -> Location:
    location = await db.get(Location, location_id)
    if location is None:
        raise NotFound("Location not found")
    return location


def _code_from_name(name: str) -> str:
    letters = "".join(ch for ch in name.upper() if ch.isalnum())
    return (letters[:6] or "LOC")


async def create_location(db: AsyncSession, data: LocationCreate) -> Location:
    code = (data.code or "").strip().upper() or _code_from_name(data.name)
    existing = await db.execute(select(Location).where(Location.code == code))
    if existing.scalar_one_or_none():
        suffix = 2
        while True:
            candidate = f"{code[:4]}{suffix}"
            taken = await db.execute(select(Location).where(Location.code == candidate))
            if taken.scalar_one_or_none() is None:
                code = candidate
                break
            suffix += 1
    location = Location(
        name=data.name.strip(),
        code=code,
        city=data.city.strip(),
        country=data.country.strip(),
        is_active=data.is_active,
    )
    db.add(location)
    await db.commit()
    await db.refresh(location)
    return location


async def update_location(db: AsyncSession, location_id: UUID, data: LocationUpdate) -> Location:
    location = await get_location(db, location_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(location, key, value.strip() if isinstance(value, str) else value)
    await db.commit()
    await db.refresh(location)
    return location


async def delete_location(db: AsyncSession, location_id: UUID) -> None:
    location = await get_location(db, location_id)
    in_use = await db.execute(select(Employee.id).where(Employee.location_id == location_id).limit(1))
    if in_use.scalar_one_or_none():
        raise BadRequest("Location is assigned to employees. Deactivate it instead.")
    await db.delete(location)
    await db.commit()
