# Neura Craft Backend

FastAPI ベースのバックエンドで、Next.js フロントエンドから REST API 経由で利用されます。Azure SQL Database と Azure Blob Storage を前提に設計されており、クリーンアーキテクチャ寄りの分離を採用しています。

## 技術構成

- FastAPI + Uvicorn
- SQLAlchemy (Azure SQL / pyodbc)
- Azure Blob Storage SDK
- JWT (python-jose) + Passlib
- Alembic (マイグレーション)
- Janome (形態素解析)
- ReportLab / OpenPyXL (データ生成)

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

## データシード（デモ用データ投入）

デモ用にリアルな食品開発データ（50 件〜）を自動投入するスクリプトを用意しています。
実行すると、`demo@example.com` ユーザーが作成され、DB と Blob Storage にデータが投入されます。

```bash
python scripts/seed_data.py
```

## 環境変数

| 変数                              | 説明                                                   |
| --------------------------------- | ------------------------------------------------------ |
| `APP_ENV`                         | `development` / `production` などの環境名              |
| `SECRET_KEY`                      | JWT 署名キー                                           |
| `ACCESS_TOKEN_EXPIRE_MINUTES`     | アクセストークン有効期限                               |
| `SQLALCHEMY_DATABASE_URI`         | DB 接続文字列（開発では SQLite でも可）                |
| `AZURE_STORAGE_ACCOUNT_NAME`      | ストレージアカウント名                                 |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob 接続文字列                                        |
| `AZURE_BLOB_FILES_CONTAINER`      | ファイル格納コンテナ                                   |
| `AZURE_BLOB_THUMBNAILS_CONTAINER` | サムネイル格納コンテナ                                 |
| `LOCAL_STORAGE_PATH`              | 開発時にファイルを保存するローカルパス                 |
| `SEARCH_BACKEND`                  | 検索エンジン (`azure` or `sql`) ※現状は `azure` を推奨 |
| `AZURE_SEARCH_ENDPOINT`           | Azure AI Search エンドポイント URL                     |
| `AZURE_SEARCH_API_KEY`            | Azure AI Search クエリキー                             |
| `AZURE_SEARCH_ADMIN_KEY`          | Azure AI Search Admin キー（セットアップ用）           |
| `AZURE_SEARCH_INDEX_NAME`         | インデックス名 (例: `neura-files-v2`)                  |
| `AZURE_SEARCH_DATASOURCE_NAME`    | データソース名 (例: `neura-files-ds`)                  |
| `AZURE_SEARCH_INDEXER_NAME`       | インデクサー名 (例: `neura-files-idx`)                 |
| `AZURE_SEARCH_SUGGESTER_NAME`     | サジェスター名 (例: `nc-suggester`)                    |

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
  - `AZURE_BLOB_THUMBNAILS_CONTAINER` にサムネイル用コンテナ名を設定（例: `thumbnails`）
- 以降のファイルアップロードは Azure Blob Storage に保存され、DB には Blob のパス（例: `files/<UUID>.ext`）が保存される

## Azure AI Search の設定

本プロジェクトでは、検索エンジンとして **Azure AI Search** を採用しています（SQL LIKE 検索は廃止済み）。

### 有効化手順

1. Azure Portal で Azure AI Search リソースを作成する。
2. `.env` に以下の変数を設定する。
   ```bash
   SEARCH_BACKEND=azure
   AZURE_SEARCH_ENDPOINT=https://<your-service-name>.search.windows.net
   AZURE_SEARCH_API_KEY=<query-key>
   AZURE_SEARCH_SYNONYM_MAP_NAME=userdict-synonyms-v1
   AZURE_SEARCH_INDEX_NAME=neura-files-v2
   AZURE_SEARCH_DATASOURCE_NAME=neura-files-ds
   AZURE_SEARCH_INDEXER_NAME=neura-files-idx
   AZURE_SEARCH_SUGGESTER_NAME=nc-suggester
   ```
3. 類義語辞書（`data/userdict.xlsx`）を Synonym Map として登録する。
   ```bash
   export AZURE_SEARCH_ADMIN_KEY=<admin-key>  # または AZURE_SEARCH_API_KEY
   python scripts/sync_synonym_map.py --xlsx data/userdict.xlsx --map-name ${AZURE_SEARCH_SYNONYM_MAP_NAME}
   ```
4. 初回セットアップ時は、Admin Key を使ってインデックス/データソース/インデクサーを作成する。
   ```bash
   export AZURE_SEARCH_ADMIN_KEY=<admin-key>
   # (.env に AZURE_SEARCH_ADMIN_KEY を設定済みなら export 不要)
   python infrastructure/search_setup.py
   ```
