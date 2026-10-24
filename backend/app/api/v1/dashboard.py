from fastapi import APIRouter

from app.core.deps import AdminUser, DbSession
from app.schemas.dashboard import AdminDashboard
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/admin/dashboard", tags=["dashboard"])


@router.get("", response_model=AdminDashboard)
async def admin_dashboard(_admin: AdminUser, db: DbSession) -> AdminDashboard:
    return await dashboard_service.admin_dashboard(db)
