import streamlit as st
from utils import execute_query
from datetime import datetime

st.set_page_config(layout="wide", page_title="Mentoring")

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

st.header("🤔 Doubts, Dependencies & Mentoring Requests")
st.info("This is your dedicated space to ask questions, flag issues, and get the help you need to succeed.")

tab1, tab2 = st.tabs(["🆕 Raise a New Issue", "📖 View My Past Issues"])

with tab1:
    st.subheader("Submit a Question or Request Help")
    my_tasks_map = {t['id']: t['title'] for t in execute_query("SELECT id, title FROM tasks WHERE assigned_to_id = ? AND project_id = ? AND status != 'Done'", (MEMBER_ID, PROJECT_ID), "all")}
    
    if not my_tasks_map:
        st.warning("You have no active tasks assigned to you. You can only raise issues for tasks that are 'To Do' or 'In Progress'.")
    else:
        with st.form("issue_form", clear_on_submit=True):
            st.markdown("**1. Select the relevant task**")
            task_id = st.selectbox("Which task is this about?", options=list(my_tasks_map.keys()), format_func=lambda x: my_tasks_map.get(x, "Unknown Task"), label_visibility="collapsed")
            
            st.markdown("**2. Define the nature of your issue**")
            issue_type = st.selectbox("What is the nature of the issue?", ["Question", "Doubt", "Dependency"], label_visibility="collapsed")
            
            st.markdown("**3. Describe the issue in detail**")
            issue_desc = st.text_area("Please provide as much context as possible.", height=150, label_visibility="collapsed")
            
            st.markdown("**4. Do you need a face-to-face discussion?**")
            req_1_on_1 = st.checkbox("I need a 1:1 meeting to resolve this.")
            
            st.divider()
            submitted = st.form_submit_button("Submit Issue to Manager", use_container_width=True, type="primary")
            
            if submitted:
                if not issue_desc.strip():
                    st.error("Please provide a description for your issue.")
                else:
                    execute_query("""
                        INSERT INTO task_issues (task_id, member_id, issue_type, description, request_1_on_1) 
                        VALUES (?, ?, ?, ?, ?)
                    """, (task_id, MEMBER_ID, issue_type, issue_desc, 1 if req_1_on_1 else 0))
                    st.success("Your issue has been submitted. Your project manager has been notified and will respond shortly.")
                    st.balloons()

with tab2:
    st.subheader("Your Communication History")
    my_issues = execute_query("SELECT ti.*, t.title FROM task_issues ti JOIN tasks t ON ti.task_id = t.id WHERE ti.member_id = ? AND t.project_id = ? ORDER BY ti.timestamp DESC", (MEMBER_ID, PROJECT_ID), "all")
    
    if not my_issues:
        st.info("You haven't raised any issues for this project yet. Use the 'Raise a New Issue' tab to get started.")
    
    for issue in my_issues:
        status_color = "orange" if issue['status'] == 'Open' else "green"
        expander_title = f"Task: **{issue['title']}** | Type: **{issue['issue_type']}** | Status: :{status_color}[{issue['status']}]"
        
        with st.expander(expander_title):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"**Your Question:**\n\n{issue['description']}")
            with col2:
                issue_time = datetime.strptime(issue['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%b %d, %Y at %I:%M %p')
                st.caption(f"**Submitted on:**\n\n{issue_time}")
            
            st.divider()
            
            responses = execute_query("SELECT r.*, a.username FROM issue_responses r JOIN admins a ON r.responder_id = a.id WHERE r.issue_id = ? ORDER BY r.timestamp ASC", (issue['id'],), "all")
            
            if responses:
                st.write("**Manager's Response(s):**")
                for resp in responses:
                    with st.container(border=True):
                        r_col1, r_col2 = st.columns([3, 1])
                        with r_col1:
                            st.markdown(f"**Response Type:** `{resp['hint_type']}`")
                            st.write(resp['response_text'])
                            if resp['reference_links']:
                                st.markdown("**References:**")
                                links = resp['reference_links'].strip().split('\n')
                                for link in links:
                                    st.markdown(f"- {link.strip()}")
                        with r_col2:
                            resp_time = datetime.strptime(resp['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%b %d, %Y at %I:%M %p')
                            st.caption(f"**Responded by {resp['username']} on:**\n\n{resp_time}")
            else:
                st.warning("⏳ Awaiting response from your project manager.")
