import logging
import os
from pathlib import Path
from uuid import uuid4

from azure.storage.blob import BlobServiceClient, ContentSettings

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BlobService:
    def __init__(self, container_name: str | None = None):
        self.use_local_storage = settings.app_env == "development"
        self.container_name = container_name or settings.azure_blob_files_container
        
        if self.use_local_storage:
            # ローカルストレージを使用
            self.storage_path = Path(settings.local_storage_path)
            self.storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using local storage at: {self.storage_path}")
        else:
            # Azure Blob Storageを使用
            try:
                self.client = BlobServiceClient.from_connection_string(
                    settings.azure_storage_connection_string
                )
            except Exception as e:
                logger.error(f"Failed to initialize BlobServiceClient: {e}")
                raise

    def generate_blob_name(self, original_filename: str) -> str:
        return f"{uuid4()}-{original_filename}"

    def upload_bytes(self, data: bytes, original_filename: str, content_type: str | None = None) -> tuple[str, str]:
        blob_name = self.generate_blob_name(original_filename)
        
        if self.use_local_storage:
            # ローカルストレージに保存
            try:
                file_path = self.storage_path / blob_name
                file_path.write_bytes(data)
                # ローカルファイルのURL（開発環境用）
                blob_url = f"file://{file_path.absolute()}"
                logger.info(f"File saved to local storage: {file_path}")
                return blob_name, blob_url
            except Exception as e:
                logger.error(f"Failed to save file to local storage: {e}")
                raise
        else:
            # Azure Blob Storageに保存
            try:
                blob_client = self.client.get_blob_client(self.container_name, blob_name)
                
                # コンテナが存在しない場合は作成を試みる
                try:
                    container_client = self.client.get_container_client(self.container_name)
                    if not container_client.exists():
                        logger.info(f"Container '{self.container_name}' does not exist, creating...")
                        container_client.create_container()
                except Exception as e:
                    logger.warning(f"Could not create container (may already exist): {e}")
                
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type),
                )
                return blob_name, blob_client.url
            except Exception as e:
                logger.error(f"Failed to upload blob: {e}")
                raise

    def delete_blob(self, blob_name: str) -> None:
        if self.use_local_storage:
            # ローカルストレージから削除
            try:
                file_path = self.storage_path / blob_name
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"File deleted from local storage: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file from local storage: {e}")
                raise
        else:
            # Azure Blob Storageから削除
            blob_client = self.client.get_blob_client(self.container_name, blob_name)
            blob_client.delete_blob()


