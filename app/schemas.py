from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class Message(BaseModel):
    message: str


class FileSchema(BaseModel):
    id: UUID | None = None
    path: str
    size: int
    mime_type: str
    original_filename: str


class FilePublic(BaseModel):
    id: UUID
    path: str
    size: int
    mime_type: str
    original_filename: str
    model_config = ConfigDict(from_attributes=True)


class ProjectSchema(BaseModel):
    name: str
    description: str


class ProjectPublic(BaseModel):
    id: UUID
    name: str
    description: str
    organization_id: UUID
    files: list[FilePublic] = []
    model_config = ConfigDict(from_attributes=True)


class ProjectList(BaseModel):
    projects: list[ProjectPublic]


class OrganizationSchema(BaseModel):
    name: str


class OrganizationPublic(BaseModel):
    id: UUID
    name: str
    projects: list[ProjectPublic]
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
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    email: EmailStr | None = None
