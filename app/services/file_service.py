import logging
from datetime import datetime
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.db.models.file import File
from app.db.models.file_download import FileDownload
from app.schemas.file import FileCreate, FileMetadataUpdate
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self, db: Session):
        self.db = db
        self.search_service = SearchService()

    def list_by_owner(
        self,
        owner_id: int | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[File]:
        query = self.db.query(File)
        if owner_id is not None:
            query = query.filter(File.owner_id == owner_id)
            
        return (
            query.order_by(File.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create(self, payload: FileCreate) -> File:
        file_obj = File(**payload.model_dump())
        self.db.add(file_obj)
        self.db.commit()
        self.db.refresh(file_obj)
        return file_obj


    def get(self, file_id: str) -> File:
        file_obj = self.db.query(File).filter(File.id == file_id).first()
        if not file_obj:
            # HTTPExceptionはAPI層でキャッチされる
            # ここではimportしていないのでstatus codeを直接使うか、呼び出し元でhandleする
            # existing implementation relied on fastapi import inside service which is slightly anti-pattern but I will follow existing imports if any
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return file_obj

    def delete(self, file_id: str) -> None:
        file_obj = self.get(file_id)
        self.db.delete(file_obj)
        self.db.commit()

    def search(
        self,
        *,
        owner_id: int | None = None,
        q: str | None = None,
        application: str | None = None,
        issue: str | None = None,
        ingredient: str | None = None,
        customer: str | None = None,
        trial_id: str | None = None,
        author: str | None = None,
        status: str | None = None,
        sort_by: str = "updated_at_desc",
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[int, List[dict]]:
        """Azure AI Search を利用した検索（SQL LIKE は廃止）"""

        if not self.search_service.is_enabled():
            raise RuntimeError("Azure Search is not configured.")

        return self.search_service.search(
            query=q,
            application=application,
            issue=issue,
            ingredient=ingredient,
            customer=customer,
            trial_id=trial_id,
            author=author,
            status=status,
            owner_id=owner_id,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )

    def update_metadata(self, file_id: str, payload: FileMetadataUpdate) -> File:
        """メタデータの部分更新"""
        file_obj = self.get(file_id)

        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(file_obj, field, value)

        # updated_at を明示的に更新（SQLite 対応）
        if hasattr(file_obj, "updated_at"):
            file_obj.updated_at = datetime.utcnow()

        self.db.add(file_obj)
        self.db.commit()
        self.db.refresh(file_obj)

        return file_obj

    def record_download(self, file_id: str, user_id: int) -> FileDownload:
        download = FileDownload(file_id=file_id, user_id=user_id)
        self.db.add(download)
        self.db.commit()
        self.db.refresh(download)
        return download

