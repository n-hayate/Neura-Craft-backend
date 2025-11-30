import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
    ComplexField,
    CorsOptions,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SearchService:
    def __init__(self):
        self.endpoint = settings.azure_search_endpoint
        self.api_key = settings.azure_search_api_key
        self.index_name = settings.azure_search_index_name
        self.client: Optional[SearchClient] = None

        if self.endpoint and self.api_key:
            try:
                credential = AzureKeyCredential(self.api_key)
                self.client = SearchClient(
                    endpoint=self.endpoint,
                    index_name=self.index_name,
                    credential=credential,
                )
            except Exception as e:
                logger.error(f"Failed to initialize Azure Search Client: {e}")
        else:
            logger.warning("Azure Search credentials not provided. Search service disabled.")

    def _is_available(self) -> bool:
        return self.client is not None

    def create_index_if_not_exists(self):
        """インデックスが存在しない場合に作成する（初期化用）"""
        if not self.endpoint or not self.api_key:
            logger.warning("Cannot create index: Credentials missing.")
            return

        credential = AzureKeyCredential(self.api_key)
        index_client = SearchIndexClient(endpoint=self.endpoint, credential=credential)

        try:
            index_client.get_index(self.index_name)
            logger.info(f"Index '{self.index_name}' already exists.")
        except ResourceNotFoundError:
            logger.info(f"Creating index '{self.index_name}'...")
            
            # インデックス定義
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="file_name", type=SearchFieldDataType.String, analyzer_name="ja.microsoft"),
                SearchableField(name="final_product", type=SearchFieldDataType.String, filterable=True, analyzer_name="ja.microsoft"),
                SearchableField(name="issue", type=SearchFieldDataType.String, filterable=True, analyzer_name="ja.microsoft"),
                SearchableField(name="ingredient", type=SearchFieldDataType.String, filterable=True, analyzer_name="ja.microsoft"),
                SearchableField(name="customer", type=SearchFieldDataType.String, filterable=True, analyzer_name="ja.microsoft"),
                SearchableField(name="trial_id", type=SearchFieldDataType.String, filterable=True, sortable=True),
                SearchableField(name="author", type=SearchFieldDataType.String, filterable=True, analyzer_name="ja.microsoft"),
                SimpleField(name="status", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SimpleField(name="owner_id", type=SearchFieldDataType.Int32, filterable=True),
                SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="ja.microsoft"),
                SimpleField(name="download_link", type=SearchFieldDataType.String),
            ]
            
            cors_options = CorsOptions(allowed_origins=["*"], max_age_in_seconds=60)
            index = SearchIndex(name=self.index_name, fields=fields, cors_options=cors_options)
            
            index_client.create_index(index)
            logger.info(f"Index '{self.index_name}' created successfully.")

    def upsert_document(self, file_obj: Any):
        """ドキュメントを追加または更新"""
        if not self._is_available():
            return

        # メタデータを結合して content フィールドに入れる（全文検索用）
        content_parts = [
            file_obj.original_filename,
            file_obj.final_product,
            file_obj.issue,
            file_obj.ingredient,
            file_obj.customer,
            file_obj.trial_id,
            file_obj.author or "",
        ]
        content = " ".join([s for s in content_parts if s])

        doc = {
            "id": str(file_obj.id),
            "file_name": file_obj.original_filename,
            "final_product": file_obj.final_product,
            "issue": file_obj.issue,
            "ingredient": file_obj.ingredient,
            "customer": file_obj.customer,
            "trial_id": file_obj.trial_id,
            "author": file_obj.author,
            "status": file_obj.status,
            "updated_at": file_obj.updated_at.isoformat() if file_obj.updated_at else None,
            "created_at": file_obj.created_at.isoformat() if file_obj.created_at else None,
            "owner_id": int(file_obj.owner_id),
            "content": content,
            "download_link": file_obj.azure_blob_url or "",
        }

        try:
            self.client.upload_documents(documents=[doc])
            logger.info(f"Indexed document {file_obj.id}")
        except Exception as e:
            logger.error(f"Failed to index document {file_obj.id}: {e}")

    def delete_document(self, file_id: str):
        """ドキュメントを削除"""
        if not self._is_available():
            return

        try:
            self.client.delete_documents(documents=[{"id": file_id}])
            logger.info(f"Deleted document {file_id} from index")
        except Exception as e:
            logger.error(f"Failed to delete document {file_id}: {e}")

    def search(
        self,
        q: Optional[str] = None,
        filter_params: Optional[Dict[str, str]] = None,
        owner_id: Optional[int] = None,
        sort_by: str = "updated_at_desc",
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """検索を実行"""
        if not self._is_available():
            raise Exception("Azure Search is not available")

        # フィルタ構築
        filter_clauses = []
        
        if owner_id is not None:
            filter_clauses.append(f"owner_id eq {owner_id}")

        if filter_params:
            for field, value in filter_params.items():
                if value:
                    # スペース区切りでAND検索
                    keywords = value.replace("　", " ").split()
                    field_conditions = []
                    for word in keywords:
                        # 部分一致的なフィルタ（AzureSearchではcontainはコスト高いが、一旦searchを使う手もある）
                        # ここでは要件に従い、絞り込みフィールドはフィルタとして扱うが、
                        # 日本語の部分一致を期待する場合は search クエリに混ぜるのがベター。
                        # ただし、search クエリに混ぜるとスコア順になる。
                        # 今回は設計通り、searchable なフィールドに対して search パラメータで絞り込むアプローチと
                        # filter パラメータで絞り込むアプローチを使い分ける。
                        # しかし filter での部分一致は難しいので、search クエリに追加する方針にするのが現実的。
                        pass
        
        # 設計修正:
        # Azure AI Search では $filter での部分一致 (search.ismatch) が強力。
        # 例: search.ismatch('text', 'field')
        
        search_text = q if q else "*"
        
        # フィルタ構築 (OData)
        # final_product 等の指定がある場合、それを filter に追加する形にする
        if filter_params:
            for field, value in filter_params.items():
                if value:
                    keywords = value.replace("　", " ").split()
                    # AND条件で結合
                    for kw in keywords:
                        # エスケープ処理は簡易的に行う（シングルクォート等）
                        safe_kw = kw.replace("'", "''")
                        # search.ismatchを使って特定のフィールドに対する検索を行う
                        # search.ismatch('keyword', 'field', 'full', 'any')
                        filter_clauses.append(f"search.ismatch('{safe_kw}', '{field}')")

        filter_expression = " and ".join(filter_clauses) if filter_clauses else None

        # ソート
        order_by = []
        if sort_by == "updated_at_desc":
            order_by.append("updated_at desc")
        elif sort_by == "updated_at_asc":
            order_by.append("updated_at asc")
        elif sort_by == "created_at_desc":
            order_by.append("created_at desc")
        elif sort_by == "created_at_asc":
            order_by.append("created_at asc")
        
        # ページネーション
        skip = (page - 1) * page_size

        try:
            results = self.client.search(
                search_text=search_text,
                filter=filter_expression,
                order_by=order_by,
                skip=skip,
                top=page_size,
                include_total_count=True,
            )
            
            files = []
            for res in results:
                # datetime文字列をdatetimeオブジェクトに戻す必要があれば変換
                # JSONレスポンスにするので文字列のままでもよいが、Pydanticがパースする
                files.append({
                    "id": res["id"],
                    "file_name": res["file_name"],
                    "final_product": res.get("final_product", ""),
                    "issue": res.get("issue", ""),
                    "ingredient": res.get("ingredient", ""),
                    "customer": res.get("customer", ""),
                    "trial_id": res.get("trial_id", ""),
                    "author": res.get("author", ""),
                    "status": res.get("status", ""),
                    "updated_at": res.get("updated_at"), # 文字列 or datetime
                    "download_link": res.get("download_link"),
                })
            
            return {
                "total_count": results.get_count(),
                "files": files
            }
            
        except Exception as e:
            logger.error(f"Search query failed: {e}")
            raise e

