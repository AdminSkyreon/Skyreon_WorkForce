from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CompanyProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "company_profile"

    legal_name: Mapped[str] = mapped_column(String(255), default="Skyreon")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(80), default="")
    website: Mapped[str] = mapped_column(String(255), default="https://www.skyreon.com")
    signatory_name: Mapped[str] = mapped_column(String(255), default="")
    signatory_title: Mapped[str] = mapped_column(String(120), default="")
    signature_image: Mapped[str] = mapped_column(Text, default="")
