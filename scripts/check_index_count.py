import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from app.core.config import get_settings

def check_index_count():
    print("Checking index count...", flush=True)
    settings = get_settings()
    endpoint = settings.azure_search_endpoint
    key = settings.azure_search_api_key or os.getenv("AZURE_SEARCH_ADMIN_KEY") or os.getenv("AZURE_SEARCH_API_KEY")
    index_name = settings.azure_search_index_name

    print(f"Endpoint: {endpoint}", flush=True)
    # Mask key for log
    print(f"Key provided: {'Yes' if key else 'No'}", flush=True)
    print(f"Index: {index_name}", flush=True)

    if not endpoint or not key:
        print("Credentials missing.", flush=True)
        return

    credential = AzureKeyCredential(key)
    client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

    try:
        count = client.get_document_count()
        print(f"Document count in index '{index_name}': {count}", flush=True)
    except Exception as e:
        print(f"Error checking index: {e}", flush=True)

if __name__ == "__main__":
    check_index_count()
