from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class FinanceProjectRow(BaseModel):
    project_id: UUID
    project_name: str
    client_name: str = ""
    manager_id: UUID | None = None
    manager_name: str | None = None
    billing: Decimal
    cost: Decimal
    margin: Decimal


class FinanceMonth(BaseModel):
    year: int
    month: int
    period_label: str
    total_billing: Decimal
    total_cost: Decimal
    total_margin: Decimal
    projects: list[FinanceProjectRow]


class FinanceTrendPoint(BaseModel):
    year: int
    month: int
    label: str
    billing: Decimal
    cost: Decimal
    margin: Decimal


class FinanceYearProject(BaseModel):
    project_id: UUID
    project_name: str
    client_name: str
    invoiced: Decimal
    received: Decimal
    cost: Decimal
    profit: Decimal


class FinanceYearManager(BaseModel):
    manager_id: UUID | None = None
    manager_name: str
    invoiced: Decimal
    received: Decimal
    cost: Decimal
    profit: Decimal
    projects: list[FinanceYearProject]


class FinanceYearMonth(BaseModel):
    month: int
    label: str
    invoiced: Decimal
    received: Decimal
    cost: Decimal
    profit: Decimal


class FinanceYear(BaseModel):
    year: int
    invoiced: Decimal
    received: Decimal
    cost: Decimal
    profit: Decimal
    cash_leftover: Decimal
    managers: list[FinanceYearManager]
    months: list[FinanceYearMonth]
