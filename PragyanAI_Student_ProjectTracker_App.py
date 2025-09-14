import streamlit as st
from utils import init_db, login_user, logout, execute_query

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Project Tracker Login",
    page_icon="🔐",
    layout="centered"
)

# --- INITIALIZE DATABASE ---
# This ensures the DB is ready before any other operations
init_db()

# --- LOGIN UI ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("Welcome to the PragyanAI Project Tracker 🚀")
    st.write("Please log in to continue.")

    login_type = st.radio("I am a:", ("Team Member", "Manager / Admin"), key="login_type_radio")

    with st.form("login_form"):
        if login_type == "Team Member":
            identifier = st.text_input("Email")
            user_type_selection = "user"
        else: # Manager / Admin
            identifier = st.text_input("Username")
            user_type_selection = "manager_or_admin"

        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if login_user(identifier, password, user_type_selection):
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
else:
    # --- MAIN APP UI AFTER LOGIN ---
    user_info = st.session_state.get('user_info', {})
    user_type = st.session_state.get('user_type', 'user')

    with st.sidebar:
        st.header(f"Welcome, {user_info.get('name', 'User')}!")
        st.write(f"**Role:** `{user_type.replace('_', ' ').title()}`")

        # --- PROJECT SELECTION ---
        if user_type == 'user':
            # Team members see projects they are assigned to
            projects = execute_query("""
                SELECT p.id, p.name FROM projects p
                JOIN project_members pm ON p.id = pm.project_id
                WHERE pm.member_id = ?
            """, (user_info.get('id', 0),), fetch="all")
        elif user_type == 'project_manager':
            # Project managers see projects they manage
            projects = execute_query("SELECT id, name FROM projects WHERE manager_id = ?", (user_info.get('id', 0),), fetch="all")
        else: # super_admin
            # Super admins see all projects
            projects = execute_query("SELECT id, name FROM projects", fetch="all")

        if projects:
            project_dict = {p['id']: p['name'] for p in projects}
            selected_project_id = st.selectbox(
                "Select a Project",
                options=list(project_dict.keys()),
                format_func=lambda x: project_dict[x],
                key='selected_project_id_widget'
            )
            # Store the selected project ID in session state
            st.session_state['selected_project_id'] = selected_project_id
        else:
            if 'selected_project_id' in st.session_state:
                del st.session_state['selected_project_id'] # Clear if no projects are available

        st.divider()

        # --- GROQ API KEY ---
        st.session_state['groq_api_key'] = st.text_input(
            "Groq API Key",
            type="password",
            help="Needed for AI features. Get yours from https://console.groq.com/keys",
            key='groq_api_key_widget'
        )

        st.divider()

        if st.button("Logout"):
            logout()

    # --- MAIN PAGE CONTENT AFTER LOGIN ---
    st.title("Project Dashboard")
    st.write("Please select a page from the sidebar to begin.")

    if 'selected_project_id' in st.session_state:
        project_name = execute_query("SELECT name FROM projects WHERE id = ?", (st.session_state['selected_project_id'],), fetch="one")
        if project_name:
            st.success(f"You are currently viewing: **{project_name['name']}**")
    elif user_type in ['user', 'project_manager'] and not projects:
         st.warning("You are not yet assigned to any projects. Please contact a Super Admin.")
    else:
        st.info("Select a project from the sidebar to get started.")
