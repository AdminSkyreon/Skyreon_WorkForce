from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import CompanyProfile
from app.models.user import User
from app.schemas.company import CompanyProfileIn, CompanyProfileOut
from app.services.audit import log_audit


def to_out(row: CompanyProfile) -> CompanyProfileOut:
    return CompanyProfileOut(
        legal_name=row.legal_name,
        address=row.address,
        phone=row.phone,
        website=row.website,
        signatory_name=row.signatory_name,
        signatory_title=row.signatory_title,
        has_signature=bool(row.signature_image),
    )


async def get_profile(db: AsyncSession) -> CompanyProfile:
    row = (await db.execute(select(CompanyProfile))).scalar_one_or_none()
    if row is None:
        row = CompanyProfile(legal_name="Skyreon", website="https://www.skyreon.com")
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


async def update_profile(db: AsyncSession, user: User, data: CompanyProfileIn) -> CompanyProfile:
    row = await get_profile(db)
    before = {
        "legal_name": row.legal_name,
        "signatory_name": row.signatory_name,
        "has_signature": bool(row.signature_image),
    }
    row.legal_name = data.legal_name
    row.address = data.address
    row.phone = data.phone
    row.website = data.website
    row.signatory_name = data.signatory_name
    row.signatory_title = data.signatory_title
    if data.signature_image is not None:
        row.signature_image = data.signature_image
    await log_audit(
        db,
        user,
        "updated",
        "company_profile",
        row.id,
        summary="Updated company letterhead",
        before=before,
        after={
            "legal_name": row.legal_name,
            "signatory_name": row.signatory_name,
            "has_signature": bool(row.signature_image),
        },
    )
    await db.commit()
    await db.refresh(row)
    return row
