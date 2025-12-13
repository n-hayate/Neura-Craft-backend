import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import requests

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SearchService:
    SEARCH_FIELDS = ["content", "original_name", "application", "customer", "trial_id", "ingredient", "author", "issue"]

    def __init__(self) -> None:
        endpoint = settings.azure_search_endpoint
        api_key = settings.azure_search_api_key
        index_name = settings.azure_search_index_name

        if not endpoint or not api_key or not index_name:
            logger.warning("Azure Search configuration missing. Search is disabled.")
            self.client = None
            return

        credential = AzureKeyCredential(api_key)
        logger.info(f"Initializing SearchService with index: {index_name}, endpoint: {endpoint}")
        self.client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

    def is_enabled(self) -> bool:
        return self.client is not None

    def _escape(self, value: str) -> str:
        return value.replace("'", "''")

    def search(
        self,
        *,
        query: str | None,
        application: str | None,
        issue: str | None,
        ingredient: str | None,
        customer: str | None,
        trial_id: str | None,
        author: str | None,
        owner_id: int | None,
        status: str | None = None,
        sort_by: str = "updated_at_desc",
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[int, List[Dict[str, Any]], Optional[int]]:
        """
        検索を実行し、結果とAzure Searchの処理時間を返す
        
        Returns:
            Tuple[total_count, files, search_time_ms]
            - total_count: 検索結果の総件数
            - files: 検索結果のファイルリスト
            - search_time_ms: Azure Searchの処理時間（ミリ秒）、取得できない場合はNone
        """
        endpoint = settings.azure_search_endpoint
        api_key = settings.azure_search_api_key
        index_name = settings.azure_search_index_name

        if not endpoint or not api_key or not index_name:
            raise RuntimeError("Azure Search client is not configured.")

        filter_clauses = []
        if status:
            filter_clauses.append(f"status eq '{self._escape(status)}'")

        def add_filter(field: str, value: Optional[str]) -> None:
            if value:
                # インデクサーがデコードするため、日本語のままフィルター可能
                filter_clauses.append(f"{field} eq '{self._escape(value)}'")

        # フィルタ可能なフィールドのみを使用（issueはfilterable=Falseのため除外）
        add_filter("application", application)
        # issueはfilterable=Falseのため、フィルタではなく検索クエリで使用
        add_filter("ingredient", ingredient)
        add_filter("customer", customer)
        add_filter("trial_id", trial_id)
        add_filter("author", author)

        if owner_id is not None:
            filter_clauses.append(f"owner_id eq '{owner_id}'")

        filter_expression = " and ".join(filter_clauses) if filter_clauses else None

        order_map = {
            "updated_at_desc": "updated_at desc",
            "updated_at_asc": "updated_at asc",
            "created_at_desc": "created_at desc",
            "created_at_asc": "created_at asc",
        }
        order_by = [order_map[sort_by]] if sort_by in order_map else None

        if page < 1:
            page = 1
        if page_size <= 0:
            page_size = 10
        skip = (page - 1) * page_size

        # インデクサーがデコードするため、日本語のまま検索可能
        # シノニム展開と前方一致の両方をサポートするため、(query|query*)の形式を使用
        # ワイルドカードが付いているとシノニム展開が無効になるため、クリーンな単語とワイルドカード付きをORで結合
        # issueはfilterable=Falseのため、検索クエリに含める
        search_terms = []
        if query and query.strip():
            q = query.strip()
            # 「ファミマ」なら -> (ファミマ|ファミマ*) となる
            # これで "ファミマ"(シノニム有効) OR "ファミマ*"(前方一致) の検索になります
            search_terms.append(f"({q}|{q}*)")
        if issue and issue.strip():
            i = issue.strip()
            # issueも同様に処理
            search_terms.append(f"({i}|{i}*)")
        
        if search_terms:
            # 複数の検索語を結合（AND検索）
            search_text = " ".join(search_terms)
        else:
            search_text = "*"

        logger.info(f"Searching index: {index_name} query: '{search_text}' filter: '{filter_expression}'")

        # REST APIでAzure Searchを呼び出す
        search_url = f"{endpoint}/indexes/{index_name}/docs/search"
        api_version = "2023-11-01"
        
        # リクエストボディを構築
        request_body: Dict[str, Any] = {
            "search": search_text,
            "searchFields": self.SEARCH_FIELDS,
            "top": page_size,
            "skip": skip,
            "includeTotalCount": True,
        }
        
        if filter_expression:
            request_body["filter"] = filter_expression
        
        if order_by:
            request_body["orderby"] = order_by

        # ヘッダーを設定
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key,
        }

        try:
            response = requests.post(
                f"{search_url}?api-version={api_version}",
                json=request_body,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            
            # レスポンスヘッダーからelapsed-timeを取得
            elapsed_time_ms: Optional[int] = None
            elapsed_time_str = response.headers.get("elapsed-time")
            if elapsed_time_str:
                try:
                    # elapsed-timeはミリ秒単位の文字列
                    elapsed_time_ms = int(float(elapsed_time_str))
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse elapsed-time header: {elapsed_time_str}")
            
            response_data = response.json()
            
            # 検索結果をパース
            files: List[Dict[str, Any]] = []
            total_count = response_data.get("@odata.count", 0)
            
            for doc in response_data.get("value", []):
                original_name = doc.get("original_name")
                file_name = doc.get("file_name")
                display_name = original_name or file_name

                files.append(
                    {
                        "id": doc.get("file_id") or doc.get("key"),
                        "file_name": file_name,
                        "original_name": original_name,
                        "display_name": display_name,
                        "application": doc.get("application"),
                        "issue": doc.get("issue"),
                        "ingredient": doc.get("ingredient"),
                        "customer": doc.get("customer"),
                        "trial_id": doc.get("trial_id"),
                        "author": doc.get("author"),
                        "status": doc.get("status"),
                        "updated_at": self._serialize_datetime(doc.get("updated_at")),
                        "blob_path": doc.get("blob_path"),
                    }
                )
            
            return total_count, files, elapsed_time_ms
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Azure Search REST API error: {e}")
            raise RuntimeError(f"Azure Search request failed: {str(e)}")

    def search_for_rag(
        self,
        *,
        query: str | None,
        application: str | None = None,
        issue: str | None = None,
        ingredient: str | None = None,
        customer: str | None = None,
        trial_id: str | None = None,
        author: str | None = None,
        owner_id: int | None = None,
        status: str | None = None,
        sort_by: str = "updated_at_desc",
        top: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        RAG（Retrieval-Augmented Generation）用の検索メソッド（PoC用）
        上位N件のcontentフィールドを含む結果を返す。
        
        注意: contentフィールドは大きいため、通常の検索APIでは使用しない。
        このメソッドはLLM分析などのPoC用途専用。
        """
        if not self.client:
            raise RuntimeError("Azure Search client is not configured.")

        filter_clauses = []
        if status:
            filter_clauses.append(f"status eq '{self._escape(status)}'")

        def add_filter(field: str, value: Optional[str]) -> None:
            if value:
                filter_clauses.append(f"{field} eq '{self._escape(value)}'")

        # フィルタ可能なフィールドのみを使用（issueはfilterable=Falseのため除外）
        add_filter("application", application)
        # issueはfilterable=Falseのため、フィルタではなく検索クエリで使用
        add_filter("ingredient", ingredient)
        add_filter("customer", customer)
        add_filter("trial_id", trial_id)
        add_filter("author", author)

        if owner_id is not None:
            filter_clauses.append(f"owner_id eq '{owner_id}'")

        filter_expression = " and ".join(filter_clauses) if filter_clauses else None

        order_map = {
            "updated_at_desc": "updated_at desc",
            "updated_at_asc": "updated_at asc",
            "created_at_desc": "created_at desc",
            "created_at_asc": "created_at asc",
        }
        order_by = [order_map[sort_by]] if sort_by in order_map else None

        # シノニム展開と前方一致の両方をサポートするため、(query|query*)の形式を使用
        # ワイルドカードが付いているとシノニム展開が無効になるため、クリーンな単語とワイルドカード付きをORで結合
        # issueはfilterable=Falseのため、検索クエリに含める
        search_terms = []
        if query and query.strip():
            q = query.strip()
            # 「ファミマ」なら -> (ファミマ|ファミマ*) となる
            # これで "ファミマ"(シノニム有効) OR "ファミマ*"(前方一致) の検索になります
            search_terms.append(f"({q}|{q}*)")
        if issue and issue.strip():
            i = issue.strip()
            # issueも同様に処理
            search_terms.append(f"({i}|{i}*)")
        
        if search_terms:
            # 複数の検索語を結合（AND検索）
            search_text = " ".join(search_terms)
        else:
            search_text = "*"

        logger.info(f"Searching for RAG: query='{search_text}' top={top}")

        results = self.client.search(
            search_text=search_text,
            search_fields=self.SEARCH_FIELDS,
            filter=filter_expression,
            order_by=order_by,
            top=top,
            include_total_count=False,
        )

        files: List[Dict[str, Any]] = []
        for doc in results:
            original_name = doc.get("original_name")
            file_name = doc.get("file_name")
            content = doc.get("content", "")

            files.append(
                {
                    "id": doc.get("file_id") or doc.get("key"),
                    "file_name": file_name,
                    "original_name": original_name,
                    "display_name": original_name or file_name,
                    "content": content,
                    "application": doc.get("application"),
                    "issue": doc.get("issue"),
                    "ingredient": doc.get("ingredient"),
                    "customer": doc.get("customer"),
                    "trial_id": doc.get("trial_id"),
                    "author": doc.get("author"),
                    "status": doc.get("status"),
                    "updated_at": self._serialize_datetime(doc.get("updated_at")),
                }
            )

        return files

    @staticmethod
    def _serialize_datetime(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        return value
