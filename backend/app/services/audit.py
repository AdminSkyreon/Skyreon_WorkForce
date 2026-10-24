import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User


def _dump(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


async def log_audit(
    db: AsyncSession,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: UUID | str | None = None,
    *,
    summary: str = "",
    before: Any = None,
    after: Any = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=user.id if user else None,
            actor_email=user.email if user else "",
            actor_role=user.role.value if user else "",
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else "",
            summary=summary,
            before_json=_dump(before),
            after_json=_dump(after),
        )
    )
    await db.flush()


async def list_audit(
    db: AsyncSession,
    *,
    actor: str | None = None,
    entity_type: str | None = None,
    limit: int = 200,
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if actor:
        stmt = stmt.where(AuditLog.actor_email.ilike(f"%{actor}%"))
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    return list((await db.execute(stmt)).scalars().all())
