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

| 変数                              | 説明                                      |
| --------------------------------- | ----------------------------------------- |
| `APP_ENV`                         | `development` / `production` などの環境名 |
| `SECRET_KEY`                      | JWT 署名キー                              |
| `ACCESS_TOKEN_EXPIRE_MINUTES`     | アクセストークン有効期限                  |
| `SQLALCHEMY_DATABASE_URI`         | DB 接続文字列（開発では SQLite でも可）   |
| `AZURE_STORAGE_ACCOUNT_NAME`      | ストレージアカウント名                    |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob 接続文字列                           |
| `AZURE_BLOB_FILES_CONTAINER`      | ファイル格納コンテナ                      |
| `LOCAL_STORAGE_PATH`              | 開発時にファイルを保存するローカルパス    |

### ストレージ設定（ローカル / Azure）

- **開発環境（ローカル）**

  - `.env` で `APP_ENV=development` を指定
  - `AZURE_STORAGE_CONNECTION_STRING` はダミーでもよい
  - アップロードされたファイルは `LOCAL_STORAGE_PATH`（デフォルト: `uploads/`）配下に保存される  
    例: `uploads/<UUID>-<元ファイル名>`

- **Azure Blob Storage を利用する場合**
  - `.env` で `APP_ENV=production` など、`development` 以外の値を設定
  - `AZURE_STORAGE_CONNECTION_STRING` に実際の接続文字列を設定
  - `AZURE_BLOB_FILES_CONTAINER` に利用するコンテナ名を設定（例: `files`）
  - 以降のファイルアップロードは Azure Blob Storage に保存され、DB には Blob の URL が格納される

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

## ファイルアップロード API 仕様

### `POST /api/v1/files`

ファイルとメタデータをアップロードするエンドポイントです。`multipart/form-data`形式で送信してください。

#### リクエストパラメータ（FormData）

| フィールド名     | 型     | 必須 | 説明                                  | 備考                                   |
| ---------------- | ------ | ---- | ------------------------------------- | -------------------------------------- |
| `file`           | File   | 必須 | アップロードするファイル              | ファイルオブジェクト                   |
| `final_product`  | string | 必須 | 最終製品名                            | 検索キーとして使用                     |
| `issue`          | string | 必須 | 課題感                                | 検索キーとして使用                     |
| `ingredient`     | string | 必須 | 使用原料                              | 検索キーとして使用                     |
| `customer`       | string | 必須 | 提案企業                              | 検索キーとして使用                     |
| `trial_id`       | string | 必須 | 試作 ID                               | 検索キーとして使用（4 桁の英数字推奨） |
| `author`         | string | 任意 | 開発担当者名                          | `null` を送信可能                      |
| `file_extension` | string | 任意 | ファイルの拡張子（例: 'xlsx', 'pdf'） | 未指定時はファイル名から自動抽出       |
| `status`         | string | 任意 | ファイルの状態                        | デフォルト: `"active"`                 |

#### レスポンス

成功時（201 Created）:

```json
{
  "id": "uuid-string",
  "owner_id": 1,
  "original_filename": "example.xlsx",
  "blob_name": "uuid-filename",
  "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "file_size": 12345,
  "azure_blob_url": "https://...",
  "created_at": "2025-01-20T12:00:00Z",
  "final_product": "最終製品名",
  "issue": "課題感",
  "ingredient": "使用原料",
  "customer": "提案企業",
  "trial_id": "0001",
  "author": "開発担当者名",
  "file_extension": "xlsx",
  "updated_at": "2025-01-20T12:00:00Z",
  "status": "active"
}
```

#### 使用例（JavaScript/TypeScript）

```javascript
const formData = new FormData();
formData.append("file", fileInput.files[0]);
formData.append("final_product", "最終製品名");
formData.append("issue", "課題感");
formData.append("ingredient", "使用原料");
formData.append("customer", "提案企業");
formData.append("trial_id", "0001");
formData.append("author", "開発担当者名"); // 任意
formData.append("file_extension", "xlsx"); // 任意（自動抽出可）
formData.append("status", "active"); // 任意（デフォルト: active）

const response = await fetch("http://localhost:8000/api/v1/files", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
  body: formData,
});

const result = await response.json();
```

#### ファイル命名規則について

ファイル名の命名規則は以下の通りです（ただし、この規則に従っていなくてもアップロード可能です）:

```
最終製品_課題感_使用原料_提案企業_試作ID.xlsx
```

フロントエンドでは、この命名規則に基づいてファイル名を解析するのではなく、上記のメタデータフィールドを個別に入力・送信してください。

## テスト

```bash
pytest
```

## 今後の拡張メモ

- Azure AD などの外部 IdP に差し替えられるよう、`app/services/auth_service.py` の抽象化を維持
- ファイル実データは Blob Storage、メタデータは SQL に保存
- Alembic マイグレーションは `app/db/migrations` 配下で管理
