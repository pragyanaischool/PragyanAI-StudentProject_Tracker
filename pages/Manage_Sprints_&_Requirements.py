import streamlit as st
from utils import execute_query, get_project_maps
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

st.set_page_config(layout="wide", page_title="Sprints & Requirements")

# --- Security Check ---
if 'logged_in' not in st.session_state or not st.session_state.get('logged_in'):
    st.error("You must be logged in to view this page.")
    st.stop()
if st.session_state.get('user_type') != 'admin':
    st.error("Access Denied: This page is for Project Managers (Admins) only.")
    st.stop()
if 'selected_project_id' not in st.session_state:
    st.warning("Please select a project from the main page sidebar to manage sprints and requirements.")
    st.stop()

# --- Page Setup ---
PROJECT_ID = st.session_state['selected_project_id']
project_details = execute_query("SELECT name FROM projects WHERE id = ?", (PROJECT_ID,), fetch="one")
st.header(f"🛠️ Sprints & Requirements for: {project_details['name']}")
st.info("Define sprints, manage requirements with AI assistance, and create tasks for your team.")

# --- AI Helper Function ---
def get_ai_response(system_prompt, human_template, context):
    """Generic function to get a response from the AI model."""
    if not st.session_state.get("groq_api_key"):
        st.error("Please set your Groq API Key in the sidebar on the main page to use AI features.")
        return None
    
    try:
        chat = ChatGroq(
            temperature=0.7,
            groq_api_key=st.session_state.get("groq_api_key"),
            model_name=st.session_state.get("selected_model", "llama3-70b-8192")
        )
        prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_template)])
        chain = prompt | chat | StrOutputParser()
        return chain.stream(context)
    except Exception as e:
        st.error(f"AI model error: {e}")
        return None

# --- UI TABS ---
tab1, tab2, tab3 = st.tabs(["📋 Requirements & AI Tools", "🏃‍♂️ Sprint Management", "📝 Task Management"])

# --- TAB 1: Requirements & AI Tools ---
with tab1:
    st.subheader("Define, Refine, and Deconstruct Requirements")
    
    # --- Part 1: Project Problem Statement ---
    with st.expander("🎯 Project Problem Statement (AI Context)", expanded=True):
        project_data = execute_query("SELECT description, problem_statement FROM projects WHERE id = ?", (PROJECT_ID,), "one")
        
        problem_statement = st.text_area(
            "Define the core problem this project solves.",
            value=project_data['problem_statement'] or "",
            height=150,
            help="This provides crucial context for the AI to generate relevant requirements and tasks."
        )
        if st.button("Save Problem Statement"):
            execute_query("UPDATE projects SET problem_statement = ? WHERE id = ?", (problem_statement, PROJECT_ID))
            st.success("Problem statement updated!")
            st.rerun()

    st.divider()

    # --- Part 2: Manage Requirements ---
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Add a New Requirement")
        with st.form("add_req_form", clear_on_submit=True):
            req_title = st.text_input("Requirement Title")
            req_desc = st.text_area("Initial High-Level Description")
            if st.form_submit_button("Add Requirement", type="primary"):
                if req_title and req_desc:
                    execute_query("INSERT INTO requirements (project_id, title, description) VALUES (?, ?, ?)",
                                  (PROJECT_ID, req_title, req_desc))
                    st.success(f"Requirement '{req_title}' added.")
                else:
                    st.error("Title and description are required.")
    
    with col2:
        st.markdown("##### Existing Requirements")
        requirements = execute_query("SELECT id, title FROM requirements WHERE project_id = ?", (PROJECT_ID,), "all")
        if not requirements:
            st.info("No requirements added yet.")
        else:
            st.dataframe(requirements, use_container_width=True)

    st.divider()

    # --- Part 3: AI Refinement & Task Generation ---
    st.subheader("✨ AI Assistant: Refine & Generate")
    if requirements:
        req_map = {r['id']: r['title'] for r in requirements}
        selected_req_id = st.selectbox("Select a requirement to work with:", options=list(req_map.keys()), format_func=lambda x: req_map[x])
        
        if selected_req_id:
            req_details = execute_query("SELECT title, description, refined_description FROM requirements WHERE id = ?", (selected_req_id,), "one")
            
            st.markdown(f"**Working on:** `{req_details['title']}`")
            st.info(f"**Initial Description:**\n{req_details['description']}")
            
            if st.button("Refine Requirement with AI ✨", key=f"refine_{selected_req_id}"):
                with st.spinner("AI is thinking..."):
                    system_prompt = "You are an expert product manager. Your task is to rewrite a high-level requirement into a clear, specific, and actionable description for a student development team. Use markdown for formatting."
                    human_template = """
                    Project Problem Statement: {problem_statement}
                    Initial Requirement Title: {req_title}
                    Initial Requirement Description: {req_desc}

                    Please refine the description.
                    """
                    context = {
                        "problem_statement": problem_statement,
                        "req_title": req_details['title'],
                        "req_desc": req_details['description']
                    }
                    ai_response = get_ai_response(system_prompt, human_template, context)
                    if ai_response:
                        st.session_state[f"refined_{selected_req_id}"] = st.write_stream(ai_response)

            if f"refined_{selected_req_id}" in st.session_state:
                refined_text = st.text_area("AI-Generated Refinement:", value=st.session_state[f"refined_{selected_req_id}"], height=250)
                if st.button("Save Refined Description", key=f"save_{selected_req_id}"):
                    execute_query("UPDATE requirements SET refined_description = ? WHERE id = ?", (refined_text, selected_req_id))
                    del st.session_state[f"refined_{selected_req_id}"]
                    st.success("Refined description saved!")
                    st.rerun()

            if req_details['refined_description']:
                st.success("**Refined Description (Saved):**")
                st.markdown(req_details['refined_description'])
                if st.button("Generate Tasks from Refinement 🤖", key=f"gen_tasks_{selected_req_id}"):
                    with st.spinner("AI is generating tasks..."):
                        system_prompt = "You are an expert senior software engineer. Based on the refined requirement, break it down into a list of specific, actionable development tasks. For each task, provide a title and a one-sentence description. Format the output as 'Task Title :: Task Description', with each task on a new line."
                        human_template = "Refined Requirement:\n{refined_desc}\n\nPlease generate the task list."
                        context = {"refined_desc": req_details['refined_description']}
                        ai_response = get_ai_response(system_prompt, human_template, context)
                        if ai_response:
                            st.session_state[f"tasks_{selected_req_id}"] = st.write_stream(ai_response)
            
            if f"tasks_{selected_req_id}" in st.session_state:
                st.code(st.session_state[f"tasks_{selected_req_id}"], language="text")
                st.warning("Review the tasks above. You can add them manually in the 'Task Management' tab.")

