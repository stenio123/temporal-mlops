import asyncio
import dataclasses
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.converter import default

# Import workflow and activities
from workflows.mlops_workflow import MLOpsWorkflow
from activities.data_processing import preprocess_data
from activities.training import train_model_mock
from activities.quality_gate import assess_model_quality
from activities.deployment import deploy_to_environment
from activities.experiment_tracking import log_experiment

# Import encryption codec
from encryption.encryption import create_encrypted_data_converter

async def main():
    """Start the Temporal worker with encryption enabled"""

    data_converter = create_encrypted_data_converter()
    # Connect to Temporal server with encryption codec
    client = await Client.connect(
        "localhost:7233",
        data_converter=data_converter
    )
    
    # Create worker with encryption
    worker = Worker(
        client,
        task_queue="mlops-task-queue",
        workflows=[MLOpsWorkflow],
        activities=[
            preprocess_data,
            train_model_mock,
            assess_model_quality,
            deploy_to_environment,
            log_experiment,
        ],
        # Worker also uses the encrypted data converter
        # retrieved automatically from Client in newer versions of Temporal
        # data_converter=data_converter
    )
    
    print("🔐 MLOps Temporal worker started with ENCRYPTION enabled!")
    print("Task queue: mlops-task-queue")
    print("Encryption: Simple demo codec active")
    print("Press Ctrl+C to stop...")
    
    # Run the worker
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())