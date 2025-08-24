import streamlit as st
import asyncio
import time
import os
import sys
from temporalio.client import Client
from workflows.mlops_workflow import MLOpsWorkflow

from encryption.encryption import create_encrypted_data_converter

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Page config
st.set_page_config(
    page_title="MLOps Temporal Dashboard",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 MLOps Temporal Dashboard")
st.markdown("Query workflow status and control execution with signals")

# Sidebar for controls
st.sidebar.header("Controls")

# File upload section
st.sidebar.subheader("Trigger Workflow")
uploaded_file = st.sidebar.file_uploader(
    "Upload CSV file",
    type=['csv'],
    help="Upload CSV to trigger MLOps pipeline"
)

if uploaded_file is not None:
    # Save uploaded file to data/raw
    os.makedirs("data/raw", exist_ok=True)
    file_path = f"data/raw/{uploaded_file.name}"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"File saved to {file_path}")
    
    # Auto-populate with the most recent workflow
    st.sidebar.info("Looking for triggered workflow...")
    time.sleep(2)  # Give file watcher time to trigger
    #recent_workflow = asyncio.run(get_most_recent_workflow())
    #if recent_workflow:
    #    st.session_state.auto_workflow_id = recent_workflow
    #    st.session_state.auto_query = True  # Flag to auto-query the workflow
    #    st.sidebar.success(f"Found workflow: {recent_workflow}")
    #    st.rerun()

# File management section
st.sidebar.subheader("File Management")
raw_files = []
if os.path.exists("data/raw"):
    raw_files = [f for f in os.listdir("data/raw") if f.endswith('.csv')]

if raw_files:
    selected_file = st.sidebar.selectbox("Select file to delete:", [""] + raw_files)
    
    if selected_file and st.sidebar.button("🗑️ Delete File", key="delete_file_btn"):
        try:
            file_to_delete = f"data/raw/{selected_file}"
            os.remove(file_to_delete)
            st.sidebar.success(f"Deleted {selected_file}")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error deleting file: {e}")
else:
    st.sidebar.info("No CSV files in data/raw/")

# Auto-refresh
auto_refresh = st.sidebar.checkbox("Auto-refresh (2s)", value=False)

async def get_temporal_client(with_encryption=True):
    """Get Temporal client connection with optional encryption support"""
    try:
        if with_encryption:
            return await Client.connect(
                "localhost:7233",
                data_converter=create_encrypted_data_converter()
            )
        else:
            return await Client.connect("localhost:7233")
    except Exception as e:
        st.error(f"Cannot connect to Temporal server: {e}")
        return None

async def get_most_recent_workflow():
    """Get the most recent MLOps workflow ID"""
    client = await get_temporal_client(with_encryption=False)  # Use non-encrypted for listing
    if not client:
        return None
    
    try:
        # List workflows with MLOps workflow type
        workflows = client.list_workflows(
            query="WorkflowType = 'MLOpsWorkflow'"
        )
        
        # Collect workflows and find the most recent by start time
        workflow_list = []
        async for workflow in workflows:
            workflow_list.append(workflow)
            # Limit to avoid loading too many workflows
            if len(workflow_list) >= 50:
                break
        
        if workflow_list:
            # Sort by start time (most recent first) and return the first one
            most_recent = max(workflow_list, key=lambda w: w.start_time)
            return most_recent.id
            
    except Exception as e:
        st.error(f"Error getting recent workflows: {e}")
        return None
    
    return None

async def query_workflow_status(workflow_id: str):
    """Query the status of a running workflow, trying both encrypted and non-encrypted clients"""
    # First try with encryption
    client = await get_temporal_client(with_encryption=True)
    if client:
        try:
            handle = client.get_workflow_handle(workflow_id)
            status = await handle.query(MLOpsWorkflow.get_status)
            return status
        except Exception as encrypted_error:
            # If encryption fails, try without encryption
            if "Unknown payload encoding" in str(encrypted_error):
                client = await get_temporal_client(with_encryption=False)
                if client:
                    try:
                        handle = client.get_workflow_handle(workflow_id)
                        status = await handle.query(MLOpsWorkflow.get_status)
                        return status
                    except Exception as non_encrypted_error:
                        st.error(f"Error querying workflow {workflow_id}: {non_encrypted_error}")
                        return None
            else:
                st.error(f"Error querying workflow {workflow_id}: {encrypted_error}")
                return None
    
    return None

async def approve_prod_deployment(workflow_id: str):
    """Send approval signal for production deployment, trying both encrypted and non-encrypted clients"""
    # First try with encryption
    client = await get_temporal_client(with_encryption=True)
    if client:
        try:
            handle = client.get_workflow_handle(workflow_id)
            await handle.signal(MLOpsWorkflow.approve_prod_deployment)
            return True
        except Exception as encrypted_error:
            # If encryption fails, try without encryption
            if "Unknown payload encoding" in str(encrypted_error):
                client = await get_temporal_client(with_encryption=False)
                if client:
                    try:
                        handle = client.get_workflow_handle(workflow_id)
                        await handle.signal(MLOpsWorkflow.approve_prod_deployment)
                        return True
                    except Exception as non_encrypted_error:
                        st.error(f"Error approving production deployment: {non_encrypted_error}")
                        return False
            else:
                st.error(f"Error approving production deployment: {encrypted_error}")
                return False
    
    return False

