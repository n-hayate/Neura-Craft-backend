from collections import Counter
from datetime import datetime, timedelta
from functools import lru_cache
import time

from sqlalchemy import func
from sqlalchemy.orm import Session
from janome.tokenizer import Tokenizer

from app.db.models.file import File
from app.schemas.dashboard import DashboardResponse

# 簡易的なキャッシュ機構（本番ではRedis等が望ましいが、今回はメモリキャッシュで実装）
class DashboardCache:
    _cache: dict = {}
    _last_updated: float = 0
    _ttl: int = 3600  # 1時間

    @classmethod
    def get(cls):
        if time.time() - cls._last_updated < cls._ttl:
            return cls._cache
        return None

    @classmethod
    def set(cls, data: dict):
        cls._cache = data
        cls._last_updated = time.time()

class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.tokenizer = Tokenizer()
        # ストップワードの定義
        self.stop_words = {
            'て', 'に', 'を', 'は', 'の', 'が', 'と', 'で', 'も', 'な', 'や', 'し', 'か', 'た', 'だ', 
            'ある', 'いる', 'する', 'なる', 'れる', 'られる', 'こと', 'もの', 'よう', 'ため', 'それ', 
            'これ', 'あれ', 'さん', 'さま', 'くん', 'ちゃん', 'ます', 'です', 'など', '等', '・', '、', '。'
        }

    def get_dashboard_data(self) -> DashboardResponse:
        # キャッシュ確認
        cached = DashboardCache.get()
        if cached:
            return DashboardResponse(**cached)

        # データ集計
        total_files = self.db.query(func.count(File.id)).filter(File.status == 'active').scalar()
        
        last_month = datetime.now() - timedelta(days=30)
        new_files = self.db.query(func.count(File.id)).filter(
            File.status == 'active',
            File.created_at >= last_month
        ).scalar()

        usage_ranking = self._get_ranking(File.application)
        ingredient_ranking = self._get_ranking(File.ingredient)
        download_ranking = self._get_download_ranking()
        
        # 総ダウンロード数（直近1ヶ月）
        from app.db.models.file_download import FileDownload
        total_downloads_last_month = self.db.query(func.count(FileDownload.id)).filter(
            FileDownload.downloaded_at >= last_month
        ).scalar() or 0
        
        # 新規追加: 今月のダウンロード数
        downloads_this_month = self._get_downloads_this_month()
        
        # 新規追加: 先週のダウンロード数Top3
        top_downloads_last_week = self._get_top_downloads_last_week()
        
        # 新規追加: 登録件数推移
        registration_trend = self._get_registration_trend()
        
        word_cloud = self._generate_word_cloud()

        response_data = {
            "total_files": total_files,
            "new_files_last_month": new_files,
            "usage_ranking": usage_ranking,
            "ingredient_ranking": ingredient_ranking,
            "download_ranking": download_ranking,
            "total_downloads_last_month": total_downloads_last_month,
            "downloads_this_month": downloads_this_month,
            "top_downloads_last_week": top_downloads_last_week,
            "registration_trend": registration_trend,
            "issue_word_cloud": word_cloud
        }

        # キャッシュ更新
        DashboardCache.set(response_data)

        return DashboardResponse(**response_data)

    def _get_ranking(self, column, limit: int = 5) -> list[dict]:
        results = (
            self.db.query(column, func.count(column).label('count'))
            .filter(File.status == 'active', column.isnot(None))
            .group_by(column)
            .order_by(func.count(column).desc())
            .limit(limit)
            .all()
        )
        return [{"name": r[0], "count": r[1]} for r in results]

    def _get_download_ranking(self, limit: int = 5) -> list[dict]:
        from app.db.models.file_download import FileDownload
        
        last_month = datetime.now() - timedelta(days=30)
        
        results = (
            self.db.query(File.original_name, func.count(FileDownload.id).label('count'))
            .join(FileDownload, File.id == FileDownload.file_id)
            .filter(FileDownload.downloaded_at >= last_month)
            .group_by(File.id, File.original_name)
            .order_by(func.count(FileDownload.id).desc())
            .limit(limit)
            .all()
        )
        return [{"name": r[0], "count": r[1]} for r in results]

    def _get_downloads_this_month(self) -> int:
        """今月のダウンロード数を取得（今月1日00:00:00から今日23:59:59まで）"""
        from app.db.models.file_download import FileDownload
        
        now = datetime.now()
        # 今月1日の00:00:00
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        count = self.db.query(func.count(FileDownload.id)).filter(
            FileDownload.downloaded_at >= start_of_month
        ).scalar() or 0
        
        return count

    def _get_top_downloads_last_week(self, limit: int = 3) -> list[dict]:
        """先週のダウンロード数Top3を取得（先週月曜日00:00:00から先週日曜日23:59:59まで）"""
        from app.db.models.file_download import FileDownload
        
        now = datetime.now()
        # 今日が何曜日か（0=月曜日、6=日曜日）
        days_since_monday = now.weekday()
        # 先週の月曜日を計算（今日から7日前の週の月曜日）
        days_to_last_monday = days_since_monday + 7
        last_monday = now - timedelta(days=days_to_last_monday)
        last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        # 先週の日曜日（先週月曜日から6日後）
        last_sunday = last_monday + timedelta(days=6)
        last_sunday = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        results = (
            self.db.query(File.original_name, func.count(FileDownload.id).label('count'))
            .join(FileDownload, File.id == FileDownload.file_id)
            .filter(
                FileDownload.downloaded_at >= last_monday,
                FileDownload.downloaded_at <= last_sunday
            )
            .group_by(File.id, File.original_name)
            .order_by(func.count(FileDownload.id).desc())
            .limit(limit)
            .all()
        )
        return [{"name": r[0], "count": r[1]} for r in results]

    def _get_registration_trend(self, days: int = 30) -> list[dict]:
        """登録件数推移を取得（過去N日間の日付ごとの集計）"""
        from sqlalchemy import cast, Date
        
        # 過去N日間の開始日時
        start_date = datetime.now() - timedelta(days=days)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 日付ごとに集計
        results = (
            self.db.query(
                cast(File.created_at, Date).label('date'),
                func.count(File.id).label('count')
            )
            .filter(
                File.status == 'active',
                File.created_at >= start_date
            )
            .group_by(cast(File.created_at, Date))
            .order_by(cast(File.created_at, Date).asc())
            .all()
        )
        
        # 日付を文字列形式（YYYY-MM-DD）に変換
        return [
            {"date": r[0].strftime("%Y-%m-%d"), "count": r[1]}
            for r in results
            if r[0] is not None
        ]

    def _generate_word_cloud(self, limit: int = 50) -> dict[str, int]:
        # issueフィールドのテキストを全取得
        issues = self.db.query(File.issue).filter(File.status == 'active').all()
        text_data = " ".join([i[0] for i in issues if i[0]])

        words = []
        for token in self.tokenizer.tokenize(text_data):
            # 名詞のみ抽出
            if token.part_of_speech.split(',')[0] == '名詞':
                word = token.base_form
                if word not in self.stop_words and len(word) > 1 and not word.isdigit():
                    words.append(word)

        counter = Counter(words)
        return dict(counter.most_common(limit))

