-- MLOps Experiment Tracking Database
-- Similar to Weights & Biases for tracking model experiments

CREATE TABLE IF NOT EXISTS experiments (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(255) NOT NULL,
    model_id VARCHAR(255) NOT NULL,
    dataset_path VARCHAR(500) NOT NULL,
    training_started_at TIMESTAMP NOT NULL,
    training_completed_at TIMESTAMP,
    
    -- Model hyperparameters
    n_estimators INTEGER,
    max_depth INTEGER,
    random_state INTEGER,
    
    -- Model metrics
    accuracy DECIMAL(5,4),
    mae DECIMAL(6,4),
    r2_score DECIMAL(5,4),
    
    -- Training metadata
    training_samples INTEGER,
    training_time_seconds DECIMAL(6,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for fast lookups by workflow_id
CREATE INDEX IF NOT EXISTS idx_experiments_workflow_id ON experiments(workflow_id);
CREATE INDEX IF NOT EXISTS idx_experiments_model_id ON experiments(model_id);
CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at);

-- Insert a sample experiment for demo
INSERT INTO experiments (
    workflow_id, model_id, dataset_path, training_started_at, training_completed_at,
    n_estimators, max_depth, random_state, accuracy, mae, r2_score,
    training_samples, training_time_seconds
) VALUES (
    'mlops-demo-sample', 'sample_model_123', 'data/processed/sample.csv',
    CURRENT_TIMESTAMP - INTERVAL '1 hour', CURRENT_TIMESTAMP - INTERVAL '59 minutes',
    100, 10, 42, 0.8542, 1.8923, 0.7834,
    4177, 15.6
);