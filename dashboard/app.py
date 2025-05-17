import streamlit as st
import pandas as pd
import altair as alt
import requests
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
API_PREFIX = os.getenv("API_PREFIX", "/api/v1")

# Page configuration
st.set_page_config(
    page_title="TaskRouterX Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Authentication state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.username = None


def authenticate(username, password):
    """
    Authenticate with the API.
    """
    try:
        response = requests.post(
            f"{API_URL}/token",
            data={
                "username": username,
                "password": password,
                "scope": "tasks:read tasks:write",
            },
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            st.session_state.authenticated = True
            st.session_state.username = username
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False


def api_request(method, endpoint, data=None, params=None):
    """
    Make an authenticated request to the API.
    """
    if not st.session_state.authenticated:
        st.error("Not authenticated")
        return None

    headers = {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json",
    }

    url = f"{API_URL}{API_PREFIX}{endpoint}"

    try:
        if method.lower() == "get":
            response = requests.get(url, headers=headers, params=params)
        elif method.lower() == "post":
            response = requests.post(url, headers=headers, json=data)
        elif method.lower() == "delete":
            response = requests.delete(url, headers=headers)
        else:
            st.error(f"Unsupported method: {method}")
            return None

        if response.status_code in [200, 201, 204]:
            if response.content:
                return response.json()
            return {"status": "success"}
        else:
            st.error(f"API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Request error: {e}")
        return None


def login_page():
    """
    Display the login page.
    """
    st.title("TaskRouterX Dashboard")
    st.subheader("Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if authenticate(username, password):
                st.success("Login successful!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

    st.info(
        """
        Demo accounts:
        - Admin: username=admin, password=admin
        - User: username=user, password=user
        - Read-only: username=readonly, password=readonly
        """
    )


def main_dashboard():
    """
    Display the main dashboard.
    """
    st.title("TaskRouterX Dashboard")
    st.sidebar.success(f"Logged in as: {st.session_state.username}")

    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.token = None
        st.session_state.username = None
        st.experimental_rerun()

    # Sidebar navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Tasks", "Simulation", "Worker Pools", "Logs", "Settings"],
    )

    if page == "Dashboard":
        display_dashboard_page()
    elif page == "Tasks":
        display_tasks_page()
    elif page == "Simulation":
        display_simulation_page()
    elif page == "Worker Pools":
        display_worker_pools_page()
    elif page == "Logs":
        display_logs_page()
    elif page == "Settings":
        display_settings_page()


def display_dashboard_page():
    """
    Display the main dashboard page with metrics and charts.
    """
    st.header("System Overview")

    # Get system stats
    stats = api_request("get", "/system/stats")
    if not stats:
        st.error("Failed to load system statistics")
        return

    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tasks Processed", stats["tasks_processed"])
    with col2:
        st.metric("Tasks Pending", stats["tasks_pending"])
    with col3:
        st.metric("Tasks Failed", stats["tasks_failed"])
    with col4:
        st.metric("Avg. Latency (s)", f"{stats['average_latency']:.3f}")

    # Worker utilization chart
    st.subheader("Worker Pool Utilization")
    utilization_data = [
        {"pool": pool, "utilization": util}
        for pool, util in stats["worker_utilization"].items()
    ]
    if utilization_data:
        df = pd.DataFrame(utilization_data)
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("pool:N", title="Worker Pool"),
            y=alt.Y("utilization:Q", title="Utilization (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("pool:N", legend=None),
            tooltip=["pool", "utilization"],
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No worker pool data available")

    # Recent tasks
    st.subheader("Recent Tasks")
    tasks = api_request("get", "/tasks", params={"page": 1, "page_size": 5})
    if tasks and "tasks" in tasks:
        if tasks["tasks"]:
            task_df = pd.DataFrame([
                {
                    "ID": str(task["id"]),
                    "Type": task["type"],
                    "Priority": task["priority"],
                    "Status": task["status"],
                    "Region": task["region"],
                    "Enqueued At": task["enqueued_at"],
                }
                for task in tasks["tasks"]
            ])
            st.dataframe(task_df, use_container_width=True)
        else:
            st.info("No recent tasks")
    else:
        st.error("Failed to load recent tasks")

    # Auto-refresh
    if st.checkbox("Auto-refresh (10s)", value=False):
        time.sleep(10)
        st.experimental_rerun()


def display_tasks_page():
    """
    Display the tasks management page.
    """
    st.header("Task Management")

    # Task creation form
    with st.expander("Create New Task", expanded=False):
        with st.form("create_task_form"):
            col1, col2 = st.columns(2)
            with col1:
                task_type = st.selectbox(
                    "Task Type",
                    ["order", "simulation", "query"],
                )
                priority = st.slider("Priority", 1, 10, 5)
            with col2:
                region = st.selectbox(
                    "Region",
                    ["us-east", "us-west", "eu-west", "ap-east"],
                )
                cost = st.number_input("Cost", min_value=0.1, max_value=100.0, value=1.0, step=0.1)

            metadata = st.text_area("Metadata (JSON)", "{}")
            submit = st.form_submit_button("Create Task")

            if submit:
                try:
                    metadata_json = json.loads(metadata)
                    task_data = {
                        "type": task_type,
                        "priority": priority,
                        "cost": cost,
                        "region": region,
                        "metadata": metadata_json,
                    }
                    result = api_request("post", "/tasks", data=task_data)
                    if result:
                        st.success(f"Task created with ID: {result['id']}")
                except json.JSONDecodeError:
                    st.error("Invalid JSON in metadata field")
                except Exception as e:
                    st.error(f"Error creating task: {e}")

    # Task filtering
    st.subheader("Task List")
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_status = st.selectbox(
            "Filter by Status",
            ["All", "queued", "processing", "completed", "failed", "cancelled"],
        )
    with col2:
        filter_type = st.selectbox(
            "Filter by Type",
            ["All", "order", "simulation", "query"],
        )
    with col3:
        filter_region = st.selectbox(
            "Filter by Region",
            ["All", "us-east", "us-west", "eu-west", "ap-east"],
        )

    # Prepare filter parameters
    params = {"page": 1, "page_size": 20}
    if filter_status != "All":
        params["status"] = filter_status
    if filter_type != "All":
        params["type"] = filter_type
    if filter_region != "All":
        params["region"] = filter_region

    # Get tasks
    tasks = api_request("get", "/tasks", params=params)
    if tasks and "tasks" in tasks:
        if tasks["tasks"]:
            task_df = pd.DataFrame([
                {
                    "ID": str(task["id"]),
                    "Type": task["type"],
                    "Priority": task["priority"],
                    "Cost": task["cost"],
                    "Region": task["region"],
                    "Status": task["status"],
                    "Enqueued At": task["enqueued_at"],
                    "Started At": task["started_at"] or "",
                    "Completed At": task["completed_at"] or "",
                    "Worker": task["worker_id"] or "",
                    "Algorithm": task["algorithm_used"] or "",
                }
                for task in tasks["tasks"]
            ])
            st.dataframe(task_df, use_container_width=True)

            # Task details
            selected_task_id = st.selectbox(
                "Select Task for Details",
                [str(task["id"]) for task in tasks["tasks"]],
            )
            if selected_task_id:
                selected_task = next(
                    (task for task in tasks["tasks"] if str(task["id"]) == selected_task_id),
                    None,
                )
                if selected_task:
                    st.json(selected_task)

                    # Cancel button for queued tasks
                    if selected_task["status"] == "queued":
                        if st.button("Cancel Task"):
                            result = api_request("delete", f"/tasks/{selected_task_id}")
                            if result:
                                st.success("Task cancelled successfully")
                                st.experimental_rerun()
        else:
            st.info("No tasks found matching the filters")
    else:
        st.error("Failed to load tasks")


def display_simulation_page():
    """
    Display the simulation page.
    """
    st.header("Traffic Simulation")

    with st.form("simulation_form"):
        col1, col2 = st.columns(2)
        with col1:
            task_count = st.slider("Number of Tasks", 1, 1000, 100)
            distribution = st.selectbox(
                "Distribution",
                ["random", "weighted", "burst"],
                help="Random: uniform distribution, Weighted: more high-priority tasks, Burst: all tasks at once",
            )
        with col2:
            region_bias = st.selectbox(
                "Region Bias",
                ["None", "us-east", "us-west", "eu-west", "ap-east"],
                help="Bias task generation towards a specific region",
            )
            priority_range = st.slider(
                "Priority Range",
                1, 10, (1, 10),
                help="Range of priorities to generate",
            )

        cost_range = st.slider(
            "Cost Range",
            0.1, 10.0, (0.1, 5.0), 0.1,
            help="Range of costs to generate",
        )

        submit = st.form_submit_button("Start Simulation")

        if submit:
            simulation_data = {
                "task_count": task_count,
                "distribution": distribution,
                "region_bias": None if region_bias == "None" else region_bias,
                "priority_range": list(priority_range),
                "cost_range": list(cost_range),
            }
            result = api_request("post", "/simulate", data=simulation_data)
            if result:
                st.success(f"Simulation started with ID: {result['id']}")

    # Simulation scenarios
    st.subheader("Predefined Scenarios")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("High Load Scenario"):
            simulation_data = {
                "task_count": 500,
                "distribution": "burst",
                "region_bias": None,
                "priority_range": [1, 10],
                "cost_range": [0.1, 5.0],
            }
            result = api_request("post", "/simulate", data=simulation_data)
            if result:
                st.success(f"High Load Simulation started with ID: {result['id']}")

    with col2:
        if st.button("Priority Test Scenario"):
            simulation_data = {
                "task_count": 100,
                "distribution": "weighted",
                "region_bias": None,
                "priority_range": [8, 10],
                "cost_range": [1.0, 3.0],
            }
            result = api_request("post", "/simulate", data=simulation_data)
            if result:
                st.success(f"Priority Test Simulation started with ID: {result['id']}")

    with col3:
        if st.button("Region Imbalance Scenario"):
            simulation_data = {
                "task_count": 200,
                "distribution": "random",
                "region_bias": "us-east",
                "priority_range": [1, 10],
                "cost_range": [0.5, 8.0],
            }
            result = api_request("post", "/simulate", data=simulation_data)
            if result:
                st.success(f"Region Imbalance Simulation started with ID: {result['id']}")


def display_worker_pools_page():
    """
    Display the worker pools page.
    """
    st.header("Worker Pools")

    # Get worker pools
    worker_pools = api_request("get", "/workers")
    if worker_pools and "worker_pools" in worker_pools:
        if worker_pools["worker_pools"]:
            # Display worker pools table
            pool_df = pd.DataFrame([
                {
                    "ID": str(pool["id"]),
                    "Name": pool["name"],
                    "Region": pool["region"],
                    "Resource Type": pool["resource_type"],
                    "Cost Per Unit": pool["cost_per_unit"],
                    "Capacity": pool["capacity"],
                    "Current Load": pool["current_load"],
                    "Utilization (%)": (pool["current_load"] / pool["capacity"]) * 100 if pool["capacity"] > 0 else 0,
                }
                for pool in worker_pools["worker_pools"]
            ])
            st.dataframe(pool_df, use_container_width=True)

            # Utilization chart
            st.subheader("Worker Pool Utilization")
            chart_data = pd.DataFrame([
                {
                    "Pool": pool["name"],
                    "Utilization (%)": (pool["current_load"] / pool["capacity"]) * 100 if pool["capacity"] > 0 else 0,
                    "Region": pool["region"],
                    "Resource Type": pool["resource_type"],
                }
                for pool in worker_pools["worker_pools"]
            ])
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X("Pool:N", title="Worker Pool"),
                y=alt.Y("Utilization (%):Q", scale=alt.Scale(domain=[0, 100])),
                color=alt.Color("Region:N"),
                tooltip=["Pool", "Utilization (%)", "Region", "Resource Type"],
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No worker pools available")
    else:
        st.error("Failed to load worker pools")


def display_logs_page():
    """
    Display the logs page.
    """
    st.header("Execution Logs")

    # Log filtering
    col1, col2 = st.columns(2)
    with col1:
        task_id = st.text_input("Filter by Task ID (optional)")
    with col2:
        event_type = st.selectbox(
            "Filter by Event Type",
            ["All", "created", "dispatched", "completed", "failed", "cancelled"],
        )

    # Prepare filter parameters
    params = {"page": 1, "page_size": 50}
    if task_id:
        params["task_id"] = task_id
    if event_type != "All":
        params["event_type"] = event_type

    # Get logs
    logs = api_request("get", "/logs", params=params)
    if logs and "logs" in logs:
        if logs["logs"]:
            log_df = pd.DataFrame([
                {
                    "ID": str(log["id"]),
                    "Task ID": str(log["task_id"]),
                    "Timestamp": log["timestamp"],
                    "Event Type": log["event_type"],
                    "Details": json.dumps(log["details"]),
                }
                for log in logs["logs"]
            ])
            st.dataframe(log_df, use_container_width=True)

            # Log details
            selected_log_id = st.selectbox(
                "Select Log for Details",
                [str(log["id"]) for log in logs["logs"]],
            )
            if selected_log_id:
                selected_log = next(
                    (log for log in logs["logs"] if str(log["id"]) == selected_log_id),
                    None,
                )
                if selected_log:
                    st.json(selected_log)
        else:
            st.info("No logs found matching the filters")
    else:
        st.error("Failed to load logs")


def display_settings_page():
    """
    Display the settings page.
    """
    st.header("System Settings")

    # Algorithm selection
    st.subheader("Scheduling Algorithm")
    current_algorithm = "fifo"  # Default, would be fetched from API in real implementation
    
    algorithm = st.selectbox(
        "Active Scheduling Algorithm",
        ["fifo", "greedy", "min_cost_flow", "ml_driven"],
        index=["fifo", "greedy", "min_cost_flow", "ml_driven"].index(current_algorithm),
    )
    
    if st.button("Update Algorithm"):
        result = api_request("post", "/algorithms/switch", data={"algorithm": algorithm})
        if result:
            st.success(f"Algorithm updated to: {algorithm}")

    # System information
    st.subheader("System Information")
    stats = api_request("get", "/system/stats")
    if stats:
        st.json(stats)

    # Health check
    st.subheader("Health Check")
    if st.button("Run Health Check"):
        health = api_request("get", "/health")
        if health:
            st.success("System is healthy")
        else:
            st.error("System health check failed")


# Main app logic
def main():
    if not st.session_state.authenticated:
        login_page()
    else:
        main_dashboard()


if __name__ == "__main__":
    main()
