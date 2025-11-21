print("Starting script...")
try:
    import app
    print("Imported app")
    from app.core import config
    print("Imported config module")
    settings = config.get_settings()
    print(f"Got settings: {settings.sqlalchemy_database_uri}")
except Exception as e:
    import traceback
    traceback.print_exc()
