import streamlit as st
import sqlite3
from pathlib import Path
import pandas as pd
from passlib.context import CryptContext
from datetime import datetime

# --- PASSWORD HASHING SETUP ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- DATABASE SETUP ---
DB_FILE = "project_tracker.db"
SQL_FILE = "project_tracker.sql"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- HASHING & VERIFICATION ---
def verify_password(plain_password, hashed_password):
    """Verifies a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hashes a password."""
    return pwd_context.hash(password)

# --- SESSION STATE & LOGIN LOGIC ---
def login_user(email, password, user_type="user"):
    """Handles the login logic for both users and admins."""
    conn = get_db_connection()
    if user_type == "admin":
        user = conn.execute("SELECT * FROM admins WHERE username = ?", (email,)).fetchone()
    else:
        user = conn.execute("SELECT * FROM team_members WHERE email = ?", (email,)).fetchone()
    conn.close()

    if user and verify_password(password, user['password']):
        st.session_state['logged_in'] = True
        st.session_state['user_type'] = user_type
        if user_type == "admin":
            st.session_state['user_info'] = {'name': user['username'], 'id': user['id']}
        else: # Regular user
             st.session_state['user_info'] = {'name': user['name'], 'email': user['email'], 'id': user['id']}
        return True
    return False

def logout():
    """Logs out the user by clearing session state."""
    st.session_state['logged_in'] = False
    st.session_state.pop('user_type', None)
    st.session_state.pop('user_info', None)
    st.success("You have been logged out.")
    st.rerun()

