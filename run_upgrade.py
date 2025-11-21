import sys
import os
from alembic.config import Config
from alembic import command

os.chdir(os.path.dirname(os.path.abspath(__file__)))
alembic_cfg = Config("alembic.ini")

print("Running alembic upgrade head...")
try:
    command.upgrade(alembic_cfg, "head")
    print("Upgrade completed.")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

