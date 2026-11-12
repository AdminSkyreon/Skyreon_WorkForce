from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequest, Unauthorized
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    refresh_expiry,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.schemas.auth import TokenUser
from app.services.hats import user_hats


async def to_token_user(db: AsyncSession, user: User) -> TokenUser:
    employee = user.employee
    people, project = await user_hats(db, user)
    return TokenUser(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        employee_id=employee.id if employee else None,
        name=employee.name if employee else None,
        is_people_manager=people,
        is_project_manager=project,
    )


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    result = await db.execute(
        select(User).options(selectinload(User.employee)).where(User.email == email.lower())
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise Unauthorized("Invalid email or password")
    return user


async def issue_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    raw = new_refresh_token()
    token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=refresh_expiry(),
    )
    db.add(token)
    await db.commit()
    access = create_access_token(user_id=user.id, role=user.role.value)
    return access, raw


async def revoke_all_user_tokens(db: AsyncSession, user_id: UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def rotate_refresh(db: AsyncSession, raw_token: str) -> tuple[str, str, User]:
    token_digest = hash_token(raw_token)
    result = await db.execute(
        select(RefreshToken)
        .options(selectinload(RefreshToken.user).selectinload(User.employee))
        .where(RefreshToken.token_hash == token_digest)
        .with_for_update()
    )
    matched = result.scalar_one_or_none()
    if matched is None:
        raise Unauthorized("Invalid refresh token")
    if matched.revoked_at is not None:
        # Refresh token reuse detected: revoke all active sessions for this user
        await revoke_all_user_tokens(db, matched.user_id)
        await db.commit()
        raise Unauthorized("Invalid refresh token")
    now = datetime.now(UTC)
    if matched.expires_at < now:
        matched.revoked_at = now
        await db.commit()
        raise Unauthorized("Refresh token expired")

    matched.revoked_at = now
    new_raw = new_refresh_token()
    replacement = RefreshToken(
        user_id=matched.user_id,
        token_hash=hash_token(new_raw),
        expires_at=refresh_expiry(),
    )
    db.add(replacement)
    await db.flush()
    matched.replaced_by_id = replacement.id
    await db.commit()
    user = matched.user
    if not user.is_active:
        raise Unauthorized("User is inactive")
    access = create_access_token(user_id=user.id, role=user.role.value)
    return access, new_raw, user


async def revoke_refresh(db: AsyncSession, raw_token: str | None) -> None:
    if not raw_token:
        return
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(raw_token),
            RefreshToken.revoked_at.is_(None),
        )
    )
    token = result.scalar_one_or_none()
    if token:
        token.revoked_at = datetime.now(UTC)
        await db.commit()



async def change_password(
    db: AsyncSession, user: User, new_password: str, current_password: str | None
) -> None:
    if not user.must_change_password:
        if not current_password or not verify_password(current_password, user.password_hash):
            raise BadRequest("Current password is incorrect")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await revoke_all_user_tokens(db, user.id)
    await db.commit()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(
        select(User).options(selectinload(User.employee)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()
