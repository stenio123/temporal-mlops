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
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .metric-container {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3b82f6;
    }
    .status-success {
        background-color: #f0fdf4;
        color: #166534;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: 500;
    }
    .status-warning {
        background-color: #fffbeb;
        color: #d97706;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: 500;
    }
    .status-error {
        background-color: #fef2f2;
        color: #dc2626;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: 500;
    }
    .section-divider {
        margin: 2rem 0;
        border-bottom: 1px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">MLOps Temporal Dashboard</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Monitor workflow execution and manage production deployments</p>', unsafe_allow_html=True)

# Sidebar for controls
st.sidebar.markdown("### File Operations")

# File upload section
st.sidebar.markdown("**Upload New Dataset**")
uploaded_file = st.sidebar.file_uploader(
    "Choose CSV file",
    type=['csv'],
    help="Upload CSV file to trigger MLOps pipeline",
    label_visibility="collapsed"
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
st.sidebar.markdown("**Manage Existing Files**")
raw_files = []
if os.path.exists("data/raw"):
    raw_files = [f for f in os.listdir("data/raw") if f.endswith('.csv')]

if raw_files:
    selected_file = st.sidebar.selectbox(
        "Files in data/raw/", 
        [""] + raw_files,
        label_visibility="collapsed"
    )
    
    if selected_file and st.sidebar.button("Delete Selected File", key="delete_file_btn", type="secondary"):
        try:
            file_to_delete = f"data/raw/{selected_file}"
            os.remove(file_to_delete)
            st.sidebar.success(f"Deleted {selected_file}")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error: {e}")
else:
    st.sidebar.info("No files available")

# Auto-refresh
st.sidebar.markdown("---")
st.sidebar.markdown("**Dashboard Settings**")
auto_refresh = st.sidebar.checkbox("Auto-refresh every 2 seconds", value=False)

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
            
            # Check if workflow is still running first
            workflow_description = await handle.describe()
            if workflow_description.status.name in ["CANCELLED", "TERMINATED", "FAILED", "TIMED_OUT"]:
                return {"workflow_status": "cancelled", "current_step": "cancelled"}
            
            status = await handle.query(MLOpsWorkflow.get_status)
            return status
        except Exception as encrypted_error:
            # If encryption fails, try without encryption
            if "Unknown payload encoding" in str(encrypted_error):
                client = await get_temporal_client(with_encryption=False)
                if client:
                    try:
                        handle = client.get_workflow_handle(workflow_id)
                        
                        # Check if workflow is still running first
                        workflow_description = await handle.describe()
                        if workflow_description.status.name in ["CANCELLED", "TERMINATED", "FAILED", "TIMED_OUT"]:
                            return {"workflow_status": "cancelled", "current_step": "cancelled"}
                        
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

# Main content area
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# Workflow controls section
st.markdown("### Workflow Monitoring")
st.markdown("Enter a workflow ID to monitor its progress and manage approvals.")

# Get workflow ID input - auto-populate if available
default_workflow_id = st.session_state.get("auto_workflow_id", "")

col1, col2 = st.columns([4, 1])
with col1:
    workflow_id = st.text_input(
        "Workflow ID",
        value=default_workflow_id,
        placeholder="e.g., mlops-1234567890-filename",
        help="Enter workflow ID or use 'Get Latest' button"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)  # Align button with input
    if st.button("Get Latest", help="Fetch the most recent workflow", type="secondary"):
        with st.spinner("Searching for workflows..."):
            recent_workflow = asyncio.run(get_most_recent_workflow())
            if recent_workflow:
                st.session_state.auto_workflow_id = recent_workflow
                st.session_state.auto_query = True
                st.success(f"Found: {recent_workflow[:30]}...")
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
        st.markdown("### Workflow Status")
        
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
            
            if current_step == "cancelled":
                st.error("❌ WORKFLOW CANCELLED")
            elif current_step == "awaiting_prod_approval":
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
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            st.markdown("### Production Deployment Approval")
            st.info("This workflow requires human approval before deploying to production.")
            
            if st.button("Approve Production Deployment", key="approve_btn", type="primary", use_container_width=False):
                with st.spinner("Sending approval signal..."):
                    if asyncio.run(approve_prod_deployment(workflow_id)):
                        st.success("Production deployment approved successfully!")
                        st.rerun()
        
        # Show quality metrics if available
        quality_metrics = status.get("quality_metrics")
        if quality_metrics:
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            st.markdown("### Model Quality Metrics")
            
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            
            with metric_col1:
                accuracy = quality_metrics.get("accuracy", 0)
                delta = f"{'+' if accuracy > 0.8 else ''}{((accuracy - 0.8) * 100):.1f}% vs threshold"
                st.metric("Accuracy", f"{accuracy:.3f}", delta=delta)
            
            with metric_col2:
                mae = quality_metrics.get("mae", 0)
                delta = f"{'-' if mae < 2.5 else '+'}{abs((mae - 2.5)):.2f} vs threshold"
                st.metric("Mean Absolute Error", f"{mae:.3f}", delta=delta)
            
            with metric_col3:
                r2 = quality_metrics.get("r2_score", 0)
                delta = f"{'+' if r2 > 0.7 else ''}{((r2 - 0.7) * 100):.1f}% vs threshold"
                st.metric("R² Score", f"{r2:.3f}", delta=delta)
            
            # Show quality gate thresholds for reference
            quality_gate_failed = status.get("quality_gate_failed", False)
            if quality_gate_failed:
                st.warning("⚠️ **Quality Gate Requirements:** Accuracy > 0.8, MAE < 2.5, R² > 0.7")

        if completed_steps:
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            st.markdown("### Pipeline Progress")
            
            progress_cols = st.columns(len(completed_steps) if len(completed_steps) <= 5 else 5)
            for i, step in enumerate(completed_steps[:5]):  # Limit to 5 steps for clean display
                with progress_cols[i % 5]:
                    step_name = step.replace('_', ' ').title()
                    st.markdown(f'<div style="text-align: center; padding: 0.5rem; background-color: #282b30; border-radius: 0.5rem; border: 1px solid #bbf7d0;"><strong>✅ {step_name}</strong></div>', unsafe_allow_html=True)
    
    elif workflow_id:
        st.error("Workflow not found or not accessible. Please verify the workflow ID.")

elif not workflow_id:
    st.markdown("### Getting Started")
    st.markdown("""
    **To monitor a workflow:**
    1. Enter a workflow ID in the field above, or
    2. Click "Get Latest" to find the most recent workflow, or  
    3. Upload a CSV file in the sidebar to trigger a new workflow
    
    **Find workflow IDs:** [Temporal Web UI](http://localhost:8233/)
    """)

# Auto-refresh
if auto_refresh:
    time.sleep(2)
    st.rerun()