import sys
import os
from alembic.config import Config
from alembic import command

# Make sure we are in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

alembic_cfg = Config("alembic.ini")

print("Running alembic revision...")
try:
    command.revision(alembic_cfg, message="add_download_count_and_file_reference", autogenerate=True)
    print("Revision generated.")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

