from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.models.project import ContractType, ProjectStatus
from app.schemas.common import ORMModel
from app.schemas.employee import EmployeeOut

NonEmpty255 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Code50 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Currency8 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8)]


class ProjectCreate(BaseModel):
    name: NonEmpty255
    client_name: NonEmpty255
    project_code: Code50
    description: str = ""
    manager_id: UUID
    start_date: date
    end_date: date | None = None
    status: ProjectStatus = ProjectStatus.PLANNED
    contract_type: ContractType = ContractType.TIME_AND_MATERIAL
    revenue_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    revenue_currency: Currency8 = "USD"
    budgeted_hours: Decimal = Field(default=Decimal("0.00"), ge=0)
    member_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectCreate":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date")
        return self


class ProjectUpdate(BaseModel):
    name: NonEmpty255 | None = None
    client_name: NonEmpty255 | None = None
    description: str | None = None
    manager_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: ProjectStatus | None = None
    contract_type: ContractType | None = None
    revenue_amount: Decimal | None = Field(default=None, ge=0)
    revenue_currency: Currency8 | None = None
    budgeted_hours: Decimal | None = Field(default=None, ge=0)
    member_ids: list[UUID] | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "ProjectUpdate":
        for field in (
            "name",
            "client_name",
            "description",
            "manager_id",
            "start_date",
            "status",
            "contract_type",
            "revenue_amount",
            "revenue_currency",
            "budgeted_hours",
            "member_ids",
        ):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        if self.start_date is not None and self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date")
        return self


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
