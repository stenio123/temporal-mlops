# MLOps Temporal Demo Guide

## Demo Flow Overview
1. **Setup & Architecture** - Show the problem and solution
2. **Basic Workflow Demo** - Show standard MLOps pipeline 
3. **Failure Resilience** - Demonstrate Temporal's reliability features
4. **Human Approval Gates** - Show workflow control with signals/queries
5. **Encryption Demo** - Show sensitive data protection
6. **Code Deep Dive** - Explain implementation details

---

## Phase 1: Setup & Architecture (5 minutes)

### Start with the Problem Statement
> "MLOps pipelines are complex, with many failure points. How do we ensure reliability, human oversight, and data security?"

### Show Project Structure
```bash
tree src/
```

**Highlight:**
- `workflows/` - Orchestration logic
- `activities/` - Individual pipeline steps  
- `triggers/` - File-based triggers
- `ui/` - Human approval interface
- `encryption/` - Data security layer

### Show README.md Architecture
```
File Watcher → Temporal Workflow → [Preprocessing] → [Training] → [Quality Gate] → [Deployment]
```

**Key Points:**
- **Durable workflows** - Survive failures and restarts
- **Human approval** - Production deployment requires approval
- **Encryption** - Sensitive data protected in logs

---

## Phase 2: Basic Workflow Demo (10 minutes)

### Terminal Setup (4 terminals)
1. **Terminal 1: Temporal Server**
   ```bash
   temporal server start-dev
   ```

2. **Terminal 2: PostgreSQL (External Dependency)**
   ```bash
   docker-compose up postgres
   ```

3. **Terminal 3: Standard Worker**
   ```bash
   python src/worker.py
   ```

4. **Terminal 4: File Watcher**
   ```bash
   python src/triggers/file_watcher.py
   ```

### Show Temporal Web UI
- Open: http://localhost:8233/
- **Highlight:** Empty workflow list initially

### Trigger First Workflow
```bash
# Drop a "good" file to ensure quality gate passes
cp data/examples/abalone.csv data/raw/good_model.csv
```

### Follow Workflow Execution
**In Temporal Web UI, show:**
1. **Workflow appears** - `mlops-{timestamp}-good_model`
2. **Activity progression** - Each step executing
3. **Activity details** - Input/output data visible
4. **Timeline view** - Duration and sequence

**Point out workflow steps:**
- `preprocess_data` - Data validation and preparation  
- `train_model_mock` - Model training (15-25s duration)
- `assess_model_quality` - Quality gate evaluation
- `log_experiment` - Database logging 
- `deploy_to_environment` - Deployment (dev environment)

### Show Successful Completion
- **Green checkmark** in workflow list
- **All activities completed** successfully
- **Deployment success** logged

---

## Phase 3: Failure Resilience Demo (10 minutes)

### Simulate Training Failure
```bash
# Create failure simulation config
echo '{"simulate_failure": true, "activity": "training"}' > config/failure_simulation.json

# Trigger workflow
cp data/examples/abalone.csv data/raw/failing_training.csv
```

**In Temporal Web UI, show:**
- **Training activity fails** with "GPU temporarily unavailable"
- **Temporal automatically retries** with exponential backoff
- **3 retry attempts** visible in activity history
- **Workflow fails** after exhausting retries

**Key Points:**
- **No manual intervention needed** 
- **Retry behavior configurable** per activity
- **Failure details preserved** for debugging

### Demonstrate External Dependency Failure
```bash
# Stop PostgreSQL to simulate service outage
docker-compose stop postgres

# Trigger workflow
cp data/examples/abalone.csv data/raw/db_failure.csv
```

**Show in Temporal Web UI:**
- **Workflow proceeds normally** through training
- **Experiment tracking fails** at database connection
- **Temporal retries indefinitely** (transient failure)
- **Activity stays pending** waiting for database

```bash
# Restart PostgreSQL to show recovery
docker-compose start postgres
```

**Show recovery:**
- **Activity immediately succeeds** when database returns
- **Workflow continues** to completion
- **No data lost** - perfect recovery

### Show Non-Retryable Failures
```bash
# Edit .env to wrong database password
# This simulates configuration errors
```

**In Temporal Web UI:**
- **Activity fails immediately** with ApplicationError
- **No retries attempted** - fail fast behavior
- **Workflow marked as failed** 

**Key Insight:** Smart error classification prevents wasted resources on permanent failures

```bash
# Clean up
rm config/failure_simulation.json
# Restore correct .env
```

---

## Phase 4: Human Approval Gates (8 minutes)

### Start Dashboard
```bash
# Terminal 5: Dashboard
streamlit run ui/dashboard.py
```

### Trigger Production Deployment Scenario
```bash
# Use "good" filename to ensure quality gate passes
cp data/examples/abalone.csv data/raw/prod_candidate.csv
```

### Show Workflow Waiting for Approval
**In Temporal Web UI:**
- **Workflow reaches** `await_production_approval`
- **Status shows** "Waiting for approval signal"
- **Workflow waits** for human decision

