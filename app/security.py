from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Annotated, Mapping
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, decode, encode
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import User
from app.schemas import TokenData
from app.settings import Settings

settings = Settings.model_validate({})
pwd_context = PasswordHash.recommended()
DbSession = Annotated[Session, Depends(get_session)]


def create_access_token(data: Mapping[str, object]):
    to_encode = dict(data)
    expire = datetime.now(tz=ZoneInfo('UTC')) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({'exp': expire, 'type': 'access'})
    encoded_jwt = encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: Mapping[str, object]):
    to_encode = dict(data)
    expire = datetime.now(tz=ZoneInfo('UTC')) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({'exp': expire, 'type': 'refresh'})
    encoded_jwt = encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def get_password_hash(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def verify_token(token: str, token_type: str):
    try:
        payload = decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get('type') != token_type:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Invalid token type',
            )
        email: str = payload.get('sub')
        if email is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Could not validate credentials',
            )
        token_data = TokenData(email=email)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Token has expired',
        )
    except DecodeError:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Could not validate credentials',
        )
    return token_data


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/token')


async def get_current_user(
    session: DbSession,
    token: str = Depends(oauth2_scheme),
):
    credentials_exception = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    try:
        token_data = verify_token(token, 'access')
    except HTTPException:
        raise credentials_exception

    user = session.scalar(select(User).where(User.email == token_data.email))

    if user is None:
        raise credentials_exception

    return user
