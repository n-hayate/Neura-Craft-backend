import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple

from urllib.parse import quote

from azure.storage.blob import (
    BlobSasPermissions,
    ContentSettings,
    generate_blob_sas,
    BlobServiceClient as SyncBlobServiceClient,
)
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BlobService:
    def __init__(self, container_name: str | None = None):
        self.use_local_storage = settings.app_env == "development"
        self.container_name = container_name or settings.azure_blob_files_container
        self.storage_path = Path(settings.local_storage_path)
        if self.use_local_storage:
            self.storage_path.mkdir(parents=True, exist_ok=True)

        self._connection_string = settings.azure_storage_connection_string
        self._async_client: AsyncBlobServiceClient | None = None
        self._sync_client: SyncBlobServiceClient | None = None
        self._container_initialized = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self) -> None:
        if self._async_client:
            await self._async_client.close()
        if self._sync_client:
            self._sync_client.close()

    def _get_async_client(self) -> AsyncBlobServiceClient:
        if not self._async_client:
            self._async_client = AsyncBlobServiceClient.from_connection_string(self._connection_string)
        return self._async_client

    def _get_sync_client(self) -> SyncBlobServiceClient:
        if not self._sync_client:
            self._sync_client = SyncBlobServiceClient.from_connection_string(self._connection_string)
        return self._sync_client

    def make_blob_path(self, blob_name: str) -> str:
        return f"{self.container_name}/{blob_name}"

    def _split_blob_identifier(self, identifier: str) -> Tuple[str, str]:
        if "/" in identifier:
            container, blob_name = identifier.split("/", 1)
        else:
            container = self.container_name
            blob_name = identifier

        if container != self.container_name:
            raise ValueError(
                f"Blob container mismatch: expected {self.container_name}, got {container}"
            )
        return container, blob_name

    async def _ensure_container(self) -> None:
        if self.use_local_storage or self._container_initialized:
            return

        async_client = self._get_async_client()
        container_client = async_client.get_container_client(self.container_name)
        exists = await container_client.exists()
        if not exists:
            logger.info("Creating container '%s'", self.container_name)
            await container_client.create_container()
        self._container_initialized = True

    async def upload_blob(
        self,
        blob_name: str,
        data: bytes,
        *,
        content_type: str | None = None,
        metadata: Dict[str, str | None] | None = None,
    ) -> tuple[str, str | None]:
        # Filter out empty values and URL-encode values to support non-ASCII characters
        encoded_metadata = {}
        if metadata:
            for k, v in metadata.items():
                if v:
                    # Azure Blob Storage headers must be ASCII. URL-encode value.
                    encoded_metadata[k] = quote(str(v))

        if self.use_local_storage:
            file_path = self.storage_path / blob_name
            await asyncio.to_thread(file_path.write_bytes, data)
            return self.make_blob_path(blob_name), f"file://{file_path.absolute()}"

        await self._ensure_container()
        async_client = self._get_async_client()
        blob_client = async_client.get_blob_client(self.container_name, blob_name)
        await blob_client.upload_blob(
            data,
            overwrite=True,
            metadata=encoded_metadata or None,
            content_settings=ContentSettings(content_type=content_type),
        )
        return self.make_blob_path(blob_name), blob_client.url

    async def delete_blob(self, blob_identifier: str) -> None:
        _, blob_name = self._split_blob_identifier(blob_identifier)

        if self.use_local_storage:
            file_path = self.storage_path / blob_name
            if file_path.exists():
                await asyncio.to_thread(file_path.unlink)
            return

        async_client = self._get_async_client()
        blob_client = async_client.get_blob_client(self.container_name, blob_name)
        await blob_client.delete_blob(delete_snapshots="include")

    async def download_blob(self, blob_identifier: str) -> bytes:
        _, blob_name = self._split_blob_identifier(blob_identifier)

        if self.use_local_storage:
            file_path = self.storage_path / blob_name
            if not file_path.exists():
                raise FileNotFoundError(f"File not found locally: {file_path}")
            return await asyncio.to_thread(file_path.read_bytes)

        async_client = self._get_async_client()
        blob_client = async_client.get_blob_client(self.container_name, blob_name)
        stream = await blob_client.download_blob()
        return await stream.readall()

    async def blob_exists(self, blob_identifier: str) -> bool:
        _, blob_name = self._split_blob_identifier(blob_identifier)

        if self.use_local_storage:
            return (self.storage_path / blob_name).exists()

        async_client = self._get_async_client()
        blob_client = async_client.get_blob_client(self.container_name, blob_name)
        return await blob_client.exists()

    def generate_sas_url(self, blob_identifier: str, expiry_minutes: int = 60) -> str:
        """
        指定されたBlobへの一時的なアクセスURL (SAS URL) を生成する。
        ローカル環境では file:// URL を返す。
        """
        _, blob_name = self._split_blob_identifier(blob_identifier)

        if self.use_local_storage:
            file_path = self.storage_path / blob_name
            return f"file://{file_path.absolute()}"

        account_name, account_key = self._parse_connection_string(settings.azure_storage_connection_string)

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes),
        )

        sync_client = self._get_sync_client()
        blob_client = sync_client.get_blob_client(self.container_name, blob_name)
        return f"{blob_client.url}?{sas_token}"

    def get_blob_url(self, blob_identifier: str) -> str:
        """SAS なしのBlob URLを取得（サムネイル等で使用）。"""
        _, blob_name = self._split_blob_identifier(blob_identifier)
        if self.use_local_storage:
            file_path = self.storage_path / blob_name
            return f"file://{file_path.absolute()}"
        sync_client = self._get_sync_client()
        blob_client = sync_client.get_blob_client(self.container_name, blob_name)
        return blob_client.url

    @staticmethod
    def _parse_connection_string(conn_str: str) -> tuple[str, str]:
        account_key = None
        account_name = None

        for part in conn_str.split(";"):
            if part.startswith("AccountKey="):
                account_key = part.split("=", 1)[1]
            elif part.startswith("AccountName="):
                account_name = part.split("=", 1)[1]

        if not account_key or not account_name:
            raise ValueError("Could not parse AccountKey or AccountName from connection string.")

        return account_name, account_key
