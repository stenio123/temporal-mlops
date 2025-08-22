from datetime import timedelta
from typing import Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy

# Per https://docs.temporal.io/develop/python/python-sdk-sandbox?_gl=1*17s2ta*_gcl_au*MTQ5NDk0OTI1MS4xNzUzNzMyNTUzLjEzNTc5MjUwNzkuMTc1NTM3MDczMy4xNzU1MzcwNzQ2*_ga*NDI3ODMwNzkzLjE3NTM3MzI1NTM.*_ga_R90Q9SJD3D*czE3NTU4NjM3MzYkbzI0JGcxJHQxNzU1ODYzNzUxJGo0NSRsMCRoMA..#passthrough-modules
with workflow.unsafe.imports_passed_through():
    from activities.data_processing import preprocess_data
    from activities.training import train_model_mock
    from activities.quality_gate import assess_model_quality
    from activities.deployment import deploy_to_environment

@workflow.defn
class MLOpsWorkflow:
    """Workflow that manages MLOps pipeline."""

    #def __init__(self) -> None:
        # Any initialization configuration here

    @workflow.run
    async def run(self, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main MLOps workflow triggered by file changes
        """
        workflow.logger.info(f"Starting MLOps workflow for: {trigger_data}")
        
        # Step 1: Data Preprocessing
        preprocessing_result = await workflow.execute_activity(
            preprocess_data,
            trigger_data,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_attempts=3
            )
        )
        
        # Step 2: Model Training (mocked for performance)
        training_result = await workflow.execute_activity(
            train_model_mock,
            preprocessing_result,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                maximum_attempts=2
            )
        )
        
        # Step 3: Quality Gate Assessment
        quality_result = await workflow.execute_activity(
            assess_model_quality,
            training_result,
            start_to_close_timeout=timedelta(minutes=2)
        )
        
        # Step 4: Conditional Deployment
        deployment_result = None
        if quality_result["passes_quality_gate"]:
            # Deploy to dev first ("Can we deploy?")
            dev_deployment = await workflow.execute_activity(
                deploy_to_environment,
                ## Unpacking training_result into new dictionary since it will be reused for prod
                {**training_result, "environment": "dev"},
                start_to_close_timeout=timedelta(minutes=5)
            )
            
            # If dev deployment successful and quality metrics are excellent, deploy to prod ("Should we deploy?")
            if (dev_deployment["success"] and 
                quality_result["metrics"]["accuracy"] > 0.85):
                
                deployment_result = await workflow.execute_activity(
                    deploy_to_environment,
                    {**training_result, "environment": "prod"},
                    start_to_close_timeout=timedelta(minutes=5)
                )
            else:
                deployment_result = {"environment": "dev_only", "success": True}
        else:
            workflow.logger.warning("Model failed quality gate - deployment skipped")
            deployment_result = {"environment": "none", "success": False, 
                               "reason": "quality_gate_failed"}
        
        return {
            "preprocessing": preprocessing_result,
            "training": training_result,
            "quality": quality_result,
            "deployment": deployment_result,
            "workflow_status": "completed"
        }