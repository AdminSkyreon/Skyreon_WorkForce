from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=20)
    city: str = ""
    country: str = ""
    is_active: bool = True


class LocationUpdate(BaseModel):
    name: str | None = None
    city: str | None = None
    country: str | None = None
    is_active: bool | None = None


class LocationOut(ORMModel):
    id: UUID
    name: str
    code: str
    city: str
    country: str
    is_active: bool
