import logging
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.utils import normalize_tags
from app.db.models.file import File
from app.schemas.file import FileCreate, FileMetadataUpdate
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)
settings = get_settings()


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

    def create(self, payload: FileCreate, blob_name: str, blob_url: str | None = None) -> File:
        file_obj = File(
            owner_id=payload.owner_id,
            original_filename=payload.original_filename,
            content_type=payload.content_type,
            file_size=payload.file_size,
            blob_name=blob_name,
            azure_blob_url=blob_url,
            final_product=normalize_tags(payload.final_product),
            issue=normalize_tags(payload.issue),
            ingredient=normalize_tags(payload.ingredient),
            customer=normalize_tags(payload.customer),
            trial_id=payload.trial_id,
            author=payload.author,
            file_extension=payload.file_extension,
            status=payload.status,
            is_preview_hidden=payload.is_preview_hidden,
        )
        self.db.add(file_obj)
        self.db.commit()
        self.db.refresh(file_obj)
        
        # インデックス更新
        try:
            self.search_service.upsert_document(file_obj)
        except Exception as e:
            logger.error(f"Failed to index file on create: {e}")

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
        
        # インデックス削除
        try:
            self.search_service.delete_document(file_id)
        except Exception as e:
            logger.error(f"Failed to delete document from index: {e}")

    def search(
        self,
        *,
        owner_id: int | None = None,
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
        """ファイル検索（オーナー単位または全体）- AND検索 & 横断検索対応"""

        # Azure AI Search が有効な場合はそちらを優先
        if settings.search_backend == "azure":
            try:
                filter_params = {
                    "final_product": final_product,
                    "issue": issue,
                    "ingredient": ingredient,
                    "customer": customer,
                    "trial_id": trial_id,
                    "author": author,
                }
                
                search_result = self.search_service.search(
                    q=q,
                    filter_params=filter_params,
                    owner_id=owner_id,
                    sort_by=sort_by,
                    page=page,
                    page_size=page_size,
                )
                
                # 結果をFileモデル（非永続化オブジェクト）にマッピング
                files = []
                for doc in search_result["files"]:
                    # updated_atの変換
                    updated_at_val = doc.get("updated_at")
                    if isinstance(updated_at_val, str):
                        try:
                            updated_at_val = datetime.fromisoformat(updated_at_val.replace('Z', '+00:00'))
                        except ValueError:
                            updated_at_val = None
                            
                    f = File(
                        id=doc["id"],
                        original_filename=doc["file_name"],
                        final_product=doc["final_product"],
                        issue=doc["issue"],
                        ingredient=doc["ingredient"],
                        customer=doc["customer"],
                        trial_id=doc["trial_id"],
                        author=doc["author"],
                        status=doc["status"],
                        updated_at=updated_at_val,
                        azure_blob_url=doc.get("download_link"),
                    )
                    files.append(f)
                
                return search_result["total_count"], files

            except Exception as e:
                logger.error(f"Azure Search failed, falling back to SQL: {e}")
                # フォールバックしてSQL検索を実行

        # === 以下、既存のSQL検索ロジック ===
        query = self.db.query(File)
        
        # owner_idが指定されている場合のみ絞り込む
        if owner_id is not None:
            query = query.filter(File.owner_id == owner_id)

        # 1. フリーテキスト (q) の横断検索 & AND検索
        if q:
            keywords = q.replace('　', ' ').split()
            for word in keywords:
                like_word = f"%{word}%"
                # 各キーワードについて、「どれかのフィールドに含まれていればOK」
                query = query.filter(
                    or_(
                        File.original_filename.ilike(like_word),
                        File.final_product.ilike(like_word),
                        File.issue.ilike(like_word),
                        File.ingredient.ilike(like_word),
                        File.customer.ilike(like_word),
                        File.trial_id.ilike(like_word),
                        File.author.ilike(like_word),
                    )
                )

        # 2. フィールドごとの絞り込み (スペース区切りでAND検索)
        def apply_like(column, value: str | None):
            nonlocal query
            if value:
                # スペース区切りで分割してAND検索
                keywords = value.replace('　', ' ').split()
                for word in keywords:
                    query = query.filter(column.ilike(f"%{word}%"))

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
            # 正規化対象フィールドの場合は正規化を実施
            if field in ["final_product", "issue", "ingredient", "customer"]:
                value = normalize_tags(value)
            setattr(file_obj, field, value)

        # updated_at を明示的に更新（SQLite 対応）
        if hasattr(file_obj, "updated_at"):
            file_obj.updated_at = datetime.utcnow()

        self.db.add(file_obj)
        self.db.commit()
        self.db.refresh(file_obj)
        
        # インデックス更新
        try:
            self.search_service.upsert_document(file_obj)
        except Exception as e:
            logger.error(f"Failed to update index on metadata update: {e}")

        return file_obj
