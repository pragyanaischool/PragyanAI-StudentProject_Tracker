import streamlit as st
import plotly.express as px
import pandas as pd
from utils import execute_query, get_project_maps
from datetime import datetime, timedelta

st.set_page_config(layout="wide", page_title="Project Manager Dashboard")

# --- Security Check ---
if 'logged_in' not in st.session_state or not st.session_state.get('logged_in'):
    st.error("You must be logged in to view this page.")
    st.stop()
if st.session_state.get('user_type') != 'admin':
    st.error("Access Denied: This page is for Project Managers (Admins) only.")
    st.stop()
if 'selected_project_id' not in st.session_state:
    st.warning("Please select a project from the main page sidebar to view the dashboard.")
    st.stop()

# --- Page Setup ---
PROJECT_ID = st.session_state['selected_project_id']
project_details = execute_query("SELECT name FROM projects WHERE id = ?", (PROJECT_ID,), fetch="one")
st.header(f"📈 Dashboard for: {project_details['name']}")
st.info("Monitor progress, support your team, and track project analytics.")

# --- Fetch Data using Cached Maps ---
members_map, requirements_map, tasks_map = get_project_maps(PROJECT_ID)

# --- UI Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📢 Activity Feed",
    "🛠️ Task Issues & Support",
    "📊 Analytics",
    "👥 Team Progress",
    "📚 Manage Resources"
])

# --- TAB 1: Activity Feed ---
with tab1:
    st.subheader("Recent Project Activity")
    
    # Fetch recent progress updates
    progress_updates = execute_query("""
        SELECT pu.*, tm.name FROM progress_updates pu
        JOIN team_members tm ON pu.member_id = tm.id
        WHERE pu.project_id = ? ORDER BY pu.submission_date DESC LIMIT 10
    """, (PROJECT_ID,), fetch="all")

    # Fetch recent issues
    new_issues = execute_query("""
        SELECT ti.*, tm.name as member_name, t.title as task_title FROM task_issues ti
        JOIN team_members tm ON ti.member_id = tm.id
        JOIN tasks t ON ti.task_id = t.id
        WHERE t.project_id = ? ORDER BY ti.created_at DESC LIMIT 10
    """, (PROJECT_ID,), fetch="all")

    if not progress_updates and not new_issues:
        st.info("No recent activity to display.")
    else:
        st.markdown("##### Last 10 Progress Updates")
        if progress_updates:
            for update in progress_updates:
                with st.container(border=True):
                    st.markdown(f"**{update['name']}** submitted an update on **{update['submission_date']}**")
                    st.caption(f"**Task:** {tasks_map.get(update['task_id'], 'N/A')}")
                    with st.expander("View Details"):
                        st.write(f"**Status:** {update['status']}")
                        st.write(f"**Summary:** {update['summary']}")
                        if update['code_link']:
                            st.write(f"**Code Link:** {update['code_link']}")
        else:
            st.write("No progress updates submitted yet.")

        st.divider()
        st.markdown("##### Last 10 Issues/Questions Raised")
        if new_issues:
             for issue in new_issues:
                with st.container(border=True):
                    st.markdown(f"**{issue['member_name']}** raised an issue for task **{issue['task_title']}** on **{issue['created_at'].split(' ')[0]}**")
                    st.caption(f"**Type:** {issue['issue_type']} | **Status:** {'Open' if not issue['is_resolved'] else 'Resolved'}")
                    if issue['needs_meeting']:
                        st.warning("🤝 1:1 Meeting Requested")
        else:
            st.write("No new issues have been raised.")


# --- TAB 2: Task Issues & Support ---
with tab2:
    st.subheader("Address Team Member Needs")
    st.info("Respond to questions, resolve dependencies, and manage meeting requests here.")
    
    open_issues = execute_query("""
        SELECT ti.id, ti.issue_text, ti.issue_type, ti.needs_meeting, ti.created_at,
               tm.name as member_name, t.title as task_title
        FROM task_issues ti
        JOIN team_members tm ON ti.member_id = tm.id
        JOIN tasks t ON ti.task_id = t.id
        WHERE t.project_id = ? AND ti.is_resolved = 0
        ORDER BY ti.needs_meeting DESC, ti.created_at ASC
    """, (PROJECT_ID,), fetch="all")

    if not open_issues:
        st.success("🎉 No open issues! The team is on track.")
    else:
        for issue in open_issues:
            with st.container(border=True):
                st.markdown(f"**Task:** `{issue['task_title']}`")
                st.write(f"**From:** {issue['member_name']} | **Type:** {issue['issue_type']} | **Raised:** {issue['created_at']}")
                if issue['needs_meeting']:
                    st.warning("🤝 **1:1 Meeting Requested**")
                
                with st.expander("View Details & Respond"):
                    st.info(f"**Question/Issue:**\n{issue['issue_text']}")
                    
                    with st.form(key=f"response_form_{issue['id']}"):
                        response_text = st.text_area("Your Response / Hint", key=f"resp_text_{issue['id']}")
                        ref_links = st.text_area("Reference Links (one per line)", key=f"ref_links_{issue['id']}", placeholder="https://docs.python.org\nhttps://github.com/example")
                        mark_resolved = st.checkbox("Mark as Resolved", key=f"resolve_{issue['id']}")
                        
                        submit_response = st.form_submit_button("Submit Response", type="primary")

                        if submit_response:
                            if not response_text:
                                st.error("Response text cannot be empty.")
                            else:
                                execute_query("""
                                    INSERT INTO issue_responses (issue_id, responder_id, response_text, reference_links)
                                    VALUES (?, ?, ?, ?)
                                """, (issue['id'], st.session_state['user_info']['id'], response_text, ref_links))
                                
                                if mark_resolved:
                                    execute_query("UPDATE task_issues SET is_resolved = 1 WHERE id = ?", (issue['id'],))
                                
                                st.success("Response submitted and issue status updated!")
                                st.rerun()


