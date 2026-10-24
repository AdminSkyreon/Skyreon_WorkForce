from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import Forbidden, Unauthorized
from app.core.security import decode_access_token
from app.models.employee import Employee
from app.models.user import User, UserRole, is_hr_admin, is_staff, is_super_admin

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    request: Request,
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None:
        raise Unauthorized()
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise Unauthorized("Invalid or expired token") from exc

    result = await db.execute(
        select(User).options(selectinload(User.employee)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise Unauthorized("User is inactive or missing")

    path = request.url.path
    allowed_while_forced = (
        path.endswith("/auth/change-password")
        or path.endswith("/auth/me")
        or path.endswith("/auth/logout")
    )
    if user.must_change_password and not allowed_while_forced:
        raise Forbidden("Password change required")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if not is_staff(user):
        raise Forbidden("Admin access required")
    return user


async def require_hr_admin(user: CurrentUser) -> User:
    if not is_hr_admin(user):
        raise Forbidden("Only an admin can manage employee accounts")
    return user


async def require_super_admin(user: CurrentUser) -> User:
    if not is_super_admin(user):
        raise Forbidden("Super admin access required")
    return user


async def require_employee(user: CurrentUser) -> User:
    if user.role == UserRole.EMPLOYEE or user.employee is not None:
        return user
    raise Forbidden("Employee workspace required")


AdminUser = Annotated[User, Depends(require_admin)]
HrAdminUser = Annotated[User, Depends(require_hr_admin)]
SuperAdminUser = Annotated[User, Depends(require_super_admin)]
EmployeeUser = Annotated[User, Depends(require_employee)]


async def get_current_employee(user: EmployeeUser, db: DbSession) -> Employee:
    if user.employee is None:
        result = await db.execute(select(Employee).where(Employee.user_id == user.id))
        employee = result.scalar_one_or_none()
    else:
        employee = user.employee
    if employee is None:
        raise Forbidden("Employee profile not found")
    return employee


CurrentEmployee = Annotated[Employee, Depends(get_current_employee)]
