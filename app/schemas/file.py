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
    # メタデータフィールド
    final_product: str
    issue: str
    ingredient: str
    customer: str
    trial_id: str
    author: str | None = None
    file_extension: str
    status: str = "active"


class FileRead(BaseModel):
    id: UUID
    owner_id: int
    original_filename: str
    blob_name: str
    content_type: str | None = None
    file_size: int | None = None
    azure_blob_url: str | None = None
    created_at: datetime
    # メタデータフィールド
    final_product: str
    issue: str
    ingredient: str
    customer: str
    trial_id: str
    author: str | None = None
    file_extension: str
    updated_at: datetime | None = None
    status: str

    class Config:
        from_attributes = True


class FileWithLink(BaseModel):
    """検索・詳細表示用: フロント仕様に合わせたレスポンス用スキーマ"""

    id: UUID
    file_name: str  # original_filename をマッピング
    final_product: str
    issue: str
    ingredient: str
    customer: str
    trial_id: str
    author: str | None = None
    status: str
    updated_at: datetime | None = None
    download_link: str | None = None


class FileSearchResponse(BaseModel):
    total_count: int
    files: list[FileWithLink]


class FileMetadataUpdate(BaseModel):
    """メタデータ更新用: 送られてきた項目のみ更新"""

    final_product: str | None = None
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


