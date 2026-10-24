import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ProjectStatus(str, enum.Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"


class ContractType(str, enum.Enum):
    FIXED = "fixed"
    TIME_AND_MATERIAL = "time_and_material"


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255))
    client_name: Mapped[str] = mapped_column(String(255))
    project_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    manager_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="projectstatus", values_callable=lambda obj: [e.value for e in obj]),
        default=ProjectStatus.PLANNED,
    )
    contract_type: Mapped[ContractType] = mapped_column(
        Enum(ContractType, name="contracttype", values_callable=lambda obj: [e.value for e in obj]),
        default=ContractType.TIME_AND_MATERIAL,
    )
    revenue_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    revenue_currency: Mapped[str] = mapped_column(String(8), default="USD")
    budgeted_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    manager: Mapped["Employee"] = relationship(foreign_keys=[manager_id])
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")


class ProjectMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "employee_id", name="uq_project_member"),)

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)

    project: Mapped[Project] = relationship(back_populates="members")
    employee: Mapped["Employee"] = relationship()


from app.models.employee import Employee  # noqa: E402
from app.models.task import Task  # noqa: E402
