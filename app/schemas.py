from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import TodoState


class Message(BaseModel):
    message: str


class OrganizationSchema(BaseModel):
    name: str


class OrganizationPublic(BaseModel):
    id: UUID
    name: str
    model_config = ConfigDict(from_attributes=True)


class OrganizationList(BaseModel):
    organizations: list[OrganizationPublic]


class UserSchema(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    organizations: list[OrganizationPublic]
    model_config = ConfigDict(from_attributes=True)


class UserList(BaseModel):
    users: list[UserPublic]


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: EmailStr | None = None


class TodoSchema(BaseModel):
    title: str
    description: str
    state: TodoState


class TodoPublic(BaseModel):
    id: UUID
    title: str
    description: str
    state: TodoState


class TodoList(BaseModel):
    todos: list[TodoPublic]


class TodoUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    state: TodoState | None = None


class ProjectSchema(BaseModel):
    name: str
    description: str


class ProjectPublic(BaseModel):
    id: UUID
    name: str
    description: str
    organization_id: UUID
    model_config = ConfigDict(from_attributes=True)


class ProjectList(BaseModel):
    projects: list[ProjectPublic]
