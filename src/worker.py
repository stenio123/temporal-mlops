import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

# Import workflow and activities
from workflows.mlops_workflow import MLOpsWorkflow
from activities.data_processing import preprocess_data
from activities.training import train_model_mock
from activities.quality_gate import assess_model_quality
from activities.deployment import deploy_to_environment

async def main():
    """Start the Temporal worker"""
    
    # Connect to Temporal server
    client = await Client.connect("localhost:7233")
    
    # Create worker
    worker = Worker(
        client,
        task_queue="mlops-task-queue",
        workflows=[MLOpsWorkflow],
        activities=[
            preprocess_data,
            train_model_mock,
            assess_model_quality,
            deploy_to_environment,
        ],
    )
    
    print("🚀 MLOps Temporal worker started!")
    print("Task queue: mlops-task-queue")
    print("Press Ctrl+C to stop...")
    
    # Run the worker
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())