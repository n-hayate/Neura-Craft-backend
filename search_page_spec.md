# Search Page Specification (食品開発ナレッジ検索)

## 1. Screen Specification Box

### ページの目的

- 過去の実験レポートや技術資料（ナレッジ）を検索・閲覧し、業務に活用する。
- ファイルのプレビュー確認とダウンロードを行う。

### 使用する API 一覧

| 用途             | Method | Endpoint                              | 備考                             |
| ---------------- | ------ | ------------------------------------- | -------------------------------- |
| **検索**         | `GET`  | `/api/v1/files/search`                | キーワード・フィルタ・ソート     |
| **プレビュー**   | `GET`  | `/api/v1/files/{file_id}/preview-url` | Office/PDF 等の表示用 URL 取得   |
| **ダウンロード** | `POST` | `/api/v1/files/{file_id}/download`    | 署名付き DL リンク生成・履歴記録 |

### 検索パラメータ (Query Params)

- `q`: 文字列 (キーワード検索)
- `application`: 文字列 (最終製品: 中華まん, うどん等)
- `issue`: 文字列 (課題感: ふわふわ, コシ等)
- `ingredient`: 文字列 (使用原料)
- `customer`: 文字列 (顧客名)
- `author`: 文字列 (担当者名)
- `sort_by`: 文字列 (デフォルト: `updated_at_desc`)
- `page`: 数値 (デフォルト: 1)
- `page_size`: 数値 (デフォルト: 10)

### 必要なデータ構造 (Response Type)

API レスポンス (`FileSearchResponse`) に基づく。

```typescript
interface SearchResult {
  total_count: number;
  files: {
    id: string;
    file_name: string; // 表示名
    application?: string | null; // Tag: 最終製品
    issue?: string | null; // Tag: 課題感
    ingredient?: string | null; // Tag: 使用原料
    customer?: string | null; // Tag: 顧客
    author?: string | null; // Tag: 担当者
    updated_at?: string | null; // 更新日
    download_link?: string | null;
    download_count: number; // ダウンロード数
    is_preview_hidden: boolean; // プレビュー不可フラグ (機密ファイル等)
  }[];
}
```

### 状態管理 (States)

- **Loading**: 検索実行中、スケルトンスクリーンまたはスピナーを表示。
- **Empty**: 検索結果 0 件の場合、「条件に一致するナレッジは見つかりませんでした」を表示。
- **Error**: API エラー時、トーストまたはアラートで通知。

### エッジケース

- **プレビュー不可**: ファイル形式によりプレビュー非対応の場合は「ダウンロードして確認」を促す。
- **機密ファイル**: `is_preview_hidden` フラグが立っているファイルはプレビュー操作を禁止し、ダウンロードのみ許可する。
- **Office ファイル**: `preview-url` API が Office Online Viewer の URL を返すため、iframe 等で埋め込むか別タブで開く。

---

## 2. Component Notes

### SearchBar

- **Props**: `initialQuery` (string)
- **Event**: `onSearch(query: string)`
- **挙動**: Enter キー押下または検索ボタンクリックで検索実行。空文字検索も許可（全件表示）。

### FilterPanel (または Chips)

- **Items**: 最終製品、課題感、使用原料、顧客、担当者
- **挙動**: 各条件変更時に即時検索、または検索ボタン押下時にパラメータに含める。

### SearchResultCard (リストアイテム)

- **Props**: `file: FileWithLink`
- **Tags 表示**: `application`, `issue`, `ingredient`, `customer`, `author` が存在する場合のみバッジを表示。
- **Action: 詳細確認 (Preview)**
  - ボタン: 「プレビュー」or「配合詳細の確認」
  - **表示制御**: `is_preview_hidden` が `true` の場合、ボタンを非表示にするか無効化する（「プレビュー不可」ツールチップ等）。
  - `GET /preview-url` をコールし、返却された URL を別タブまたはモーダルで開く。
- **Action: ダウンロード**
  - ボタン: 「ダウンロード」
  - 表示: ボタン横またはバッジとして「ダウンロード数」を表示（例: ⬇️ 15）
  - 挙動: `POST /download` をコールし、`download_url` を取得して遷移。成功時に表示カウントを+1 する (Optimistic Update)。
    - ※参考: API レスポンスには `download_count` が含まれるため、初期表示はこれを使用。

### Pagination

- **Props**: `currentPage`, `totalCount`, `pageSize`
- **Event**: `onPageChange(page: number)`
- **計算**: 総ページ数 = `Math.ceil(totalCount / pageSize)`

---

## 3. Flow Notes

### ユーザー操作フロー

1. **初期表示**

   - `useEffect` で初期検索を実行（パラメータなし or 前回の条件）。
   - ローディング表示 → 結果リスト描画。

2. **検索実行**

   - キーワード入力 / フィルタ変更 → 「検索」ボタン。
   - API: `GET /files/search?q=...&page=1` をコール。
   - リストをリセットし、結果を表示。

3. **プレビューフロー**

   - カード内の「プレビュー」クリック。
   - API: `GET /files/{id}/preview-url` コール。
   - レスポンス (`{ preview_url, type }`) を確認。
   - `type === 'office'` なら Office Online Viewer で表示。

4. **ダウンロードフロー**
   - カード内の「ダウンロード」クリック。
   - API: `POST /files/{id}/download` コール (ここで DL 履歴がサーバーに残る)。
   - レスポンスの `download_url` (SAS 付き) を使用してブラウザでダウンロード開始。
   - （UI 更新）該当ファイルのダウンロード数表示をインクリメント。
