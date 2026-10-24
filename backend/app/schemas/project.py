from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.project import ContractType, ProjectStatus
from app.schemas.common import ORMModel
from app.schemas.employee import EmployeeOut


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    client_name: str
    project_code: str = Field(min_length=1, max_length=50)
    description: str = ""
    manager_id: UUID
    start_date: date
    end_date: date | None = None
    status: ProjectStatus = ProjectStatus.PLANNED
    contract_type: ContractType = ContractType.TIME_AND_MATERIAL
    revenue_amount: Decimal = Decimal("0.00")
    revenue_currency: str = "USD"
    budgeted_hours: Decimal = Decimal("0.00")
    member_ids: list[UUID] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    name: str | None = None
    client_name: str | None = None
    description: str | None = None
    manager_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: ProjectStatus | None = None
    contract_type: ContractType | None = None
    revenue_amount: Decimal | None = None
    revenue_currency: str | None = None
    budgeted_hours: Decimal | None = None
    member_ids: list[UUID] | None = None


class ProjectFinancials(BaseModel):
    total_hours: Decimal
    cost: Decimal
    revenue: Decimal
    profit: Decimal
    margin_percent: Decimal
    budget_consumed_percent: Decimal


class ProjectOut(ORMModel):
    id: UUID
    name: str
    client_name: str
    project_code: str
    description: str
    manager_id: UUID
    manager_name: str | None = None
    start_date: date
    end_date: date | None
    status: ProjectStatus
    contract_type: ContractType
    revenue_amount: Decimal
    revenue_currency: str
    budgeted_hours: Decimal
    members: list[EmployeeOut] = Field(default_factory=list)
    financials: ProjectFinancials | None = None
