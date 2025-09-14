Advanced Project Tracker Streamlit App
This is a comprehensive, multi-page Streamlit application designed to help manage student or small team projects. It provides role-based access for Admins and Team Members, robust tracking features, and an integrated AI Assistant to provide hints and guidance.

✨ Key Features
🔐 Role-Based Access: Separate, secure logins for Admins (Managers) and Team Members.

🗂️ Multi-Project Management: Admins can create multiple projects and assign different members to each.

🛠️ Sprint & Task Tracking: Admins can define sprints, requirements, and tasks, and assign them to members.

📊 Detailed Progress Reporting: Team members have a dedicated interface to update task status, submit detailed progress reports with code links, and flag issues.

💬 Integrated Communication: A built-in system for raising doubts, asking questions, and requesting 1:1 mentoring sessions on a per-task basis.

🤖 AI-Powered Assistant (Groq & LangChain): An interactive chatbot that provides project-context-aware hints, step-by-step guidance, and suggestions to help students overcome challenges.

📈 Manager Dashboard: A centralized view for project managers to monitor activity feeds, respond to student issues, and view project analytics.

📁 Project Structure
Here is an overview of the recommended file structure for this project on GitHub. This structure leverages Streamlit's multi-page app conventions.

.
├── .gitignore          # Tells Git which files to ignore (e.g., venv, __pycache__)
├── app.py              # Main application entry point. Handles login and general layout.
├── pages/              # Directory for all other Streamlit pages.
│   ├── 1_🚀_My_Tasks_&_Schedule.py
│   ├── 2_🤔_Doubts_&_Mentoring.py
│   ├── 3_📊_Submit_Progress_Update.py
│   ├── 4_🤖_AI_&_Resources.py
│   ├── 5_👑_Admin_Panel.py
│   ├── 6_📈_Project_Manager_Dashboard.py
│   └── 7_🛠️_Manage_Sprints_&_Requirements.py
├── project_tracker.sql # The SQL schema to initialize the database.
├── README.md           # This file, explaining the project.
├── requirements.txt    # Lists all the Python packages required to run the app.
└── utils.py            # Utility functions for database connections, queries, and password hashing.
