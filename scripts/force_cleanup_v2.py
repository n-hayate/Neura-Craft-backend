import sys
import os
import traceback

LOG_FILE = "force_cleanup_v2.log"

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

if __name__ == "__main__":
    # Reset log
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("Script V2 Started\n")

    try:
        log("Loading dotenv...")
        from dotenv import load_dotenv
        load_dotenv()
        log("dotenv loaded.")

        log("Importing Azure Blob...")
        from azure.storage.blob import BlobServiceClient
        log("Azure Blob imported.")

        log("Importing Azure Credentials...")
        from azure.core.credentials import AzureKeyCredential
        log("Azure Credentials imported.")

        log("Importing Azure Search...")
        from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
        log("Azure Search imported.")

        # --- Logic ---
        
        # 1. Blob
        log("Checking Blob Connection String...")
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not conn_str:
            log("ERROR: AZURE_STORAGE_CONNECTION_STRING is not set.")
        else:
            log("Connecting to Blob Service...")
            blob_service = BlobServiceClient.from_connection_string(conn_str)
            container_name = os.getenv("AZURE_BLOB_FILES_CONTAINER", "files")
            container_client = blob_service.get_container_client(container_name)
            
            if container_client.exists():
                log(f"Container '{container_name}' exists. Listing blobs...")
                blobs = list(container_client.list_blobs())
                log(f"Found {len(blobs)} blobs.")
                for b in blobs:
                    log(f"Deleting {b.name}...")
                    container_client.delete_blob(b.name)
                log("Blob cleanup done.")
            else:
                log(f"Container '{container_name}' does not exist.")

        # 2. Search
        log("Checking Search Config...")
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        key = os.getenv("AZURE_SEARCH_ADMIN_KEY") or os.getenv("AZURE_SEARCH_API_KEY")
        
        if not endpoint or not key:
            log("ERROR: Search Endpoint or Key is missing.")
        else:
            log(f"Connecting to Search Endpoint: {endpoint}")
            cred = AzureKeyCredential(key)
            indexer_client = SearchIndexerClient(endpoint=endpoint, credential=cred)
            index_client = SearchIndexClient(endpoint=endpoint, credential=cred)

            idx_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "neura-files-v2")
            indexer_name = os.getenv("AZURE_SEARCH_INDEXER_NAME", "neura-files-idx")
            ds_name = os.getenv("AZURE_SEARCH_DATASOURCE_NAME", "neura-files-ds")

            # Indexer
            try:
                log(f"Deleting Indexer: {indexer_name}")
                indexer_client.delete_indexer(indexer_name)
                log("Indexer deleted.")
            except Exception as e:
                log(f"Indexer delete error/skip: {e}")

            # DataSource
            try:
                log(f"Deleting DataSource: {ds_name}")
                indexer_client.delete_data_source_connection(ds_name)
                log("DataSource deleted.")
            except Exception as e:
                log(f"DataSource delete error/skip: {e}")

            # Index
            try:
                log(f"Deleting Index: {idx_name}")
                index_client.delete_index(idx_name)
                log("Index deleted.")
            except Exception as e:
                log(f"Index delete error/skip: {e}")
        
        log("All Done.")

    except Exception as e:
        log(f"FATAL ERROR: {e}")
        log(traceback.format_exc())

