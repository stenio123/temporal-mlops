import time
import yaml
import os
import json
import random
from temporalio import activity
from typing import Dict, Any

@activity.defn
async def deploy_to_environment(deployment_data: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy model to specified environment"""
    
    environment = deployment_data["environment"]
    model_id = deployment_data["model_id"]
    
    activity.logger.info(f"Deploying {model_id} to {environment}")
    
    # Load environment config
    with open(f"config/{environment}.yml", "r") as f:
        env_config = yaml.safe_load(f)

    # Simulate occasional deployment failures that should retry
    if random.random() < 0.1:
        raise Exception(f"Deployment service temporarily unavailable")
    
    
    # Simulate deployment steps
    # We are grouping all the steps within this activity to simplify the workflow and minimize network calls.
    # In real world these could be part of a child workflow if any of the steps require unique timeouts, different retry policies,
    # manual approvals or more sophisticated behavior. For this MLOps PoC we are considering that if one of these steps fails, the Activity 
    # should resume from the start and not maintain state.
    steps = [
        "Creating deployment package",
        "Uploading to container registry",
        "Updating service configuration",
        "Rolling deployment",
        "Health checks"
    ]
    
    for step in steps:
        activity.logger.info(f"  - {step}")
        time.sleep(0.5)  # Simulate work
    
    # Mock deployment result
    deployment_url = f"http://{env_config['host']}/models/{model_id}/predict"
    
    return {
        "success": True,
        "environment": environment,
        "model_id": model_id,
        "deployment_url": deployment_url,
        "deployed_at": time.time(),
        "config": env_config
    }