from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Forbidden, NotFound
from app.models.notification import Notification
from app.models.user import User, UserRole


async def notify(
    db: AsyncSession,
    user_id: UUID,
    ntype: str,
    title: str,
    body: str,
    link: str | None = None,
) -> Notification:
    item = Notification(user_id=user_id, type=ntype, title=title, body=body, link=link)
    db.add(item)
    await db.flush()
    return item


async def notify_admins(
    db: AsyncSession, ntype: str, title: str, body: str, link: str | None = None
) -> None:
    result = await db.execute(
        select(User).where(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]), User.is_active.is_(True))
    )
    for admin in result.scalars().all():
        await notify(db, admin.id, ntype, title, body, link)


async def notify_user_if(
    db: AsyncSession, user_id: UUID | None, ntype: str, title: str, body: str, link: str | None = None
) -> None:
    if user_id:
        await notify(db, user_id, ntype, title, body, link)


async def list_notifications(db: AsyncSession, user_id: UUID) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


async def mark_read(db: AsyncSession, user_id: UUID, notification_id: UUID) -> Notification:
    item = await db.get(Notification, notification_id)
    if item is None:
        raise NotFound("Notification not found")
    if item.user_id != user_id:
        raise Forbidden("You can only update your own notifications")
    item.is_read = True
    await db.commit()
    await db.refresh(item)
    return item


async def unread_count(db: AsyncSession, user_id: UUID) -> int:
    result = await db.execute(
        select(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))
    )
    return len(list(result.scalars().all()))
