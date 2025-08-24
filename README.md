# MLOps Temporal PoC

Proof of concept demonstrating MLOps pipeline orchestration using Temporal.io. File drops trigger workflows that process data, train models, validate quality, and deploy.

## Architecture

```
File Watcher → Temporal Workflow → [Preprocessing] → [Training] → [Quality Gate] → [Deployment]
```

## Setup

1. **Install dependencies**
   ```bash
   uv pip install -e . --only-binary=temporalio
   ```

2. **Configure environment**
   ```bash
   # .env file is already configured for local development
   # Includes database credentials and encryption key
   # In production: load from secure key management (AWS KMS, etc.)
   ```

3. **Start external services**
   ```bash
   # Start PostgreSQL (experiment tracking database)
   docker-compose up -d postgres
   
   # Start Temporal server
   temporal server start-dev
   ```

4. **Start worker**
   ```bash
   # Standard worker (sensitive data visible in Temporal logs)
   python src/worker.py
   
   # OR encrypted worker (sensitive data encrypted in Temporal logs)
   python src/worker_encrypted.py
   ```

5. **Start file watcher** (new terminal)
   ```bash
   python src/triggers/file_watcher.py
   ```

6. **Launch dashboard** (optional, new terminal)
   ```bash
   streamlit run ui/dashboard.py
   ```

## Usage

Drop CSV files into `data/raw/` to trigger workflows. Monitor at:
- **Temporal Web UI**: http://localhost:8233/
- **Dashboard**: http://localhost:8501/ (if running Streamlit)

Example dataset:
```bash
cd data/raw
wget https://archive.ics.uci.edu/ml/machine-learning-databases/abalone/abalone.data
cp abalone.data abalone.csv
```

## Demo Scenarios

### Quality Gate Behavior
- Files named "good" → Pass quality gate
- Files named "bad" → Fail quality gate  
- Other files → Random outcome

### Failure Simulation
Create failure config to test Temporal's retry behavior:
```bash
# Simulate training failure
echo '{"simulate_failure": true, "activity": "training"}' > config/failure_simulation.json

# Clear failure simulation
rm config/failure_simulation.json
```

Available failure modes: `data_processing`, `training`, `quality_gate`, `deployment`

### External Dependency Failure Simulation
Simulate real-world external service failures:

#### **Transient Failures (Retryable)**
```bash
# Stop PostgreSQL to simulate service unavailable
docker-compose stop postgres

# Watch Temporal retry 3 times with exponential backoff
# Restart PostgreSQL to see recovery
docker-compose start postgres
```

#### **Authentication Failures (Non-retryable)**
```bash
# Edit .env and change POSTGRES_PASSWORD to wrong value
# Triggers InvalidPassword error - workflow fails immediately
# No wasted retries on permanent configuration issues
```

#### **Configuration Failures (Non-retryable)**
```bash
# Edit .env and change POSTGRES_DB to 'wrong_db'
# Triggers InvalidCatalogName error - workflow fails immediately
# Demonstrates smart error classification and fail-fast behavior
```

**Key Benefits:**
- **Transient failures**: Indefinite retry with exponential backoff (capped at 1 minute)
- **Permanent failures**: Fail fast with ApplicationError for config/auth issues
- **Production ready**: Experiment tracking treated as critical dependency
- **Robust recovery**: Database outages don't permanently fail workflows

## Encryption Demo (Temporal Codecs)

Demonstrate how workflow data can be encrypted in Temporal logs while remaining readable in your application.

### **Phase 1: Show Data Exposure**
1. **Start standard worker**: `python src/worker.py`
2. **Upload file and trigger workflow**
3. **Check Temporal Web UI** → Workflow data visible in activity logs
4. **Security concern**: Sensitive data exposed in workflow history

### **Phase 2: Enable Encryption**
1. **Stop standard worker** (Ctrl+C)
2. **Start encrypted worker**: `python src/worker_encrypted.py`  
3. **Upload file and trigger workflow**
4. **Check Temporal Web UI** → Workflow data now encrypted (base64 strings)
5. **Check worker logs** → Data still readable in your application

### **Key Benefits:**
- **Regulatory compliance**: Workflow data encrypted at rest in Temporal
- **Operational visibility**: Your application can still log/debug normally  
- **Data protection**: Payloads encrypted in Temporal storage
- **Zero workflow changes**: Same workflow code, just different worker startup
- **Secure key management**: Keys stored in environment variables, not hardcoded

### **Key Management Best Practices:**
```bash
# Generate new encryption key (for new environments)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# In production, use proper key management:
# - AWS KMS / Azure Key Vault / GCP Secret Manager
# - HashiCorp Vault
# - Kubernetes secrets with encryption at rest
# - Regular key rotation policies
```

## Workflow Controls (Signals & Queries)

### Via Dashboard
Use the Streamlit dashboard workflow controls to approve production deployments interactively.

### Via CLI
```bash
# Approve production deployment for a workflow waiting for human approval
temporal workflow signal --workflow-id mlops-{timestamp}-{filename} --name approve_prod_deployment

# Query current workflow status
temporal workflow query --workflow-id mlops-{timestamp}-{filename} --name get_status
```

**Real MLOps Use Cases:**
- **Human Approval Gates**: Approve production deployments after manual review
- **Quality Control**: Human verification of model performance before deployment
- **Compliance**: Manual checks for regulatory requirements
- **Business Logic**: Custom approval workflows for different deployment tiers

## Key Features

- **Workflow Orchestration**: Multi-step ML pipeline with dependencies
- **Retries & Timeouts**: Automatic retry with exponential backoff
- **Quality Gates**: Conditional deployment based on model metrics
- **Failure Simulation**: Test resilience with configurable failures
- **Visual Dashboard**: Real-time monitoring with Streamlit UI
- **Observability**: Built-in monitoring via Temporal Web UI
- **Durability**: Workflow state preserved across failures