import sys
import os

print("Start cleanup script", flush=True)

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)
print(f"Added to path: {root_dir}", flush=True)

try:
    from app.db.session import SessionLocal
    print("SessionLocal imported", flush=True)
    from app.db.models import User, File, FileReference, FileDownload
    print("Models imported", flush=True)
except Exception as e:
    print(f"Import Error: {e}", flush=True)
    sys.exit(1)

def run():
    db = SessionLocal()
    try:
        print("Deleting FileDownloads...", flush=True)
        db.query(FileDownload).delete()
        
        print("Deleting FileReferences...", flush=True)
        db.query(FileReference).delete()
        
        print("Deleting Files...", flush=True)
        db.query(File).delete()
        
        print("Deleting Users...", flush=True)
        db.query(User).delete()
        
        db.commit()
        print("Cleanup Committed!", flush=True)
    except Exception as e:
        print(f"DB Error: {e}", flush=True)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run()
