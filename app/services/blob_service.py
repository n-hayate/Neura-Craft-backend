import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions

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

    def download_blob(self, blob_name: str) -> bytes:
        """Blobからデータをダウンロードしてbytesで返す"""
        if self.use_local_storage:
            file_path = self.storage_path / blob_name
            if not file_path.exists():
                raise FileNotFoundError(f"File not found locally: {file_path}")
            return file_path.read_bytes()
        else:
            try:
                blob_client = self.client.get_blob_client(self.container_name, blob_name)
                return blob_client.download_blob().readall()
            except Exception as e:
                logger.error(f"Failed to download blob: {e}")
                raise
    
    def blob_exists(self, blob_name: str) -> bool:
        if self.use_local_storage:
            return (self.storage_path / blob_name).exists()
        else:
            return self.client.get_blob_client(self.container_name, blob_name).exists()

    def generate_sas_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """
        指定されたBlobへの一時的なアクセスURL (SAS URL) を生成する
        
        Args:
            blob_name: Blob名
            expiry_hours: 有効期限（時間）。デフォルト1時間。
            
        Returns:
            SAS付きのURL
        """
        if self.use_local_storage:
            # ローカルストレージの場合はSASがないため、そのままファイルURLを返す（開発用）
            # 注意: file:// はブラウザのセキュリティ制限でiframe等では使えない場合が多い
            # 実際にはローカルサーバーでホストするなどの工夫が必要だが、今回はfile://を返す
            file_path = self.storage_path / blob_name
            return f"file://{file_path.absolute()}"
        else:
            try:
                # アカウントキーなどを取得
                # connection_stringからパースするか、設定から取る
                # SDKのgenerate_blob_sasにはaccount_keyが必要
                
                # Note: Connection Stringからキーを取り出すのは少し手間なので、
                # 設定ファイルに key がある前提で config から取るのが楽だが、
                # settings.azure_storage_account_key は "storage-key" (ダミー) の可能性もある。
                # Connection String をパースするのが確実。
                
                conn_str = settings.azure_storage_connection_string
                account_key = None
                account_name = None
                
                for part in conn_str.split(";"):
                    if part.startswith("AccountKey="):
                        account_key = part.split("=", 1)[1]
                    elif part.startswith("AccountName="):
                        account_name = part.split("=", 1)[1]
                
                if not account_key or not account_name:
                    raise ValueError("Could not parse AccountKey or AccountName from connection string")

                sas_token = generate_blob_sas(
                    account_name=account_name,
                    container_name=self.container_name,
                    blob_name=blob_name,
                    account_key=account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
                )
                
                # Blob ClientからURLを取得し、SASトークンを付与
                blob_client = self.client.get_blob_client(self.container_name, blob_name)
                return f"{blob_client.url}?{sas_token}"
                
            except Exception as e:
                logger.error(f"Failed to generate SAS URL: {e}")
                raise
