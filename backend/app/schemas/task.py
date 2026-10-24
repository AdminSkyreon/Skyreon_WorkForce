from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.task import TaskPriority, TaskStatus
from app.schemas.common import ORMModel


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_hours: Decimal = Decimal("0.00")
    due_date: date | None = None
    assignee_id: UUID | None = None
    status: TaskStatus = TaskStatus.NOT_STARTED


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    estimated_hours: Decimal | None = None
    due_date: date | None = None
    assignee_id: UUID | None = None
    status: TaskStatus | None = None


class TaskOut(ORMModel):
    id: UUID
    project_id: UUID
    project_name: str | None = None
    title: str
    description: str
    priority: TaskPriority
    estimated_hours: Decimal
    due_date: date | None
    assignee_id: UUID | None
    assignee_name: str | None = None
    status: TaskStatus
    logged_seconds: int = 0
    remaining_seconds: int = 0
