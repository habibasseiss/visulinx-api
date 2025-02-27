from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Organization, User
from app.schemas import Message, UserPublic, UserSchema
from app.security import get_current_user, get_password_hash

router = APIRouter(prefix='/users', tags=['users'])
DbSession = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post('/', status_code=HTTPStatus.CREATED, response_model=UserPublic)
def create_user(user: UserSchema, session: DbSession):
    db_user: User | None = session.scalar(
        select(User).where(User.email == user.email)
    )

    if db_user:
        if db_user.email == user.email:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Email already exists',
            )

    organization = Organization(  # type: ignore
        name='Default',
    )

    hashed_password = get_password_hash(user.password)

    db_user = User(  # type: ignore
        email=user.email,
        password=hashed_password,
        organizations=[organization],
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


@router.get('/me', response_model=UserPublic)
def read_user(current_user: CurrentUser):
    return current_user


@router.put('/{user_id}', response_model=UserPublic)
def update_user(
    user_id: UUID,
    user: UserSchema,
    session: DbSession,
    current_user: CurrentUser,
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail='Not enough permissions'
        )

    current_user.password = get_password_hash(user.password)
    current_user.email = user.email
    session.commit()
    session.refresh(current_user)

    return current_user


@router.delete('/{user_id}', response_model=Message)
def delete_user(
    user_id: UUID,
    session: DbSession,
    current_user: CurrentUser,
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail='Not enough permissions'
        )

    session.delete(current_user)
    session.commit()

    return {'message': 'User deleted'}
