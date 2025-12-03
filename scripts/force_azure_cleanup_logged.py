import os
import sys
import traceback

LOG_FILE = "force_cleanup.log"

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    # Also try print
    try:
        print(msg, flush=True)
    except:
        pass

def main():
    # Initialize log
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("Starting cleanup script...\n")

    try:
        log("Importing modules...")
        from azure.storage.blob import BlobServiceClient
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
        from dotenv import load_dotenv
        log("Modules imported.")

        log("Loading .env...")
        load_dotenv()
        
        # 1. Azure Blob Cleanup
        log("--- Azure Blob Cleanup ---")
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.getenv("AZURE_BLOB_FILES_CONTAINER", "files")

        if conn_str:
            log(f"Connecting to container: {container_name}")
            try:
                blob_service_client = BlobServiceClient.from_connection_string(conn_str)
                container_client = blob_service_client.get_container_client(container_name)
                
                if container_client.exists():
                    blobs = list(container_client.list_blobs())
                    log(f"Found {len(blobs)} blobs. Deleting...")
                    count = 0
                    for blob in blobs:
                        container_client.delete_blob(blob.name)
                        count += 1
                    log(f"Deleted {count} blobs.")
                else:
                    log("Container does not exist.")
            except Exception as e:
                log(f"Blob Error: {e}")
                log(traceback.format_exc())
        else:
            log("AZURE_STORAGE_CONNECTION_STRING missing.")

        # 2. Azure Search Cleanup
        log("--- Azure Search Cleanup ---")
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        key = os.getenv("AZURE_SEARCH_ADMIN_KEY") or os.getenv("AZURE_SEARCH_API_KEY")
        index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "neura-files-v2")
        indexer_name = os.getenv("AZURE_SEARCH_INDEXER_NAME", "neura-files-idx")
        datasource_name = os.getenv("AZURE_SEARCH_DATASOURCE_NAME", "neura-files-ds")

        if endpoint and key:
            log(f"Connecting to Search: {endpoint}")
            try:
                credential = AzureKeyCredential(key)
                indexer_client = SearchIndexerClient(endpoint=endpoint, credential=credential)
                index_client = SearchIndexClient(endpoint=endpoint, credential=credential)

                # Indexer
                try:
                    log(f"Deleting Indexer: {indexer_name}")
                    indexer_client.delete_indexer(indexer_name)
                    log("Indexer deleted.")
                except Exception as e:
                    log(f"Indexer deletion warning: {e}")

                # DataSource
                try:
                    log(f"Deleting DataSource: {datasource_name}")
                    indexer_client.delete_data_source_connection(datasource_name)
                    log("DataSource deleted.")
                except Exception as e:
                    log(f"DataSource deletion warning: {e}")

                # Index
                try:
                    log(f"Deleting Index: {index_name}")
                    index_client.delete_index(index_name)
                    log("Index deleted.")
                except Exception as e:
                    log(f"Index deletion warning: {e}")

            except Exception as e:
                log(f"Search connection error: {e}")
                log(traceback.format_exc())
        else:
            log("Search credentials missing.")

        log("Cleanup completed successfully.")

    except Exception as e:
        log(f"Fatal Error: {e}")
        log(traceback.format_exc())

if __name__ == "__main__":
    main()

