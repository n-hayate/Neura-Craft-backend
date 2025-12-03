"""
Manual trigger for Azure Search indexer.

Usage:
    export AZURE_SEARCH_ENDPOINT="https://<service>.search.windows.net"
    export AZURE_SEARCH_ADMIN_KEY="<admin-key>"
    export AZURE_SEARCH_INDEXER_NAME="neura-files-idx"
    python scripts/reindex_search.py
"""

import logging
import os
import time

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexerClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Environment variable '{name}' is required.")
    return value


def run_indexer() -> None:
    endpoint = env("AZURE_SEARCH_ENDPOINT")
    admin_key = env("AZURE_SEARCH_ADMIN_KEY")
    indexer_name = env("AZURE_SEARCH_INDEXER_NAME", "neura-files-idx")

    client = SearchIndexerClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))
    logger.info("Triggering indexer '%s'...", indexer_name)
    client.run_indexer(indexer_name)
    logger.info("Indexer run request sent.")


if __name__ == "__main__":
    start = time.time()
    run_indexer()
    logger.info("Elapsed: %.2fs", time.time() - start)