# --- TAB 3: Analytics ---
with tab3:
    st.subheader("Project Health Analytics")
    all_tasks = execute_query("SELECT status, due_date, completion_date, assigned_to_id FROM tasks WHERE project_id = ?", (PROJECT_ID,), fetch="all")
    
    if not all_tasks:
        st.info("No tasks created yet to generate analytics.")
    else:
        df = pd.DataFrame(all_tasks)
        df['due_date'] = pd.to_datetime(df['due_date'])
        df['completion_date'] = pd.to_datetime(df['completion_date'])

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Task Status Breakdown")
            status_counts = df['status'].value_counts().reset_index()
            status_counts.columns = ['status', 'count']
            fig_pie = px.pie(status_counts, names='status', values='count', title="Current Task Statuses", hole=0.3)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            st.markdown("##### On-Time Completion")
            df_done = df[df['status'] == 'Done'].copy()
            df_done['on_time'] = df_done['completion_date'] <= df_done['due_date']
            on_time_counts = df_done['on_time'].value_counts().reset_index()
            on_time_counts.columns = ['on_time', 'count']
            on_time_counts['on_time'] = on_time_counts['on_time'].map({True: 'On Time', False: 'Late'})
            fig_bar = px.bar(on_time_counts, x='on_time', y='count', title="On-Time vs. Late Task Completion", color='on_time')
            st.plotly_chart(fig_bar, use_container_width=True)


# --- TAB 4: Team Progress ---
with tab4:
    st.subheader("Individual Team Member Progress")
    if not members_map:
        st.warning("No members are assigned to this project.")
    else:
        for member_id, member_name in members_map.items():
            with st.expander(f"**{member_name}**"):
                member_tasks = execute_query("SELECT title, status, due_date FROM tasks WHERE assigned_to_id = ? AND project_id = ?", (member_id, PROJECT_ID), "all")
                open_issues_count = execute_query("SELECT COUNT(id) as count FROM task_issues WHERE member_id = ? AND task_id IN (SELECT id FROM tasks WHERE project_id = ?) AND is_resolved = 0", (member_id, PROJECT_ID), "one")['count']
                
                st.metric(label="Open Issues", value=open_issues_count)
                
                if not member_tasks:
                    st.write("No tasks assigned yet.")
                else:
                    st.write("Assigned Tasks:")
                    st.dataframe(member_tasks, use_container_width=True)


# --- TAB 5: Manage Resources ---
with tab5:
    st.subheader("Shared Project Resources")
    st.info("Add links to documentation, articles, or tools that are useful for the entire team.")

    col1, col2 = st.columns([1, 2])
    with col1:
        with st.form("add_resource_form", clear_on_submit=True):
            st.markdown("##### Add a New Resource")
            res_title = st.text_input("Resource Title")
            res_link = st.text_input("URL / Link")
            res_desc = st.text_area("Brief Description")
            
            if st.form_submit_button("Add Resource"):
                if res_title and res_link:
                    execute_query("INSERT INTO resources (project_id, title, link, description) VALUES (?, ?, ?, ?)",
                                  (PROJECT_ID, res_title, res_link, res_desc))
                    st.success("Resource added successfully!")
                else:
                    st.error("Title and Link are required.")

    with col2:
        st.markdown("##### Existing Resources")
        resources = execute_query("SELECT id, title, link, description FROM resources WHERE project_id = ?", (PROJECT_ID,), "all")
        if not resources:
            st.write("No resources have been added yet.")
        else:
            for res in resources:
                with st.container(border=True):
                    st.markdown(f"**[{res['title']}]({res['link']})**")
                    if res['description']:
                        st.caption(res['description'])

