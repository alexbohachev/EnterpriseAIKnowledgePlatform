"""Stable external DTOs: never return ORM models or internal secrets directly."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["admin", "reader"] = "reader"


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class MemberCreate(BaseModel):
    user_id: str


class UploadResponse(BaseModel):
    document_id: str
    version_id: str
    job_id: str
    status: str


class DocumentResponse(BaseModel):
    id: str
    title: str
    owner_id: str
    classification: str
    acl_epoch: int
    active_index_run_id: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class JobResponse(BaseModel):
    id: str
    version_id: str
    status: str
    attempts: int
    failure_code: str | None
    index_run_id: str | None
    model_config = ConfigDict(from_attributes=True)


class ACLChange(BaseModel):
    action: Literal["grant", "revoke"]
    principal_type: Literal["user", "group"]
    principal_id: str
    permission: Literal["read", "write", "admin"] = "read"


class ACLChangeResponse(BaseModel):
    document_id: str
    acl_epoch: int
    changed: bool


class QueryInput(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


class QueryCitation(BaseModel):
    source: str
    document_id: str
    chunk_id: str
    page_number: int


class QueryResponse(BaseModel):
    answer: str
    citations: list[QueryCitation]
    retrieval_count: int
