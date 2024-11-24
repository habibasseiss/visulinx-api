from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.security import get_password_hash


@pytest.fixture
def other_user(session: Session) -> User:
    user = User(  # type: ignore
        email='test2@example.com',
        password=get_password_hash('securepassword'),
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    user.clean_password = 'securepassword'  # type: ignore

    return user


def test_db_user_creation(session: Session):
    # Create a new user
    user = User(  # type: ignore
        email='test@example.com',
        password='securepassword',
    )
    session.add(user)
    session.commit()

    # Verify user is persisted
    queried_user = (
        session.query(User).filter_by(email='test@example.com').first()
    )
    assert queried_user is not None
    assert queried_user.email == 'test@example.com'


def test_create_user(client: TestClient):
    response = client.post(
        '/users/',
        json={
            'email': 'alice@example.com',
            'password': 'secret',
        },
    )
    assert response.status_code == HTTPStatus.CREATED

    data = response.json()
    assert data['email'] == 'alice@example.com'
    # newly created user must have an organization
    assert any(org['name'] == 'Default' for org in data['organizations'])


def test_cannot_read_users(client: TestClient):
    response = client.get('/users')
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_update_user(client: TestClient, user: User, token: str):
    response = client.put(
        f'/users/{user.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': 'bob@example.com',
            'password': 'mynewpassword',
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['email'] == 'bob@example.com'


def test_delete_user(client: TestClient, user: User, token: str):
    response = client.delete(
        f'/users/{user.id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'User deleted'}


def test_update_user_with_wrong_user(
    client: TestClient, other_user: User, token: str
):
    response = client.put(
        f'/users/{other_user.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': 'bob@example.com',
            'password': 'mynewpassword',
        },
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {'detail': 'Not enough permissions'}


def test_delete_user_wrong_user(
    client: TestClient, other_user: User, token: str
):
    response = client.delete(
        f'/users/{other_user.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {'detail': 'Not enough permissions'}
