from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class BillingIn(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    amount: Decimal = Field(ge=0)
    note: str = ""


class BillingOut(ORMModel):
    id: UUID
    project_id: UUID
    project_name: str | None = None
    year: int
    month: int
    amount: Decimal | None = None
    note: str
    entered_by_id: UUID | None = None
    missing: bool = False


class InvoiceCreate(BaseModel):
    project_id: UUID
    invoice_no: str | None = Field(default=None, max_length=80)
    invoice_date: date
    taxable_amount: Decimal = Field(gt=0)
    gst_percent: Decimal = Field(default=Decimal("18.00"), ge=0, le=100)
    note: str = ""


class InvoiceUpdate(BaseModel):
    project_id: UUID | None = None
    invoice_no: str | None = Field(default=None, max_length=80)
    invoice_date: date | None = None
    taxable_amount: Decimal | None = Field(default=None, gt=0)
    gst_percent: Decimal | None = Field(default=None, ge=0, le=100)
    note: str | None = None


class InvoiceOut(ORMModel):
    id: UUID
    invoice_no: str
    project_id: UUID
    project_name: str | None = None
    invoice_date: date
    year: int
    month: int
    taxable_amount: Decimal
    gst_percent: Decimal
    gst_amount: Decimal
    amount: Decimal
    received: Decimal
    outstanding: Decimal
    status: str
    note: str


class InvoiceSuggestOut(BaseModel):
    project_id: UUID
    project_name: str | None = None
    year: int
    month: int
    approved_hours: Decimal
    bill_rate: Decimal | None = None
    taxable_amount: Decimal
    gst_percent: Decimal = Decimal("18.00")
    gst_amount: Decimal
    total_amount: Decimal
    detail: str = ""


class InvoicePaymentIn(BaseModel):
    amount: Decimal = Field(gt=0)
    received_date: date
    note: str = ""


class InvoicePaymentUpdate(BaseModel):
    invoice_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    received_date: date | None = None
    note: str | None = None


class InvoicePaymentOut(ORMModel):
    id: UUID
    invoice_id: UUID | None = None
    invoice_no: str | None = None
    project_id: UUID
    project_name: str | None = None
    year: int
    month: int
    amount: Decimal
    received_date: date
    note: str
    against_earlier_invoice: bool = False
