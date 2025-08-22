import asyncio
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from temporalio.client import Client
from workflows.mlops_workflow import MLOpsWorkflow

# This part is not durable - if the watcher process crashes, it wont trigger Temporal.
# The durable part is the MLOps pipeline, which assumes the trigger to start will work.
class MLOpsFileHandler(FileSystemEventHandler):
    def __init__(self, temporal_client, loop):
        self.temporal_client = temporal_client
        self.loop = loop
        
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.csv'):
            print(f"New CSV file detected: {event.src_path}")
            asyncio.run_coroutine_threadsafe(
                self.trigger_workflow(event.src_path), 
                self.loop
            )
    
    async def trigger_workflow(self, file_path):
        """Trigger the MLOps workflow"""
        workflow_id = f"mlops-{int(time.time())}-{Path(file_path).stem}"
        
        await self.temporal_client.start_workflow(
            MLOpsWorkflow.run,
            {"file_path": file_path, "trigger_type": "file_created"},
            id=workflow_id,
            task_queue="mlops-task-queue"
        )
        print(f"Started workflow: {workflow_id}")

async def start_file_watcher():
    """Start watching for file changes"""
    client = await Client.connect("localhost:7233")
    loop = asyncio.get_running_loop()
    
    event_handler = MLOpsFileHandler(client, loop)
    observer = Observer()
    observer.schedule(event_handler, "data/raw", recursive=True)
    observer.start()
    
    print("File watcher started. Drop CSV files in data/raw/ to trigger workflows...")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    asyncio.run(start_file_watcher())