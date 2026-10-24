from fastapi import Response

from app.core.config import get_settings

settings = get_settings()

REFRESH_COOKIE = "refresh_token"
ROLE_COOKIE = "swp_role"
MUST_CHANGE_COOKIE = "swp_must_change"
WORKSPACE_COOKIE = "swp_workspace"


def set_auth_cookies(
    response: Response, refresh_token: str, role: str, must_change: bool, has_workspace: bool = False
) -> None:
    cookie_opts: dict[str, object] = {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.cookie_secure,
        "path": "/",
        "max_age": settings.jwt_refresh_ttl_days * 24 * 60 * 60,
    }
    response.set_cookie(REFRESH_COOKIE, refresh_token, **cookie_opts)
    response.set_cookie(ROLE_COOKIE, role, **cookie_opts)
    response.set_cookie(MUST_CHANGE_COOKIE, "1" if must_change else "0", **cookie_opts)
    response.set_cookie(WORKSPACE_COOKIE, "1" if has_workspace else "0", **cookie_opts)


def clear_auth_cookies(response: Response) -> None:
    for name in (REFRESH_COOKIE, ROLE_COOKIE, MUST_CHANGE_COOKIE, WORKSPACE_COOKIE):
        response.delete_cookie(name, path="/")
