from datetime import date as Date
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class HolidayCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    date: Date
    location_id: UUID | None = None


class HolidayUpdate(BaseModel):
    name: str | None = None
    date: Date | None = None
    location_id: UUID | None = None


class HolidayOut(ORMModel):
    id: UUID
    name: str
    date: Date
    location_id: UUID | None = None
    location_name: str | None = None
