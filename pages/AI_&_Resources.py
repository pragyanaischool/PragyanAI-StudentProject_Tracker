import streamlit as st
from utils import execute_query
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

st.set_page_config(layout="wide", page_title="AI & Resources")

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
GROQ_API_KEY = st.session_state.get("groq_api_key")

st.header("🤖 AI Assistant & 📚 Shared Resources")
st.info("Your central hub for getting AI-powered help and accessing materials shared by your project manager.")

# --- Helper function to get project context ---
@st.cache_data(ttl=600)
def get_project_context(_project_id):
    project_details = execute_query("SELECT name, description FROM projects WHERE id = ?", (_project_id,), fetch="one")
    requirements = execute_query("SELECT title, description FROM requirements WHERE project_id = ?", (_project_id,), fetch="all")
    
    context = f"Project Name: {project_details['name']}\nProject Description: {project_details['description']}\n\nProject Requirements:\n"
    for req in requirements:
        context += f"- {req['title']}: {req['description']}\n"
    return context

# --- UI TABS ---
tab1, tab2 = st.tabs(["🤖 AI Assistant", "📚 Manager's Resources"])

with tab1:
    st.subheader("Get AI-Powered Guidance")
    
    if not GROQ_API_KEY:
        st.warning("Please enter your Groq API Key in the sidebar on the main page to enable the AI Assistant.")
        st.stop()

    # --- Task Selection for Context ---
    my_tasks_map = {t['id']: f"{t['title']} (Due: {t['due_date']})" for t in execute_query("SELECT id, title, due_date FROM tasks WHERE assigned_to_id = ? AND project_id = ? AND status != 'Done'", (MEMBER_ID, PROJECT_ID), "all")}

    if not my_tasks_map:
        st.info("You have no active tasks. The AI Assistant provides help on a per-task basis.")
    else:
        st.markdown("Select a task to get specific help from the AI Assistant.")
        selected_task_id = st.selectbox(
            "Select Your Task",
            options=list(my_tasks_map.keys()),
            format_func=lambda x: my_tasks_map.get(x),
            label_visibility="collapsed"
        )

        task_details = execute_query("SELECT title, description FROM tasks WHERE id = ?", (selected_task_id,), fetch="one")
        task_context = f"Current Task Title: {task_details['title']}\nCurrent Task Description: {task_details['description']}"

        st.divider()

        # --- AI Interaction ---
        st.markdown(f"**Getting help for:** `{task_details['title']}`")
        
        col1, col2, col3 = st.columns(3)
        # Pre-defined prompts
        if col1.button("🧠 Suggest an Approach", use_container_width=True):
            st.session_state.user_question = "Based on the task description, suggest a high-level approach or a couple of strategies to get started."
        if col2.button("📋 Break it Down (Steps)", use_container_width=True):
            st.session_state.user_question = "Break this task down into a detailed, step-by-step plan that I can follow."
        if col3.button("💻 Suggest Code Prompts", use_container_width=True):
            st.session_state.user_question = "Give me 2-3 specific, advanced prompts that I could use with a code generation AI (like ChatGPT or Claude) to get useful code snippets for this task. Do not write the code yourself, just the prompts."

        # Custom user input
        if prompt := st.chat_input("Ask a follow-up question about this task..."):
            st.session_state.user_question = prompt

        # --- LangChain & Groq Logic ---
        if st.session_state.get("user_question"):
            user_question = st.session_state.pop("user_question")
            
            with st.chat_message("user"):
                st.markdown(user_question)

            with st.chat_message("assistant"):
                try:
                    chat = ChatGroq(temperature=0.7, groq_api_key=GROQ_API_KEY, model_name="llama3-70b-8192")
                    
                    system_prompt = (
                        "You are an expert project mentor AI. Your goal is to help a student developer succeed with their assigned task. "
                        "You must be encouraging and helpful. Do not just give the final answer or write large blocks of code. Instead, guide them by breaking down the problem, "
                        "suggesting technologies, and explaining concepts. Ground your answers in the provided project and task context."
                    )
                    
                    prompt_template = ChatPromptTemplate.from_messages([
                        ("system", system_prompt),
                        ("human", "Here is the overall project context:\n{project_context}\n\nHere is my specific task context:\n{task_context}\n\nMy question is: {user_question}")
                    ])

                    chain = prompt_template | chat | StrOutputParser()
                    
                    full_context = {
                        "project_context": get_project_context(PROJECT_ID),
                        "task_context": task_context,
                        "user_question": user_question
                    }
                    
                    st.write_stream(chain.stream(full_context))

                except Exception as e:
                    st.error(f"An error occurred with the AI Assistant: {e}")


with tab2:
    st.subheader("Resources from Your Manager")
    st.info("Find general project resources and specific references your manager shared in response to your questions.")
    
    # --- General Project Resources ---
    st.markdown("#### General Project Resources")
    general_resources = execute_query("SELECT title, link, description FROM resources WHERE project_id = ?", (PROJECT_ID,), "all")
    if not general_resources:
        st.write("No general resources have been added for this project yet.")
    else:
        for res in general_resources:
            with st.container(border=True):
                st.markdown(f"**[{res['title']}]({res['link']})**")
                if res['description']:
                    st.caption(res['description'])

    st.divider()

    # --- Task-Specific References from Issue Responses ---
    st.markdown("#### Task-Specific Help & References")
    my_responses = execute_query("""
        SELECT 
            t.title as task_title, 
            ir.response_text, 
            ir.reference_links 
        FROM issue_responses ir
        JOIN task_issues ti ON ir.issue_id = ti.id
        JOIN tasks t ON ti.task_id = t.id
        WHERE ti.member_id = ? AND t.project_id = ? AND ir.reference_links IS NOT NULL AND ir.reference_links != ''
    """, (MEMBER_ID, PROJECT_ID), "all")

    if not my_responses:
        st.write("Your manager hasn't shared any specific reference links in response to your questions yet.")
    else:
        for resp in my_responses:
            with st.expander(f"References for Task: **{resp['task_title']}**"):
                st.info(f"**Manager's Comment:** {resp['response_text']}")
                st.markdown("**Reference Links:**")
                links = resp['reference_links'].strip().split('\n')
                for link in links:
                    st.markdown(f"- {link.strip()}")

