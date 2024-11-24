import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, ForeignKey, Table, func
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    registry,
    relationship,
)

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


class TodoState(str, Enum):
    draft = 'draft'
    todo = 'todo'
    doing = 'doing'
    done = 'done'
    trash = 'trash'


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
    todos: Mapped[list['Todo']] = relationship(
        init=False, back_populates='user', cascade='all, delete-orphan'
    )
    organizations: Mapped[list['Organization']] = relationship(
        'Organization',
        secondary=organization_user_association,
        back_populates='users',
        default_factory=list,
    )


@table_registry.mapped_as_dataclass
class Todo:
    __tablename__ = 'todos'

    id: Mapped[uuid.UUID] = mapped_column(
        init=False, primary_key=True, default_factory=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(init=True)
    description: Mapped[str] = mapped_column(init=True)
    state: Mapped[TodoState] = mapped_column(init=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), init=True)
    user: Mapped[User] = relationship(init=False, back_populates='todos')


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
        ForeignKey('organizations.id'), default=None
    )

    # Many-to-one relationship
    organization: Mapped[Organization | None] = relationship(
        'Organization', back_populates='projects', default=None
    )
