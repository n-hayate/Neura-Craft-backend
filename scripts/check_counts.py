import sys
import os

print("Step 1: Imports started", flush=True)
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print("Step 2: Sys path added", flush=True)
    
    from app.db.session import SessionLocal
    print("Step 3: SessionLocal imported", flush=True)
    
    from app.db.models import User, File
    print("Step 4: Models imported", flush=True)

    print("Step 5: Connecting to DB...", flush=True)
    db = SessionLocal()
    print("Step 6: DB Connected", flush=True)
    
    count = db.query(User).count()
    print(f"Users: {count}", flush=True)
    
    db.close()

except Exception as e:
    print(f"Error: {e}", flush=True)
