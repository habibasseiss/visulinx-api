from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Organization, Project, User
from app.schemas import (
    OrganizationList,
    ProjectList,
    ProjectPublic,
    ProjectSchema,
)
from app.security import get_current_user

router = APIRouter(prefix='/organizations', tags=['organizations'])

DbSession = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# Utility functions
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


# Routes
@router.get('/', response_model=OrganizationList)
def list_organizations(session: DbSession, user: CurrentUser):
    organizations = session.scalars(
        select(Organization).where(Organization.users.contains(user))
    ).all()
    return {'organizations': organizations}


@router.get('/{organization_id}/projects', response_model=ProjectList)
def list_organization_projects(
    organization_id: UUID, session: DbSession, user: CurrentUser
):
    organization = get_organization(session, user, organization_id)
    projects = session.scalars(
        select(Project).where(Project.organization_id == organization.id)
    ).all()
    return {'projects': projects}


@router.post(
    '/{organization_id}/projects',
    response_model=ProjectPublic,
    status_code=HTTPStatus.CREATED,
)
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


@router.get(
    '/{organization_id}/projects/{project_id}', response_model=ProjectPublic
)
def read_project(
    organization_id: UUID,
    project_id: UUID,
    session: DbSession,
    user: CurrentUser,
):
    return get_project(session, user, organization_id, project_id)


@router.put(
    '/{organization_id}/projects/{project_id}', response_model=ProjectPublic
)
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


@router.delete(
    '/{organization_id}/projects/{project_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
def delete_project(
    organization_id: UUID,
    project_id: UUID,
    session: DbSession,
    user: CurrentUser,
):
    project = get_project(session, user, organization_id, project_id)
    session.delete(project)
    session.commit()
