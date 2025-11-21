import sys
from sqlalchemy import create_engine, inspect
from app.core.config import get_settings

try:
    settings = get_settings()
    engine = create_engine(settings.sqlalchemy_database_uri)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables: {tables}")
    
    if "file_references" in tables:
        cols = [c['name'] for c in inspector.get_columns("file_references")]
        print(f"file_references columns: {cols}")
        
    if "files" in tables:
        cols = [c['name'] for c in inspector.get_columns("files")]
        print(f"files columns: {cols}")
        
except Exception as e:
    print(f"Error: {e}")

