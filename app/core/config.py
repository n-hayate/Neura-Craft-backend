import json
from functools import lru_cache
from typing import Any, List

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 未定義の環境変数を無視
    )

    app_name: str = "Neura Craft Backend"
    app_env: str = "development"
    api_v1_str: str = "/api/v1"
    backend_cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @model_validator(mode="before")
    @classmethod
    def parse_cors_origins(cls, data: Any) -> Any:
        """環境変数の読み込み前にCORS originsを処理"""
        if isinstance(data, dict):
            # 環境変数のキー名を確認（大文字小文字を考慮）
            cors_key = None
            for key in data.keys():
                if key.lower() == "backend_cors_origins":
                    cors_key = key
                    break
            
            if cors_key and cors_key in data:
                value = data[cors_key]
                if isinstance(value, str):
                    # JSON配列として解釈を試みる
                    if value.strip().startswith("["):
                        try:
                            parsed = json.loads(value)
                            if isinstance(parsed, list):
                                data[cors_key] = parsed
                                return data
                        except (json.JSONDecodeError, ValueError):
                            pass
                    # カンマ区切りの文字列として処理
                    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
                    data[cors_key] = origins if origins else ["http://localhost:3000"]
        return data

    # secret_key: str = Field(default="change-me") 
    secret_key: str = Field(...) # defaultを削除して、.envに無いと起動エラーにする
    access_token_expire_minutes: int = Field(default=30)
    jwt_algorithm: str = Field(default="HS256")

    sqlalchemy_database_uri: str = Field(
        default=(
            "mssql+pyodbc://user:password@server.database.windows.net:1433/db"
            "?driver=ODBC+Driver+18+for+SQL+Server"
        )
    )

    azure_storage_account_name: str = "storage-account"
    azure_storage_account_key: str = "storage-key"
    azure_storage_connection_string: str = Field(
        default="DefaultEndpointsProtocol=https;AccountName=storage-account;"
        "AccountKey=storage-key;EndpointSuffix=core.windows.net"
    )
    azure_blob_files_container: str = "files"
    azure_blob_thumbnails_container: str = "thumbnails"
    local_storage_path: str = Field(default="uploads")  # 開発環境用のローカルストレージパス

    # Azure AI Search
    search_backend: str = Field(default="azure")  # 固定でAzure Searchを利用
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index_name: str = "neura-files-v2"
    azure_search_suggester_name: str = "nc-suggester"



@lru_cache
def get_settings() -> Settings:
    return Settings()


