import streamlit as st
import sqlite3
from pathlib import Path
from passlib.context import CryptContext

# --- CONSTANTS ---
DB_FILE = "project_tracker.db"
SQL_FILE = "project_tracker.sql"

# --- PASSWORD HASHING SETUP ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- DATABASE SETUP ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes or updates the database using the schema from project_tracker.sql."""
    if 'db_initialized' not in st.session_state:
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
            st.session_state['db_initialized'] = True
        except Exception as e:
            st.error(f"Error initializing/updating database: {e}")
            st.stop()

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
    """Logs out the user by clearing session state but preserving API key."""
    groq_api_key = st.session_state.get('groq_api_key') # Preserve API key
    for key in list(st.session_state.keys()):
        if key != 'db_initialized': # Don't reset db init flag
            del st.session_state[key]
    if groq_api_key:
        st.session_state['groq_api_key'] = groq_api_key
    st.session_state['logged_in'] = False
    st.success("You have been logged out.")
    st.rerun()

# --- UNIVERSAL DB HELPERS ---
def execute_query(query, params=(), fetch=None):
    """General purpose function to execute database queries."""
    try:
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
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return None # Or handle more gracefully

# --- DATA MAPPINGS (Cache project-specific data) ---
@st.cache_data(ttl=600) # Cache for 10 minutes
def get_project_maps(_project_id): # Use a dummy arg to force re-run when project changes
    """Gets and caches maps for members, requirements, and tasks for a given project."""
    if 'selected_project_id' not in st.session_state:
        return {}, {}, {}
    
    project_id = st.session_state['selected_project_id']
    
    members_query = """
        SELECT tm.id, tm.name FROM team_members tm
        JOIN project_members pm ON tm.id = pm.member_id
        WHERE pm.project_id = ?
    """
    members = {m['id']: m['name'] for m in execute_query(members_query, (project_id,), fetch="all")}
    requirements = {r['id']: r['title'] for r in execute_query("SELECT id, title FROM requirements WHERE project_id = ?", (project_id,), fetch="all")}
    tasks = {t['id']: t['title'] for t in execute_query("SELECT id, title FROM tasks WHERE project_id = ?", (project_id,), fetch="all")}
    return members, requirements, tasks
