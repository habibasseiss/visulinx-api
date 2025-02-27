import asyncio
import logging
import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Table, Text, event, func
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
    # Create a coroutine that deletes all files
    async def delete_all_files():
        for file in target.files:
            try:
                await delete_file_from_s3(file.path)
            except Exception as e:
                # Log any other unexpected errors
                logger.error(
                    f'Failed to delete file {file.path} from S3: {str(e)}'
                )

    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()

        # If we're already in an event loop, run the coroutine directly
        if loop.is_running():
            loop.create_task(delete_all_files())
        else:
            # If we're not in an event loop, run it to completion
            loop.run_until_complete(delete_all_files())
    except Exception as e:
        logger.error(f'Failed to delete files from S3: {str(e)}')


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
    contents: Mapped[str | None] = mapped_column(
        Text, init=False, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        init=False, nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('projects.id'),
        init=True,
    )
    project: Mapped[Project] = relationship(
        init=False,
        back_populates='files',
    )


@table_registry.mapped_as_dataclass
class Preference:
    __tablename__ = 'preferences'

    key: Mapped[str] = mapped_column(init=True, primary_key=True)
    value: Mapped[str] = mapped_column(init=True)
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )
