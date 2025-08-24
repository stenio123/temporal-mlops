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
    from activities.experiment_tracking import log_experiment

@workflow.defn
class MLOpsWorkflow:
    """Workflow that manages MLOps pipeline."""

    def __init__(self) -> None:
        self.current_step = ""
        self.step_results = {}
        self.prod_approved = False

    @workflow.signal
    async def approve_prod_deployment(self) -> None:
        """Signal to approve production deployment"""
        workflow.logger.info("✅ Production deployment approved by human")
        self.prod_approved = True

    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """Query current workflow status - useful for monitoring dashboards"""
        # Check for quality gate failure
        quality_failed = False
        deployment_status = "unknown"
        failure_reason = None
        
        if "final_deployment" in self.step_results:
            deployment_result = self.step_results["final_deployment"]
            if deployment_result.get("success") == False:
                quality_failed = True
                failure_reason = deployment_result.get("reason", "unknown")
                deployment_status = "failed"
            else:
                deployment_status = "success"
        elif "prod_deployment" in self.step_results:
            deployment_status = "prod_deployed"
        elif "dev_deployment" in self.step_results:
            deployment_status = "dev_deployed"
        
        # Get quality metrics if available
        quality_metrics = None
        if "quality" in self.step_results:
            quality_metrics = self.step_results["quality"].get("metrics", {})
        
        return {
            "current_step": self.current_step,
            "completed_steps": list(self.step_results.keys()),
            "workflow_id": workflow.info().workflow_id,
            "awaiting_approval": self.current_step == "awaiting_prod_approval",
            "prod_approved": getattr(self, 'prod_approved', False),
            # Quality gate information
            "quality_gate_failed": quality_failed,
            "deployment_status": deployment_status,
            "failure_reason": failure_reason,
            "quality_metrics": quality_metrics
        }

    async def _execute_step(self, step_name: str) -> None:
        """Execute a workflow step with logging"""
        self.current_step = step_name
        workflow.logger.info(f"🔄 Starting step: {step_name}")

    @workflow.run
    async def run(self, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main MLOps workflow with pause/resume capability for demos and approvals
        """
        workflow.logger.info(f"🚀 Starting MLOps workflow for: {trigger_data}")
        
        # Step 1: Data Preprocessing
        await self._execute_step("data_preprocessing")
        preprocessing_result = await workflow.execute_activity(
            preprocess_data,
            trigger_data,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_attempts=3,
                backoff_coefficient=2.0
            )
        )
        self.step_results["preprocessing"] = preprocessing_result
        
        # Step 2: Model Training (mocked for performance)
        await self._execute_step("model_training")
        training_result = await workflow.execute_activity(
            train_model_mock,
            preprocessing_result,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5),
                maximum_attempts=0,  # Retry indefinitely - training is too expensive to lose to transient failures
                backoff_coefficient=2.0,
                maximum_interval=timedelta(minutes=2)  # Cap backoff to avoid excessive delays
            )
        )
        self.step_results["training"] = training_result
        
        # Step 2.5: Log experiment to tracking database (like W&B)
        # Critical step - retry indefinitely for transient failures, fail fast for config issues
        await self._execute_step("experiment_tracking")
        experiment_result = await workflow.execute_activity(
            log_experiment,
            training_result,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                maximum_attempts=0,  # Retry indefinitely for transient failures
                backoff_coefficient=2.0,
                maximum_interval=timedelta(minutes=1)  # Cap backoff at 1 minute
            )
        )
        self.step_results["experiment_tracking"] = experiment_result
        
        # Step 3: Quality Gate Assessment  
        await self._execute_step("quality_assessment")
        quality_result = await workflow.execute_activity(
            assess_model_quality,
            training_result,
            start_to_close_timeout=timedelta(minutes=2),
        )
        self.step_results["quality"] = quality_result
        
        # Step 4: Conditional Deployment
        deployment_result = None
        if quality_result["passes_quality_gate"]:
            # Deploy to dev first ("Can we deploy?")
            await self._execute_step("dev_deployment") 
            dev_deployment = await workflow.execute_activity(
                deploy_to_environment,
                ## Unpacking training_result into new dictionary since it will be reused for prod
                {**training_result, "environment": "dev"},
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    maximum_attempts=3,
                    backoff_coefficient=2.0
                )
            )
            self.step_results["dev_deployment"] = dev_deployment
            
            # If dev deployment successful and quality metrics are excellent, wait for human approval for prod
            if (dev_deployment["success"] and 
                quality_result["metrics"]["accuracy"] > 0.85):
                
                # Human approval gate - wait for signal from UI
                self.current_step = "awaiting_prod_approval"
                workflow.logger.info("🔒 Awaiting human approval for production deployment")
                
                # Wait for approval signal - this is where Streamlit comes in
                await workflow.wait_condition(lambda: self.prod_approved)
                
                await self._execute_step("prod_deployment")
                deployment_result = await workflow.execute_activity(
                    deploy_to_environment,
                    {**training_result, "environment": "prod"},
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=5),
                        maximum_attempts=2,  # More conservative for prod
                        backoff_coefficient=2.0
                    )
                )
                self.step_results["prod_deployment"] = deployment_result
            else:
                deployment_result = {"environment": "dev_only", "success": True}
                self.step_results["final_deployment"] = deployment_result
        else:
            workflow.logger.warning("Model failed quality gate - deployment skipped")
            deployment_result = {"environment": "none", "success": False, 
                               "reason": "quality_gate_failed"}
            self.step_results["final_deployment"] = deployment_result
        
        self.current_step = "completed"
        return {
            "preprocessing": preprocessing_result,
            "training": training_result,
            "quality": quality_result,
            "deployment": deployment_result,
            "workflow_status": "completed"
        }