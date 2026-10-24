from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole
from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str | None = None
    new_password: str = Field(min_length=8)


class TokenUser(ORMModel):
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    must_change_password: bool
    employee_id: UUID | None = None
    name: str | None = None
    is_people_manager: bool = False
    is_project_manager: bool = False


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: TokenUser
