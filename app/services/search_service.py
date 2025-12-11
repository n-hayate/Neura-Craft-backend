import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

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
    ) -> Tuple[int, List[Dict[str, Any]]]:
        if not self.client:
            raise RuntimeError("Azure Search client is not configured.")

        filter_clauses = []
        if status:
            filter_clauses.append(f"status eq '{self._escape(status)}'")

        def add_filter(field: str, value: Optional[str]) -> None:
            if value:
                # インデクサーがデコードするため、日本語のままフィルター可能
                filter_clauses.append(f"{field} eq '{self._escape(value)}'")

        add_filter("application", application)
        add_filter("issue", issue)
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
        # 前方一致検索のため、queryが存在する場合は末尾に*を自動で追加
        if query and query.strip():
            # 既に末尾に*が含まれている場合は追加しない
            search_text = query if query.rstrip().endswith("*") else query.rstrip() + "*"
        else:
            search_text = "*"

        logger.info(f"Searching index: {self.client._index_name} query: '{search_text}' filter: '{filter_expression}'")

        results = self.client.search(
            search_text=search_text,
            search_fields=self.SEARCH_FIELDS,
            filter=filter_expression,
            order_by=order_by,
            skip=skip,
            top=page_size,
            include_total_count=True,
        )

        files: List[Dict[str, Any]] = []
        for doc in results:
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

        total_count = results.get_count() or 0
        return total_count, files

    @staticmethod
    def _serialize_datetime(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        return value