# Workflow controls - inline implementation for simplicity
st.subheader("🎮 Workflow Control")

# Get workflow ID input - auto-populate if available
default_workflow_id = st.session_state.get("auto_workflow_id", "")

col1, col2 = st.columns([3, 1])
with col1:
    workflow_id = st.text_input(
        "Workflow ID",
        value=default_workflow_id,
        placeholder="mlops-1234567890-filename", 
        help="Auto-populated from recent workflows or enter manually"
    )

with col2:
    st.write("")  # Add spacing
    if st.button("🔄 Get Latest", help="Fetch the most recent workflow"):
        recent_workflow = asyncio.run(get_most_recent_workflow())
        if recent_workflow:
            st.session_state.auto_workflow_id = recent_workflow
            st.session_state.auto_query = True  # Flag to auto-query the workflow
            st.success(f"Found: {recent_workflow}")
            st.rerun()
        else:
            st.warning("No recent workflows found")

# Auto-query if flag is set or if workflow_id exists
should_query = workflow_id and (st.session_state.get("auto_query", False) or workflow_id != "")

if should_query:
    # Clear the auto_query flag after using it
    if st.session_state.get("auto_query", False):
        st.session_state.auto_query = False
    
    # Query and display workflow status
    status = asyncio.run(query_workflow_status(workflow_id))
    if status:
        st.success("✅ Workflow Status")
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_step = status.get("current_step", "Unknown")
            st.metric("Current Step", current_step)
            completed_steps = status.get("completed_steps", [])
            st.metric("Completed Steps", len(completed_steps))
        
        with col2:
            current_step = status.get("current_step", "")
            quality_gate_failed = status.get("quality_gate_failed", False)
            deployment_status = status.get("deployment_status", "unknown")
            
            if current_step == "awaiting_prod_approval":
                st.warning("🔒 AWAITING APPROVAL")
            elif current_step == "completed":
                if quality_gate_failed:
                    st.error("❌ QUALITY GATE FAILED")
                    failure_reason = status.get("failure_reason", "unknown")
                    st.caption(f"Reason: {failure_reason.replace('_', ' ').title()}")
                elif deployment_status == "prod_deployed":
                    st.success("🚀 PROD DEPLOYED")
                elif deployment_status == "dev_deployed":
                    st.info("🧪 DEV DEPLOYED")  
                else:
                    st.success("✅ COMPLETED")
        
        # Show approval button if waiting for approval
        if status.get("awaiting_approval", False):
            st.divider()
            st.subheader("🚀 Production Deployment Approval")
            st.warning("**Human approval required for production deployment**")
            
            if st.button("✅ Approve Production Deployment", key="approve_btn", type="primary"):
                with st.spinner("Sending approval..."):
                    if asyncio.run(approve_prod_deployment(workflow_id)):
                        st.success("✅ Production deployment approved!")
                        st.rerun()
        
        # Show quality metrics if available
        quality_metrics = status.get("quality_metrics")
        if quality_metrics:
            st.divider()
            st.markdown("**Model Quality Metrics:**")
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            
            with metric_col1:
                accuracy = quality_metrics.get("accuracy", 0)
                color = "normal" if accuracy > 0.8 else "inverse"
                st.metric("Accuracy", f"{accuracy:.3f}", delta_color=color)
            
            with metric_col2:
                mae = quality_metrics.get("mae", 0)
                color = "normal" if mae < 2.5 else "inverse" 
                st.metric("MAE", f"{mae:.3f}", delta_color=color)
            
            with metric_col3:
                r2 = quality_metrics.get("r2_score", 0)
                color = "normal" if r2 > 0.7 else "inverse"
                st.metric("R² Score", f"{r2:.3f}", delta_color=color)
            
            # Show quality gate thresholds for reference
            if quality_gate_failed:
                st.info("💡 **Quality Gate Requirements:** Accuracy > 0.8, MAE < 2.5, R² > 0.7")

        if completed_steps:
            st.divider()
            st.markdown("**Completed Steps:**")
            for step in completed_steps:
                st.write(f"✅ {step}")
    
    elif workflow_id:
        st.warning("⚠️ Workflow not found or not running")

else:
    st.info("💡 Enter a workflow ID above to monitor and control it")
    st.markdown("Find workflow IDs at: [Temporal Web UI](http://localhost:8233/)")

# Auto-refresh
if auto_refresh:
    time.sleep(2)
    st.rerun()