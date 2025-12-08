from pydantic import BaseModel


class DashboardResponse(BaseModel):
    total_files: int
    new_files_last_month: int
    usage_ranking: list[dict[str, int | str]]
    ingredient_ranking: list[dict[str, int | str]]
    issue_word_cloud: dict[str, int]
    download_ranking: list[dict[str, int | str]] = []  # 直近1ヶ月のダウンロード数ランキング
    total_downloads_last_month: int = 0  # 直近1ヶ月の総ダウンロード数
    # 新規追加フィールド
    downloads_this_month: int = 0  # 今月のダウンロード数（今月1日から今日まで）
    top_downloads_last_week: list[dict[str, int | str]] = []  # 先週のダウンロード数Top3
    registration_trend: list[dict[str, int | str]] = []  # 登録件数推移（日付と件数のペア）



