import logging
import os
import sys
import time

from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.models.file import File
from app.db.session import SessionLocal
from app.services.search_service import SearchService

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reindex_all():
    db: Session = SessionLocal()
    search_service = SearchService()

    try:
        logger.info("Starting re-indexing process...")
        
        # 1. インデックス作成（存在しない場合）
        search_service.create_index_if_not_exists()
        
        # 2. 全ファイル取得
        files = db.query(File).all()
        total_files = len(files)
        logger.info(f"Found {total_files} files in database.")
        
        # 3. インデックス登録
        success_count = 0
        error_count = 0
        
        for i, file_obj in enumerate(files):
            try:
                search_service.upsert_document(file_obj)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to index file {file_obj.id}: {e}")
                error_count += 1
                
            # 進捗表示
            if (i + 1) % 50 == 0:
                logger.info(f"Processed {i + 1}/{total_files} files...")
                
        logger.info(f"Re-indexing completed. Success: {success_count}, Errors: {error_count}")
        
    except Exception as e:
        logger.error(f"Fatal error during re-indexing: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    start_time = time.time()
    reindex_all()
    elapsed = time.time() - start_time
    logger.info(f"Total execution time: {elapsed:.2f} seconds")

