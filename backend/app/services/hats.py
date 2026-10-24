from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee, EmployeeStatus
from app.models.project import Project
from app.models.user import User


async def user_hats(db: AsyncSession, user: User) -> tuple[bool, bool]:
    if user.employee is None:
        return False, False
    people = (
        await db.execute(
            select(func.count())
            .select_from(Employee)
            .where(
                Employee.reporting_manager_id == user.employee.id,
                Employee.status == EmployeeStatus.ACTIVE,
            )
        )
    ).scalar_one()
    projects = (
        await db.execute(
            select(func.count()).select_from(Project).where(Project.manager_id == user.employee.id)
        )
    ).scalar_one()
    return people > 0, projects > 0