5. DB マイグレーションを実行する（日本語対応カラムへの変更等）。
   ```bash
   alembic upgrade head
   ```
6. 既存データや Blob メタデータを再クロールしたい場合は、インデクサーを手動起動する（または Portal から実行）。
   ```bash
   python scripts/reindex_search.py
   ```

補足:

- `infrastructure/search_setup.py` は既存インデックスがある場合、スキーマを壊さず search 可能な文字列フィールドにだけ `AZURE_SEARCH_SYNONYM_MAP_NAME` の Synonym Map を割り当て直します。クエリ時展開なので再インデックスは通常不要です。

※ Admin Key はセットアップ時のみ使用し、アプリケーションからのクエリには `AZURE_SEARCH_API_KEY`（クエリキー）を利用してください。

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

| Next.js 画面 (想定パス)        | 利用 API                                              |
| ------------------------------ | ----------------------------------------------------- |
| `/login` (認証)                | `POST /api/v1/auth/login`                             |
| `/signup` (新規登録)           | `POST /api/v1/auth/register`                          |
| `/dashboard` (ユーザー情報)    | `GET /api/v1/users/me`, `GET /api/v1/files/dashboard` |
| `/admin/users` (ユーザー管理)  | `GET/POST/PUT /api/v1/users`                          |
| `/files` (ファイル一覧)        | `GET /api/v1/files`                                   |
| `/files/upload` (ファイル登録) | `POST /api/v1/files`                                  |

Swagger UI: `http://localhost:8000/docs`  
OpenAPI JSON: `http://localhost:8000/openapi.json`

## ファイルアップロード / メタデータ API 仕様

### `POST /api/v1/files`（ファイルアップロード）

ファイルをアップロードすると、指定されたメタデータとともに Azure Blob Storage に保存します。`multipart/form-data`形式で送信してください。

#### リクエストパラメータ（FormData）

| フィールド名  | 型     | 必須 | 説明                                 | 備考                                   |
| ------------- | ------ | ---- | ------------------------------------ | -------------------------------------- |
| `file`        | File   | 必須 | アップロードするファイル             | `application/pdf` など任意の形式に対応 |
| `file_status` | string | 任意 | ファイルの状態 (`active`/`archived`) | 指定しない場合は `active`              |
| `application` | string | 任意 | アプリケーション名                   |                                        |
| `issue`       | string | 任意 | 課題                                 |                                        |
| `ingredient`  | string | 任意 | 材料                                 |                                        |
| `customer`    | string | 任意 | 顧客                                 |                                        |
| `trial_id`    | string | 任意 | 試作 ID                              |                                        |
| `author`      | string | 任意 | 担当者                               |                                        |

フォームパラメータで指定されたメタデータが優先されます。指定がない場合は `null` となります。

#### レスポンス

成功時（201 Created）:

```json
{
  "id": "uuid-string",
  "owner_id": 1,
  "original_name": "example.xlsx",
  "blob_path": "files/uuid-string.xlsx",
  "application": "アプリケーション",
  "issue": "課題",
  "ingredient": "材料",
  "customer": "顧客",
  "trial_id": "試作ID",
  "author": "担当者",
  "status": "active",
  "created_at": "2025-01-20T12:00:00Z",
  "updated_at": "2025-01-20T12:00:00Z"
}
```

#### 使用例（JavaScript/TypeScript）

```javascript
const formData = new FormData();
formData.append("file", fileInput.files[0]);
formData.append("file_status", "active");
formData.append("application", "Cake");
formData.append("issue", "Sweetness");

const response = await fetch("http://localhost:8000/api/v1/files", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
  body: formData,
});

const result = await response.json();
```

---

### `GET /api/v1/files/search`（ファイル検索）

ファイル名およびメタデータで検索・絞り込みするエンドポイントです。  
画面の検索バー + 絞り込みフィルタ用に利用します。

#### クエリパラメータ

