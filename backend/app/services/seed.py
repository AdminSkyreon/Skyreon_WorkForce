from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.company import CompanyProfile
from app.models.hrms import DocumentRequirement
from app.models.leave import LeaveAccrualMode, LeaveType
from app.models.location import Location
from app.models.org import Department, Designation
from app.models.user import User, UserRole

settings = get_settings()


async def seed_super_admin(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.email == settings.super_admin_email.lower()))
    if result.scalar_one_or_none():
        return
    db.add(
        User(
            email=settings.super_admin_email.lower(),
            password_hash=hash_password(settings.super_admin_password),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            must_change_password=False,
        )
    )
    await db.commit()


async def seed_admin(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.email == settings.admin_email.lower()))
    if result.scalar_one_or_none():
        return
    admin = User(
        email=settings.admin_email.lower(),
        password_hash=hash_password(settings.admin_password),
        role=UserRole.ADMIN,
        is_active=True,
        must_change_password=False,
    )
    db.add(admin)
    await db.commit()


async def seed_leave_types(db: AsyncSession) -> None:
    result = await db.execute(select(LeaveType))
    existing = {row.code for row in result.scalars().all()}
    defaults: list[tuple[str, str, int, bool, LeaveAccrualMode, Decimal]] = [
        ("Casual Leave", "CL", 12, False, LeaveAccrualMode.MONTHLY, Decimal("1.00")),
        ("Sick Leave", "SL", 10, False, LeaveAccrualMode.MONTHLY, Decimal("1.00")),
        ("Earned Leave", "EL", 15, False, LeaveAccrualMode.MONTHLY, Decimal("1.00")),
        ("Leave Without Pay", "LWP", 0, True, LeaveAccrualMode.LUMP, Decimal("0.00")),
        ("Comp Off", "CO", 0, False, LeaveAccrualMode.LUMP, Decimal("0.00")),
    ]
    added = False
    for name, code, days, unpaid, mode, per_month in defaults:
        if code in existing:
            continue
        db.add(
            LeaveType(
                name=name,
                code=code,
                annual_allocation_days=days,
                is_unpaid=unpaid,
                accrual_mode=mode,
                days_per_month=per_month,
            )
        )
        added = True
    if added:
        await db.commit()


async def seed_locations(db: AsyncSession) -> None:
    result = await db.execute(select(Location))
    if result.scalars().first():
        return
    for name, code, city, country in [
        ("Bhubaneswar", "BBS", "Bhubaneswar", "India"),
        ("Bengaluru", "BLR", "Bengaluru", "India"),
        ("Remote", "REM", "Remote", "Global"),
    ]:
        db.add(Location(name=name, code=code, city=city, country=country, is_active=True))
    await db.commit()


async def seed_company(db: AsyncSession) -> None:
    if (await db.execute(select(CompanyProfile))).scalar_one_or_none():
        return
    db.add(
        CompanyProfile(
            legal_name="Skyreon",
            address="",
            website="https://www.skyreon.com",
            signatory_name="",
            signatory_title="",
        )
    )
    await db.commit()


async def seed_org_lists(db: AsyncSession) -> None:
    if (await db.execute(select(Department))).scalars().first() is None:
        for name in ("Engineering", "Delivery", "Finance", "People", "Operations"):
            db.add(Department(name=name))
        await db.commit()
    if (await db.execute(select(Designation))).scalars().first() is None:
        for name in ("Software Engineer", "Project Manager", "HR Executive", "Accountant", "Contractor"):
            db.add(Designation(name=name))
        await db.commit()
    if (await db.execute(select(DocumentRequirement))).scalars().first() is None:
        for name in ("PAN", "Aadhaar", "Offer letter", "Bank details", "Education certificate"):
            db.add(DocumentRequirement(name=name))
        await db.commit()


async def run_seed(db: AsyncSession) -> None:
    await seed_super_admin(db)
    await seed_admin(db)
    await seed_leave_types(db)
    await seed_locations(db)
    await seed_company(db)
    await seed_org_lists(db)


_ = (date, Decimal)
