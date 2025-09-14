import streamlit as st
from utils import execute_query
from datetime import datetime

st.set_page_config(layout="wide", page_title="Progress Update")

# --- Security and Session Check ---
if 'logged_in' not in st.session_state or not st.session_state.get('logged_in'):
    st.error("Please log in on the main page to access this section.")
    st.stop()
if st.session_state.get('user_type') == 'admin':
    st.error("This page is for team members only.")
    st.stop()
if 'selected_project_id' not in st.session_state:
    st.warning("Please select a project from the main page sidebar.")
    st.stop()

# --- Page Content ---
PROJECT_ID = st.session_state['selected_project_id']
MEMBER_ID = st.session_state['user_info']['id']

st.header("Submit Weekly Progress Update")

my_tasks_map = {t['id']: t['title'] for t in execute_query("SELECT id, title FROM tasks WHERE assigned_to_id = ? AND project_id = ? AND status != 'Done'", (MEMBER_ID, PROJECT_ID), "all")}
if not my_tasks_map:
    st.success("You have no active tasks to report on. Great job!")
else:
    with st.form("progress_update_form"):
        task_id = st.selectbox("Select Task to Update", options=list(my_tasks_map.keys()), format_func=lambda x: my_tasks_map[x])
        update_desc = st.text_area("Activities completed this week", help="Be specific about what you achieved.")
        code_link = st.text_input("Code Base Link (GitHub, Colab, etc.)")
        help_needed = st.text_area("What is still in progress and where do you need help?")
        eta = st.text_input("Estimated time to complete this task?", help="e.g., 2 days, 4 hours")
        submitted = st.form_submit_button("Submit Update")
        if submitted and update_desc:
            execute_query("""
                INSERT INTO progress_updates (task_id, member_id, update_description, code_link, help_needed_summary, eta_to_complete)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (task_id, MEMBER_ID, update_desc, code_link, help_needed, eta))
            st.success("Progress update submitted successfully!")

st.subheader("Recent Updates")
updates = execute_query("SELECT p.*, t.title FROM progress_updates p JOIN tasks t ON p.task_id = t.id WHERE p.member_id = ? AND t.project_id = ? ORDER BY p.timestamp DESC LIMIT 10", (MEMBER_ID, PROJECT_ID), "all")
if not updates:
    st.info("No recent updates found.")
else:
    for update in updates:
        with st.container(border=True):
            update_time = datetime.fromisoformat(update['timestamp']).strftime('%Y-%m-%d %H:%M')
            st.markdown(f"**Update for '{update['title']}' on {update_time}**")
            st.markdown(f"**- Activities:** {update['update_description']}")
            st.markdown(f"**- Code Link:** {update['code_link']}")
            st.markdown(f"**- Help Needed:** {update['help_needed_summary']}")
            st.markdown(f"**- ETA:** {update['eta_to_complete']}")
