import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="taskpriority", values_callable=lambda obj: [e.value for e in obj]),
        default=TaskPriority.MEDIUM,
    )
    estimated_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assignee_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("employees.id"), nullable=True, index=True
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="taskstatus", values_callable=lambda obj: [e.value for e in obj]),
        default=TaskStatus.NOT_STARTED,
    )

    project: Mapped["Project"] = relationship(back_populates="tasks")
    assignee: Mapped["Employee | None"] = relationship()
    time_entries: Mapped[list["TaskTimeEntry"]] = relationship(back_populates="task")


from app.models.employee import Employee  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.time_entry import TaskTimeEntry  # noqa: E402
