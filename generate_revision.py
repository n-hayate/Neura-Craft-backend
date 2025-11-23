import sys
import os
from alembic.config import Config
from alembic import command

os.chdir(os.path.dirname(os.path.abspath(__file__)))
alembic_cfg = Config("alembic.ini")

print("Generating revision...")
try:
    # script.py.mako が app/db/migrations にあるか確認
    print(f"Config script location: {alembic_cfg.get_main_option('script_location')}")
    
    revision = command.revision(alembic_cfg, message="fix_varchar_to_nvarchar", autogenerate=True)
    print(f"Revision generated: {revision}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

