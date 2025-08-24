import time
import random
import json
import os
from temporalio import activity
from temporalio.exceptions import ApplicationError
from typing import Dict, Any
import hashlib

@activity.defn
async def train_model_mock(preprocessing_result: Dict[str, Any]) -> Dict[str, Any]:
    """Mock model training with realistic timing and metrics
    
    Note: In production ML training, it's good practice to implement checkpointing
    after certain epochs so training can resume from the last checkpoint rather
    than starting over. This is a concern of the training logic itself, not Temporal.
    Temporal provides workflow durability (retry/recovery of the entire training step),
    while ML frameworks handle intra-training checkpointing for efficiency.
    """
    
    activity.logger.info("Starting mock model training...")
    
    # Only validate the most critical business logic
    if preprocessing_result["num_samples"] < 25:
        raise ApplicationError("Insufficient training data", non_retryable=True)
    
    # Check for failure simulation config
    failure_config_path = "config/failure_simulation.json"
    if os.path.exists(failure_config_path):
        try:
            with open(failure_config_path, 'r') as f:
                failure_config = json.load(f)
            
            if failure_config.get("simulate_failure", False) and failure_config.get("activity") == "training":
                activity.logger.warning("Failure simulation active for training activity")
                raise Exception("Simulated training failure - GPU cluster unavailable")
        except (json.JSONDecodeError, KeyError) as e:
            activity.logger.warning(f"Invalid failure simulation config: {e}")
    
    # Simulate occasional infrastructure failures that should retry (reduced chance when demo mode)
    # In production: GPU OOM, preemption, network issues, etc.
    failure_chance = 0.01  
    if random.random() < failure_chance:
        raise Exception("GPU temporarily unavailable")  # Let Temporal handle as retryable
    
    # Simulate training time (2-5 seconds instead of hours)
    training_time = random.uniform(15, 25)
    time.sleep(training_time)
    
    # Add proprietary configuration - this contains sensitive business logic
    # In production, these would be competitive advantages not visible in logs
    proprietary_config = {
        "secret_learning_rate_multiplier": 1.337,  # Proprietary optimization
        "custom_regularization_alpha": 0.00042,    # Trade secret parameter  
        "advanced_dropout_schedule": "exponential_secret",  # Proprietary technique
        "internal_model_architecture": "CompanyXL_v2.1"     # Confidential architecture
    }
    
    activity.logger.info(f"Training with proprietary config: {proprietary_config}")
    
    # Generate deterministic metrics based on file content for demo predictability
    file_path = preprocessing_result.get("processed_file_path", "")
    # Use a stable hash function from hashlib
    sha256 = hashlib.sha256(file_path.encode()).hexdigest()
    # Convert the hex hash to an integer for the seed
    seed = int(sha256, 16) % 10000000
    random.seed(seed)
    
    # Create predictable scenarios based on filename
    filename = os.path.basename(file_path).lower()
    
    if "good" in filename:
        # Good model scenario - will pass quality gate
        accuracy = random.uniform(0.85, 0.92)
        mae = random.uniform(1.2, 2.0)
        r2_score = random.uniform(0.75, 0.88)
    elif "bad" in filename:
        # Bad model scenario - will fail quality gate
        accuracy = random.uniform(0.70, 0.78)
        mae = random.uniform(2.6, 3.5)
        r2_score = random.uniform(0.60, 0.68)
    else:
        # Default to moderate performance (might pass or fail)
        accuracy = random.uniform(0.78, 0.85)
        mae = random.uniform(2.0, 2.6)
        r2_score = random.uniform(0.68, 0.75)
    
    # Simulate model artifact creation
    model_id = f"abalone_model_{int(time.time())}"
    model_path = f"models/{model_id}.joblib"
    
    # Mock saving model (just create a placeholder file)
    os.makedirs("models", exist_ok=True)
    with open(model_path, "w") as f:
        json.dump({
            "model_type": "RandomForestRegressor",
            "hyperparameters": {
                "n_estimators": random.choice([50, 100, 200]),
                "max_depth": random.choice([5, 10, 15]),
                "random_state": 42
            },
            "training_data": preprocessing_result["processed_file_path"],
            "trained_at": time.time()
        }, f)
    
    return {
        "model_id": model_id,
        "model_path": model_path,
        "metrics": {
            "accuracy": accuracy,
            "mae": mae,
            "r2_score": r2_score,
            "training_samples": preprocessing_result["num_samples"]
        },
        "training_time_seconds": training_time,
        "training_completed": True,
        "proprietary_config": proprietary_config
    }