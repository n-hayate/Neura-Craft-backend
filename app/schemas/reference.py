from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReferenceCreate(BaseModel):
    trial_id: str = Field(..., max_length=50, description="参照するプロジェクトのTrial ID")


class ReferenceRead(BaseModel):
    id: UUID
    file_id: UUID
    trial_id: str
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

