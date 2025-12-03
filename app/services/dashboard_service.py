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
        
        word_cloud = self._generate_word_cloud()

        response_data = {
            "total_files": total_files,
            "new_files_last_month": new_files,
            "usage_ranking": usage_ranking,
            "ingredient_ranking": ingredient_ranking,
            "download_ranking": download_ranking,
            "total_downloads_last_month": total_downloads_last_month,
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

