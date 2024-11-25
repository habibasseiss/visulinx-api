from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import File, Organization, Project, User
from app.schemas import ProjectList, ProjectPublic, ProjectSchema
from app.security import get_current_user
from app.services.upload_service import delete_file_from_s3, upload_file_to_s3
from app.settings import Settings

settings = Settings.model_validate({})


router = APIRouter(
    prefix='/organizations/{organization_id}/projects', tags=['projects']
)

DbSession = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_organization(
    session: DbSession, user: CurrentUser, organization_id: UUID
) -> Organization:
    query = select(Organization).where(Organization.users.contains(user))
    if organization_id:
        query = query.where(Organization.id == organization_id)

    organization = session.scalar(query)
    if not organization:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Organization not found.',
        )
    return organization


def get_project(
    session: DbSession,
    user: CurrentUser,
    organization_id: UUID,
    project_id: UUID,
) -> Project:
    project = session.scalar(
        select(Project).where(
            Project.organization_id == organization_id,
            Project.id == project_id,
            Project.organization.has(Organization.users.contains(user)),
        )
    )
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Project not found.',
        )
    return project


@router.get('/', response_model=ProjectList)
def list_organization_projects(
    organization_id: UUID, session: DbSession, user: CurrentUser
):
    organization = get_organization(session, user, organization_id)
    projects = session.scalars(
        select(Project).where(Project.organization_id == organization.id)
    ).all()
    return {'projects': projects}


@router.post('/', response_model=ProjectPublic, status_code=HTTPStatus.CREATED)
def create_project(
    organization_id: UUID,
    project: ProjectSchema,
    session: DbSession,
    user: CurrentUser,
):
    organization = get_organization(session, user, organization_id)

    db_project = Project(  # type: ignore
        name=project.name,
        description=project.description,
        organization_id=organization_id,
        organization=organization,
    )
    session.add(db_project)
    session.commit()
    session.refresh(db_project)

    return db_project


@router.get('/{project_id}', response_model=ProjectPublic)
def read_project(
    organization_id: UUID,
    project_id: UUID,
    session: DbSession,
    user: CurrentUser,
):
    return get_project(session, user, organization_id, project_id)


@router.put('/{project_id}', response_model=ProjectPublic)
def update_project(
    organization_id: UUID,
    project_id: UUID,
    project: ProjectSchema,
    session: DbSession,
    user: CurrentUser,
):
    db_project = get_project(session, user, organization_id, project_id)
    db_project.name = project.name
    db_project.description = project.description
    session.commit()
    session.refresh(db_project)
    return db_project


@router.delete('/{project_id}', status_code=HTTPStatus.NO_CONTENT)
def delete_project(
    organization_id: UUID,
    project_id: UUID,
    session: DbSession,
    user: CurrentUser,
):
    project = get_project(session, user, organization_id, project_id)
    session.delete(project)
    session.commit()


@router.post('/{project_id}/files')
async def upload(  # noqa
    organization_id: UUID,
    project_id: UUID,
    user: CurrentUser,
    file: UploadFile,
    session: DbSession,
):
    # Verify project exists and user has access
    _ = get_project(session, user, organization_id, project_id)

    # Upload file to S3
    result = await upload_file_to_s3(project_id, file)

    # Create file record in database
    db_file = File(  # type: ignore
        path=result.path,
        size=result.size,
        project_id=project_id,
    )
    session.add(db_file)
    session.commit()
    result.id = db_file.id

    return result


@router.delete(
    '/{project_id}/files/{file_id}', status_code=HTTPStatus.NO_CONTENT
)
async def delete_file(
    organization_id: UUID,
    project_id: UUID,
    file_id: UUID,
    user: CurrentUser,
    session: DbSession,
):
    # Verify project exists and user has access
    _ = get_project(session, user, organization_id, project_id)

    # Find the file record in database
    db_file = (
        session.query(File)
        .filter(File.id == file_id, File.project_id == project_id)
        .first()
    )

    if not db_file:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='File not found in database',
        )

    # Delete file from S3
    await delete_file_from_s3(db_file.path)

    # Delete the database record
    session.delete(db_file)
    session.commit()

    return Response(status_code=HTTPStatus.NO_CONTENT)
