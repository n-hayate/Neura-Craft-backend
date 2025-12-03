import os
import sys
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from dotenv import load_dotenv

def force_cleanup():
    print("Loading environment variables...", flush=True)
    load_dotenv()
    
    print("Starting Force Cleanup...", flush=True)

    # 1. Azure Blob Cleanup
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_BLOB_FILES_CONTAINER", "files")

    if conn_str:
        try:
            print(f"Connecting to Blob Storage container: {container_name}", flush=True)
            blob_service_client = BlobServiceClient.from_connection_string(conn_str)
            container_client = blob_service_client.get_container_client(container_name)
            
            if container_client.exists():
                blobs = list(container_client.list_blobs())
                print(f"Found {len(blobs)} blobs. Deleting...", flush=True)
                count = 0
                for blob in blobs:
                    container_client.delete_blob(blob.name)
                    count += 1
                    if count % 10 == 0:
                        print(f"Deleted {count} blobs...", flush=True)
                print(f"Blob container cleaned. Total deleted: {count}", flush=True)
            else:
                print("Blob container does not exist.", flush=True)
        except Exception as e:
            print(f"Error cleaning blobs: {e}", flush=True)
    else:
        print("AZURE_STORAGE_CONNECTION_STRING not found in environment variables.", flush=True)

    # 2. Azure Search Cleanup
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_ADMIN_KEY") or os.getenv("AZURE_SEARCH_API_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "neura-files-v2")
    indexer_name = os.getenv("AZURE_SEARCH_INDEXER_NAME", "neura-files-idx")
    datasource_name = os.getenv("AZURE_SEARCH_DATASOURCE_NAME", "neura-files-ds")

    print(f"Endpoint: {endpoint}", flush=True)
    print(f"Index Name: {index_name}", flush=True)

    if endpoint and key:
        try:
            print("Connecting to Azure Search...", flush=True)
            credential = AzureKeyCredential(key)
            indexer_client = SearchIndexerClient(endpoint=endpoint, credential=credential)
            index_client = SearchIndexClient(endpoint=endpoint, credential=credential)

            # Delete Indexer
            try:
                print(f"Deleting indexer: {indexer_name}", flush=True)
                indexer_client.delete_indexer(indexer_name)
                print("Indexer deleted.", flush=True)
            except Exception as e:
                print(f"Indexer deletion failed/skipped: {e}", flush=True)

            # Delete DataSource
            try:
                print(f"Deleting datasource: {datasource_name}", flush=True)
                indexer_client.delete_data_source_connection(datasource_name)
                print("DataSource deleted.", flush=True)
            except Exception as e:
                print(f"DataSource deletion failed/skipped: {e}", flush=True)

            # Delete Index
            try:
                print(f"Deleting index: {index_name}", flush=True)
                index_client.delete_index(index_name)
                print("Index deleted.", flush=True)
            except Exception as e:
                print(f"Index deletion failed/skipped: {e}", flush=True)
        
        except Exception as e:
            print(f"Error connecting to Azure Search: {e}", flush=True)
    else:
        print("Azure Search credentials (ENDPOINT or KEY) not found.", flush=True)

    print("Cleanup process finished.", flush=True)

if __name__ == "__main__":
    try:
        force_cleanup()
    except Exception as e:
        print(f"Fatal Error: {e}", flush=True)