| パラメータ名  | 型     | 必須 | 説明                                                                                 |
| ------------- | ------ | ---- | ------------------------------------------------------------------------------------ |
| `q`           | string | 任意 | `content,application,customer,trial_id,ingredient,author` に対する全文検索キーワード |
| `application` | string | 任意 | アプリケーション名（完全一致フィルタ）                                               |
| `issue`       | string | 任意 | 課題（完全一致フィルタ）                                                             |
| `ingredient`  | string | 任意 | 材料（完全一致フィルタ）                                                             |
| `customer`    | string | 任意 | 顧客（完全一致フィルタ）                                                             |
| `trial_id`    | string | 任意 | 試作 ID（完全一致フィルタ）                                                          |
| `author`      | string | 任意 | 担当者（完全一致フィルタ）                                                           |
| `status`      | string | 任意 | ステータス（デフォルト `active`）                                                    |
| `mine_only`   | bool   | 任意 | `true` の場合は自分がアップロードしたファイルのみ                                    |
| `sort_by`     | string | 任意 | ソートキー（例: `updated_at_desc`）                                                  |
| `page`        | int    | 任意 | ページ番号（1 始まり、デフォルト 1）                                                 |
| `page_size`   | int    | 任意 | 1 ページあたり件数（デフォルト 10, 最大 100）                                        |

**検索ロジックについて:**

- Azure AI Search を利用し、`content` フィールド（Blob から抽出された本文）を含む全文検索を行います。
- フィルタ項目は完全一致です。入力が複数語の場合はそのまま 1 語の扱いになります。
- `mine_only=true` の場合、Blob メタデータに埋め込まれた `owner_id` でフィルタリングします。
- ソートは `updated_at` または `created_at` を指定できます。

サポートされる `sort_by` の例:

- `updated_at_desc`（更新日時 新しい順, デフォルト）
- `updated_at_asc`
- `created_at_desc`
- `created_at_asc`

#### レスポンス

```json
{
  "total_count": 123,
  "files": [
    {
      "id": "uuid-string",
      "file_name": "アプリケーション_課題_...xlsx",
      "application": "アプリケーション",
      "issue": "課題",
      "ingredient": "材料",
      "customer": "顧客",
      "trial_id": "0001",
      "author": "担当者",
      "status": "active",
      "updated_at": "2025-01-20T12:00:00Z",
      "download_link": "https://...SAS..." // Blob への一時URL（ローカルの場合は file:// パス）
    }
  ]
}
```

フロント側では `files` 配列を一覧表示に使い、`total_count` でページネーション総件数を表示できます。

---

### `GET /api/v1/files/suggest`（検索サジェスト）

Azure AI Search の Suggest API をプロキシします。フロント側でサジェスト ON/OFF を切り替え可能。

#### クエリパラメータ

| パラメータ名  | 型     | 必須 | 説明                                            |
| ------------- | ------ | ---- | ----------------------------------------------- |
| `q`           | string | 必須 | サジェスト用の入力文字列（例: `"カル"`）        |
| `top`         | int    | 任意 | 返却件数（デフォルト 8, 最大 20）               |
| `use_suggest` | bool   | 任意 | `true` でサジェスト実行、`false` で空配列を返す |
| `mine_only`   | bool   | 任意 | `true` の場合は自分のファイルのみに限定         |

#### レスポンス

```json
{
  "suggestions": [
    { "text": "カルボナーラソース（TK-2023-001）", "id": "abc123" },
    { "text": "カルビ焼肉のタレ", "id": "def456" }
  ]
}
```

#### 補足

- サジェスター名は `.env` の `AZURE_SEARCH_SUGGESTER_NAME` に設定（デフォルト `nc-suggester`）。
- インデックス側で `suggest_text` フィールドを `sourceFields` に指定したサジェスターを事前に作成してください。
- `mine_only=true` の場合、`owner_id` でフィルタして返します。

---

### `GET /api/v1/files/{file_id}`（ファイルメタデータ取得）

1 件のファイルのメタデータとダウンロードリンクを取得します。  
詳細モーダルや編集画面の初期表示に利用します。

#### パスパラメータ

| パラメータ名 | 型   | 必須 | 説明        |
| ------------ | ---- | ---- | ----------- |
| `file_id`    | UUID | 必須 | ファイル ID |

#### レスポンス

`GET /api/v1/files/search` の `files` 要素と同じ形 (`FileWithLink`) を返します:

```json
{
  "id": "uuid-string",
  "file_name": "アプリケーション_課題_...xlsx",
  "application": "アプリケーション",
  "issue": "課題",
  "ingredient": "材料",
  "customer": "顧客",
  "trial_id": "0001",
  "author": "担当者",
  "status": "active",
  "updated_at": "2025-01-20T12:00:00Z",
  "download_link": "https://..."
}
```

※ 現状は「ログインユーザーが owner のファイルのみ取得可能」です。

---

### `GET /api/v1/files/{file_id}/preview-url`（プレビュー URL 取得）

ファイルのプレビュー用 URL を取得します。Office ファイルは Microsoft Office Online Viewer 形式、PDF は直接リンクを返します。

#### パスパラメータ

