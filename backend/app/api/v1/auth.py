from fastapi import APIRouter, Cookie, Response

from app.core.cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from app.core.deps import CurrentUser, DbSession
from app.core.exceptions import Unauthorized
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, TokenUser
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, response: Response, db: DbSession) -> LoginResponse:
    user = await auth_service.authenticate(db, payload.email, payload.password)
    access, refresh = await auth_service.issue_tokens(db, user)
    token_user = await auth_service.to_token_user(db, user)
    set_auth_cookies(response, refresh, user.role.value, user.must_change_password, token_user.employee_id is not None)
    return LoginResponse(access_token=access, user=token_user)


@router.post("/refresh", response_model=LoginResponse)
async def refresh(
    response: Response,
    db: DbSession,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
) -> LoginResponse:
    if not refresh_token:
        raise Unauthorized("Missing refresh token")
    access, new_refresh, user = await auth_service.rotate_refresh(db, refresh_token)
    token_user = await auth_service.to_token_user(db, user)
    set_auth_cookies(
        response, new_refresh, user.role.value, user.must_change_password, token_user.employee_id is not None
    )
    return LoginResponse(access_token=access, user=token_user)


@router.post("/logout")
async def logout(
    response: Response,
    db: DbSession,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
) -> dict[str, str]:
    await auth_service.revoke_refresh(db, refresh_token)
    clear_auth_cookies(response)
    return {"status": "ok"}


@router.get("/me", response_model=TokenUser)
async def me(user: CurrentUser, db: DbSession) -> TokenUser:
    return await auth_service.to_token_user(db, user)


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    await auth_service.change_password(db, user, payload.new_password, payload.current_password)
    return {"status": "ok"}
