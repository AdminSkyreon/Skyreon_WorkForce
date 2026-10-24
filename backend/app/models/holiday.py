from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Holiday(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "holidays"
    __table_args__ = (
        Index(
            "uq_holiday_company_date",
            "date",
            unique=True,
            postgresql_where=text("location_id IS NULL"),
        ),
        Index(
            "uq_holiday_location_date",
            "location_id",
            "date",
            unique=True,
            postgresql_where=text("location_id IS NOT NULL"),
        ),
    )

    name: Mapped[str] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date, index=True)
    location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    location: Mapped["Location | None"] = relationship()


from app.models.location import Location  # noqa: E402
