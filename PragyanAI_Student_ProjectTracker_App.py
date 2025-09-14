import streamlit as st
from utils import init_db, login_user, logout, execute_query
from langchain_groq import ChatGroq

# --- APP INITIALIZATION ---
# Set page config and initialize the database on first run
st.set_page_config(layout="wide", page_title="Advanced Project Tracker")
init_db()

# --- LOGIN WALL ---
# If the user is not logged in, display the login form and stop execution
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    
    st.title("Welcome to the Advanced Project Tracker")
    st.info("Please log in to continue.")
    
    with st.form("unified_login_form"):
        login_as = st.radio("Login as:", ["Team Member", "Admin"], horizontal=True)
        
        if login_as == "Admin":
            username = st.text_input("Admin Username")
            password = st.text_input("Admin Password", type="password")
        else:
            email = st.text_input("Team Member Email")
            password = st.text_input("Team Member Password", type="password")
        
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if login_as == "Admin":
                if login_user(username, password, user_type="admin"):
                    st.rerun()
                else:
                    st.error("Invalid admin username or password.")
            else:
                if login_user(email, password, user_type="user"):
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
    st.stop()

# --- MAIN APP INTERFACE (for logged-in users) ---
st.sidebar.title(f"Welcome, {st.session_state['user_info']['name']}")
if st.sidebar.button("Logout"):
    logout()
st.sidebar.divider()

# --- AI CONFIGURATION ---
st.sidebar.subheader("AI Assistant Configuration")
st.session_state['groq_api_key'] = st.sidebar.text_input(
    "Groq API Key", 
    type="password", 
    help="Get your key from GroqCloud.", 
    key="groq_key_input", 
    value=st.session_state.get('groq_api_key', '')
)
if st.session_state.get('groq_api_key'):
    try:
        # Store the model in session state so page files can access it
        st.session_state['ai_model'] = ChatGroq(api_key=st.session_state['groq_api_key'], model_name="llama3-8b-8192")
        st.sidebar.success("AI Model Ready")
    except Exception as e:
        st.sidebar.error("Invalid API Key.")
        st.session_state['ai_model'] = None
else:
    st.session_state['ai_model'] = None
st.sidebar.divider()

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
    
    # Get the index of the currently selected project to maintain state across page reloads
    project_ids = list(project_map.keys())
    current_project_id = st.session_state.get('selected_project_id', project_ids[0])
    current_index = project_ids.index(current_project_id) if current_project_id in project_ids else 0

    selected_project_id = st.sidebar.selectbox(
        "Select Project", 
        options=project_ids, 
        format_func=lambda x: project_map[x],
        index=current_index
    )
    st.session_state['selected_project_id'] = selected_project_id
    st.sidebar.markdown(f"**Current Project:** {project_map[selected_project_id]}")
    st.sidebar.divider()

st.header("Project Tracker")
st.info("Please select a page from the sidebar to view its contents.")
st.markdown("---")
st.image("https://images.unsplash.com/photo-1557804506-669a67965ba0?q=80&w=2670&auto=format&fit=crop", caption="Team Collaboration")
