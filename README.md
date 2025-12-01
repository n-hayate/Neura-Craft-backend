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

| 変数                              | 説明                                      |
| --------------------------------- | ----------------------------------------- |
| `APP_ENV`                         | `development` / `production` などの環境名 |
| `SECRET_KEY`                      | JWT 署名キー                              |
| `ACCESS_TOKEN_EXPIRE_MINUTES`     | アクセストークン有効期限                  |
| `SQLALCHEMY_DATABASE_URI`         | DB 接続文字列（開発では SQLite でも可）   |
| `AZURE_STORAGE_ACCOUNT_NAME`      | ストレージアカウント名                    |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob 接続文字列                           |
| `AZURE_BLOB_FILES_CONTAINER`      | ファイル格納コンテナ                      |
| `AZURE_BLOB_THUMBNAILS_CONTAINER` | サムネイル格納コンテナ                    |
| `LOCAL_STORAGE_PATH`              | 開発時にファイルを保存するローカルパス    |
| `SEARCH_BACKEND`                  | 検索エンジン (`azure` or `sql`)           |
| `AZURE_SEARCH_ENDPOINT`           | Azure AI Search エンドポイント URL        |
| `AZURE_SEARCH_API_KEY`            | Azure AI Search API キー (Admin Key)      |
| `AZURE_SEARCH_INDEX_NAME`         | インデックス名 (例: `files-index`)        |

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
  - 以降のファイルアップロードは Azure Blob Storage に保存され、DB には Blob の URL が格納される

## Azure AI Search の設定

本プロジェクトでは、検索エンジンとして **Azure AI Search** を推奨しています。

### 有効化手順

1. Azure Portal で Azure AI Search リソースを作成する。
2. `.env` に以下の変数を設定する。
   ```bash
   SEARCH_BACKEND=azure
   AZURE_SEARCH_ENDPOINT=https://<your-service-name>.search.windows.net
   AZURE_SEARCH_API_KEY=<admin-key>
   AZURE_SEARCH_INDEX_NAME=files-index
   ```
3. 既存データがある場合、以下のスクリプトを実行してインデックスを作成・データ登録する。
   ```bash
   python scripts/reindex_search.py
   ```

※ `SEARCH_BACKEND=sql` (または未設定) の場合、従来の SQL `LIKE` 検索が動作します。
※ Azure Search の設定が正しくない場合や接続エラー時は、自動的に SQL 検索にフォールバックします。

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

---

### `GET /api/v1/files/search`（ファイル検索）

ファイル名およびメタデータで検索・絞り込みするエンドポイントです。  
画面の検索バー + 絞り込みフィルタ用に利用します。

#### クエリパラメータ

| パラメータ名    | 型     | 必須 | 説明                                                                                              |
| --------------- | ------ | ---- | ------------------------------------------------------------------------------------------------- |
| `q`             | string | 任意 | ファイル名および全メタデータ（課題、原料等）の部分一致・横断検索（スペース区切りで AND 検索対応） |
| `final_product` | string | 任意 | 最終製品名での部分一致（スペース区切りで AND 検索対応）                                           |
| `issue`         | string | 任意 | 課題感での部分一致（スペース区切りで AND 検索対応）                                               |
| `ingredient`    | string | 任意 | 使用原料での部分一致（スペース区切りで AND 検索対応）                                             |
| `customer`      | string | 任意 | 提案企業での部分一致（スペース区切りで AND 検索対応）                                             |
| `trial_id`      | string | 任意 | 試作 ID での部分一致                                                                              |
| `author`        | string | 任意 | 開発担当者名での部分一致                                                                          |
| `sort_by`       | string | 任意 | ソートキー（例: `updated_at_desc`）                                                               |
| `page`          | int    | 任意 | ページ番号（1 始まり、デフォルト 1）                                                              |
| `page_size`     | int    | 任意 | 1 ページあたり件数（デフォルト 10, 最大 100）                                                     |

**検索ロジックについて:**

- `q` パラメータは、ファイル名だけでなく、メタデータ（製品名、課題、原料、顧客名、試作 ID、作成者）も対象に検索します。
- スペース区切りで複数のキーワードを指定した場合、**AND 検索**となります（すべてのキーワードを含むレコードがヒット）。
  - 例: `q="塩味 改善"` → 「塩味」と「改善」の両方が（ファイル名またはメタデータのどこかに）含まれるファイルを検索。
- 各絞り込みフィールド（`issue` など）も同様にスペース区切りで AND 検索が可能です。

サポートされる `sort_by` の例:

- `updated_at_desc`（更新日時 新しい順, デフォルト）
- `updated_at_asc`
- `final_product_asc`
- `final_product_desc`
- `created_at_desc`
- `created_at_asc`

#### レスポンス

```json
{
  "total_count": 123,
  "files": [
    {
      "id": "uuid-string",
      "file_name": "example.xlsx",
      "final_product": "最終製品名",
      "issue": "課題感",
      "ingredient": "使用原料",
      "customer": "提案企業",
      "trial_id": "0001",
      "author": "開発担当者名",
      "status": "active",
      "updated_at": "2025-01-20T12:00:00Z",
      "download_link": "https://..." // Blob への URL（開発環境では file:// パス）
    }
  ]
}
```

フロント側では `files` 配列を一覧表示に使い、`total_count` でページネーション総件数を表示できます。

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
  "file_name": "example.xlsx",
  "final_product": "最終製品名",
  "issue": "課題感",
  "ingredient": "使用原料",
  "customer": "提案企業",
  "trial_id": "0001",
  "author": "開発担当者名",
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
  "final_product": "新しい最終製品名",
  "issue": "新しい課題感",
  "ingredient": "新しい使用原料",
  "customer": "新しい提案企業",
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

### `POST /api/v1/files/{file_id}/download`（ダウンロード URL 取得 & カウント）

ファイルをダウンロードするための URL を取得し、ダウンロード回数をカウントアップします。
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
  }
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
