from datetime import datetime
from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.db.models.file import File
from app.schemas.file import FileCreate, FileMetadataUpdate


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

    def increment_download_count(self, file_id: str) -> File:
        """ダウンロード数をアトミックにインクリメント"""
        # 存在確認
        self.get(file_id)
        
        self.db.query(File).filter(File.id == file_id).update(
            {"download_count": File.download_count + 1},
            synchronize_session=False
        )
        self.db.commit()
        return self.get(file_id)


    def get(self, file_id: str) -> File:
        file_obj = self.db.query(File).filter(File.id == file_id).first()
        if not file_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return file_obj

    def delete(self, file_id: str) -> None:
        file_obj = self.get(file_id)
        self.db.delete(file_obj)
        self.db.commit()

    def search(
        self,
        *,
        owner_id: int,
        q: str | None = None,
        final_product: str | None = None,
        issue: str | None = None,
        ingredient: str | None = None,
        customer: str | None = None,
        trial_id: str | None = None,
        author: str | None = None,
        sort_by: str = "updated_at_desc",
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[int, List[File]]:
        """ファイル検索（オーナー単位）"""

        query = self.db.query(File).filter(File.owner_id == owner_id)

        # フリーテキスト（ファイル名）検索
        if q:
            like = f"%{q}%"
            query = query.filter(File.original_filename.ilike(like))

        # メタデータでの絞り込み
        def apply_like(column, value: str | None):
            nonlocal query
            if value:
                query = query.filter(column.ilike(f"%{value}%"))

        apply_like(File.final_product, final_product)
        apply_like(File.issue, issue)
        apply_like(File.ingredient, ingredient)
        apply_like(File.customer, customer)
        apply_like(File.trial_id, trial_id)
        apply_like(File.author, author)

        total_count = query.count()

        # ソート
        sort_map = {
            "updated_at_desc": desc(File.updated_at),
            "updated_at_asc": asc(File.updated_at),
            "final_product_asc": asc(File.final_product),
            "final_product_desc": desc(File.final_product),
            "created_at_desc": desc(File.created_at),
            "created_at_asc": asc(File.created_at),
        }
        order_clause = sort_map.get(sort_by, desc(File.updated_at))
        query = query.order_by(order_clause)

        # ページネーション
        if page < 1:
            page = 1
        if page_size <= 0:
            page_size = 10
        offset = (page - 1) * page_size

        files = query.offset(offset).limit(page_size).all()
        return total_count, files

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

    def increment_download_count(self, file_id: str) -> File:
        """ダウンロード数をアトミックにインクリメント"""
        # 存在確認
        self.get(file_id)
        
        self.db.query(File).filter(File.id == file_id).update(
            {"download_count": File.download_count + 1},
            synchronize_session=False
        )
        self.db.commit()
        return self.get(file_id)

