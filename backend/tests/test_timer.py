from datetime import date

import pytest
from httpx import AsyncClient

from app.core.config import get_settings

settings = get_settings()


async def login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_one_running_timer(client: AsyncClient) -> None:
    admin = await login(client, settings.admin_email, settings.admin_password)
    emp = await client.post(
        "/api/v1/admin/employees",
        headers=admin,
        json={
            "name": "Grace Hopper",
            "email": "grace@skyreon.com",
            "employee_code": "EMP-GRACE",
            "designation": "Engineer",
            "department": "Engineering",
            "joining_date": date.today().isoformat(),
            "hourly_cost_rate": "90.00",
            "temporary_password": "TempPass123",
        },
    )
    assert emp.status_code == 201
    employee_id = emp.json()["id"]
    await client.post(
        "/api/v1/auth/login",
        json={"email": "grace@skyreon.com", "password": "TempPass123"},
    )
    emp_headers = await login(client, "grace@skyreon.com", "TempPass123")
    await client.post(
        "/api/v1/auth/change-password",
        headers=emp_headers,
        json={"new_password": "NewPass1234"},
    )
    emp_headers = await login(client, "grace@skyreon.com", "NewPass1234")

    project = await client.post(
        "/api/v1/admin/projects",
        headers=admin,
        json={
            "name": "Portal",
            "client_name": "Skyreon",
            "project_code": "PRJ-1",
            "description": "Internal",
            "manager_id": employee_id,
            "start_date": date.today().isoformat(),
            "status": "active",
            "contract_type": "time_and_material",
            "revenue_amount": "10000",
            "revenue_currency": "USD",
            "budgeted_hours": "100",
            "member_ids": [employee_id],
        },
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    t1 = await client.post(
        f"/api/v1/admin/projects/{project_id}/tasks",
        headers=admin,
        json={
            "title": "Build API",
            "estimated_hours": "4",
            "assignee_id": employee_id,
            "priority": "high",
        },
    )
    t2 = await client.post(
        f"/api/v1/admin/projects/{project_id}/tasks",
        headers=admin,
        json={
            "title": "Build UI",
            "estimated_hours": "4",
            "assignee_id": employee_id,
            "priority": "medium",
        },
    )
    assert t1.status_code == 201
    assert t2.status_code == 201

    start1 = await client.post(
        f"/api/v1/me/tasks/{t1.json()['id']}/timer/start",
        headers=emp_headers,
        json={"pause_current": False},
    )
    assert start1.status_code == 200
    assert start1.json()["running"] is True

    blocked = await client.post(
        f"/api/v1/me/tasks/{t2.json()['id']}/timer/start",
        headers=emp_headers,
        json={"pause_current": False},
    )
    assert blocked.status_code == 409

    switched = await client.post(
        f"/api/v1/me/tasks/{t2.json()['id']}/timer/start",
        headers=emp_headers,
        json={"pause_current": True},
    )
    assert switched.status_code == 200
    assert switched.json()["task_id"] == t2.json()["id"]
