from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Organization, Project, User
from app.security import get_password_hash


@pytest.fixture
def organization(session: Session, user: User) -> Organization:
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
                projects=[
                    Project(  # type: ignore
                        name='Other Project',
                        description='Another test project',
                    )
                ],
            ),
        ],
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    user.clean_password = 'securepassword'  # type: ignore

    return user


def test_list_projects(
    client: TestClient, token: str, organization: Organization
):
    response = client.get(
        f'/organizations/{organization.id}/projects',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    assert 'projects' in response.json()


def test_create_project(
    client: TestClient, token: str, organization: Organization
):
    project_data = {
        'name': 'New Project',
        'description': 'New project description',
    }
    response = client.post(
        f'/organizations/{organization.id}/projects',
        headers={'Authorization': f'Bearer {token}'},
        json=project_data,
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['name'] == project_data['name']

    response = client.get(
        f'/organizations/{organization.id}/projects',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    assert any(
        project['name'] == project_data['name']
        for project in response.json()['projects']
    )


def test_read_project(
    client: TestClient, token: str, organization: Organization, project: Project
):
    response = client.get(
        f'/organizations/{organization.id}/projects/{project.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['name'] == project.name


def test_crud_project_for_wrong_organization(
    client: TestClient, token: str, other_user: User
):
    organization = other_user.organizations[0]
    assert len(organization.projects) == 1  # project created in the fixture
    organization_project = organization.projects[0]
    # create
    response = client.post(
        f'/organizations/{organization.id}/projects',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'name': 'New Project',
            'description': 'New project description',
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    # read
    response = client.get(
        f'/organizations/{organization.id}/projects/{organization_project.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    # update
    response = client.put(
        f'/organizations/{organization.id}/projects/{organization_project.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'name': 'Updated Project',
            'description': 'Updated description',
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    # delete
    response = client.delete(
        f'/organizations/{organization.id}/projects/{organization_project.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_update_project(
    client: TestClient, token: str, organization: Organization, project: Project
):
    updated_data = {
        'name': 'Updated Project',
        'description': 'Updated description',
    }
    response = client.put(
        f'/organizations/{organization.id}/projects/{project.id}',
        headers={'Authorization': f'Bearer {token}'},
        json=updated_data,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['name'] == updated_data['name']


def test_delete_project(
    client: TestClient, token: str, organization: Organization, project: Project
):
    response = client.delete(
        f'/organizations/{organization.id}/projects/{project.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Verify the project is deleted
    response = client.get(
        f'/organizations/{organization.id}/projects/{project.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
