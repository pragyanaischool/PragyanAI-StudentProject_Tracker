import streamlit as st
from utils import execute_query, get_password_hash

st.set_page_config(layout="wide", page_title="Admin Panel")

# --- Security Check ---
# Ensure the user is logged in and is an admin
if 'logged_in' not in st.session_state or not st.session_state.get('logged_in'):
    st.error("You must be logged in to view this page.")
    st.stop()
if st.session_state.get('user_type') != 'admin':
    st.error("Access Denied: This page is for Admins only.")
    st.stop()

st.header("👑 Admin Control Panel")
st.info("Manage users, projects, and their assignments from this central hub.")

# --- UI Tabs for different admin functions ---
tab1, tab2, tab3 = st.tabs(["👥 User Management", "📂 Project Management", "🔗 Assign Members to Projects"])

# --- TAB 1: User Management ---
with tab1:
    st.subheader("Team Member Accounts")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("##### Add a New Team Member")
        with st.form("add_user_form", clear_on_submit=True):
            new_name = st.text_input("Full Name")
            new_email = st.text_input("Email Address")
            new_password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Create User Account")

            if submitted:
                if not all([new_name, new_email, new_password]):
                    st.error("All fields are required.")
                else:
                    # Check if user already exists
                    existing_user = execute_query("SELECT id FROM team_members WHERE email = ?", (new_email,), fetch="one")
                    if existing_user:
                        st.error("A user with this email already exists.")
                    else:
                        hashed_password = get_password_hash(new_password)
                        execute_query("INSERT INTO team_members (name, email, password) VALUES (?, ?, ?)", (new_name, new_email, hashed_password))
                        st.success(f"Successfully created account for {new_name}.")

    with col2:
        st.markdown("##### Existing Team Members")
        users = execute_query("SELECT id, name, email FROM team_members", fetch="all")
        if users:
            st.dataframe(users, use_container_width=True)
        else:
            st.info("No team members have been added yet.")

# --- TAB 2: Project Management ---
with tab2:
    st.subheader("Projects")
    
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("##### Create a New Project")
        with st.form("add_project_form", clear_on_submit=True):
            project_name = st.text_input("Project Name")
            project_desc = st.text_area("Project Description")
            submitted = st.form_submit_button("Create Project")

            if submitted:
                if not all([project_name, project_desc]):
                    st.error("Both project name and description are required.")
                else:
                    execute_query("INSERT INTO projects (name, description, manager_id) VALUES (?, ?, ?)", 
                                  (project_name, project_desc, st.session_state['user_info']['id']))
                    st.success(f"Successfully created project '{project_name}'.")

    with col2:
        st.markdown("##### Existing Projects")
        projects = execute_query("SELECT id, name, description FROM projects", fetch="all")
        if projects:
            st.dataframe(projects, use_container_width=True)
        else:
            st.info("No projects have been created yet.")

# --- TAB 3: Assign Members to Projects ---
with tab3:
    st.subheader("Project Assignments")
    
    projects_list = execute_query("SELECT id, name FROM projects", fetch="all")
    users_list = execute_query("SELECT id, name, email FROM team_members", fetch="all")

    if not projects_list or not users_list:
        st.warning("Please create at least one project and one user before assigning members.")
    else:
        project_map = {p['id']: p['name'] for p in projects_list}
        user_map = {u['id']: f"{u['name']} ({u['email']})" for u in users_list}
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Assign a Member to a Project")
            selected_project_id = st.selectbox("Select Project", options=list(project_map.keys()), format_func=lambda x: project_map[x])
            
            # Get members already in the selected project
            assigned_members_ids = [row['member_id'] for row in execute_query("SELECT member_id FROM project_members WHERE project_id = ?", (selected_project_id,), fetch="all")]
            
            # Filter out already assigned members from the list of users to assign
            unassigned_users = {uid: uname for uid, uname in user_map.items() if uid not in assigned_members_ids}

            if not unassigned_users:
                st.warning("All available users are already assigned to this project.")
            else:
                selected_user_id = st.selectbox("Select Team Member to Add", options=list(unassigned_users.keys()), format_func=lambda x: unassigned_users[x])
                
                if st.button("Assign Member", type="primary"):
                    # Check for existing assignment (double-check)
                    existing = execute_query("SELECT * FROM project_members WHERE project_id = ? AND member_id = ?", (selected_project_id, selected_user_id), fetch="one")
                    if existing:
                        st.error("This user is already assigned to this project.")
                    else:
                        execute_query("INSERT INTO project_members (project_id, member_id) VALUES (?, ?)", (selected_project_id, selected_user_id))
                        st.success(f"Assigned {user_map[selected_user_id]} to {project_map[selected_project_id]}.")
                        st.rerun()

        with col2:
            st.markdown("##### Current Project Assignments")
            if selected_project_id:
                st.write(f"**Showing members for:** `{project_map[selected_project_id]}`")
                
                # Fetch members assigned to the selected project
                assigned_members = execute_query("""
                    SELECT tm.name, tm.email FROM team_members tm
                    JOIN project_members pm ON tm.id = pm.member_id
                    WHERE pm.project_id = ?
                """, (selected_project_id,), fetch="all")

                if assigned_members:
                    st.dataframe(assigned_members, use_container_width=True)
                else:
                    st.info("No members have been assigned to this project yet.")
