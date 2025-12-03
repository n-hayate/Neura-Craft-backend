import sys
import os
import shutil
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.db.models import User, File, FileReference, FileDownload
from app.services.blob_service import BlobService

# Force stdout logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

def cleanup_all_sync():
    print("=== Starting SYNC Cleanup ===", flush=True)
    settings = get_settings()

    # 1. DB Cleanup
    print("\n[1/3] Cleaning DB...", flush=True)
    db = SessionLocal()
    try:
        c_dl = db.query(FileDownload).delete()
        c_ref = db.query(FileReference).delete()
        c_file = db.query(File).delete()
        c_user = db.query(User).delete()
        db.commit()
        print(f"Deleted: {c_dl} DLs, {c_ref} Refs, {c_file} Files, {c_user} Users", flush=True)
    except Exception as e:
        print(f"DB Error: {e}", flush=True)
        db.rollback()
    finally:
        db.close()

    # 2. Blob Cleanup
    print("\n[2/3] Cleaning Blobs...", flush=True)
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
        # Sync Blob Client
        try:
            sync_client = service._get_sync_client()
            container_client = sync_client.get_container_client(service.container_name)
            if container_client.exists():
                blobs = container_client.list_blobs()
                for blob in blobs:
                    container_client.delete_blob(blob.name)
                    print(f"Deleted blob: {blob.name}", flush=True)
                print("Azure blobs cleaned.", flush=True)
            else:
                print("Container not found.", flush=True)
        except Exception as e:
            print(f"Blob Error: {e}", flush=True)

    # 3. Search Cleanup
    print("\n[3/3] Cleaning Search...", flush=True)
    endpoint = settings.azure_search_endpoint
    key = settings.azure_search_api_key or os.getenv("AZURE_SEARCH_ADMIN_KEY") or os.getenv("AZURE_SEARCH_API_KEY")
    
    if endpoint and key:
        credential = AzureKeyCredential(key)
        indexer_client = SearchIndexerClient(endpoint=endpoint, credential=credential)
        index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
        
        index_name = settings.azure_search_index_name
        indexer_name = os.getenv("AZURE_SEARCH_INDEXER_NAME", "neura-files-idx")
        datasource_name = os.getenv("AZURE_SEARCH_DATASOURCE_NAME", "neura-files-ds")

        try:
            indexer_client.delete_indexer(indexer_name)
            print(f"Indexer '{indexer_name}' deleted.", flush=True)
        except Exception:
            print(f"Indexer '{indexer_name}' not found or already deleted.", flush=True)

        try:
            indexer_client.delete_data_source_connection(datasource_name)
            print(f"DataSource '{datasource_name}' deleted.", flush=True)
        except Exception:
            print(f"DataSource '{datasource_name}' not found or already deleted.", flush=True)

        try:
            index_client.delete_index(index_name)
            print(f"Index '{index_name}' deleted.", flush=True)
        except Exception:
            print(f"Index '{index_name}' not found or already deleted.", flush=True)
    else:
        print("Skipping search cleanup (no credentials).", flush=True)

    print("\n=== Cleanup Finished ===", flush=True)

if __name__ == "__main__":
    cleanup_all_sync()

