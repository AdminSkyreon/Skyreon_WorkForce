from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.models.task import TaskPriority, TaskStatus
from app.schemas.common import ORMModel

Title255 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class TaskCreate(BaseModel):
    title: Title255
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_hours: Decimal = Field(default=Decimal("0.00"), ge=0)
    due_date: date | None = None
    assignee_id: UUID | None = None
    status: TaskStatus = TaskStatus.NOT_STARTED


class TaskUpdate(BaseModel):
    title: Title255 | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    estimated_hours: Decimal | None = Field(default=None, ge=0)
    due_date: date | None = None
    assignee_id: UUID | None = None
    status: TaskStatus | None = None

    @model_validator(mode="after")
    def reject_nulls(self) -> "TaskUpdate":
        for field in ("title", "description", "priority", "estimated_hours", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


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
