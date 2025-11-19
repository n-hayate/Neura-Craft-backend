from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel


class FileBase(BaseModel):
    original_filename: str
    content_type: str | None = None
    file_size: int | None = None


class FileCreate(FileBase):
    owner_id: int
    blob_name: str | None = None


class FileRead(BaseModel):
    id: UUID
    owner_id: int
    original_filename: str
    blob_name: str
    content_type: str | None = None
    file_size: int | None = None
    azure_blob_url: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class FileIngestRequest(BaseModel):
    id: UUID = uuid4()
    owner_email: str
    blob_url: str
    original_filename: str


