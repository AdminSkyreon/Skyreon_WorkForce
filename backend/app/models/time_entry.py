import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TimeEntrySource(str, enum.Enum):
    TIMER = "timer"
    MANUAL = "manual"


class TaskTimeEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "task_time_entries"
    __table_args__ = (
        Index(
            "uq_time_entries_one_running",
            "employee_id",
            unique=True,
            postgresql_where=text("end_time IS NULL"),
        ),
    )

    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[TimeEntrySource] = mapped_column(
        Enum(TimeEntrySource, name="timeentrysource", values_callable=lambda obj: [e.value for e in obj]),
        default=TimeEntrySource.TIMER,
    )
    manual_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    task: Mapped["Task"] = relationship(back_populates="time_entries")
    employee: Mapped["Employee"] = relationship()


from app.models.employee import Employee  # noqa: E402
from app.models.task import Task  # noqa: E402
