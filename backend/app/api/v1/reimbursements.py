from uuid import UUID

from fastapi import APIRouter

from app.core.deps import AdminUser, CurrentEmployee, CurrentUser, DbSession
from app.models.reimbursement import ReimbursementStatus
from app.schemas.reimbursement import ReimbursementCreate, ReimbursementOut, ReimbursementReview
from app.services import notifications as notification_service
from app.services import reimbursements as claim_service
from app.services.employees import get_employee

router = APIRouter(tags=["reimbursements"])


@router.get("/me/reimbursements", response_model=list[ReimbursementOut])
async def my_claims(employee: CurrentEmployee, db: DbSession) -> list[ReimbursementOut]:
    return await claim_service.list_my_claims(db, employee.id)


@router.post("/me/reimbursements", response_model=ReimbursementOut, status_code=201)
async def apply_claim(
    payload: ReimbursementCreate, employee: CurrentEmployee, db: DbSession
) -> ReimbursementOut:
    result = await claim_service.apply_claim(db, employee, payload)
    if employee.reporting_manager_id:
        manager = await get_employee(db, employee.reporting_manager_id)
        await notification_service.notify(
            db,
            manager.user_id,
            "reimbursement_submitted",
            "Reimbursement to review",
            f"{employee.name} submitted a {result.amount} claim.",
            "/employee/team",
        )
    else:
        await notification_service.notify_admins(
            db,
            "reimbursement_submitted",
            "Reimbursement to review",
            f"{employee.name} submitted a {result.amount} claim.",
            "/admin/reimbursements",
        )
    await db.commit()
    return result


@router.post("/me/reimbursements/{claim_id}/cancel", response_model=ReimbursementOut)
async def cancel_claim(claim_id: UUID, employee: CurrentEmployee, db: DbSession) -> ReimbursementOut:
    return await claim_service.cancel_claim(db, employee.id, claim_id)


@router.get("/reimbursements", response_model=list[ReimbursementOut])
async def list_claims(user: CurrentUser, db: DbSession) -> list[ReimbursementOut]:
    return await claim_service.list_manageable_claims(db, user)


@router.post("/reimbursements/{claim_id}/approve", response_model=ReimbursementOut)
async def approve_claim(
    claim_id: UUID, payload: ReimbursementReview, user: CurrentUser, db: DbSession
) -> ReimbursementOut:
    result = await claim_service.review_claim(db, user, claim_id, ReimbursementStatus.APPROVED, payload.comment)
    employee = await get_employee(db, result.employee_id)
    await notification_service.notify(
        db,
        employee.user_id,
        "reimbursement_approved",
        "Reimbursement approved",
        f"Your {result.amount} claim was approved.",
        "/employee/reimbursements",
    )
    await db.commit()
    return result


@router.post("/reimbursements/{claim_id}/reject", response_model=ReimbursementOut)
async def reject_claim(
    claim_id: UUID, payload: ReimbursementReview, user: CurrentUser, db: DbSession
) -> ReimbursementOut:
    result = await claim_service.review_claim(db, user, claim_id, ReimbursementStatus.REJECTED, payload.comment)
    employee = await get_employee(db, result.employee_id)
    await notification_service.notify(
        db,
        employee.user_id,
        "reimbursement_rejected",
        "Reimbursement rejected",
        f"Your {result.amount} claim was rejected.",
        "/employee/reimbursements",
    )
    await db.commit()
    return result


_ = AdminUser
