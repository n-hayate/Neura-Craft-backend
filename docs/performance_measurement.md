# 検索パフォーマンス測定機能

## 概要

検索処理のパフォーマンスを3つの観点から測定し、パーセンタイル（p50/p95）を計算してブラウザコンソールに出力する機能です。

## 測定指標

### 1. End-to-End（E2E）時間
- **定義**: ユーザーが検索を実行（キー入力/検索ボタンクリック）してから、結果が表示されるまでの時間
- **計測場所**: フロントエンド（ブラウザ）
- **計測方法**: `performance.now()`を使用して高精度に計測
- **単位**: ミリ秒（ms）

### 2. Azure Search処理時間
- **定義**: Azure AI Searchが検索クエリを受けて結果を返すまでの純粋な検索処理時間
- **計測場所**: Azure Searchサービス
- **計測方法**: Azure Search REST APIのレスポンスヘッダー`elapsed-time`から取得
- **単位**: ミリ秒（ms）
- **ヘッダー名**: `X-Search-Time-ms`

### 3. Backend処理時間
- **定義**: FastAPIがリクエストを受けてからレスポンスを返すまでのサーバー側の処理時間（ネットワーク時間を除く）
- **計測場所**: FastAPIバックエンド
- **計測方法**: `time.perf_counter()`を使用してエンドポイント内で計測
- **単位**: ミリ秒（ms）
- **ヘッダー名**: `X-Server-Time-ms`

## アーキテクチャ

### データフロー

```
[フロントエンド]
  ↓ E2E計測開始
  ↓
[APIリクエスト] → [FastAPI]
                      ↓ Backend計測開始
                      ↓
                  [Azure Search REST API]
                      ↓ elapsed-time取得
                      ↓
                  [FastAPI]
                      ↓ Backend計測終了
                      ↓ X-Server-Time-ms, X-Search-Time-msをヘッダーに設定
  ↓
[APIレスポンス] ← [FastAPI]
  ↓ E2E計測終了
  ↓
[パフォーマンスデータ収集]
  ↓
[パーセンタイル計算]
  ↓
[コンソール出力]
```

## 実装詳細

### バックエンド実装

#### Azure Search REST API呼び出し

**ファイル**: `app/services/search_service.py`

- `search`メソッドをREST APIで直接呼び出すように実装
- エンドポイント: `POST https://{service}.search.windows.net/indexes/{index}/docs/search?api-version=2023-11-01`
- レスポンスヘッダー`elapsed-time`を取得し、戻り値の3番目の要素として返す

```python
def search(...) -> Tuple[int, List[Dict[str, Any]], Optional[int]]:
    """
    Returns:
        Tuple[total_count, files, search_time_ms]
    """
    response = requests.post(...)
    elapsed_time_ms = int(response.headers.get("elapsed-time", 0))
    return total_count, files, elapsed_time_ms
```

#### FastAPI処理時間の計測

**ファイル**: `app/api/v1/routes_files.py`

- `search_files`エンドポイントで処理開始・終了時刻を記録
- 経過時間をミリ秒単位で計算
- レスポンスヘッダー`X-Server-Time-ms`に設定

```python
@router.get("/search")
def search_files(response: Response, ...):
    server_start_time = time.perf_counter()
    # ... 処理 ...
    server_end_time = time.perf_counter()
    server_time_ms = int((server_end_time - server_start_time) * 1000)
    response.headers["X-Server-Time-ms"] = str(server_time_ms)
    response.headers["X-Search-Time-ms"] = str(search_time_ms)
```

### フロントエンド実装

#### パフォーマンスデータ管理

**ファイル**: `utils/performance.ts`

- `PerformanceCollector`クラスでメモリ内にデータを保持（最大100件）
- 各検索ごとに以下のデータを記録：
  - `e2eTimeMs`: E2E時間（ミリ秒）
  - `searchTimeMs`: Azure Search処理時間（ミリ秒、null可）
  - `serverTimeMs`: Backend処理時間（ミリ秒、null可）
  - `timestamp`: 記録時刻（Unix timestamp）

#### パーセンタイル計算

- p50（中央値）とp95を計算
- 各指標（E2E、Search、Server）ごとに独立して計算
- null値は除外して計算

```typescript
private calculatePercentiles(values: number[]): PercentileStats {
  const sorted = [...values].sort((a, b) => a - b);
  const p50Index = Math.floor(sorted.length * 0.5);
  const p95Index = Math.floor(sorted.length * 0.95);
  return {
    p50: sorted[p50Index] || 0,
    p95: sorted[p95Index] || 0,
  };
}
```

