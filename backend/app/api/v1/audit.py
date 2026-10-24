from fastapi import APIRouter, Query

from app.core.deps import DbSession, SuperAdminUser
from app.schemas.audit import AuditOut
from app.services import audit as audit_service

router = APIRouter(prefix="/super/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
async def list_audit(
    _user: SuperAdminUser,
    db: DbSession,
    actor: str | None = None,
    entity_type: str | None = None,
    limit: int = Query(200, ge=1, le=500),
) -> list[AuditOut]:
    return await audit_service.list_audit(db, actor=actor, entity_type=entity_type, limit=limit)
