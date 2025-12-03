"""
NeuraCraft Azure AI Search setup script.

Usage:
    export AZURE_SEARCH_ENDPOINT="https://<your-service>.search.windows.net"
    export AZURE_SEARCH_ADMIN_KEY="<admin-key>"
    export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=..."
    python infrastructure/search_setup.py

The script is idempotent. It will create/update:
    - Search Index         (AZURE_SEARCH_INDEX_NAME, default: neura-files-v2)
    - Data Source          (AZURE_SEARCH_DATASOURCE_NAME, default: neura-files-ds)
    - Search Indexer       (AZURE_SEARCH_INDEXER_NAME, default: neura-files-idx)
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    FieldMapping,
    FieldMappingFunction,
    SearchFieldDataType,
    SearchIndexer,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SearchIndex,
    SearchableField,
    SimpleField,
    IndexingParameters
)


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Environment variable '{name}' is required.")
    return value


def get_admin_key() -> str:
    """Get admin key, fallback to API key if admin key is not set."""
    admin_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    if admin_key:
        return admin_key
    api_key = os.getenv("AZURE_SEARCH_API_KEY")
    if api_key:
        return api_key
    raise RuntimeError(
        "Either 'AZURE_SEARCH_ADMIN_KEY' or 'AZURE_SEARCH_API_KEY' is required."
    )


def build_index(index_name: str) -> SearchIndex:
    """Define the v2 index structure."""
    fields = [
        SimpleField(name="key", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="file_name", type=SearchFieldDataType.String, analyzer_name="ja.microsoft"),
        SimpleField(name="file_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="owner_id", type=SearchFieldDataType.String, filterable=True),
        SearchableField(
            name="application",
            type=SearchFieldDataType.String,
            analyzer_name="ja.microsoft",
            filterable=True,
            facetable=True,
        ),
        SearchableField(name="issue", type=SearchFieldDataType.String, analyzer_name="ja.microsoft"),
        SearchableField(
            name="ingredient",
            type=SearchFieldDataType.String,
            analyzer_name="ja.microsoft",
            filterable=True,
        ),
        SearchableField(
            name="customer",
            type=SearchFieldDataType.String,
            analyzer_name="ja.microsoft",
            filterable=True,
            facetable=True,
        ),
        SearchableField(
            name="trial_id",
            type=SearchFieldDataType.String,
            analyzer_name="ja.microsoft",
            filterable=True,
        ),
        SearchableField(
            name="author",
            type=SearchFieldDataType.String,
            analyzer_name="ja.microsoft",
            filterable=True,
        ),
        SimpleField(name="status", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="ja.microsoft"),
        SimpleField(name="blob_path", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, sortable=True, filterable=True),
        SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, sortable=True, filterable=True),
    ]
    return SearchIndex(name=index_name, fields=fields)


def ensure_index(client: SearchIndexClient, index_name: str) -> None:
    index = build_index(index_name)
    try:
        client.get_index(index_name)
        client.create_or_update_index(index)
        print(f"[SearchSetup] Updated index '{index_name}'.")
    except Exception:
        client.create_index(index)
        print(f"[SearchSetup] Created index '{index_name}'.")


def ensure_data_source(
    client: SearchIndexerClient,
    data_source_name: str,
    storage_connection_string: str,
    container_name: str,
) -> None:
    container = SearchIndexerDataContainer(name=container_name)
    data_source = SearchIndexerDataSourceConnection(
        name=data_source_name,
        type="azureblob",
        connection_string=storage_connection_string,
        container=container,
        description="NeuraCraft files container",
    )
    client.create_or_update_data_source_connection(data_source)
    print(f"[SearchSetup] Data source '{data_source_name}' ready.")


def ensure_indexer(
    client: SearchIndexerClient,
    *,
    indexer_name: str,
    data_source_name: str,
    target_index_name: str,
) -> None:
    base_mappings = [
        FieldMapping(
            source_field_name="metadata_storage_path",
            target_field_name="key",
            mapping_function=FieldMappingFunction(name="base64Encode"),
        ),
        FieldMapping(source_field_name="metadata_storage_path", target_field_name="blob_path"),
        FieldMapping(source_field_name="metadata_storage_name", target_field_name="file_name"),
        FieldMapping(source_field_name="metadata_storage_last_modified", target_field_name="updated_at"),
        FieldMapping(source_field_name="metadata_creation_time", target_field_name="created_at"),
    ]

    custom_metadata_mappings = [
        FieldMapping(source_field_name="x-ms-meta-application", target_field_name="application"),
        FieldMapping(source_field_name="x-ms-meta-issue", target_field_name="issue"),
        FieldMapping(source_field_name="x-ms-meta-ingredient", target_field_name="ingredient"),
        FieldMapping(source_field_name="x-ms-meta-customer", target_field_name="customer"),
        FieldMapping(source_field_name="x-ms-meta-trial_id", target_field_name="trial_id"),
        FieldMapping(source_field_name="x-ms-meta-author", target_field_name="author"),
        FieldMapping(source_field_name="x-ms-meta-status", target_field_name="status"),
        FieldMapping(source_field_name="x-ms-meta-file_id", target_field_name="file_id"),
        FieldMapping(source_field_name="x-ms-meta-owner_id", target_field_name="owner_id"),
    ]

    mapping_objects = base_mappings + custom_metadata_mappings

    indexer = SearchIndexer(
        name=indexer_name,
        data_source_name=data_source_name,
        target_index_name=target_index_name,
        description="Blob -> Search indexer for NeuraCraft files",
        field_mappings=mapping_objects,
        parameters={"configuration": {"dataToExtract": "contentAndMetadata", "parsingMode": "default"}},
    )

    client.create_or_update_indexer(indexer)
    print(f"[SearchSetup] Indexer '{indexer_name}' ready.")


def main():
    # Load environment variables from .env file
    load_dotenv()
    
    endpoint = env("AZURE_SEARCH_ENDPOINT")
    admin_key = get_admin_key()  # Falls back to AZURE_SEARCH_API_KEY if needed
    storage_connection_string = env("AZURE_STORAGE_CONNECTION_STRING")

    index_name = env("AZURE_SEARCH_INDEX_NAME", "neura-files-v2")
    data_source_name = env("AZURE_SEARCH_DATASOURCE_NAME", "neura-files-ds")
    indexer_name = env("AZURE_SEARCH_INDEXER_NAME", "neura-files-idx")
    container_name = env("AZURE_BLOB_FILES_CONTAINER", "files")

    credential = AzureKeyCredential(admin_key)
    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
    indexer_client = SearchIndexerClient(endpoint=endpoint, credential=credential)

    ensure_index(index_client, index_name)
    ensure_data_source(indexer_client, data_source_name, storage_connection_string, container_name)
    ensure_indexer(
        indexer_client,
        indexer_name=indexer_name,
        data_source_name=data_source_name,
        target_index_name=index_name,
    )


if __name__ == "__main__":
    main()

