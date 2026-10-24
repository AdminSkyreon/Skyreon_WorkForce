import pytest
from httpx import AsyncClient

from app.core.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_admin_login_and_refresh(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["user"]["role"] == "admin"
    assert body["access_token"]
    assert client.cookies.get("refresh_token")

    refresh = await client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200
    assert refresh.json()["access_token"] != body["access_token"]

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    again = await client.post("/api/v1/auth/refresh")
    assert again.status_code == 401


@pytest.mark.asyncio
async def test_invalid_login(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@skyreon.com", "password": "wrong-pass"},
    )
    assert response.status_code == 401
