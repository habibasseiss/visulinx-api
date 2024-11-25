import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Table, func
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship

table_registry = registry()


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
    name: Mapped[str] = mapped_column(unique=True)
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
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
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


@table_registry.mapped_as_dataclass
class File:
    __tablename__ = 'files'

    id: Mapped[uuid.UUID] = mapped_column(
        init=False, primary_key=True, default_factory=uuid.uuid4
    )
    path: Mapped[str] = mapped_column(init=True)
    size: Mapped[int] = mapped_column(init=True)
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
