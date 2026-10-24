from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.database import Base, create_db_engine, get_db
from app.main import app
from app.models import *  # noqa: F403
from app.services.seed import run_seed

settings = get_settings()


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    engine = create_db_engine(settings.resolved_database_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "TRUNCATE TABLE audit_logs, company_profile, payroll_adjustments, payroll_periods, project_billings, "
                "project_invoices, "
                "project_payments, salary_payments, contractor_payments, vendor_bills, jobs, applicants, "
                "document_requirements, employee_documents, attendance_days, review_cycles, performance_reviews, "
                "company_assets, departments, designations, "
                "reimbursements, notifications, leave_requests, leave_types, holidays, "
                "timesheet_weeks, task_time_entries, tasks, project_members, projects, "
                "employee_payroll, refresh_tokens, employees, locations, users RESTART IDENTITY CASCADE"
            )
        )
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await run_seed(session)
        yield session
    await engine.dispose()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_db() -> AsyncIterator[AsyncSession]:
        yield db

    app.dependency_overrides[get_db] = override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
