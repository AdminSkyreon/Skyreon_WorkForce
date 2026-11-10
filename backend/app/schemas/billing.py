from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.schemas.common import ORMModel

InvoiceNo80 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]


class BillingIn(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    amount: Decimal = Field(ge=0)
    note: str = Field(default="", max_length=500)


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
    invoice_no: InvoiceNo80 | None = None
    invoice_date: date
    taxable_amount: Decimal = Field(gt=0)
    gst_percent: Decimal = Field(default=Decimal("18.00"), ge=0, le=100)
    note: str = Field(default="", max_length=500)


class InvoiceUpdate(BaseModel):
    project_id: UUID | None = None
    invoice_no: InvoiceNo80 | None = None
    invoice_date: date | None = None
    taxable_amount: Decimal | None = Field(default=None, gt=0)
    gst_percent: Decimal | None = Field(default=None, ge=0, le=100)
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def reject_nulls(self) -> "InvoiceUpdate":
        for field in ("project_id", "invoice_no", "invoice_date", "taxable_amount", "gst_percent", "note"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


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
    note: str = Field(default="", max_length=500)


class InvoicePaymentUpdate(BaseModel):
    invoice_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    received_date: date | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def reject_nulls(self) -> "InvoicePaymentUpdate":
        for field in ("invoice_id", "amount", "received_date", "note"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


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
