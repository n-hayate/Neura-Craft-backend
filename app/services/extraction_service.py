from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.file_extraction import FileExtraction


def upsert_extraction(db: Session, file_id: str, data: dict) -> None:
    row = db.query(FileExtraction).filter(FileExtraction.file_id == file_id).one_or_none()
    if row is None:
        row = FileExtraction(file_id=file_id, data=data)
        db.add(row)
    else:
        row.data = data
    db.commit()


def get_extraction(db: Session, file_id: str) -> dict | None:
    row = db.query(FileExtraction).filter(FileExtraction.file_id == file_id).one_or_none()
    return row.data if row else None