# --- TAB 2: Sprint Management ---
with tab2:
    st.subheader("Organize Work into Sprints")
    members_map, requirements_map, _ = get_project_maps(PROJECT_ID)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("##### Create a New Sprint")
        with st.form("add_sprint_form", clear_on_submit=True):
            sprint_name = st.text_input("Sprint Name (e.g., Week 1, Alpha Release)")
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            if st.form_submit_button("Create Sprint"):
                if sprint_name and start_date and end_date:
                    execute_query("INSERT INTO sprints (project_id, name, start_date, end_date) VALUES (?, ?, ?, ?)",
                                  (PROJECT_ID, sprint_name, str(start_date), str(end_date)))
                    st.success(f"Sprint '{sprint_name}' created.")
                else:
                    st.error("All fields are required.")

    with col2:
        st.markdown("##### Assign Requirements to a Sprint")
        sprints = execute_query("SELECT id, name FROM sprints WHERE project_id = ?", (PROJECT_ID,), "all")
        if sprints and requirements_map:
            sprint_map = {s['id']: s['name'] for s in sprints}
            selected_sprint_id = st.selectbox("Select Sprint", options=list(sprint_map.keys()), format_func=lambda x: sprint_map[x])
            
            assigned_req_ids = [r['requirement_id'] for r in execute_query("SELECT requirement_id FROM sprint_requirements WHERE sprint_id=?", (selected_sprint_id,), "all")]
            unassigned_reqs = {rid: rname for rid, rname in requirements_map.items() if rid not in assigned_req_ids}

            if not unassigned_reqs:
                st.warning("All requirements are assigned to this sprint.")
            else:
                req_to_add = st.selectbox("Select Requirement to Add", options=list(unassigned_reqs.keys()), format_func=lambda x: unassigned_reqs[x])
                if st.button("Add to Sprint"):
                    execute_query("INSERT INTO sprint_requirements (sprint_id, requirement_id) VALUES (?, ?)", (selected_sprint_id, req_to_add))
                    st.success("Requirement added to sprint.")
                    st.rerun()
        else:
            st.warning("Create a sprint and at least one requirement first.")

# --- TAB 3: Task Management ---
with tab3:
    st.subheader("Create and Assign Tasks")
    members_map, requirements_map, _ = get_project_maps(PROJECT_ID)
    
    if not members_map or not requirements_map:
        st.warning("Please add at least one requirement and assign one member to the project.")
    else:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("##### Add a New Task")
            with st.form("add_task_form", clear_on_submit=True):
                task_title = st.text_input("Task Title")
                task_desc = st.text_area("Task Description")
                task_req = st.selectbox("Link to Requirement", options=list(requirements_map.keys()), format_func=lambda x: requirements_map[x])
                task_assignee = st.selectbox("Assign To", options=list(members_map.keys()), format_func=lambda x: members_map[x])
                task_due_date = st.date_input("Due Date")
                if st.form_submit_button("Create Task"):
                    if all([task_title, task_desc, task_req, task_assignee, task_due_date]):
                        execute_query("""
                            INSERT INTO tasks (project_id, requirement_id, title, description, assigned_to_id, due_date, status)
                            VALUES (?, ?, ?, ?, ?, ?, 'To Do')
                        """, (PROJECT_ID, task_req, task_title, task_desc, task_assignee, str(task_due_date)))
                        st.success("Task created and assigned.")
                    else:
                        st.error("All fields are required.")
        with col2:
            st.markdown("##### All Project Tasks")
            all_tasks = execute_query("""
                SELECT t.title, t.status, t.due_date, tm.name as assigned_to, r.title as requirement
                FROM tasks t
                JOIN team_members tm ON t.assigned_to_id = tm.id
                JOIN requirements r ON t.requirement_id = r.id
                WHERE t.project_id = ?
            """, (PROJECT_ID,), "all")
            if all_tasks:
                st.dataframe(all_tasks, use_container_width=True)
            else:
                st.info("No tasks created yet.")
