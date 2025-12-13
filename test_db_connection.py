from app.core.config import get_settings
from sqlalchemy import create_engine, text

settings = get_settings()
engine = create_engine(settings.sqlalchemy_database_uri, pool_pre_ping=True)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("接続成功:", result.fetchone())
except Exception as e:
    print("接続エラー:", e)







