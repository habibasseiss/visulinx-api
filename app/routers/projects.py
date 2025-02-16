import asyncio
import json
import logging
from datetime import datetime
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import File, Organization, Preference, Project, User
from app.schemas import (
    FileSchema,
    ProjectList,
    ProjectPublic,
    ProjectPublicList,
    ProjectSchema,
)
from app.security import get_current_user
from app.services import ai_service, document_service
from app.services.upload_service import (
    delete_file_from_s3,
    get_download_url,
    upload_file_to_s3,
)

logger = logging.getLogger(__name__)

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
    ignore_deleted: bool = True,
) -> Project:
    query = select(Project).where(
        Project.organization_id == organization_id,
        Project.id == project_id,
        Project.organization.has(Organization.users.contains(user)),
    )
    project = session.scalar(query)

    if ignore_deleted and project and project.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Project not found.',
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
        select(Project).where(
            Project.organization_id == organization.id,
            Project.deleted_at.is_(None),
        )
    ).all()

    project_list = []
    for project in projects:
        file_count = session.scalar(
            select(func.count()).where(File.project_id == project.id)
        )
        if project.organization_id:
            project_list.append(
                ProjectPublicList(
                    id=project.id,
                    name=project.name,
                    description=project.description,
                    organization_id=project.organization_id,
                    created_at=project.created_at,
                    file_count=file_count or 0,
                )
            )

    return {'projects': project_list}


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
    project.deleted_at = datetime.utcnow()
    session.commit()


@router.delete('/{project_id}/hard', status_code=HTTPStatus.NO_CONTENT)
async def hard_delete_project(
    organization_id: UUID,
    project_id: UUID,
    session: DbSession,
    user: CurrentUser,
):
    project = get_project(
        session, user, organization_id, project_id, ignore_deleted=False
    )

    # Delete files from S3
    for file in project.files:
        try:
            await delete_file_from_s3(file.path)
        except HTTPException as e:
            # Log the error but don't stop the deletion process
            logger.error(
                f'Failed to delete file {file.path} from S3: {str(e)}'
            )
        except Exception as e:
            # Log any other unexpected errors
            logger.error(
                f'Unexpected error deleting file {file.path} from S3: {str(e)}'
            )

    # Delete the project and all associated files from database
    session.delete(project)
    session.commit()


@router.post('/{project_id}/files', status_code=HTTPStatus.CREATED)
async def upload(  # noqa: PLR0913, PLR0917
    organization_id: UUID,
    project_id: UUID,
    user: CurrentUser,
    files: list[UploadFile],
    session: DbSession,
    background_tasks: BackgroundTasks,
):
    # Verify project exists and user has access
    _ = get_project(session, user, organization_id, project_id)

    # Upload files to S3 in parallel
    upload_tasks = [upload_file_to_s3(project_id, file) for file in files]
    results = await asyncio.gather(*upload_tasks)

    # Get download URLs for each file
    download_urls = [
        await get_download_url(result.path, result.original_filename)
        for result in results
    ]

    # Create file records in database
    db_files = []
    for result in results:
        db_file = File(  # type: ignore
            path=result.path,
            size=result.size,
            project_id=project_id,
            mime_type=result.mime_type,
            original_filename=result.original_filename,
        )
        db_files.append(db_file)
        session.add(db_file)

    session.commit()

    # Update results with database IDs
    for result, db_file in zip(results, db_files):
        result.id = db_file.id

    # Schedule processing of each file in the background
    for result, download_url in zip(results, download_urls):
        if result and result.id and result.mime_type == 'application/pdf':
            background_tasks.add_task(
                document_service.extract_text,
                download_url,
                result.id,
                session,
            )

    return results


@router.delete('/{project_id}/files', status_code=HTTPStatus.NO_CONTENT)
async def delete_file(
    organization_id: UUID,
    project_id: UUID,
    user: CurrentUser,
    session: DbSession,
    ids: list[UUID] = Query(alias='ids[]'),
):
    # Verify project exists and user has access
    _ = get_project(session, user, organization_id, project_id)

    if not ids:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='No file IDs provided.',
        )

    # Remove duplicates in ids
    ids = list(set(ids))

    # Find all file records in database
    db_files = (
        session.query(File)
        .filter(File.id.in_(ids), File.project_id == project_id)
        .all()
    )

    if not db_files:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='No files found in database',
        )

    # Delete files from S3 in parallel
    await asyncio.gather(*[
        delete_file_from_s3(file.path) for file in db_files
    ])

    # Delete the database records
    for db_file in db_files:
        session.delete(db_file)
    session.commit()

    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.get('/{project_id}/files/{file_id}', response_model=FileSchema)
async def read_file(
    organization_id: UUID,
    project_id: UUID,
    file_id: UUID,
    user: CurrentUser,
    session: DbSession,
):
    _ = get_project(session, user, organization_id, project_id)

    file = session.scalar(
        select(File).where(
            File.id == file_id,
            File.project_id == project_id,
        )
    )
    if not file:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='File not found.',
        )

    return file


@router.get('/{project_id}/files/{file_id}/download')
async def download_file(
    organization_id: UUID,
    project_id: UUID,
    file_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> dict[str, str]:
    _ = get_project(session, user, organization_id, project_id)

    file = session.scalar(
        select(File).where(
            File.id == file_id,
            File.project_id == project_id,
        )
    )
    if not file:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='File not found.',
        )

    download_url = await get_download_url(file.path, file.original_filename)

    return {'download_url': download_url}


@router.get(
    '/{project_id}/files/{file_id}/extract_bounding_boxes',
    response_model=ai_service.DetectedObjectListSchema,
)
async def extract_bounding_boxes(
    organization_id: UUID,
    project_id: UUID,
    file_id: UUID,
    user: CurrentUser,
    session: DbSession,
):
    _ = get_project(session, user, organization_id, project_id)

    preferences = {
        pref.key: pref.value
        for pref in session.scalars(
            select(Preference).where(
                Preference.key.in_(['system_prompt', 'assistant_prompt'])
            )
        ).all()
    }

    image_file = session.scalar(
        select(File).where(
            File.id == file_id,
            File.project_id == project_id,
        )
    )
    if not image_file:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='File not found.',
        )

    if not image_file.mime_type.startswith('image'):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='File is not an image.',
        )

    download_url = await get_download_url(
        image_file.path, image_file.original_filename
    )

    documents = session.scalars(
        select(File).where(
            File.project_id == project_id,
            File.mime_type == 'application/pdf',
            File.processed_at.isnot(None),
        )
    ).all()

    if not documents:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='No PDF documents found in project.',
        )

    document_contents = {
        document.original_filename: document.contents
        for document in documents
        if document.contents is not None
    }

    ai = ai_service.GeminiAiService()

    bounding_boxes = ai.extract_bounding_boxes(
        image_url=download_url,
        document_contents=document_contents,
        system_prompt=preferences['system_prompt'],
        assistant_prompt=preferences['assistant_prompt'],
    )

    # image_file.contents = str(bounding_boxes)
    image_file.contents = json.dumps(bounding_boxes)
    image_file.processed_at = datetime.now()
    session.commit()
    session.refresh(image_file)

    return bounding_boxes
