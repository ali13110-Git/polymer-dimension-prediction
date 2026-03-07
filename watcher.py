import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from r2_uploader import upload_to_r2  # Import your uploader logic

# --- CONFIGURATION ---
WATCH_FOLDER = "/home/tunnel/dimension_project/reports"
os.makedirs(WATCH_FOLDER, exist_ok=True)

class ReportHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".pdf"):
            filename = os.path.basename(event.src_path)
            print(f"📂 New file detected: {filename}. Starting upload...")
            # Wait 1 second to ensure the file is fully saved to disk
            time.sleep(1)
            upload_to_r2(event.src_path, filename)

if __name__ == "__main__":
    event_handler = ReportHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_FOLDER, recursive=False)
    
    print(f"👀 Watching for new PDF reports in: {WATCH_FOLDER}")
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