| パラメータ名 | 型   | 必須 | 説明        |
| ------------ | ---- | ---- | ----------- |
| `file_id`    | UUID | 必須 | ファイル ID |

#### レスポンス

```json
{
  "preview_url": "https://view.officeapps.live.com/op/embed.aspx?src=...",
  "type": "office" // "office", "pdf", "local", "other"
}
```

---

### `GET /api/v1/files/{file_id}/thumbnail`（サムネイル取得）

ファイルのサムネイル（PNG 画像）を取得します。

#### パスパラメータ

| パラメータ名 | 型   | 必須 | 説明        |
| ------------ | ---- | ---- | ----------- |
| `file_id`    | UUID | 必須 | ファイル ID |

#### レスポンス

`image/png` 形式のバイナリデータ。

---

### `PUT /api/v1/files/{file_id}`（ファイルメタデータ更新）

既存ファイルのメタデータを部分的に更新します。  
送信された項目だけが更新され、送っていない項目はそのまま維持されます。

#### パスパラメータ

| パラメータ名 | 型   | 必須 | 説明        |
| ------------ | ---- | ---- | ----------- |
| `file_id`    | UUID | 必須 | ファイル ID |

#### リクエストボディ（JSON）

すべて任意。更新したい項目だけ送ってください。

```json
{
  "application": "新アプリケーション",
  "issue": "新しい課題感",
  "ingredient": "新しい使用原料",
  "customer": "新しい顧客",
  "trial_id": "0002",
  "author": "別の担当者",
  "status": "inactive"
}
```

#### レスポンス

```json
{
  "message": "File metadata updated successfully",
  "file_id": "uuid-string"
}
```

更新時には `updated_at` が現在時刻に更新されます。

※ 現状は「ログインユーザーが owner のファイルのみ更新可能」です（将来的に管理者ロールチェックに差し替え予定）。

---

### `POST /api/v1/files/{file_id}/download`（ダウンロード URL 取得 & 履歴記録）

ファイルをダウンロードするための URL を取得し、ダウンロード履歴（日時・ユーザー）を記録します。  
フロントエンドでは、この API から返された URL を使用してブラウザでダウンロードを開始させてください。

#### パスパラメータ

| パラメータ名 | 型   | 必須 | 説明        |
| ------------ | ---- | ---- | ----------- |
| `file_id`    | UUID | 必須 | ファイル ID |

#### レスポンス

```json
{
  "download_url": "https://.../files/uuid-filename.xlsx"
  // 開発環境では "file://..." のようなローカルパスが返る場合があります
}
```

---

### `POST /api/v1/files/{file_id}/reference`（参照登録）

検索したファイルに対して「参照した」という意味で、自身の PJ コード（Trial ID）を紐付けます。
既に同じユーザー・同じファイル・同じ Trial ID で登録済みの場合は、既存の登録情報を返します（409 エラーにはなりません）。

#### パスパラメータ

| パラメータ名 | 型   | 必須 | 説明        |
| ------------ | ---- | ---- | ----------- |
| `file_id`    | UUID | 必須 | ファイル ID |

#### リクエストボディ（JSON）

```json
{
  "trial_id": "Trial-2025-B" // 参照元のPJコード（最大50文字）
}
```

#### レスポンス

```json
{
  "id": "uuid-string",
  "file_id": "uuid-string",
  "trial_id": "Trial-2025-B",
  "user_id": 1,
  "created_at": "2025-11-21T12:00:00Z"
}
```

---

### `GET /api/v1/files/dashboard`（ダッシュボード統計情報）

ダッシュボード表示用の統計データを取得します。結果は 1 時間キャッシュされます。

#### レスポンス

```json
{
  "total_files": 150,
  "new_files_last_month": 12,
  "usage_ranking": [
    { "name": "Product A", "count": 45 },
    { "name": "Product B", "count": 30 }
  ],
  "ingredient_ranking": [
    { "name": "Sugar", "count": 50 },
    { "name": "Salt", "count": 20 }
  ],
  "issue_word_cloud": {
    "改善": 15,
    "コスト": 10,
    "風味": 8
  },
  "total_downloads_last_month": 10,
  "download_ranking": [
    { "name": "PopularFile.xlsx", "count": 5 },
    { "name": "DocB.docx", "count": 3 }
  ]
}
```

## テスト

```bash
pytest
```

## 今後の拡張メモ

- Azure AD などの外部 IdP に差し替えられるよう、`app/services/auth_service.py` の抽象化を維持
- ファイル実データは Blob Storage、メタデータは SQL に保存
- Alembic マイグレーションは `app/db/migrations` 配下で管理
