from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel


class FileCreate(BaseModel):
    id: str
    blob_path: str
    original_name: str
    application: str | None = None
    issue: str | None = None
    ingredient: str | None = None
    customer: str | None = None
    trial_id: str | None = None
    author: str | None = None
    status: str = "active"
    owner_id: int | None = None


class FileRead(BaseModel):
    id: UUID
    owner_id: int | None = None
    original_name: str
    blob_path: str
    created_at: datetime
    updated_at: datetime
    application: str | None = None
    issue: str | None = None
    ingredient: str | None = None
    customer: str | None = None
    trial_id: str | None = None
    author: str | None = None
    status: str

    class Config:
        from_attributes = True


class FileWithLink(BaseModel):
    """検索・詳細表示用: フロント仕様に合わせたレスポンス用スキーマ"""

    id: str  # UUID or Base64 key
    file_name: str
    application: str | None = None
    issue: str | None = None
    ingredient: str | None = None
    customer: str | None = None
    trial_id: str | None = None
    author: str | None = None
    status: str | None = None
    updated_at: datetime | str | None = None  # datetime or ISO string
    download_link: str | None = None


class FileSearchResponse(BaseModel):
    total_count: int
    files: list[FileWithLink]


class FileMetadataUpdate(BaseModel):
    """メタデータ更新用: 送られてきた項目のみ更新"""

    application: str | None = None
    issue: str | None = None
    ingredient: str | None = None
    customer: str | None = None
    trial_id: str | None = None
    author: str | None = None
    status: str | None = None


class FileIngestRequest(BaseModel):
    id: UUID = uuid4()
    owner_email: str
    blob_url: str
    original_filename: str


