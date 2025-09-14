import streamlit as st
import pandas as pd
from utils import execute_query, get_password_hash

st.set_page_config(layout="wide", page_title="Super Admin Panel")

# --- Security Check ---
if 'logged_in' not in st.session_state or not st.session_state.get('logged_in'):
    st.error("You must be logged in to view this page.")
    st.stop()
if st.session_state.get('user_type') != 'super_admin':
    st.error("Access Denied: This page is for Super Admins only.")
    st.stop()

# --- Page Content ---
st.title("👑 Super Admin Panel")
st.write("Manage projects, project managers, and team members across the entire application.")

tab1, tab2, tab3 = st.tabs(["Manage Projects", "Manage Users (Managers & Members)", "Assign Members to Projects"])

# --- TAB 1: Manage Projects ---
with tab1:
    st.subheader("Create and View Projects")
    managers = execute_query("SELECT id, username FROM project_managers", fetch="all")
    manager_map = {m['id']: m['username'] for m in managers} if managers else {}

    col1, col2 = st.columns([1, 2])
    with col1:
        with st.form("add_project_form", clear_on_submit=True):
            st.markdown("##### Create a New Project")
            project_name = st.text_input("Project Name")
            project_desc = st.text_area("Project Description")
            if not manager_map:
                st.warning("Please create a Project Manager first before creating a project.")
                submitted = st.form_submit_button("Create Project", disabled=True)
            else:
                manager_id = st.selectbox("Assign Project Manager", options=list(manager_map.keys()), format_func=lambda x: manager_map[x])
                submitted = st.form_submit_button("Create Project", type="primary")

            if submitted and project_name and manager_id:
                execute_query("INSERT INTO projects (name, description, manager_id) VALUES (?, ?, ?)", (project_name, project_desc, manager_id))
                st.success(f"Project '{project_name}' created and assigned to {manager_map[manager_id]}.")
            elif submitted:
                st.error("Project Name and Manager are required.")

    with col2:
        st.markdown("##### All Projects")
        all_projects_query = """
            SELECT p.name, p.description, pm.username as manager
            FROM projects p
            LEFT JOIN project_managers pm ON p.manager_id = pm.id
        """
        all_projects = execute_query(all_projects_query, fetch="all")
        if all_projects:
            st.dataframe(pd.DataFrame(all_projects), use_container_width=True)
        else:
            st.info("No projects created yet.")

# --- TAB 2: Manage Users ---
with tab2:
    st.subheader("Create and View Users")
    col1, col2 = st.columns(2)
    with col1:
        with st.form("add_user_form", clear_on_submit=True):
            st.markdown("##### Create a New User")
            user_type = st.selectbox("User Role", ["Project Manager", "Team Member"])
            username_or_name = st.text_input("Username (for Manager) or Full Name (for Member)")
            email = st.text_input("Email (for Team Member)")
            password = st.text_input("Password", type="password")

            submitted = st.form_submit_button("Create User", type="primary")
            if submitted:
                if not (username_or_name and password):
                    st.error("Name/Username and Password are required.")
                elif user_type == "Team Member" and not email:
                    st.error("Email is required for Team Members.")
                else:
                    hashed_password = get_password_hash(password)
                    try:
                        if user_type == "Project Manager":
                            execute_query("INSERT INTO project_managers (username, password) VALUES (?, ?)", (username_or_name, hashed_password))
                            st.success(f"Project Manager '{username_or_name}' created.")
                        else: # Team Member
                            execute_query("INSERT INTO team_members (name, email, password) VALUES (?, ?, ?)", (username_or_name, email, hashed_password))
                            st.success(f"Team Member '{username_or_name}' created.")
                    except Exception as e:
                        st.error(f"Failed to create user. Email/Username might already exist. Error: {e}")

    with col2:
        st.markdown("##### Existing Project Managers")
        all_managers = execute_query("SELECT id, username FROM project_managers", fetch="all")
        st.dataframe(pd.DataFrame(all_managers), use_container_width=True)

        st.markdown("##### Existing Team Members")
        all_members = execute_query("SELECT id, name, email FROM team_members", fetch="all")
        st.dataframe(pd.DataFrame(all_members), use_container_width=True)

# --- TAB 3: Assign Members to Projects ---
with tab3:
    st.subheader("Manage Project Assignments")
    projects = execute_query("SELECT id, name FROM projects", fetch="all")
    members = execute_query("SELECT id, name FROM team_members", fetch="all")

    if not projects or not members:
        st.warning("Please create at least one project and one team member to manage assignments.")
    else:
        project_map = {p['id']: p['name'] for p in projects}
        member_map = {m['id']: m['name'] for m in members}

        selected_project_id = st.selectbox("Select Project to Manage", options=list(project_map.keys()), format_func=lambda x: project_map[x], key="assign_proj_select")

        st.markdown(f"##### Members for: **{project_map[selected_project_id]}**")

        # Get members already in the project
        assigned_members_query = """
            SELECT tm.id, tm.name FROM team_members tm
            JOIN project_members pm ON tm.id = pm.member_id
            WHERE pm.project_id = ?
        """
        assigned_members = execute_query(assigned_members_query, (selected_project_id,), fetch="all")
        assigned_member_ids = [m['id'] for m in assigned_members]

        st.write("Currently Assigned:")
        if assigned_members:
            st.dataframe(pd.DataFrame(assigned_members), use_container_width=True)
        else:
            st.info("No members assigned to this project yet.")

        # Form to add new members
        st.markdown("---")
        st.markdown("##### Assign a New Member")
        unassigned_members = {mid: mname for mid, mname in member_map.items() if mid not in assigned_member_ids}

        if not unassigned_members:
            st.warning("All available team members are already assigned to this project.")
        else:
            with st.form("assign_member_form", clear_on_submit=True):
                member_to_add = st.selectbox("Select Member to Add", options=list(unassigned_members.keys()), format_func=lambda x: unassigned_members[x])
                submitted = st.form_submit_button("Assign Member")
                if submitted:
                    execute_query("INSERT INTO project_members (project_id, member_id) VALUES (?, ?)", (selected_project_id, member_to_add))
                    st.success(f"{unassigned_members[member_to_add]} has been assigned to {project_map[selected_project_id]}.")
                    st.rerun()

