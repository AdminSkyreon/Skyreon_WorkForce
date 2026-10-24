from fastapi import APIRouter

from app.api.v1 import (
    admins,
    audit,
    auth,
    billing,
    company,
    dashboard,
    employees,
    extra_work,
    finance,
    holidays,
    hrms,
    leave,
    locations,
    me,
    org,
    payroll,
    projects,
    reimbursements,
    timesheets,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(employees.router)
api_router.include_router(projects.router)
api_router.include_router(me.router)
api_router.include_router(holidays.public_router)
api_router.include_router(holidays.admin_router)
api_router.include_router(leave.router)
api_router.include_router(extra_work.router)
api_router.include_router(locations.router)
api_router.include_router(locations.public_router)
api_router.include_router(timesheets.router)
api_router.include_router(payroll.router)
api_router.include_router(dashboard.router)
api_router.include_router(reimbursements.router)
api_router.include_router(billing.router)
api_router.include_router(company.router)
api_router.include_router(audit.router)
api_router.include_router(admins.router)
api_router.include_router(finance.router)
api_router.include_router(org.router)
api_router.include_router(hrms.router)
