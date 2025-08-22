import time
import random
import json
import os
from temporalio import activity
from typing import Dict, Any

@activity.defn
async def train_model_mock(preprocessing_result: Dict[str, Any]) -> Dict[str, Any]:
    """Mock model training with realistic timing and metrics"""
    
    activity.logger.info("Starting mock model training...")
    
    # Simulate training time (2-5 seconds instead of hours)
    training_time = random.uniform(2, 5)
    time.sleep(training_time)
    
    # Generate realistic but mock metrics
    accuracy = random.uniform(0.75, 0.92)
    mae = random.uniform(1.2, 2.8)
    r2_score = random.uniform(0.65, 0.88)
    
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
        "training_completed": True
    }