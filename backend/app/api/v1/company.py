from fastapi import APIRouter

from app.core.deps import DbSession, SuperAdminUser
from app.schemas.company import CompanyProfileIn, CompanyProfileOut
from app.services import company as company_service

router = APIRouter(prefix="/super/company", tags=["company"])


@router.get("", response_model=CompanyProfileOut)
async def get_company(_user: SuperAdminUser, db: DbSession) -> CompanyProfileOut:
    return company_service.to_out(await company_service.get_profile(db))


@router.put("", response_model=CompanyProfileOut)
async def update_company(
    payload: CompanyProfileIn, user: SuperAdminUser, db: DbSession
) -> CompanyProfileOut:
    return company_service.to_out(await company_service.update_profile(db, user, payload))
