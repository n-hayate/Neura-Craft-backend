import os
import shutil
import sys

def cleanup_local_files():
    print("Cleaning local uploads...", flush=True)
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    print(f"Target directory: {uploads_dir}", flush=True)
    
    if os.path.exists(uploads_dir):
        count = 0
        for item in os.listdir(uploads_dir):
            item_path = os.path.join(uploads_dir, item)
            try:
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                    count += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    count += 1
            except Exception as e:
                print(f"Error deleting {item}: {e}", flush=True)
        print(f"Deleted {count} files/dirs from uploads.", flush=True)
    else:
        print("Uploads directory not found.", flush=True)

if __name__ == "__main__":
    cleanup_local_files()

