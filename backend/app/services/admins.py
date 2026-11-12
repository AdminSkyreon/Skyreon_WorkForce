from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import Conflict, NotFound
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.admin_user import AdminCreate, AdminOut
from app.services.audit import log_audit
from app.services.auth import revoke_all_user_tokens


def to_out(user: User) -> AdminOut:
    return AdminOut(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        name=user.employee.name if user.employee else None,
    )


async def list_admins(db: AsyncSession) -> list[AdminOut]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.employee))
        .where(User.role == UserRole.ADMIN)
        .order_by(User.email)
    )
    return [to_out(user) for user in result.scalars().all()]


async def create_admin(db: AsyncSession, actor: User, data: AdminCreate) -> AdminOut:
    existing = await db.execute(select(User).where(User.email == data.email.lower()))
    if existing.scalar_one_or_none():
        raise Conflict("Email already in use")
    user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.temporary_password),
        role=UserRole.ADMIN,
        is_active=True,
        must_change_password=True,
    )
    db.add(user)
    await db.flush()
    await log_audit(db, actor, "created", "admin", user.id, summary=f"Created admin {user.email}")
    await db.commit()
    loaded = (
        await db.execute(select(User).options(selectinload(User.employee)).where(User.id == user.id))
    ).scalar_one()
    return to_out(loaded)


async def deactivate_admin(db: AsyncSession, actor: User, admin_id) -> AdminOut:
    user = (
        await db.execute(select(User).options(selectinload(User.employee)).where(User.id == admin_id))
    ).scalar_one_or_none()
    if user is None or user.role != UserRole.ADMIN:
        raise NotFound("Admin not found")
    user.is_active = False
    await revoke_all_user_tokens(db, user.id)
    await log_audit(db, actor, "updated", "admin", user.id, summary=f"Deactivated admin {user.email}")
    await db.commit()
    return to_out(user)
