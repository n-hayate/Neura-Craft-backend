import asyncio
import os
import shutil
import sys
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient

from app.core.config import get_settings
from app.services.blob_service import BlobService

# Configure basic logging to stdout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

settings = get_settings()

async def cleanup_blobs():
    print("Cleaning up blobs...", flush=True)
    service = BlobService()
    if service.use_local_storage:
        path = service.storage_path
        print(f"Local storage path: {path}", flush=True)
        if path.exists():
            for item in path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        print("Local blobs cleaned.", flush=True)
    else:
        print("Connecting to Azure Blob Storage...", flush=True)
        async with service:
            container_client = service._get_async_client().get_container_client(service.container_name)
            if await container_client.exists():
                print(f"Deleting blobs in container '{service.container_name}'...", flush=True)
                async for blob in container_client.list_blobs():
                    await container_client.delete_blob(blob.name)
                    print(f"Deleted blob: {blob.name}", flush=True)
                print("Azure blobs cleaned.", flush=True)
            else:
                print("Blob container does not exist.", flush=True)

def cleanup_search():
    print("Cleaning up search resources...", flush=True)
    endpoint = settings.azure_search_endpoint
    key = settings.azure_search_api_key or os.getenv("AZURE_SEARCH_ADMIN_KEY") or os.getenv("AZURE_SEARCH_API_KEY")
    
    if not endpoint or not key:
        print("Azure Search credentials not found. Skipping search cleanup.", flush=True)
        return

    print(f"Endpoint: {endpoint}", flush=True)
    
    credential = AzureKeyCredential(key)
    indexer_client = SearchIndexerClient(endpoint=endpoint, credential=credential)
    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
    
    index_name = settings.azure_search_index_name
    indexer_name = os.getenv("AZURE_SEARCH_INDEXER_NAME", "neura-files-idx")
    datasource_name = os.getenv("AZURE_SEARCH_DATASOURCE_NAME", "neura-files-ds")

    try:
        print(f"Deleting indexer '{indexer_name}'...", flush=True)
        indexer_client.delete_indexer(indexer_name)
        print(f"Indexer '{indexer_name}' deleted.", flush=True)
    except Exception as e:
        print(f"Indexer deletion skipped: {e}", flush=True)

    try:
        print(f"Deleting datasource '{datasource_name}'...", flush=True)
        indexer_client.delete_data_source_connection(datasource_name)
        print(f"DataSource '{datasource_name}' deleted.", flush=True)
    except Exception as e:
        print(f"DataSource deletion skipped: {e}", flush=True)

    try:
        print(f"Deleting index '{index_name}'...", flush=True)
        index_client.delete_index(index_name)
        print(f"Index '{index_name}' deleted.", flush=True)
    except Exception as e:
        print(f"Index deletion skipped: {e}", flush=True)

async def main():
    print("Starting Blob and Search cleanup...", flush=True)
    await cleanup_blobs()
    cleanup_search()
    print("Cleanup finished.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())

