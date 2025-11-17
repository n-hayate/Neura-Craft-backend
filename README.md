# Neura Craft Backend

FastAPI ベースのバックエンドで、Next.js フロントエンドから REST API 経由で利用されます。Azure SQL Database と Azure Blob Storage を前提に設計されており、クリーンアーキテクチャ寄りの分離を採用しています。

## 技術構成

- FastAPI + Uvicorn
- SQLAlchemy (Azure SQL / pyodbc)
- Azure Blob Storage SDK
- JWT (python-jose) + Passlib
- Alembic (マイグレーション)

## セットアップ

1. Python 3.11 以上を用意
2. `env.example` を `.env` にリネームし、値を環境に合わせて修正
3. 必要なら `.env` を `.env.example` としてコミットできるよう、ローカルでファイル名を変更（本環境では `env.example` ファイルで代替しています）
4. 依存関係をインストール
   ```bash
   pip install -e .
   ```
   もしくは
   ```bash
   pip install -r requirements.txt  # requirements を生成した場合
   ```
5. アプリを起動
   ```bash
   uvicorn app.main:app --reload
   ```

## 環境変数

| 変数                              | 説明                     |
| --------------------------------- | ------------------------ |
| `SECRET_KEY`                      | JWT 署名キー             |
| `ACCESS_TOKEN_EXPIRE_MINUTES`     | アクセストークン有効期限 |
| `SQLALCHEMY_DATABASE_URI`         | Azure SQL への接続文字列 |
| `AZURE_STORAGE_ACCOUNT_NAME`      | ストレージアカウント名   |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob 接続文字列          |
| `AZURE_BLOB_FILES_CONTAINER`      | ファイル格納コンテナ     |

## ディレクトリ構成

```
.
  app/
    api/        # ルーター層
    services/   # ビジネスロジック
    schemas/    # Pydantic スキーマ
    db/         # DB モデル & セッション
    core/       # 設定・認証
    main.py
  scripts/
  tests/
  alembic.ini
  pyproject.toml
```

## Next.js 画面と API 対応表

| Next.js 画面 (想定パス)        | 利用 API                     |
| ------------------------------ | ---------------------------- |
| `/login` (認証)                | `POST /api/v1/auth/login`    |
| `/signup` (新規登録)           | `POST /api/v1/auth/register` |
| `/dashboard` (ユーザー情報)    | `GET /api/v1/users/me`       |
| `/admin/users` (ユーザー管理)  | `GET/POST/PUT /api/v1/users` |
| `/files` (ファイル一覧)        | `GET /api/v1/files`          |
| `/files/upload` (ファイル登録) | `POST /api/v1/files`         |

Swagger UI: `http://localhost:8000/docs`  
OpenAPI JSON: `http://localhost:8000/openapi.json`

## テスト

```bash
pytest
```

## 今後の拡張メモ

- Azure AD などの外部 IdP に差し替えられるよう、`app/services/auth_service.py` の抽象化を維持
- ファイル実データは Blob Storage、メタデータは SQL に保存
- Alembic マイグレーションは `app/db/migrations` 配下で管理
