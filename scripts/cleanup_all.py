import asyncio
import logging
import os
import shutil
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.db.models import User, File, FileReference, FileDownload
from app.services.blob_service import BlobService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()

async def cleanup_db():
    print("Cleaning up database...", flush=True)
    db = SessionLocal()
    try:
        # Delete in order of dependencies
        count_dl = db.query(FileDownload).delete()
        print(f"Deleted {count_dl} FileDownloads", flush=True)
        
        count_ref = db.query(FileReference).delete()
        print(f"Deleted {count_ref} FileReferences", flush=True)
        
        count_file = db.query(File).delete()
        print(f"Deleted {count_file} Files", flush=True)
        
        count_user = db.query(User).delete()
        print(f"Deleted {count_user} Users", flush=True)
        
        db.commit()
        print("Database cleanup complete (Committed).", flush=True)
    except Exception as e:
        print(f"Error cleaning DB: {e}", flush=True)
        db.rollback()
    finally:
        db.close()

async def cleanup_blobs():
    print("Cleaning up blobs...", flush=True)
    service = BlobService()
    if service.use_local_storage:
        path = service.storage_path
        if path.exists():
            for item in path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        print("Local blobs cleaned.", flush=True)
    else:
        async with service:
            container_client = service._get_async_client().get_container_client(service.container_name)
            if await container_client.exists():
                async for blob in container_client.list_blobs():
                    await container_client.delete_blob(blob.name)
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

    credential = AzureKeyCredential(key)
    indexer_client = SearchIndexerClient(endpoint=endpoint, credential=credential)
    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
    
    index_name = settings.azure_search_index_name
    indexer_name = os.getenv("AZURE_SEARCH_INDEXER_NAME", "neura-files-idx")
    datasource_name = os.getenv("AZURE_SEARCH_DATASOURCE_NAME", "neura-files-ds")

    try:
        indexer_client.delete_indexer(indexer_name)
        print(f"Indexer '{indexer_name}' deleted.", flush=True)
    except Exception as e:
        print(f"Indexer deletion skipped: {e}", flush=True)

    try:
        indexer_client.delete_data_source_connection(datasource_name)
        print(f"DataSource '{datasource_name}' deleted.", flush=True)
    except Exception as e:
        print(f"DataSource deletion skipped: {e}", flush=True)

    try:
        index_client.delete_index(index_name)
        print(f"Index '{index_name}' deleted.", flush=True)
    except Exception as e:
        print(f"Index deletion skipped: {e}", flush=True)

async def main():
    print("Starting full cleanup...", flush=True)
    await cleanup_db()
    await cleanup_blobs()
    cleanup_search()
    print("Cleanup finished.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
