from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Organization, Project, User
from app.security import get_password_hash


@pytest.fixture
def organization(session: Session, user) -> Organization:
    organization = Organization(  # type: ignore
        name='Test Organization',
        users=[user],
    )
    session.add(organization)
    session.commit()
    session.refresh(organization)
    return organization


@pytest.fixture
def project(session: Session, organization: Organization) -> Project:
    project = Project(  # type: ignore
        name='Test Project',
        description='A test project',
        organization_id=organization.id,
        organization=organization,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@pytest.fixture
def other_user(session: Session) -> User:
    user = User(  # type: ignore
        email='test2@example.com',
        password=get_password_hash('securepassword'),
        organizations=[
            Organization(  # type: ignore
                name='Other Organization',
            ),
        ],
    )

    user.organizations[0].projects.append(
        Project(  # type: ignore
            name='Other Project',
            description='Another test project',
            organization=user.organizations[0],
            organization_id=user.organizations[0].id,
        )
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    user.clean_password = 'securepassword'  # type: ignore

    return user


def test_list_organizations(client: TestClient, token: str):
    response = client.get(
        '/organizations/',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    assert 'organizations' in response.json()


# def test_create_organization(client: TestClient, token: str):
#     response = client.post(
#         '/organizations/',
#         headers={'Authorization': f'Bearer {token}'},
#         json={'name': 'Test Organization'},
#     )
#     assert response.status_code == HTTPStatus.CREATED

#     data = response.json()
#     assert data['name'] == 'Test Organization'
