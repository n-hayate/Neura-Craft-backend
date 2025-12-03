import os
import shutil

target = "uploads"
if os.path.exists(target):
    print(f"Cleaning {target}...")
    for item in os.listdir(target):
        path = os.path.join(target, item)
        try:
            if os.path.isfile(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            print(f"Error {item}: {e}")
    print("Done cleaning uploads.")
else:
    print("Uploads dir not found.")