**In Dashboard (http://localhost:8501/):**
1. **Enter workflow ID** from Temporal UI
2. **Query status** shows "awaiting_prod_approval"
3. **Approval button appears** with warning

### Show Human Decision Making
**Point out in dashboard:**
- **Model metrics visible** (accuracy, MAE, R²)
- **Quality checks passed** 
- **Human can review** before production

**Click "Approve Production Deployment"**

**Back in Temporal Web UI:**
- **Workflow immediately continues**
- **Production deployment activity** executes
- **Workflow completes successfully**

**Real MLOps Use Cases:**
- **Model performance review**
- **A/B testing coordination** 
- **Regulatory compliance checks**
- **Resource allocation approval**

---

## Phase 5: Encryption Demo (12 minutes)

### Phase 5a: Show Sensitive Data Exposure
**Stop standard worker** (Ctrl+C in Terminal 3)

```bash
# Trigger workflow with standard worker
cp data/examples/abalone.csv data/raw/sensitive_data.csv
```

**In Temporal Web UI:**
1. **Click on training activity**
2. **Show activity input/output** 
3. **Highlight sensitive configuration** visible in plain text:
   ```json
   "proprietary_config": {
     "secret_learning_rate_multiplier": 1.337,
     "custom_regularization_alpha": 0.00042,
     "advanced_dropout_schedule": "exponential_secret",
     "internal_model_architecture": "CompanyXL_v2.1"
   }
   ```

**Problem:** Sensitive data visible in Temporal logs!

### Phase 5b: Enable Encryption

**Terminal 3: Start Encrypted Worker**
```bash
python src/worker_encrypted.py
```

**Show encryption active:**
```
🔐 MLOps Temporal worker started with ENCRYPTION enabled!
Encryption: Simple demo codec active
```

### Trigger Encrypted Workflow
```bash
cp data/examples/abalone.csv data/raw/good.csv
```

**In Temporal Web UI:**
1. **Click on training activity**  
2. **Show activity input/output**
3. **Point out encrypted data** - long base64 strings instead of readable data
4. **Highlight:** Same workflow, encrypted storage

**In Worker Logs:**
- **Show readable data** in application logs
- **Application functionality unchanged**

### Show Dashboard Still Works
**In Dashboard:**
1. **Query encrypted workflow** 
2. **Dashboard can decrypt** and show status
3. **Human approval still possible** with encrypted data

**Key Benefits:**
- ✅ **Regulatory compliance** - Workflow data encrypted at rest
- ✅ **Operational visibility** - Applications can decrypt for business logic  
- ✅ **Zero workflow changes** - Same code, just different worker startup

---

## Phase 6: Code Deep Dive (10 minutes)

### Show Workflow Definition
**File:** `src/workflows/mlops_workflow.py`

**Highlight:**
```python
@workflow.defn
class MLOpsWorkflow:
    @workflow.run
    async def run(self, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        # Activity chain with error handling
        preprocessing_result = await workflow.execute_activity(
            preprocess_data,
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        # Human approval gate
        await workflow.wait_condition(lambda: self._approved)
```

**Key Points:**
- **Declarative workflow** - Define what, not how
- **Retry policies** per activity  
- **Signals for human interaction**
- **Durable state** - survives worker restarts

### Show Activity Implementation  
**File:** `src/activities/training.py`

**Highlight:**
```python
@activity.defn
async def train_model_mock(preprocessing_result: Dict[str, Any]) -> Dict[str, Any]:
    # Simulate occasional failures
    if random.random() < 0.1:
        raise Exception("GPU temporarily unavailable")
    
    # Business logic
    return {"model_id": model_id, "metrics": {...}}
```

**Key Points:**
- **Simple functions** - No Temporal-specific code in business logic
- **Exception handling** - Let Temporal manage retries
- **Testable** - Pure Python functions

### Show Encryption Implementation
**File:** `src/encryption/encryption.py`

**Highlight:**
```python
class EncryptionCodec(PayloadCodec):
    async def encode(self, payloads: Iterable[Payload]) -> List[Payload]:
        return [
            Payload(
                metadata={"encoding": b"binary/encrypted"},
                data=self.cipher.encrypt(p.SerializeToString())
            ) for p in payloads
        ]
```

**Key Points:**
- **Codec pattern** - Intercepts serialization
- **Transparent to application** - No code changes needed
- **Fernet encryption** - Industry standard, secure

### Show File Watcher Trigger
**File:** `src/triggers/file_watcher.py`

**Highlight:**
```python
async def trigger_mlops_workflow(file_path: str):
    client = await Client.connect("localhost:7233")
    await client.start_workflow(
        MLOpsWorkflow.run,
        {"file_path": file_path, "trigger_type": "file_upload"},
        id=f"mlops-{int(time.time())}-{os.path.basename(file_path)}"
    )
```

**Key Points:**
- **Event-driven** - Real-world trigger pattern
- **Async client** - High performance
- **Unique workflow IDs** - Prevent duplicates

---

## Demo Wrap-up (3 minutes)

### Summary of What We Showed
1. ✅ **Durable workflows** - Survive failures, retries, restarts
2. ✅ **Human approval gates** - Production deployment control  
3. ✅ **Failure handling** - Smart retries vs fail-fast
4. ✅ **External dependencies** - Database recovery scenarios
5. ✅ **Encryption** - Sensitive data protection
6. ✅ **Real-world triggers** - File-based automation

### Key Temporal Benefits for MLOps
- **Reliability** - No lost work, automatic retries
- **Observability** - Full pipeline visibility  
- **Scalability** - Handle thousands of concurrent workflows
- **Compliance** - Audit trails and data encryption
- **Developer Experience** - Write business logic, not infrastructure

### Production Considerations
- **Key management** - Use AWS KMS, HashiCorp Vault
- **Monitoring** - Prometheus metrics, custom dashboards  
- **Scaling** - Multiple workers, different task queues
- **Testing** - Temporal's test framework for workflows

### Questions?
- **Architecture questions** - Temporal patterns
- **MLOps integration** - Real pipeline scenarios
- **Security concerns** - Encryption, compliance
- **Scaling considerations** - Production deployment