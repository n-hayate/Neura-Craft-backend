"""Utility script to backfill SQL metadata for existing Blob objects."""

import argparse
from typing import Optional
from uuid import uuid4

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
                id=str(uuid4()),
                blob_path=f"{container_name}/{blob.name}",
                original_name=meta.original_filename,
                application=meta.application,
                issue=meta.issue,
                ingredient=meta.ingredient,
                customer=meta.customer,
                trial_id=meta.trial_id,
                author=meta.author,
                status="active",
                owner_id=owner_id,
            )
            file_service.create(payload)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest blob metadata into SQL DB.")
    parser.add_argument("--owner-id", type=int, required=True)
    parser.add_argument("--container", type=str, default=None)
    args = parser.parse_args()
    ingest(owner_id=args.owner_id, container=args.container)

