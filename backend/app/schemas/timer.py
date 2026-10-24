from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class TimerStartRequest(BaseModel):
    pause_current: bool = False


class TimerStopRequest(BaseModel):
    note: str = ""


class RunningTimer(ORMModel):
    running: bool
    task_id: UUID | None = None
    task_title: str | None = None
    project_name: str | None = None
    entry_id: UUID | None = None
    started_at: datetime | None = None
    remaining_seconds: int = 0
    estimated_seconds: int = 0
    logged_seconds: int = 0
    server_time: datetime
    is_overtime: bool = False
