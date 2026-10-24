from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.deps import DbSession, SuperAdminUser
from app.schemas.finance import FinanceMonth, FinanceTrendPoint, FinanceYear
from app.services import finance as finance_service

router = APIRouter(prefix="/super/finance", tags=["finance"])


@router.get("", response_model=FinanceMonth)
async def finance_month(
    _user: SuperAdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> FinanceMonth:
    return await finance_service.month_report(db, year, month)


@router.get("/trend", response_model=list[FinanceTrendPoint])
async def finance_trend(
    _user: SuperAdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> list[FinanceTrendPoint]:
    return await finance_service.trend(db, year, month)


@router.get("/year", response_model=FinanceYear)
async def finance_year(
    _user: SuperAdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
) -> FinanceYear:
    return await finance_service.year_report(db, year)


@router.get("/year.pdf")
async def finance_year_pdf(
    _user: SuperAdminUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
) -> Response:
    report = await finance_service.year_report(db, year)
    filename = f"finance-{year}.pdf"
    return Response(
        content=await finance_service.render_year_pdf(report, db),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