#### E2E計測とコンソール出力

**ファイル**: `app/search/page.tsx`, `app/mobile/search/page.tsx`

- 検索開始時に`performance.now()`で開始時刻を記録
- 検索結果表示完了時に終了時刻を記録
- レスポンスヘッダーから処理時間を取得
- パフォーマンスデータを収集
- コンソールにパーセンタイル統計を出力

```typescript
const performSearch = async () => {
  const e2eStartTime = performance.now();
  
  const result = await filesApi.search({...});
  
  const e2eEndTime = performance.now();
  const e2eTimeMs = Math.round(e2eEndTime - e2eStartTime);
  
  performanceCollector.add({
    e2eTimeMs,
    searchTimeMs: result.headers['X-Search-Time-ms'],
    serverTimeMs: result.headers['X-Server-Time-ms'],
    timestamp: Date.now(),
  });
  
  console.log(formatPerformanceStats());
};
```

## 使用方法

### 1. 検索を実行

通常通り検索機能を使用します。検索ボタンをクリックするか、Enterキーを押して検索を実行します。

### 2. コンソールで確認

ブラウザの開発者ツール（F12）を開き、コンソールタブを確認します。

検索実行後、以下のような形式でパフォーマンス統計が出力されます：

```
検索パフォーマンス:
- E2E: p50=320ms, p95=780ms
- Azure Search: p50=35ms, p95=120ms
- Backend: p50=18ms, p95=45ms
```

### 3. データの蓄積

- パフォーマンスデータはメモリ内に最大100件まで保持されます
- 100件を超えると、古いデータから削除されます
- ページをリロードするとデータはリセットされます

## パフォーマンス指標の解釈

### p50（中央値）
- 全測定値の50%がこの値以下
- 一般的なユーザー体験を表す指標
- 平均値よりも外れ値の影響を受けにくい

### p95（95パーセンタイル）
- 全測定値の95%がこの値以下
- 遅いケースの上限を表す指標
- ユーザー体験のボトルネックを特定するのに有用

### 指標の比較

3つの指標を比較することで、パフォーマンスのボトルネックを特定できます：

- **E2E >> Server + Search**: ネットワーク遅延やフロントエンド処理がボトルネック
- **Search >> Server**: Azure Searchの処理がボトルネック
- **Server >> Search**: バックエンドの追加処理（DBクエリ、Blob処理など）がボトルネック

## 技術的な注意事項

### Azure Search REST API

- SDKの`SearchClient.search()`ではレスポンスヘッダーを直接取得できないため、REST APIで直接呼び出しています
- `search_for_rag`メソッドは既存のSDKを継続使用（パフォーマンス測定不要のため）

### ヘッダー名の大文字小文字

- HTTPヘッダーは大文字小文字を区別しませんが、フロントエンドでは小文字で統一しています
- `X-Search-Time-ms` → `x-search-time-ms`
- `X-Server-Time-ms` → `x-server-time-ms`

### タイムアウト

- Azure Search REST APIのタイムアウト: 30秒
- フロントエンドのAPIリクエストタイムアウト: 30秒

### エラーハンドリング

- Azure Searchの`elapsed-time`ヘッダーが取得できない場合、`searchTimeMs`は`null`になります
- パーセンタイル計算時は`null`値を除外します

## 今後の拡張可能性

- データの永続化（localStorage、IndexedDB、またはバックエンドへの送信）
- リアルタイムダッシュボードでの可視化
- アラート機能（p95が閾値を超えた場合）
- 詳細な分析（時間帯別、クエリ別の統計）
- パフォーマンストレンドの可視化

## 関連ファイル

### バックエンド
- `app/services/search_service.py` - Azure Search REST API実装
- `app/services/file_service.py` - ファイル検索サービス
- `app/api/v1/routes_files.py` - 検索エンドポイント

### フロントエンド
- `utils/performance.ts` - パフォーマンスデータ管理とパーセンタイル計算
- `api/files.ts` - APIクライアント（レスポンスヘッダー取得）
- `app/search/page.tsx` - デスクトップ版検索ページ
- `app/mobile/search/page.tsx` - モバイル版検索ページ

## 参考資料

- [Azure AI Search REST API](https://learn.microsoft.com/azure/search/search-rest-api)
- [Performance API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Performance)
- [Percentile (Wikipedia)](https://en.wikipedia.org/wiki/Percentile)


