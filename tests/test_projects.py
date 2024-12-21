import uuid
from http import HTTPStatus
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient
from mypy_boto3_s3.client import S3Client
from sqlalchemy.orm import Session

from app.models import File, Organization, Project, User
from app.schemas import FileSchema
from app.security import get_password_hash
from app.settings import Settings

settings = Settings.model_validate({})


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
                projects=[],
            ),
        ],
    )
    Project(  # type: ignore
        name='Other Project',
        description='Another test project',
        organization=user.organizations[0],
        organization_id=user.organizations[0].id,
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
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
):
    response = client.get(
        f'/organizations/{organization.id}/projects/{project.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['name'] == project.name


def test_read_project_with_files(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
    session: Session,
):
    # Create a test file associated with the project
    test_file = File(  # type: ignore
        path='test_file.txt',
        size=100,
        project_id=project.id,
        mime_type='text/plain',
        original_filename='test_file.txt',
    )
    session.add(test_file)
    session.commit()
    session.refresh(project)

    response = client.get(
        f'/organizations/{organization.id}/projects/{project.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    response_json = response.json()
    assert response_json['name'] == project.name
    assert 'files' in response_json
    assert len(response_json['files']) == 1
    assert response_json['files'][0]['path'] == 'test_file.txt'
    assert response_json['files'][0]['size'] == 100  # noqa: PLR2004


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
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
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
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
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


def test_upload_file(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
):
    # Simulate a file upload
    file_content = b'%PDF-1.4 fake pdf content'
    files = [('files', ('test.pdf', file_content, 'application/pdf'))]

    # Mock the upload_file_to_s3 function and prevent background tasks
    with (
        patch('app.routers.projects.upload_file_to_s3') as mock_upload,
        patch('app.routers.projects.get_download_url'),
        patch('app.routers.projects.process'),
    ):
        mock_upload.return_value = FileSchema(
            path='mocked/path/to/test.pdf',
            size=len(file_content),
            mime_type='application/pdf',
            original_filename='test.pdf',
            contents=None,
            processed_at=None,
        )

        # Call the endpoint
        response = client.post(
            f'/organizations/{organization.id}/projects/{project.id}/files',
            headers={'Authorization': f'Bearer {token}'},
            files=files,
        )

        # Assertions
        assert response.status_code == HTTPStatus.CREATED
        response_json = response.json()
        assert isinstance(response_json, list)
        assert len(response_json) == 1
        file_response = response_json[0]
        assert file_response['path'] == 'mocked/path/to/test.pdf'
        assert file_response['size'] == len(file_content)

        # Ensure only the upload mock was called
        mock_upload.assert_called_once()


@pytest.mark.asyncio
async def test_upload_file_with_processing(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
    session: Session,
):
    # Simulate a file upload
    file_content = b'%PDF-1.4 fake pdf content'
    files = [('files', ('test.pdf', file_content, 'application/pdf'))]

    # Mock the upload_file_to_s3 function and get_download_url
    with (
        patch('app.routers.projects.upload_file_to_s3') as mock_upload,
        patch('app.routers.projects.get_download_url') as mock_get_url,
        patch('httpx.AsyncClient') as mock_client,
    ):
        # Setup mock for file upload
        mock_upload.return_value = FileSchema(
            path='mocked/path/to/test.pdf',
            size=len(file_content),
            mime_type='application/pdf',
            original_filename='test.pdf',
            contents=None,
            processed_at=None,
        )

        # Setup mock for download URL
        mock_get_url.return_value = 'https://example.com/test.pdf'

        # Setup mock for HTTP client
        mock_response = MagicMock()
        mock_response.text = 'processed content'
        mock_response.raise_for_status = lambda: None
        mock_client.return_value.__aenter__.return_value.post.return_value = (
            mock_response
        )

        # Call the endpoint
        response = client.post(
            f'/organizations/{organization.id}/projects/{project.id}/files',
            headers={'Authorization': f'Bearer {token}'},
            files=files,
        )

        # Assertions for response
        assert response.status_code == HTTPStatus.CREATED
        response_json = response.json()
        assert isinstance(response_json, list)
        assert len(response_json) == 1
        file_response = response_json[0]
        assert file_response['path'] == 'mocked/path/to/test.pdf'
        assert file_response['size'] == len(file_content)

        # Verify file was created in database
        db_file = (
            session.query(File)
            .filter_by(path='mocked/path/to/test.pdf')
            .first()
        )
        assert db_file is not None
        assert db_file.original_filename == 'test.pdf'

        # Verify processing completed and database was updated
        assert db_file.processed_at is not None
        assert db_file.contents is not None

        # Verify the HTTP request was made
        mock_client.return_value.__aenter__.return_value.post.assert_called_once()


def test_delete_file(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
    session: Session,
):
    # Create three file records in the database
    db_files = [
        File(  # type: ignore
            path=f'projects/test-project/test{i}.txt',
            size=100,
            project_id=project.id,
            mime_type='text/plain',
            original_filename=f'test{i}.txt',
        )
        for i in range(3)
    ]
    session.add_all(db_files)
    session.commit()

    # Test deleting a single file
    with patch('app.routers.projects.delete_file_from_s3') as mock_delete:
        response = client.delete(
            f'/organizations/{organization.id}/projects/{project.id}/files',
            headers={'Authorization': f'Bearer {token}'},
            params={'ids[]': str(db_files[0].id)},
        )

        # Assertions for single file deletion
        assert response.status_code == HTTPStatus.NO_CONTENT
        mock_delete.assert_called_once_with(db_files[0].path)
        assert (
            session.query(File).filter(File.id == db_files[0].id).first()
            is None
        )
        assert (
            session.query(File).filter(File.id == db_files[1].id).first()
            is not None
        )

    # Test deleting multiple files
    with patch('app.routers.projects.delete_file_from_s3') as mock_delete:
        response = client.delete(
            f'/organizations/{organization.id}/projects/{project.id}/files',
            headers={'Authorization': f'Bearer {token}'},
            params={'ids[]': [str(db_files[1].id), str(db_files[2].id)]},
        )

        # Assertions for multiple file deletion
        assert response.status_code == HTTPStatus.NO_CONTENT

        # Verify both files were deleted from S3
        mock_delete.assert_has_calls(
            [
                call(db_files[1].path),
                call(db_files[2].path),
            ],
            any_order=True,
        )
        assert mock_delete.call_count == 2  # noqa: PLR2004

        # Verify both files were deleted from database
        assert (
            session.query(File).filter(File.id == db_files[1].id).first()
            is None
        )
        assert (
            session.query(File).filter(File.id == db_files[2].id).first()
            is None
        )


def test_delete_nonexistent_file(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
):
    # Use a random UUID that doesn't exist in the database
    nonexistent_file_id = uuid.uuid4()

    # Call the endpoint
    response = client.delete(
        f'/organizations/{organization.id}/projects/{project.id}/files',
        headers={'Authorization': f'Bearer {token}'},
        params={'ids[]': str(nonexistent_file_id)},
    )

    # Assertions
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'No files found in database'


def test_delete_file_wrong_organization(
    client: TestClient,
    token: str,
    other_user: User,
    session: Session,
):
    organization = other_user.organizations[0]
    project = organization.projects[0]

    # Create a file record in the database
    db_file = File(  # type: ignore
        path='projects/test-project/test.txt',
        size=100,
        project_id=project.id,
        mime_type='text/plain',
        original_filename='test.txt',
    )
    session.add(db_file)
    session.commit()

    # Call the endpoint
    response = client.delete(
        f'/organizations/{organization.id}/projects/{project.id}/files',
        headers={'Authorization': f'Bearer {token}'},
        params={'ids[]': str(db_file.id)},
    )

    # Should fail with NOT_FOUND, user doesn't have access to the organization
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_upload_file_wrong_organization(
    client: TestClient,
    token: str,
    other_user: User,
):
    # Create a file for upload
    file_content = b'test content'
    files = [('files', ('test.txt', file_content, 'text/plain'))]

    # Try to upload to a project in an organization the user doesn't belong to
    response = client.post(
        f'/organizations/{other_user.organizations[0].id}/projects/{other_user.organizations[0].projects[0].id}/files',
        files=files,
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_project_deletion_with_files(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
    session: Session,
):
    # Create some test files in the database
    files = [
        File(  # type: ignore
            path=f'projects/{project.id}/test{i}.txt',
            size=100,
            mime_type='text/plain',
            original_filename=f'test{i}.txt',
            project_id=project.id,
        )
        for i in range(3)
    ]
    session.add_all(files)
    session.commit()
    for file in files:
        session.refresh(file)

    # Delete the project
    response = client.delete(
        f'/organizations/{organization.id}/projects/{project.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Verify project is marked as deleted but files still exist
    db_project = session.get(Project, project.id)
    assert db_project is not None
    assert db_project.deleted_at is not None

    for file in files:
        db_file = session.get(File, file.id)
        assert db_file is not None


@pytest.mark.asyncio
async def test_project_deletion_handles_s3_error(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
    session: Session,
):
    # Create a test file
    file = File(  # type: ignore
        path=f'projects/{project.id}/test.txt',
        size=100,
        mime_type='text/plain',
        original_filename='test.txt',
        project_id=project.id,
    )
    session.add(file)
    session.commit()
    session.refresh(file)

    # Delete the project
    response = client.delete(
        f'/organizations/{organization.id}/projects/{project.id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    # Expect success
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Verify project is marked as deleted but file still exists
    db_project = session.get(Project, project.id)
    assert db_project is not None
    assert db_project.deleted_at is not None

    db_file = session.get(File, file.id)
    assert db_file is not None


def test_soft_delete_project(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
    session: Session,
):
    # Delete the project
    response = client.delete(
        f'/organizations/{organization.id}/projects/{project.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Verify project is not in the list
    response = client.get(
        f'/organizations/{organization.id}/projects',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data['projects']) == 0

    # Verify project cannot be accessed directly
    response = client.get(
        f'/organizations/{organization.id}/projects/{project.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND

    # Verify project exists in database with deleted_at timestamp
    db_project = session.get(Project, project.id)
    assert db_project is not None
    assert db_project.deleted_at is not None


def test_soft_delete_project_with_files(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
    session: Session,
):
    # Add a file to the project
    file = File(  # type: ignore
        path='test/path',
        size=100,
        mime_type='text/plain',
        original_filename='test.txt',
        project_id=project.id,
    )
    session.add(file)
    session.commit()

    # Delete the project
    response = client.delete(
        f'/organizations/{organization.id}/projects/{project.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Verify project and file still exist in database
    db_project = session.get(Project, project.id)
    assert db_project is not None
    assert db_project.deleted_at is not None

    db_file = session.get(File, file.id)
    assert db_file is not None


@pytest.mark.asyncio
async def test_hard_delete_project(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
    session: Session,
):
    # Delete the project
    response = client.delete(
        f'/organizations/{organization.id}/projects/{project.id}/hard',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Verify project is completely removed from database
    db_project = session.get(Project, project.id)
    assert db_project is None


@pytest.mark.asyncio
async def test_hard_delete_project_with_files(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
    session: Session,
):
    # Create some test files in the database
    files = [
        File(  # type: ignore
            path=f'projects/{project.id}/test{i}.txt',
            size=100,
            mime_type='text/plain',
            original_filename=f'test{i}.txt',
            project_id=project.id,
        )
        for i in range(3)
    ]
    session.add_all(files)
    session.commit()
    for file in files:
        session.refresh(file)

    # Mock the S3 deletion
    with patch('app.services.upload_service.boto3.client') as mock_s3:
        mock_s3_client: S3Client = mock_s3.return_value
        mock_s3_client.delete_object = MagicMock(  # type: ignore
            return_value={
                'ResponseMetadata': {'HTTPStatusCode': HTTPStatus.NO_CONTENT}
            }
        )

        # Delete the project
        response = client.delete(
            f'/organizations/{organization.id}/projects/{project.id}/hard',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert response.status_code == HTTPStatus.NO_CONTENT

        # Verify S3 files were deleted
        assert mock_s3_client.delete_object.call_count == 3  # noqa: PLR2004
        for file in files:
            mock_s3_client.delete_object.assert_any_call(
                Bucket=settings.BUCKET_NAME,
                Key=file.path,
            )

    # Verify files are deleted from database
    for file in files:
        db_file = session.get(File, file.id)
        assert db_file is None

    # Verify project is deleted
    db_project = session.get(Project, project.id)
    assert db_project is None


@pytest.mark.asyncio
async def test_hard_delete_project_handles_s3_error(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
    session: Session,
):
    # Create a test file
    file = File(  # type: ignore
        path=f'projects/{project.id}/test.txt',
        size=100,
        mime_type='text/plain',
        original_filename='test.txt',
        project_id=project.id,
    )
    session.add(file)
    session.commit()
    session.refresh(file)

    # Mock S3 deletion to fail
    with patch('app.services.upload_service.boto3.client') as mock_s3:
        mock_s3_client: S3Client = mock_s3.return_value
        mock_s3_client.delete_object = MagicMock(  # type: ignore
            return_value={
                'ResponseMetadata': {
                    'HTTPStatusCode': HTTPStatus.INTERNAL_SERVER_ERROR
                }
            }
        )

        # Delete the project
        response = client.delete(
            f'/organizations/{organization.id}/projects/{project.id}/hard',
            headers={'Authorization': f'Bearer {token}'},
        )

        # Expect success even if S3 deletion fails
        assert response.status_code == HTTPStatus.NO_CONTENT

        # Verify S3 deletion was attempted
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket=settings.BUCKET_NAME,
            Key=file.path,
        )

    # Verify database records are deleted even if S3 deletion fails
    db_file = session.get(File, file.id)
    assert db_file is None
    db_project = session.get(Project, project.id)
    assert db_project is None


@pytest.mark.asyncio
async def test_download_file(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
    session: Session,
):
    # Create a test file in the database
    file = File(  # type: ignore
        project_id=project.id,
        path='test/path/file.txt',
        original_filename='test_file.txt',
        size=1000,
        mime_type='text/plain',
    )
    session.add(file)
    session.commit()
    session.refresh(file)

    # Mock the get_download_url function
    mock_url = 'https://example.com/download/test_file.txt'
    with patch(
        'app.routers.projects.get_download_url', return_value=mock_url
    ) as mock_get_url:
        response = client.get(
            f'/organizations/{organization.id}/projects/{project.id}/files/{file.id}/download',
            headers={'Authorization': f'Bearer {token}'},
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {'download_url': mock_url}
        mock_get_url.assert_called_once_with(file.path, file.original_filename)


@pytest.mark.asyncio
async def test_download_nonexistent_file(
    client: TestClient,
    token: str,
    organization: Organization,
    project: Project,
):
    nonexistent_file_id = uuid.uuid4()
    response = client.get(
        f'/organizations/{organization.id}/projects/{project.id}/files/{nonexistent_file_id}/download',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'File not found.'


@pytest.mark.asyncio
async def test_download_file_wrong_organization(
    client: TestClient,
    token: str,
    other_user: User,
    session: Session,
):
    # Create a project and file in a different organization
    other_org = other_user.organizations[0]
    project = Project(  # type: ignore
        name='Other Project',
        description='Another test project',
        organization_id=other_org.id,
        organization=other_org,
    )
    session.add(project)
    session.commit()

    file = File(  # type: ignore
        project_id=project.id,
        path='test/path/file.txt',
        original_filename='test_file.txt',
        size=1000,
        mime_type='text/plain',
    )
    session.add(file)
    session.commit()

    response = client.get(
        f'/organizations/{other_org.id}/projects/{project.id}/files/{file.id}/download',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
