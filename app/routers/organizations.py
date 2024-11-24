from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Organization, User
from app.schemas import OrganizationList
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


# Routes
@router.get('/', response_model=OrganizationList)
def list_organizations(session: DbSession, user: CurrentUser):
    organizations = session.scalars(
        select(Organization).where(Organization.users.contains(user))
    ).all()
    return {'organizations': organizations}
