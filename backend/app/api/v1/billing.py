from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from decimal import Decimal

from app.schemas.billing import (
    InvoiceCreate,
    InvoiceOut,
    InvoicePaymentIn,
    InvoicePaymentOut,
    InvoicePaymentUpdate,
    InvoiceSuggestOut,
    InvoiceUpdate,
)
from app.services import billing as billing_service

router = APIRouter(tags=["billing"])


@router.get("/invoices", response_model=list[InvoiceOut])
async def list_invoices(
    user: CurrentUser,
    db: DbSession,
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    outstanding: bool = False,
) -> list[InvoiceOut]:
    return await billing_service.list_invoices(db, user, year=year, month=month, outstanding_only=outstanding)


@router.get("/invoices/suggest", response_model=InvoiceSuggestOut)
async def suggest_invoice(
    user: CurrentUser,
    db: DbSession,
    project_id: UUID,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    gst_percent: Decimal | None = Query(default=None, ge=0, le=100),
) -> InvoiceSuggestOut:
    return await billing_service.suggest_invoice(db, user, project_id, year, month, gst_percent)


@router.post("/invoices", response_model=InvoiceOut, status_code=201)
async def create_invoice(payload: InvoiceCreate, user: CurrentUser, db: DbSession) -> InvoiceOut:
    return await billing_service.create_invoice(db, user, payload)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(invoice_id: UUID, payload: InvoiceUpdate, user: CurrentUser, db: DbSession) -> InvoiceOut:
    return await billing_service.update_invoice(db, user, invoice_id, payload)


@router.post("/invoices/{invoice_id}/payments", response_model=InvoicePaymentOut, status_code=201)
async def pay_invoice(
    invoice_id: UUID, payload: InvoicePaymentIn, user: CurrentUser, db: DbSession
) -> InvoicePaymentOut:
    return await billing_service.apply_payment(db, user, invoice_id, payload)


@router.patch("/payments/{payment_id}", response_model=InvoicePaymentOut)
async def update_payment(
    payment_id: UUID, payload: InvoicePaymentUpdate, user: CurrentUser, db: DbSession
) -> InvoicePaymentOut:
    return await billing_service.update_payment(db, user, payment_id, payload)


@router.get("/payments", response_model=list[InvoicePaymentOut])
async def list_payments(
    user: CurrentUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> list[InvoicePaymentOut]:
    return await billing_service.list_payments(db, user, year, month)
