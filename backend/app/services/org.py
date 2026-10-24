from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict
from app.models.org import Department, Designation
from app.schemas.org import NamedCreate, NamedOut


def _out(row: Department | Designation) -> NamedOut:
    return NamedOut(id=row.id, name=row.name, is_active=row.is_active)


async def list_departments(db: AsyncSession, active_only: bool = True) -> list[NamedOut]:
    stmt = select(Department).order_by(Department.name)
    if active_only:
        stmt = stmt.where(Department.is_active.is_(True))
    return [_out(row) for row in (await db.execute(stmt)).scalars().all()]


async def list_designations(db: AsyncSession, active_only: bool = True) -> list[NamedOut]:
    stmt = select(Designation).order_by(Designation.name)
    if active_only:
        stmt = stmt.where(Designation.is_active.is_(True))
    return [_out(row) for row in (await db.execute(stmt)).scalars().all()]


async def create_department(db: AsyncSession, data: NamedCreate) -> NamedOut:
    name = data.name.strip()
    existing = (await db.execute(select(Department).where(Department.name.ilike(name)))).scalar_one_or_none()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            await db.commit()
            await db.refresh(existing)
        return _out(existing)
    row = Department(name=name)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _out(row)


async def create_designation(db: AsyncSession, data: NamedCreate) -> NamedOut:
    name = data.name.strip()
    existing = (await db.execute(select(Designation).where(Designation.name.ilike(name)))).scalar_one_or_none()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            await db.commit()
            await db.refresh(existing)
        return _out(existing)
    row = Designation(name=name)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _out(row)


_ = Conflict
