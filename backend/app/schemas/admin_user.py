from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class AdminCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    temporary_password: str = Field(min_length=8)


class AdminOut(ORMModel):
    id: UUID
    email: EmailStr
    is_active: bool
    name: str | None = None
