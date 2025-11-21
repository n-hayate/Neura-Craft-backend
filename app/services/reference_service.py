from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.file_reference import FileReference
from app.schemas.reference import ReferenceCreate


class ReferenceService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, file_id: str, user_id: int, payload: ReferenceCreate) -> FileReference:
        """ファイル参照（Reference）を作成"""
        try:
            ref = FileReference(
                file_id=file_id,
                user_id=user_id,
                trial_id=payload.trial_id,
            )
            self.db.add(ref)
            self.db.commit()
            self.db.refresh(ref)
            return ref
        except IntegrityError:
            self.db.rollback()
            # 既に存在する場合は既存のものを返すか、エラーにする
            # 要件: "Handle IntegrityError gracefully and return 409 or 200 OK"
            # ここでは、既に存在する場合は409 Conflictを返す（クライアント側でハンドリング可能にする）
            # もしくは、既存レコードを取得して返す（冪等性確保）
            
            existing = self.db.query(FileReference).filter(
                FileReference.file_id == file_id,
                FileReference.user_id == user_id,
                FileReference.trial_id == payload.trial_id
            ).first()
            
            if existing:
                return existing
                
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reference already exists for this user and trial_id"
            )

