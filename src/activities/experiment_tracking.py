import psycopg2
import psycopg2.errors
import time
from datetime import datetime
from temporalio import activity
from temporalio.exceptions import ApplicationError
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@activity.defn
async def log_experiment(training_result: Dict[str, Any]) -> Dict[str, Any]:
    """Log experiment metadata to tracking database (like Weights & Biases)"""
    
    activity.logger.info("📊 Logging experiment to tracking database...")
    
    # Database connection parameters from environment
    conn_params = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'mlops_tracking'),
        'user': os.getenv('POSTGRES_USER', 'mlops'),
        'password': os.getenv('POSTGRES_PASSWORD', 'mlops123')
    }
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Extract data from training result
        model_id = training_result["model_id"]
        metrics = training_result["metrics"]
        
        # Read model metadata from file for hyperparameters
        import json
        model_path = training_result["model_path"]
        with open(model_path, 'r') as f:
            model_data = json.load(f)
        
        hyperparams = model_data.get("hyperparameters", {})
        
        # Insert experiment record - focus on training metrics only
        insert_query = """
            INSERT INTO experiments (
                workflow_id, model_id, dataset_path, training_started_at, training_completed_at,
                n_estimators, max_depth, random_state, 
                accuracy, mae, r2_score,
                training_samples, training_time_seconds
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s
            ) RETURNING id;
        """
        
        # Calculate training timestamps
        training_time = training_result["training_time_seconds"]
        completed_at = datetime.now()
        started_at = datetime.fromtimestamp(completed_at.timestamp() - training_time)
        
        cursor.execute(insert_query, (
            f"temporal-workflow-{int(time.time())}", # Would be actual workflow ID in real impl
            model_id,
            model_data.get("training_data", "unknown"),
            started_at,
            completed_at,
            hyperparams.get("n_estimators"),
            hyperparams.get("max_depth"),
            hyperparams.get("random_state"),
            round(metrics["accuracy"], 4),
            round(metrics["mae"], 4),
            round(metrics["r2_score"], 4),
            metrics["training_samples"],
            round(training_time, 2)
        ))
        
        experiment_id = cursor.fetchone()[0]
        conn.commit()
        
        activity.logger.info(f"✅ Experiment logged with ID: {experiment_id}")
        
        cursor.close()
        conn.close()
        
        return {
            "experiment_id": experiment_id,
            "tracking_status": "logged",
            "database_connection": "successful",
            "logged_at": completed_at.isoformat(),
            **training_result  # Pass through all training data
        }
        
    except (psycopg2.errors.InvalidAuthorizationSpecification, 
            psycopg2.errors.InvalidPassword) as e:
        # Class 28: Invalid Authorization Specification - non-retryable
        activity.logger.error(f"❌ Database authentication failed: {e}")
        raise ApplicationError(
            f"Database credentials invalid: {e}",
            non_retryable=True,
            type="AuthenticationError"
        )
    
    except psycopg2.errors.InvalidCatalogName as e:
        # Database doesn't exist - non-retryable configuration error
        activity.logger.error(f"❌ Database does not exist: {e}")
        raise ApplicationError(
            f"Database configuration error - database does not exist: {e}",
            non_retryable=True,
            type="DatabaseConfigError"
        )
    
    except psycopg2.OperationalError as e:
        # Network/connection issues (retryable) - database might be starting up
        activity.logger.warning(f"⚠️ Database connection failed (retryable): {e}")
        raise Exception(f"Experiment tracking database unavailable: {e}")
        
    except psycopg2.Error as e:
        # Other PostgreSQL errors - treat as configuration issues (non-retryable)
        activity.logger.error(f"❌ Database error: {e}")
        raise ApplicationError(
            f"Database error: {e}",
            non_retryable=True,
            type="DatabaseError"
        )
        
    except Exception as e:
        activity.logger.error(f"❌ Unexpected error logging experiment: {e}")
        raise Exception(f"Experiment tracking failed: {e}")

