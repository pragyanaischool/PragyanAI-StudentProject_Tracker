-- Drop tables if they exist to ensure a clean slate
DROP TABLE IF EXISTS issue_responses;
DROP TABLE IF EXISTS progress_updates;
DROP TABLE IF EXISTS task_issues;
DROP TABLE IF EXISTS sprint_requirements;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS sprints;
DROP TABLE IF EXISTS requirements;
DROP TABLE IF EXISTS project_members;
DROP TABLE IF EXISTS resources;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS team_members;
DROP TABLE IF EXISTS project_managers;
DROP TABLE IF EXISTS super_admins;

-- Super Admins Table
CREATE TABLE super_admins (
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT UNIQUE NOT NULL,
password TEXT NOT NULL
);

-- Project Managers Table
CREATE TABLE project_managers (
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT UNIQUE NOT NULL,
password TEXT NOT NULL
);

-- Team Members Table: For students or team members
CREATE TABLE team_members (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT NOT NULL,
email TEXT UNIQUE NOT NULL,
password TEXT NOT NULL
);

-- Projects Table: To manage multiple projects
CREATE TABLE projects (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT NOT NULL,
description TEXT,
problem_statement TEXT,
manager_id INTEGER,
FOREIGN KEY (manager_id) REFERENCES project_managers(id)
);

-- Project Members Junction Table: To link members to projects
CREATE TABLE project_members (
project_id INTEGER,
member_id INTEGER,
PRIMARY KEY (project_id, member_id),
FOREIGN KEY (project_id) REFERENCES projects(id),
FOREIGN KEY (member_id) REFERENCES team_members(id)
);

-- Requirements Table
CREATE TABLE requirements (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
title TEXT NOT NULL,
description TEXT,
refined_description TEXT,
FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Sprints Table
CREATE TABLE sprints (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
name TEXT NOT NULL,
start_date TEXT,
end_date TEXT,
FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Sprint Requirements Junction Table
CREATE TABLE sprint_requirements (
sprint_id INTEGER,
requirement_id INTEGER,
PRIMARY KEY (sprint_id, requirement_id),
FOREIGN KEY (sprint_id) REFERENCES sprints(id),
FOREIGN KEY (requirement_id) REFERENCES requirements(id)
);

-- Tasks Table
CREATE TABLE tasks (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
requirement_id INTEGER,
title TEXT NOT NULL,
description TEXT,
assigned_to_id INTEGER,
status TEXT DEFAULT 'To Do',
due_date TEXT,
completion_date TEXT,
FOREIGN KEY (project_id) REFERENCES projects(id),
FOREIGN KEY (requirement_id) REFERENCES requirements(id),
FOREIGN KEY (assigned_to_id) REFERENCES team_members(id)
);

-- Task Issues Table: For doubts, questions, dependencies
CREATE TABLE task_issues (
id INTEGER PRIMARY KEY AUTOINCREMENT,
task_id INTEGER NOT NULL,
member_id INTEGER NOT NULL,
issue_type TEXT NOT NULL,
issue_text TEXT NOT NULL,
needs_meeting BOOLEAN DEFAULT 0,
is_resolved BOOLEAN DEFAULT 0,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (task_id) REFERENCES tasks(id),
FOREIGN KEY (member_id) REFERENCES team_members(id)
);

-- Issue Responses Table: For manager's replies
CREATE TABLE issue_responses (
id INTEGER PRIMARY KEY AUTOINCREMENT,
issue_id INTEGER NOT NULL,
responder_id INTEGER NOT NULL,
response_text TEXT NOT NULL,
response_type TEXT,
reference_links TEXT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (issue_id) REFERENCES task_issues(id)
);

-- Progress Updates Table
CREATE TABLE progress_updates (
id INTEGER PRIMARY KEY AUTOINCREMENT,
task_id INTEGER NOT NULL,
member_id INTEGER NOT NULL,
project_id INTEGER NOT NULL,
summary TEXT NOT NULL,
status TEXT NOT NULL,
code_link TEXT,
hours_spent REAL,
submission_date TEXT,
FOREIGN KEY (task_id) REFERENCES tasks(id),
FOREIGN KEY (member_id) REFERENCES team_members(id),
FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Resources Table: For manager to share general links
CREATE TABLE resources (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
title TEXT NOT NULL,
link TEXT NOT NULL,
description TEXT,
FOREIGN KEY (project_id) REFERENCES projects(id)
);
