# db_config.py
# ----------------------------------------
# Database connection setup for Flask + MySQL
# ----------------------------------------

import mysql.connector

def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="lakshitasql",
        database="student_project_submission_tracker"  # <-- NEW DB NAME
    )
    print("Connected to:", conn.database)
    return conn