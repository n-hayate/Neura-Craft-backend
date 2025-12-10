"""
デバッグ用スクリプト：インデクサーの状態とBlobメタデータを確認する
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexerClient
from azure.storage.blob import BlobServiceClient

load_dotenv()

def check_indexer_status():
    """インデクサーの状態を確認"""
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    api_key = os.getenv("AZURE_SEARCH_ADMIN_KEY") or os.getenv("AZURE_SEARCH_API_KEY")
    indexer_name = os.getenv("AZURE_SEARCH_INDEXER_NAME", "neura-files-idx")
    
    client = SearchIndexerClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
    
    # インデクサーの状態を取得
    status = client.get_indexer_status(indexer_name)
    print("=" * 60)
    print("インデクサー状態")
    print("=" * 60)
    print(f"Status: {status.status}")
    print(f"Last Result: {status.last_result.status if status.last_result else 'N/A'}")
    
    if status.last_result:
        print(f"  - Items Processed: {status.last_result.item_count}")
        print(f"  - Items Failed: {status.last_result.failed_item_count}")
        print(f"  - Start Time: {status.last_result.start_time}")
        print(f"  - End Time: {status.last_result.end_time}")
        
        if status.last_result.errors:
            print("\n  エラー:")
            for error in status.last_result.errors:
                print(f"    - {error.error_message}")
        
        if status.last_result.warnings:
            print("\n  警告:")
            for warning in status.last_result.warnings:
                print(f"    - {warning.message}")


def check_blob_metadata():
    """Blobのメタデータを確認"""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_BLOB_FILES_CONTAINER", "files")
    
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client(container_name)
    
    print("\n" + "=" * 60)
    print("Blobメタデータ確認（最初の3件）")
    print("=" * 60)
    
    count = 0
    for blob in container_client.list_blobs(include=['metadata']):
        if count >= 3:
            break
        print(f"\nBlob名: {blob.name}")
        print(f"メタデータ:")
        if blob.metadata:
            for key, value in blob.metadata.items():
                # 長い値は省略
                display_value = value[:50] + "..." if len(value) > 50 else value
                print(f"  {key}: {display_value}")
        else:
            print("  (メタデータなし)")
        count += 1
    
    if count == 0:
        print("Blobが見つかりませんでした。")


def check_index_documents():
    """インデックス内のドキュメントを確認"""
    from azure.search.documents import SearchClient
    
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    api_key = os.getenv("AZURE_SEARCH_ADMIN_KEY") or os.getenv("AZURE_SEARCH_API_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "neura-files-v2")
    
    client = SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(api_key))
    
    print("\n" + "=" * 60)
    print("インデックス内ドキュメント確認（最初の3件）")
    print("=" * 60)
    
    results = client.search("*", top=3)
    
    count = 0
    for doc in results:
        print(f"\n--- ドキュメント {count + 1} ---")
        for key, value in doc.items():
            if key.startswith("@"):
                continue
            display_value = str(value)[:50] + "..." if value and len(str(value)) > 50 else value
            print(f"  {key}: {display_value}")
        count += 1
    
    if count == 0:
        print("ドキュメントが見つかりませんでした。")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    print("デバッグスクリプト開始\n", flush=True)
    
    try:
        check_indexer_status()
    except Exception as e:
        import traceback
        print(f"インデクサー状態確認エラー: {e}")
        traceback.print_exc()
    
    try:
        check_blob_metadata()
    except Exception as e:
        import traceback
        print(f"Blobメタデータ確認エラー: {e}")
        traceback.print_exc()
    
    try:
        check_index_documents()
    except Exception as e:
        import traceback
        print(f"インデックスドキュメント確認エラー: {e}")
        traceback.print_exc()
    
    print("\n\nデバッグスクリプト完了", flush=True)

