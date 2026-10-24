from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AdminDashboard(BaseModel):
    active_employees: int
    active_projects: int
    pending_timesheets: int
    pending_leaves: int
    hours_this_week: Decimal
    cost_this_week: Decimal
    revenue_active_projects: Decimal
    project_financials: list[dict[str, object]] = Field(default_factory=list)
    pending_claims: int = 0
    missing_billing: int = 0
    role: str = "admin"


class EmployeeDashboard(BaseModel):
    open_tasks: int
    hours_this_week: Decimal
    leave_balances: list[dict[str, object]] = Field(default_factory=list)
    running_task_id: UUID | None = None
    running_task_title: str | None = None
    timesheet_status: str = "draft"
    project_count: int = 0
    is_people_manager: bool = False
    is_project_manager: bool = False
    pending_team_leaves: int = 0
    pending_team_claims: int = 0
    pending_team_timesheets: int = 0
    missing_billing: int = 0
