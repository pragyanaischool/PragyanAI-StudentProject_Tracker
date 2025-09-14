import streamlit as st
from utils import execute_query
from datetime import datetime

# --- SECURITY CHECK ---
# Ensure the user is logged in and is a team member
if 'logged_in' not in st.session_state or not st.session_state['logged_in'] or st.session_state.get('user_type') == 'admin':
    st.warning("Please log in as a team member to view this page.")
    st.stop()

# Ensure a project is selected
if 'selected_project_id' not in st.session_state:
    st.warning("Please select a project from the sidebar.")
    st.stop()

# --- PAGE SETUP ---
st.set_page_config(layout="wide", page_title="My Tasks & Schedule")
st.title("🚀 My Tasks & Schedule")
st.info("Here you can view and update the status of all tasks assigned to you for the current project.")

# --- DATA FETCHING ---
project_id = st.session_state['selected_project_id']
user_id = st.session_state['user_info']['id']

query = """
    SELECT 
        t.id, t.title, t.description, t.status, t.due_date,
        s.name as sprint_name
    FROM tasks t
    JOIN sprints s ON t.sprint_id = s.id
    WHERE t.assigned_to_id = ? AND t.project_id = ?
    ORDER BY s.end_date, t.due_date
"""
tasks = execute_query(query, (user_id, project_id), fetch="all")

# --- TASK DISPLAY ---
if not tasks:
    st.success("🎉 You have no tasks assigned for this project. Great job!")
    st.balloons()
else:
    # Group tasks by sprint
    tasks_by_sprint = {}
    for task in tasks:
        sprint = task['sprint_name']
        if sprint not in tasks_by_sprint:
            tasks_by_sprint[sprint] = []
        tasks_by_sprint[sprint].append(task)

    # Display tasks grouped by sprint
    for sprint_name, sprint_tasks in tasks_by_sprint.items():
        st.subheader(f"Sprint: {sprint_name}")
        for task in sprint_tasks:
            task_id = task['id']
            status_options = ["To Do", "In Progress", "Done", "Blocked"]
            current_status_index = status_options.index(task['status']) if task['status'] in status_options else 0
            
            # Use color-coding for status
            color = "blue"
            if task['status'] == 'Done':
                color = "green"
            elif task['status'] == 'Blocked':
                color = "red"
            elif task['status'] == 'In Progress':
                color = "orange"

            with st.expander(f"**{task['title']}** - Status: :{color}[{task['status']}]"):
                st.markdown(f"**Description:** {task['description']}")
                st.markdown(f"**Due Date:** `{task['due_date']}`")
                
                st.divider()

                # --- STATUS UPDATE ---
                new_status = st.selectbox(
                    "Update Status",
                    options=status_options,
                    index=current_status_index,
                    key=f"status_{task_id}"
                )

                if new_status != task['status']:
                    completion_date = None
                    # If task is marked as 'Done', record the completion date
                    if new_status == 'Done':
                        completion_date = datetime.now().strftime("%Y-%m-%d")
                        update_query = "UPDATE tasks SET status = ?, completion_date = ? WHERE id = ?"
                        params = (new_status, completion_date, task_id)
                    else:
                        # If status is changed from 'Done' to something else, clear completion date
                        update_query = "UPDATE tasks SET status = ?, completion_date = NULL WHERE id = ?"
                        params = (new_status, task_id)
                    
                    execute_query(update_query, params)
                    st.toast(f"Task '{task['title']}' updated to '{new_status}'!", icon="✅")
                    st.rerun() # Rerun to update the UI immediately
