from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class NotificationOut(ORMModel):
    id: UUID
    type: str
    title: str
    body: str
    is_read: bool
    link: str | None
    created_at: datetime
