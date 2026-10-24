import asyncio
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.time_entry import TaskTimeEntry, TimeEntrySource

settings = get_settings()


async def login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_timer_stops_at_estimate(client: AsyncClient, db: AsyncSession) -> None:
    admin = await login(client, settings.admin_email, settings.admin_password)
    emp = await client.post(
        "/api/v1/admin/employees",
        headers=admin,
        json={
            "name": "Timer Cap",
            "email": "timercap@skyreon.com",
            "employee_code": "EMP-TIMERCAP",
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
        json={"email": "timercap@skyreon.com", "password": "TempPass123"},
    )
    emp_headers = await login(client, "timercap@skyreon.com", "TempPass123")
    await client.post(
        "/api/v1/auth/change-password",
        headers=emp_headers,
        json={"new_password": "NewPass1234"},
    )
    emp_headers = await login(client, "timercap@skyreon.com", "NewPass1234")

    project = await client.post(
        "/api/v1/admin/projects",
        headers=admin,
        json={
            "name": "Cap Project",
            "client_name": "Skyreon",
            "project_code": "PRJ-CAP",
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

    task = await client.post(
        f"/api/v1/admin/projects/{project_id}/tasks",
        headers=admin,
        json={
            "title": "Eight hour task",
            "estimated_hours": "8",
            "assignee_id": employee_id,
            "priority": "high",
        },
    )
    assert task.status_code == 201
    task_id = task.json()["id"]

    cap_seconds = 8 * 3600
    db.add(
        TaskTimeEntry(
            task_id=task_id,
            employee_id=employee_id,
            start_time=datetime.now(UTC) - timedelta(hours=1),
            end_time=datetime.now(UTC) - timedelta(hours=1),
            duration_seconds=cap_seconds - 3,
            source=TimeEntrySource.TIMER,
        )
    )
    await db.commit()

    start = await client.post(
        f"/api/v1/me/tasks/{task_id}/timer/start",
        headers=emp_headers,
        json={"pause_current": False},
    )
    assert start.status_code == 200
    assert start.json()["remaining_seconds"] == 3

    await asyncio.sleep(4)

    pause = await client.post(
        f"/api/v1/me/tasks/{task_id}/timer/pause",
        headers=emp_headers,
    )
    assert pause.status_code == 200
    assert pause.json()["running"] is False

    result = await db.execute(
        select(TaskTimeEntry).where(
            TaskTimeEntry.task_id == task_id,
            TaskTimeEntry.employee_id == employee_id,
        )
    )
    total = sum(e.duration_seconds for e in result.scalars().all())
    assert total == cap_seconds

    blocked = await client.post(
        f"/api/v1/me/tasks/{task_id}/timer/start",
        headers=emp_headers,
        json={"pause_current": False},
    )
    assert blocked.status_code == 400
