from temporalio import activity
from typing import Dict, Any

@activity.defn
async def assess_model_quality(training_result: Dict[str, Any]) -> Dict[str, Any]:
    """Assess if model meets quality thresholds"""
    
    metrics = training_result["metrics"]
    
    # Define quality thresholds
    QUALITY_THRESHOLDS = {
        "min_accuracy": 0.80,
        "max_mae": 2.5,
        "min_r2": 0.70
    }
    
    # Check each threshold
    checks = {
        "accuracy_check": metrics["accuracy"] >= QUALITY_THRESHOLDS["min_accuracy"],
        "mae_check": metrics["mae"] <= QUALITY_THRESHOLDS["max_mae"],
        "r2_check": metrics["r2_score"] >= QUALITY_THRESHOLDS["min_r2"]
    }
    
    # Python all() function returns True if all true
    passes_quality_gate = all(checks.values())
    
    activity.logger.info(f"Quality gate assessment: {'PASSED' if passes_quality_gate else 'FAILED'}")
    
    return {
        "passes_quality_gate": passes_quality_gate,
        "individual_checks": checks,
        "thresholds": QUALITY_THRESHOLDS,
        "metrics": metrics,
        "model_id": training_result["model_id"]
    }