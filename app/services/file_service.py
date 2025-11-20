from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.file import File
from app.schemas.file import FileCreate


class FileService:
    def __init__(self, db: Session):
        self.db = db

    def list_by_owner(self, owner_id: int, limit: int = 50, offset: int = 0) -> List[File]:
        return (
            self.db.query(File)
            .filter(File.owner_id == owner_id)
            .order_by(File.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create(self, payload: FileCreate, blob_name: str, blob_url: str | None = None) -> File:
        file_obj = File(
            owner_id=payload.owner_id,
            original_filename=payload.original_filename,
            content_type=payload.content_type,
            file_size=payload.file_size,
            blob_name=blob_name,
            azure_blob_url=blob_url,
            final_product=payload.final_product,
            issue=payload.issue,
            ingredient=payload.ingredient,
            customer=payload.customer,
            trial_id=payload.trial_id,
            author=payload.author,
            file_extension=payload.file_extension,
            status=payload.status,
        )
        self.db.add(file_obj)
        self.db.commit()
        self.db.refresh(file_obj)
        return file_obj

    def get(self, file_id: str) -> File:
        file_obj = self.db.query(File).filter(File.id == file_id).first()
        if not file_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return file_obj

    def delete(self, file_id: str) -> None:
        file_obj = self.get(file_id)
        self.db.delete(file_obj)
        self.db.commit()


