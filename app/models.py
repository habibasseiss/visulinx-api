import asyncio
import logging
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import Column, ForeignKey, Table, event, func
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship

from app.services.upload_service import delete_file_from_s3

table_registry = registry()

logger = logging.getLogger(__name__)

# Association table for many-to-many relationship: Organization and User
organization_user_association = Table(
    'organization_user',
    table_registry.metadata,
    Column(
        'organization_id',
        ForeignKey('organizations.id'),
        primary_key=True,
    ),
    Column(
        'user_id',
        ForeignKey('users.id'),
        primary_key=True,
    ),
)


@table_registry.mapped_as_dataclass
class User:
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(
        init=False, primary_key=True, default_factory=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    organizations: Mapped[list['Organization']] = relationship(
        'Organization',
        secondary=organization_user_association,
        back_populates='users',
        default_factory=list,
    )


@table_registry.mapped_as_dataclass
class Organization:
    __tablename__ = 'organizations'

    id: Mapped[uuid.UUID] = mapped_column(
        init=False, primary_key=True, default_factory=uuid.uuid4
    )
    name: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )

    # Many-to-many relationship with User
    users: Mapped[list[User]] = relationship(
        'User',
        secondary=organization_user_association,
        back_populates='organizations',
        default_factory=list,
    )

    # One-to-many relationship with Project
    projects: Mapped[list['Project']] = relationship(
        'Project',
        back_populates='organization',
        cascade='all, delete-orphan',
        default_factory=list,
    )


@table_registry.mapped_as_dataclass
class Project:
    __tablename__ = 'projects'

    id: Mapped[uuid.UUID] = mapped_column(
        init=False, primary_key=True, default_factory=uuid.uuid4
    )
    name: Mapped[str] = mapped_column()
    description: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        init=False, nullable=True, default=None
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey('organizations.id'), nullable=False
    )
    # Many-to-one relationship
    organization: Mapped[Organization | None] = relationship(
        'Organization', back_populates='projects'
    )
    files: Mapped[list['File']] = relationship(
        'File',
        back_populates='project',
        cascade='all, delete-orphan',
        default_factory=list,
    )


# Set up event listener for Project deletion
@event.listens_for(Project, 'before_delete')
def delete_project_files_from_s3(mapper, connection, target: Project):
    # We need to run the async function in a new event loop
    for file in target.files:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(delete_file_from_s3(file.path))
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
        finally:
            loop.close()


@table_registry.mapped_as_dataclass
class File:
    __tablename__ = 'files'

    id: Mapped[uuid.UUID] = mapped_column(
        init=False, primary_key=True, default_factory=uuid.uuid4
    )
    path: Mapped[str] = mapped_column(init=True)
    size: Mapped[int] = mapped_column(init=True)
    mime_type: Mapped[str] = mapped_column(init=True)
    original_filename: Mapped[str] = mapped_column(init=True)
    contents: Mapped[str | None] = mapped_column(init=False, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('projects.id'),
        init=True,
    )
    project: Mapped[Project] = relationship(
        init=False,
        back_populates='files',
    )
