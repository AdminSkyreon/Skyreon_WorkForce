from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class NamedCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class NamedOut(ORMModel):
    id: UUID
    name: str
    is_active: bool
