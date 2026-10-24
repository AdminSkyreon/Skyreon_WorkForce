from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import AdminUser, DbSession
from app.models.project import ProjectStatus
from app.schemas.common import Page
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services import projects as project_service
from app.services import tasks as task_service

router = APIRouter(prefix="/admin/projects", tags=["projects"])


@router.get("", response_model=Page[ProjectOut])
async def list_projects(
    _admin: AdminUser,
    db: DbSession,
    search: str | None = None,
    status: ProjectStatus | None = None,
    manager_id: UUID | None = None,
    start_from: date | None = None,
    start_to: date | None = None,
    sort: str = "name",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ProjectOut]:
    items, total = await project_service.list_projects(
        db,
        search=search,
        status=status,
        manager_id=manager_id,
        start_from=start_from,
        start_to=start_to,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return Page(
        items=[project_service.to_project_out(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(payload: ProjectCreate, _admin: AdminUser, db: DbSession) -> ProjectOut:
    project = await project_service.create_project(db, payload)
    return project_service.to_project_out(project)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: UUID, _admin: AdminUser, db: DbSession) -> ProjectOut:
    project = await project_service.get_project(db, project_id)
    financials = await project_service.compute_financials(db, project_id)
    return project_service.to_project_out(project, financials)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID, payload: ProjectUpdate, _admin: AdminUser, db: DbSession
) -> ProjectOut:
    project = await project_service.update_project(db, project_id, payload)
    financials = await project_service.compute_financials(db, project_id)
    return project_service.to_project_out(project, financials)


@router.get("/{project_id}/tasks", response_model=list[TaskOut])
async def list_tasks(project_id: UUID, _admin: AdminUser, db: DbSession) -> list[TaskOut]:
    await project_service.get_project(db, project_id)
    return await task_service.list_project_tasks(db, project_id)


@router.post("/{project_id}/tasks", response_model=TaskOut, status_code=201)
async def create_task(
    project_id: UUID, payload: TaskCreate, _admin: AdminUser, db: DbSession
) -> TaskOut:
    await project_service.get_project(db, project_id)
    return await task_service.create_task(db, project_id, payload)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: UUID, payload: TaskUpdate, _admin: AdminUser, db: DbSession
) -> TaskOut:
    return await task_service.update_task(db, task_id, payload)
