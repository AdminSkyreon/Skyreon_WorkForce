from datetime import date

import pytest
from httpx import AsyncClient

from app.core.config import get_settings

settings = get_settings()


async def admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_employee_cannot_list_employees(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    created = await client.post(
        "/api/v1/admin/employees",
        headers=headers,
        json={
            "name": "Ada Lovelace",
            "email": "ada@skyreon.com",
            "employee_code": "EMP-ADA",
            "designation": "Engineer",
            "department": "Engineering",
            "joining_date": date.today().isoformat(),
            "hourly_cost_rate": "80.00",
            "temporary_password": "TempPass123",
        },
    )
    assert created.status_code == 201

    emp_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "ada@skyreon.com", "password": "TempPass123"},
    )
    assert emp_login.status_code == 200
    emp_token = emp_login.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    blocked = await client.get("/api/v1/admin/employees", headers=emp_headers)
    assert blocked.status_code == 403

    change = await client.post(
        "/api/v1/auth/change-password",
        headers=emp_headers,
        json={"new_password": "NewPass1234"},
    )
    assert change.status_code == 200

    me = await client.get("/api/v1/auth/me", headers=emp_headers)
    assert me.status_code == 200
    assert me.json()["role"] == "employee"
