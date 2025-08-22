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

2. **Start Temporal server**
   ```bash
   temporal server start-dev
   ```

3. **Start worker**
   ```bash
   python src/worker.py
   ```

4. **Start file watcher** (new terminal)
   ```bash
   python src/triggers/file_watcher.py
   ```

## Usage

Drop CSV files into `data/raw/` to trigger workflows. Monitor at http://localhost:8233/

Example dataset:
```bash
cd data/raw
wget https://archive.ics.uci.edu/ml/machine-learning-databases/abalone/abalone.data
cp abalone.data abalone.csv
```

## Key Features

- **Workflow Orchestration**: Multi-step ML pipeline with dependencies
- **Retries & Timeouts**: Automatic retry with exponential backoff
- **Quality Gates**: Conditional deployment based on model metrics
- **Observability**: Built-in monitoring via Temporal Web UI
- **Durability**: Workflow state preserved across failures