from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class AuditOut(ORMModel):
    id: UUID
    actor_id: UUID | None
    actor_email: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str
    summary: str
    before_json: str
    after_json: str
    created_at: datetime
