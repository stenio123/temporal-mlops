import pandas as pd
import os
from temporalio import activity
from typing import Dict, Any

@activity.defn
async def preprocess_data(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    """Preprocess abalone dataset"""
    file_path = trigger_data["file_path"]
    
    activity.logger.info(f"Processing data file: {file_path}")
    
    # Load abalone dataset
    df = pd.read_csv(file_path, names=[
        'sex', 'length', 'diameter', 'height', 'whole_weight',
        'shucked_weight', 'viscera_weight', 'shell_weight', 'rings'
    ])
    
    # Simulate preprocessing steps
    # Convert sex to numeric
    df['sex_numeric'] = df['sex'].map({'M': 0, 'F': 1, 'I': 2})
    
    # Create target variable (age = rings + 1.5)
    df['age'] = df['rings'] + 1.5
    
    # Basic feature engineering
    df['weight_ratio'] = df['shucked_weight'] / df['whole_weight']
    df['volume_estimate'] = df['length'] * df['diameter'] * df['height']
    
    # Save processed data
    processed_path = file_path.replace('/raw/', '/processed/')
    os.makedirs(os.path.dirname(processed_path), exist_ok=True)
    df.to_csv(processed_path, index=False)
    
    return {
        "processed_file_path": processed_path,
        "original_file_path": file_path,
        "num_samples": len(df),
        "num_features": len(df.columns),
        "processing_completed": True
    }