def display_login_form():
    """Displays the login form in the Streamlit app."""
    st.header("Login")
    login_tab, signup_tab = st.tabs(["User Login", "Admin Login"])

    with login_tab:
        with st.form("user_login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if login_user(email, password, user_type="user"):
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

    with signup_tab:
        with st.form("admin_login_form"):
            username = st.text_input("Admin Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if login_user(username, password, user_type="admin"):
                    st.rerun()
                else:
                    st.error("Invalid admin username or password.")

def init_db():
    """Initializes or updates the database using the schema from project_tracker.sql."""
    if not Path(DB_FILE).is_file():
        st.info("Database not found. Initializing a new one...")
    try:
        conn = get_db_connection()
        with open(SQL_FILE, 'r') as f:
            conn.executescript(f.read())
        # Check if default admin exists, if not, create one
        admin = conn.execute("SELECT * FROM admins WHERE username = 'Sateesh'").fetchone()
        if not admin:
            hashed_password = get_password_hash("Kanasu@1976")
            conn.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ("Sateesh", hashed_password))
            conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error initializing/updating database: {e}")
        st.stop()

# --- UNIVERSAL DB HELPERS ---
def execute_query(query, params=(), fetch=None):
    """General purpose function to execute database queries."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    last_id = cursor.lastrowid
    if fetch == "one":
        result = cursor.fetchone()
    elif fetch == "all":
        result = cursor.fetchall()
    else:
        result = None
    conn.commit()
    conn.close()
    return result if fetch else last_id

# --- APP INITIALIZATION ---
init_db()
st.set_page_config(layout="wide", page_title="Advanced Project Tracker")

# --- LOGIN WALL ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    display_login_form()
    st.stop()

# --- MAIN APP INTERFACE ---
st.sidebar.title(f"Welcome, {st.session_state['user_info']['name']}")
if st.sidebar.button("Logout"):
    logout()

st.title("Advanced Project Tracker")

# --- PROJECT SELECTION (for non-admins) ---
if st.session_state['user_type'] != 'admin':
    user_id = st.session_state['user_info']['id']
    assigned_projects = execute_query(
        "SELECT p.id, p.name FROM projects p JOIN project_members pm ON p.id = pm.project_id WHERE pm.member_id = ?",
        (user_id,),
        fetch="all"
    )
    if not assigned_projects:
        st.warning("You are not assigned to any projects. Please contact an administrator.")
        st.stop()
    
    project_map = {p['id']: p['name'] for p in assigned_projects}
    selected_project_id = st.sidebar.selectbox("Select Project", options=list(project_map.keys()), format_func=lambda x: project_map[x])
    st.session_state['selected_project_id'] = selected_project_id
    st.sidebar.markdown(f"**Current Project:** {project_map[selected_project_id]}")


# --- NAVIGATION ---
PAGES_USER = ["Dashboard", "Sprint Dashboard", "Sprints & Tasks", "My Progress", "Project Coordination"]
PAGES_ADMIN = ["Admin Panel", "Project Manager Dashboard"]

if st.session_state['user_type'] == 'admin':
    page = st.sidebar.radio("Navigation", PAGES_ADMIN)
else:
    page = st.sidebar.radio("Navigation", PAGES_USER)


# --- DATA MAPPINGS (Cache project-specific data) ---
@st.cache_data
def get_maps(project_id):
    if project_id is None: return {}, {}, {}
    members_query = """
        SELECT tm.id, tm.name FROM team_members tm
        JOIN project_members pm ON tm.id = pm.member_id
        WHERE pm.project_id = ?
    """
    members = {m['id']: m['name'] for m in execute_query(members_query, (project_id,), fetch="all")}
    requirements = {r['id']: r['title'] for r in execute_query("SELECT id, title FROM requirements WHERE project_id = ?", (project_id,), fetch="all")}
    tasks = {t['id']: t['title'] for t in execute_query("SELECT id, title FROM tasks WHERE project_id = ?", (project_id,), fetch="all")}
    return members, requirements, tasks

if st.session_state['user_type'] != 'admin':
    PROJECT_ID = st.session_state.get('selected_project_id')
    MEMBERS_MAP, REQUIREMENTS_MAP, TASKS_MAP = get_maps(PROJECT_ID)
else:
    MEMBERS_MAP, REQUIREMENTS_MAP, TASKS_MAP = {}, {}, {} # Admin views all data, doesn't need project-specific maps

# =====================================================================================
# ADMIN PANEL
# =====================================================================================
if page == "Admin Panel":
    st.header("Admin Panel")
    tab1, tab2, tab3 = st.tabs(["Create Project", "Add/Assign Users", "View All Projects"])

    with tab1:
        st.subheader("Create New Project")
        with st.form("create_project_form"):
            project_name = st.text_input("Project Name")
            project_desc = st.text_area("Project Description")
            submitted = st.form_submit_button("Create Project")
            if submitted and project_name:
                try:
                    execute_query("INSERT INTO projects (name, description) VALUES (?, ?)", (project_name, project_desc))
                    st.success(f"Project '{project_name}' created.")
                except sqlite3.IntegrityError:
                    st.error("A project with this name already exists.")
    
    with tab2:
        st.subheader("Add New User")
        with st.form("add_user_form"):
            member_name = st.text_input("Student Name")
            member_email = st.text_input("Student Email")
            member_pass = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Add User")
            if submitted and member_name and member_email and member_pass:
                hashed_pass = get_password_hash(member_pass)
                try:
                    execute_query("INSERT INTO team_members (name, email, password) VALUES (?, ?, ?)", (member_name, member_email, hashed_pass))
                    st.success(f"User '{member_name}' created.")
                except sqlite3.IntegrityError:
                    st.error("A user with this email already exists.")

        st.subheader("Assign User to Project")
        all_users = {u['id']: u['name'] for u in execute_query("SELECT id, name FROM team_members", fetch="all")}
        all_projects = {p['id']: p['name'] for p in execute_query("SELECT id, name FROM projects", fetch="all")}
        
        if all_users and all_projects:
            with st.form("assign_user_form"):
                user_id = st.selectbox("Select User", options=list(all_users.keys()), format_func=lambda x: all_users[x])
                project_id = st.selectbox("Select Project to Assign", options=list(all_projects.keys()), format_func=lambda x: all_projects[x])
                submitted = st.form_submit_button("Assign Project")
                if submitted:
                    try:
                        execute_query("INSERT INTO project_members (project_id, member_id) VALUES (?, ?)", (project_id, user_id))
                        st.success(f"'{all_users[user_id]}' assigned to '{all_projects[project_id]}'.")
                    except sqlite3.IntegrityError:
                        st.warning("This user is already assigned to this project.")
        else:
            st.info("Create users and projects before assigning them.")

    with tab3:
        st.subheader("Existing Projects and Members")
        projects = execute_query("SELECT * FROM projects", fetch="all")
        for proj in projects:
            with st.expander(f"**Project: {proj['name']}**"):
                members = execute_query("""
                    SELECT tm.name, tm.email FROM team_members tm
                    JOIN project_members pm ON tm.id = pm.member_id
                    WHERE pm.project_id = ?
                """, (proj['id'],), fetch="all")
                if members:
                    df = pd.DataFrame(members)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.write("No members assigned to this project yet.")


# =====================================================================================
# PROJECT MANAGER DASHBOARD
# =====================================================================================
elif page == "Project Manager Dashboard":
    st.header("Project Manager Dashboard")
    
    all_projects = {p['id']: p['name'] for p in execute_query("SELECT id, name FROM projects", fetch="all")}
    if not all_projects:
        st.info("No projects created yet.")
        st.stop()

    proj_id_pm = st.selectbox("Select Project to View", options=list(all_projects.keys()), format_func=lambda x: all_projects[x])
    st.subheader(f"Dashboard for: {all_projects[proj_id_pm]}")
    
    tab1, tab2, tab3 = st.tabs(["Overview", "Activity Feed", "Task Issues & Support"])

    with tab1:
        st.subheader("Task Status Overview")
        tasks_df = pd.DataFrame(execute_query("SELECT status, COUNT(*) as count FROM tasks WHERE project_id=? GROUP BY status", (proj_id_pm,), fetch="all"))
        if not tasks_df.empty:
            st.bar_chart(tasks_df.set_index('status'))
        else:
            st.info("No tasks in this project to display.")

        st.subheader("Task Distribution per Member")
        dist_df = pd.DataFrame(execute_query("""
            SELECT tm.name, COUNT(t.id) as task_count
            FROM team_members tm
            JOIN project_members pm ON tm.id = pm.member_id
            LEFT JOIN tasks t ON tm.id = t.assigned_to_id AND t.project_id = ?
            WHERE pm.project_id = ?
            GROUP BY tm.name
        """, (proj_id_pm, proj_id_pm), fetch="all"))
        if not dist_df.empty:
            st.bar_chart(dist_df.set_index('name'))

    with tab2:
        st.subheader("Recent Activity")
        activity = execute_query("""
            SELECT 'Progress' as type, p.description, tm.name as member_name, t.title as task_title, p.timestamp
            FROM progress_updates p
            JOIN team_members tm ON p.member_id = tm.id
            JOIN tasks t ON p.task_id = t.id WHERE t.project_id = ?
            UNION ALL
            SELECT 'Issue Raised' as type, i.description, tm.name as member_name, t.title as task_title, i.timestamp
            FROM task_issues i
            JOIN team_members tm ON i.member_id = tm.id
            JOIN tasks t ON i.task_id = t.id WHERE t.project_id = ?
            ORDER BY timestamp DESC LIMIT 20
        """, (proj_id_pm, proj_id_pm), fetch="all")
        if not activity:
            st.info("No recent activity in this project.")
        for item in activity:
            with st.container(border=True):
                if item['type'] == 'Progress':
                    st.markdown(f"**Progress Update** on **{item['task_title']}** by **{item['member_name']}**")
                else:
                    st.markdown(f"**New Issue** on **{item['task_title']}** by **{item['member_name']}**")
                st.write(f"> {item['description']}")
                st.caption(f"_{datetime.fromisoformat(item['timestamp']).strftime('%Y-%m-%d %H:%M')}_")
    
    with tab3:
        st.subheader("Open Issues & Requests")
        
        meeting_requests = execute_query("""
            SELECT ti.id, t.title as task_title, tm.name as member_name, ti.description 
            FROM task_issues ti
            JOIN tasks t ON ti.task_id = t.id
            JOIN team_members tm ON ti.member_id = tm.id
            WHERE t.project_id = ? AND ti.request_1_on_1 = 1 AND ti.status = 'Open'
        """, (proj_id_pm,), "all")
        if meeting_requests:
            st.warning("1:1 Meeting Requests")
            for req in meeting_requests:
                st.markdown(f"- **{req['member_name']}** requested a meeting for task **'{req['task_title']}'** regarding: *{req['description']}*")
        
        open_issues = execute_query("""
            SELECT ti.*, t.title as task_title, tm.name as member_name 
            FROM task_issues ti
            JOIN tasks t ON ti.task_id = t.id
            JOIN team_members tm ON ti.member_id = tm.id
            WHERE t.project_id = ? AND ti.status = 'Open'
        """, (proj_id_pm,), "all")
        
        if not open_issues:
            st.success("No open issues. All student concerns have been addressed!")
        for issue in open_issues:
            with st.container(border=True):
                st.markdown(f"**Issue on task '{issue['task_title']}' from {issue['member_name']}** ({issue['issue_type']})")
                st.info(f"**Description:** {issue['description']}")
                with st.form(key=f"issue_response_{issue['id']}"):
                    response_text = st.text_area("Your Answer/Clarification")
                    ref_links = st.text_area("Reference Links (one URL per line)")
                    hint_type = st.selectbox("Response Type", ["Clarification", "Manager Hint", "AI Suggestion"])
                    submitted = st.form_submit_button("Post Response & Resolve Issue")
                    if submitted and response_text:
                        execute_query("""
                            INSERT INTO issue_responses (issue_id, responder_id, response_text, reference_links, hint_type) 
                            VALUES (?, ?, ?, ?, ?)
                        """, (issue['id'], st.session_state['user_info']['id'], response_text, ref_links, hint_type))
                        execute_query("UPDATE task_issues SET status = 'Resolved' WHERE id = ?", (issue['id'],))
                        st.success("Response posted and issue marked as resolved.")
                        st.rerun()

# =====================================================================================
# USER-FACING PAGES (PROJECT-SPECIFIC)
# =====================================================================================
elif 'selected_project_id' in st.session_state:
    PROJECT_ID = st.session_state['selected_project_id']

    if page == "Sprint Dashboard":
        st.header("Sprint Dashboard")
        sprints = execute_query("SELECT * FROM sprints WHERE project_id = ? ORDER BY id DESC", (PROJECT_ID,), "all")
        if not sprints:
            st.info("No sprints created for this project yet. Go to 'Sprints & Tasks' to create one.")
        else:
            sprint_map = {s['id']: s['name'] for s in sprints}
            selected_sprint_id = st.selectbox("Select a Sprint to view its dashboard", options=list(sprint_map.keys()), format_func=lambda x: sprint_map[x])
            
            sprint_details = execute_query("SELECT * FROM sprints WHERE id = ?", (selected_sprint_id,), "one")
            st.subheader(f"Details for {sprint_details['name']}")
            st.markdown(f"**Goal:** {sprint_details['goal']}")
            st.markdown(f"**Schedule:** `{sprint_details['start_date']}` to `{sprint_details['end_date']}`")

            sprint_tasks = execute_query("SELECT * FROM tasks WHERE sprint_id = ?", (selected_sprint_id,), "all")
            if sprint_tasks:
                total_tasks = len(sprint_tasks)
                done_tasks = len([t for t in sprint_tasks if t['status'] == 'Done'])
                progress = done_tasks / total_tasks if total_tasks > 0 else 0
                st.progress(progress, text=f"Sprint Progress: {done_tasks}/{total_tasks} tasks completed")
            else:
                st.info("No tasks have been added to this sprint yet.")

            st.subheader("Features & Requirements for this Sprint")
            sprint_reqs = execute_query("""
                SELECT r.title, r.description FROM requirements r
                JOIN sprint_requirements sr ON r.id = sr.requirement_id
                WHERE sr.sprint_id = ?
            """, (selected_sprint_id,), "all")
            if not sprint_reqs:
                st.warning("No requirements have been assigned to this sprint.")
            for req in sprint_reqs:
                with st.container(border=True):
                    st.markdown(f"**{req['title']}**")
                    st.write(req['description'])

            st.subheader("Your Tasks in this Sprint")
            my_sprint_tasks = [t for t in sprint_tasks if t['assigned_to_id'] == st.session_state['user_info']['id']]
            if not my_sprint_tasks:
                st.info("You do not have any tasks assigned to you in this sprint.")
            else:
                for task in my_sprint_tasks:
                    st.markdown(f"- **{task['title']}** (Status: `{task['status']}`)")

    elif page == "Sprints & Tasks":
        st.header("Manage Sprints, Requirements & Tasks")
        tab1, tab2 = st.tabs(["Sprints & Tasks", "Project Requirements"])
        
        with tab1:
            with st.expander("Create New Sprint"):
                 with st.form("new_sprint_form"):
                    sprint_name = st.text_input("Sprint Name")
                    sprint_goal = st.text_area("Sprint Goal")
                    start_date = st.date_input("Start Date")
                    end_date = st.date_input("End Date")
                    
                    all_reqs = {r['id']: r['title'] for r in execute_query("SELECT id, title FROM requirements WHERE project_id = ?", (PROJECT_ID,), "all")}
                    selected_reqs = st.multiselect("Select Requirements for this Sprint", options=list(all_reqs.keys()), format_func=lambda x: all_reqs[x])
                    
                    submitted = st.form_submit_button("Create Sprint")
                    if submitted and sprint_name:
                        sprint_id = execute_query("INSERT INTO sprints (project_id, name, goal, start_date, end_date) VALUES (?, ?, ?, ?, ?)",
                                      (PROJECT_ID, sprint_name, sprint_goal, str(start_date), str(end_date)))
                        for req_id in selected_reqs:
                            execute_query("INSERT INTO sprint_requirements (sprint_id, requirement_id) VALUES (?, ?)", (sprint_id, req_id))
                        st.success("Sprint created and requirements assigned.")
                        st.rerun()

            sprints = execute_query("SELECT * FROM sprints WHERE project_id = ? ORDER BY id DESC", (PROJECT_ID,), "all")
            if not sprints:
                st.info("No sprints created for this project yet.")
            else:
                sprint_map = {s['id']: s['name'] for s in sprints}
                selected_sprint_id = st.selectbox("Select a Sprint to manage tasks", options=list(sprint_map.keys()), format_func=lambda x: sprint_map[x])
                
                with st.expander("Add New Task to this Sprint"):
                    with st.form(f"add_task_form_{selected_sprint_id}"):
                        task_title = st.text_input("Task Title")
                        task_desc = st.text_area("Task Description")
                        assigned_to_id = st.selectbox("Assign To", options=list(MEMBERS_MAP.keys()), format_func=lambda x: MEMBERS_MAP[x])
                        submitted = st.form_submit_button("Add Task")
                        if submitted and task_title:
                            execute_query("INSERT INTO tasks (project_id, sprint_id, title, description, assigned_to_id, status) VALUES (?, ?, ?, ?, ?, ?)",
                                          (PROJECT_ID, selected_sprint_id, task_title, task_desc, assigned_to_id, "To Do"))
                            st.success("Task added.")
                            st.rerun()
                
                tasks = execute_query("SELECT * FROM tasks WHERE sprint_id = ?", (selected_sprint_id,), "all")
                for task in tasks:
                    with st.container(border=True):
                        st.markdown(f"#### {task['title']}")
                        st.caption(f"Assigned to: **{MEMBERS_MAP.get(task['assigned_to_id'], 'N/A')}** | Status: **{task['status']}**")
                        st.write(task['description'])
                        
        with tab2:
            st.subheader("Manage Project Requirements / Features")
            with st.form("add_requirement_form"):
                req_title = st.text_input("Requirement Title")
                req_desc = st.text_area("Requirement Description")
                submitted = st.form_submit_button("Add Requirement")
                if submitted and req_title:
                    execute_query("INSERT INTO requirements (project_id, title, description) VALUES (?, ?, ?)", (PROJECT_ID, req_title, req_desc))
                    st.success("Requirement added.")
            
            st.subheader("Existing Requirements")
            all_reqs = execute_query("SELECT * FROM requirements WHERE project_id = ?", (PROJECT_ID,), "all")
            for req in all_reqs:
                st.markdown(f"- **{req['title']}**")


    elif page == "My Progress":
        st.header("My Personal Workspace")
        member_id = st.session_state['user_info']['id']
        st.subheader("My Assigned Tasks")
        my_tasks = execute_query("SELECT * FROM tasks WHERE assigned_to_id = ? AND project_id = ?", (member_id, PROJECT_ID), "all")
        if not my_tasks:
            st.info("You have no tasks assigned to you for this project.")
        else:
            for task in my_tasks:
                with st.container(border=True):
                    st.markdown(f"### {task['title']}")
                    
                    # --- Status Update ---
                    cols = st.columns(2)
                    with cols[0]:
                        current_status_index = ["To Do", "In Progress", "Done", "Blocked"].index(task['status'])
                        new_status = st.selectbox("Update Task Status", ["To Do", "In Progress", "Done", "Blocked"], index=current_status_index, key=f"status_{task['id']}")
                        if new_status != task['status']:
                            execute_query("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task['id']))
                            st.success("Status updated!")
                            st.rerun()

                    # --- Weekly Activity Log ---
                    with st.expander("Log Weekly Activities"):
                        with st.form(f"activity_log_form_{task['id']}"):
                            activity_date = st.date_input("Week Ending On")
                            activity_desc = st.text_area("Activities Completed this Week")
                            submitted = st.form_submit_button("Log Activity")
                            if submitted and activity_desc:
                                execute_query("INSERT INTO weekly_activities (task_id, member_id, activity_date, description) VALUES (?, ?, ?, ?)",
                                              (task['id'], member_id, str(activity_date), activity_desc))
                                st.success("Activity logged.")
                        
                        st.markdown("**Past Activities:**")
                        activities = execute_query("SELECT * FROM weekly_activities WHERE task_id = ? ORDER BY activity_date DESC", (task['id'],), "all")
                        if not activities:
                            st.caption("No activities logged for this task yet.")
                        for act in activities:
                            st.markdown(f"- **{act['activity_date']}**: {act['description']}")

                    # --- Task Issues & Doubts ---
                    with st.expander("Raise Issue / Ask Question"):
                        with st.form(f"issue_form_{task['id']}"):
                            issue_type = st.selectbox("Issue Type", ["Doubt", "Dependency", "Question"])
                            issue_desc = st.text_area("Describe the issue")
                            req_1_on_1 = st.checkbox("I need a 1:1 meeting to discuss this")
                            submitted = st.form_submit_button("Submit Issue")
                            if submitted and issue_desc:
                                execute_query("""
                                    INSERT INTO task_issues (task_id, member_id, issue_type, description, request_1_on_1) 
                                    VALUES (?, ?, ?, ?, ?)
                                """, (task['id'], member_id, issue_type, issue_desc, 1 if req_1_on_1 else 0))
                                st.success("Issue submitted. Your manager has been notified.")
                    
                    # --- View Issues & Responses ---
                    with st.expander("View Communication on this Task"):
                        issues = execute_query("SELECT * FROM task_issues WHERE task_id = ? ORDER BY timestamp DESC", (task['id'],), "all")
                        if not issues:
                            st.caption("No issues raised for this task yet.")
                        for issue in issues:
                            with st.container(border=True):
                                st.markdown(f"**Issue ({issue['issue_type']}) - Status: {issue['status']}**")
                                st.info(issue['description'])
                                responses = execute_query("SELECT * FROM issue_responses WHERE issue_id = ?", (issue['id'],), "all")
                                if responses:
                                    for resp in responses:
                                        st.success(f"**Response ({resp['hint_type']}) from Manager:**")
                                        st.write(resp['response_text'])
                                        if resp['reference_links']:
                                            st.markdown("**References:**")
                                            for link in resp['reference_links'].strip().split('\n'):
                                                st.markdown(f"- <{link}>")


    elif page == "Project Coordination":
        st.header("Project Coordination")
        tab1, tab2, tab3 = st.tabs(["Project Q&A Forum", "Resource Center", "Schedule Meeting"])

        with tab1:
            st.subheader("Ask a General Question or View Discussions")
            with st.form("ask_doubt_form"):
                question_text = st.text_area("Post a general project-wide question for your manager")
                submitted = st.form_submit_button("Post Question")
                if submitted and question_text:
                    execute_query("INSERT INTO doubts_forum (project_id, member_id, question) VALUES (?, ?, ?)",
                                  (PROJECT_ID, st.session_state['user_info']['id'], question_text))
                    st.success("Your question has been posted.")
            
            st.subheader("Forum History")
            doubts = execute_query("SELECT d.*, tm.name FROM doubts_forum d JOIN team_members tm ON d.member_id = tm.id WHERE d.project_id = ? ORDER BY d.timestamp DESC", (PROJECT_ID,), "all")
            for doubt in doubts:
                with st.expander(f"**Q from {doubt['name']}**: {doubt['question'][:50]}... ({doubt['status']})"):
                    st.info(f"**Question:** {doubt['question']}")
                    # Note: Admin responses to this general forum are handled in the manager dashboard
                    st.warning("Awaiting response from the manager if status is 'Open'.")

        with tab2:
            st.subheader("Helpful Resources")
            resources = execute_query("SELECT * FROM resources WHERE project_id = ?", (PROJECT_ID,), "all")
            if not resources:
                st.info("No resources have been added for this project yet.")
            for res in resources:
                st.markdown(f"[{res['title']}]({res['link']})")
                st.write(res['description'])
                st.markdown("---")
        
        with tab3:
            st.subheader("Request a Meeting")
            st.info("Functionality to request meetings is now handled directly within each task on the 'My Progress' page.")

    else: # Dashboard
        st.header("My Project Dashboard")
        st.subheader("Task Status Overview")
        tasks_df = pd.DataFrame(execute_query("SELECT status, COUNT(*) as count FROM tasks WHERE project_id = ? GROUP BY status", (PROJECT_ID,), fetch="all"))
        if not tasks_df.empty:
            st.bar_chart(tasks_df.set_index('status'))
        else:
            st.info("No tasks to display for this project.")
        
        st.subheader("My Tasks at a Glance")
        my_tasks_df = pd.DataFrame(execute_query("SELECT title, status FROM tasks WHERE project_id = ? AND assigned_to_id = ?", (PROJECT_ID, st.session_state['user_info']['id']), fetch="all"))
        if not my_tasks_df.empty:
            st.dataframe(my_tasks_df, use_container_width=True)
        else:
            st.info("You currently have no tasks assigned to you.")

