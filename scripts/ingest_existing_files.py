"""Utility script to ingest metadata for files that already exist in Blob Storage."""

from typing import Optional

from azure.storage.blob import BlobServiceClient

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas.file import FileCreate
from app.services.file_service import FileService
from scripts.utils.filename_parser import extract_metadata


settings = get_settings()


def ingest(owner_id: int, container: Optional[str] = None) -> None:
    container_name = container or settings.azure_blob_files_container
    db = SessionLocal()
    file_service = FileService(db)
    try:
        client = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
        container_client = client.get_container_client(container_name)
        for blob in container_client.list_blobs():
            meta = extract_metadata(blob.name)
            payload = FileCreate(
                owner_id=owner_id,
                original_filename=meta.original_filename,
                content_type=blob.content_settings.content_type if blob.content_settings else None,
                file_size=blob.size,
                blob_name=blob.name,
            )
            blob_url = f"{container_client.url}/{blob.name}"
            file_service.create(payload, blob_name=blob.name, blob_url=blob_url)
    finally:
        db.close()


if __name__ == "__main__":
    # Example usage: adapt to CLI as needed
    import argparse

    parser = argparse.ArgumentParser(description="Ingest blob metadata into SQL DB.")
    parser.add_argument("--owner-id", type=int, required=True)
    parser.add_argument("--container", type=str, default=None)
    args = parser.parse_args()
    ingest(owner_id=args.owner_id, container=args.container)

