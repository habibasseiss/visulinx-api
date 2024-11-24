import mimetypes
from http import HTTPStatus
from typing import Annotated
from uuid import UUID, uuid4

import magic
from boto3 import client
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from mypy_boto3_s3.client import S3Client
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Organization, Project, User
from app.schemas import ProjectList, ProjectPublic, ProjectSchema
from app.security import get_current_user
from app.settings import Settings

settings = Settings()


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


@router.post('/{project_id}/upload')
async def upload(
    organization_id: UUID,
    project_id: UUID,
    user: CurrentUser,
    file: UploadFile,
    response: Response,
):
    if not file:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='No file uploaded.',
        )

    contents = await file.read()
    filetype = magic.from_buffer(contents, mime=True)
    extension = mimetypes.guess_extension(filetype)

    if not extension:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Unsupported file type.',
        )

    key = f'projects/{project_id}/{uuid4()}{extension}'

    # Save the file to S3
    s3: S3Client = client('s3')
    s3response = s3.put_object(
        Body=contents,
        Bucket=settings.BUCKET_NAME,
        Key=key,
        ContentType=filetype,
        Metadata={
            'filename': str(file.filename),
        },
    )

    response.status_code = s3response['ResponseMetadata']['HTTPStatusCode']

    return {
        'path': key,
    }
