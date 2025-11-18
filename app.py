from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
import mysql.connector
import os
from datetime import datetime
from db_config import get_db_connection

# Flask setup
app = Flask(__name__)
app.secret_key = "supersecretkey"   # change in production

# File upload config
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# -------------------------------------------------
# 🧱 Helper: Get user by role and email
# -------------------------------------------------
def get_user(role, email):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    if role == "student":
        cur.execute("SELECT * FROM Student WHERE email=%s", (email,))
    else:
        cur.execute("SELECT * FROM Faculty WHERE email=%s", (email,))
    user = cur.fetchone()
    conn.close()
    return user


# -------------------------------------------------
# 🏠 Home / Login Page
# -------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# -------------------------------------------------
# 🔑 Login (plaintext check for testing)
# -------------------------------------------------
@app.route("/login", methods=["POST"])
def login():
    role = request.form["role"]
    email = request.form["email"]
    password = request.form["password"]

    user = get_user(role, email)
    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("index"))

    # ✅ Plain-text password comparison for testing
    if user["password"] == password:
        session["user_id"] = user["student_id"] if role == "student" else user["faculty_id"]
        session["role"] = role
        session["name"] = user["name"]
        flash(f"Welcome, {user['name']}!", "success")

        return redirect(url_for("student_dashboard" if role == "student" else "faculty_dashboard"))
    else:
        flash("Incorrect email or password!", "danger")
        return redirect(url_for("index"))


# -------------------------------------------------
# 🚪 Logout
# -------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))


# -------------------------------------------------
# 📋 Faculty Dashboard
# -------------------------------------------------
@app.route("/faculty_dashboard")
def faculty_dashboard():
    if session.get("role") != "faculty":
        return redirect(url_for("index"))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Faculty's own projects (include max_marks)
    cur.execute("""
        SELECT p.project_id, p.title, p.deadline, p.max_marks, COUNT(s.submission_id) AS submissions
        FROM Project p
        LEFT JOIN submission s ON p.project_id = s.project_id
        WHERE p.faculty_id = %s
        GROUP BY p.project_id
    """, (session["user_id"],))
    projects = cur.fetchall()

    # Submissions for this faculty’s projects (include max_marks)
    cur.execute("""
        SELECT s.submission_id, st.name AS student_name, p.title, p.max_marks, 
               s.status, s.submission_date, s.file_link, s.grade, s.faculty_comments
        FROM submission s
        JOIN Student st ON s.student_id = st.student_id
        JOIN Project p ON s.project_id = p.project_id
        WHERE p.faculty_id = %s
        ORDER BY s.submission_date DESC
    """, (session["user_id"],))
    submissions = cur.fetchall()

    conn.close()
    return render_template("faculty_dashboard.html", projects=projects, submissions=submissions)


# -------------------------------------------------
# 🗑️ Delete Project (Now relies on the MySQL TRIGGER for submission deletion)
# -------------------------------------------------
@app.route("/delete_project/<int:project_id>", methods=["POST"])
def delete_project(project_id):
    if session.get("role") != "faculty":
        flash("Unauthorized!", "danger")
        return redirect(url_for("index"))

    conn = get_db_connection()
    cur = conn.cursor()

    # The MySQL TRIGGER 'before_project_delete' handles the deletion of submissions.
    # We only need to delete the project itself.
    cur.execute("DELETE FROM Project WHERE project_id = %s AND faculty_id = %s",
                (project_id, session["user_id"]))
    conn.commit()
    conn.close()

    flash("🗑️ Project deleted successfully!", "info")
    return redirect(url_for("faculty_dashboard"))


# -------------------------------------------------
# ➕ Create Project
# -------------------------------------------------
@app.route("/create_project", methods=["POST"])
def create_project():
    if session.get("role") != "faculty":
        return redirect(url_for("index"))

    title = request.form["title"]
    description = request.form["description"]
    deadline = request.form["deadline"]
    max_marks = request.form.get("max_marks", 100)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Project (title, description, max_marks, deadline, faculty_id)
        VALUES (%s, %s, %s, %s, %s)
    """, (title, description, max_marks, deadline, session["user_id"]))
    conn.commit()
    conn.close()

    flash("✅ Project created successfully!", "success")
    return redirect(url_for("faculty_dashboard"))


# -------------------------------------------------
# 👨‍🎓 Student Dashboard (Includes Nested Query/Subquery)
# -------------------------------------------------
@app.route("/student_dashboard")
def student_dashboard():
    if session.get("role") != "student":
        return redirect(url_for("index"))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Available projects (Includes a Nested Query to get the faculty name)
    # The submission list below acts as a read for student submissions.
    cur.execute("""
        SELECT 
            p.project_id, 
            p.title, 
            p.description, 
            p.deadline, 
            f.name AS faculty_name,
            # NESTED QUERY / SUBQUERY: Check the student's grade if they have submitted
            (SELECT grade FROM submission s 
             WHERE s.project_id = p.project_id AND s.student_id = %s 
             ORDER BY s.submission_date DESC LIMIT 1) AS student_grade
        FROM Project p
        JOIN Faculty f ON p.faculty_id = f.faculty_id
        ORDER BY p.deadline ASC
    """, (session["user_id"],))
    projects = cur.fetchall()

    # Student submissions
    cur.execute("""
        SELECT s.submission_id, p.title, s.submission_date, s.status, s.file_link,s.grade, s.faculty_comments
        FROM submission s
        JOIN Project p ON s.project_id = p.project_id
        WHERE s.student_id = %s
        ORDER BY s.submission_date DESC
    """, (session["user_id"],))
    submissions = cur.fetchall()

    conn.close()
    return render_template("student_dashboard.html", projects=projects, submissions=submissions)


# -------------------------------------------------
# 📤 Submit Project
# -------------------------------------------------
@app.route("/submit_project", methods=["POST"])
def submit_project():
    if session.get("role") != "student":
        flash("Unauthorized", "danger")
        return redirect(url_for("index"))

    student_id = session["user_id"]
    project_id = request.form["project_id"]
    file = request.files["file"]

    if file:
        filename = f"{student_id}_{project_id}_{file.filename}"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Check if submission already exists (for re-submission)
        cur.execute("""
            SELECT submission_id FROM submission 
            WHERE student_id = %s AND project_id = %s
        """, (student_id, project_id))
        existing_submission = cur.fetchone()

        if existing_submission:
            # Update existing submission (Re-submission)
            cur.execute("""
                UPDATE submission
                SET submission_date = %s, file_link = %s, status = 'Submitted', grade = NULL, faculty_comments = NULL
                WHERE student_id = %s AND project_id = %s
            """, (datetime.now().date(), filename, student_id, project_id))
            flash_message = "🔄 Project re-submitted successfully! Previous grade cleared."
        else:
            # Insert new submission
            cur.execute("""
                INSERT INTO submission (student_id, project_id, submission_date, file_link, status)
                VALUES (%s, %s, %s, %s, 'Submitted')
            """, (student_id, project_id, datetime.now().date(), filename))
            flash_message = "✅ Project submitted successfully!"
            
        conn.commit()
        conn.close()

        flash(flash_message, "success")
        return redirect(url_for("student_dashboard"))
    else:
        flash("No file uploaded!", "danger")
        return redirect(url_for("student_dashboard"))


# -------------------------------------------------
# 🧾 Faculty Grading Route
# -------------------------------------------------
@app.route("/grade_submission/<int:submission_id>", methods=["POST"])
def grade_submission(submission_id):
    if session.get("role") != "faculty":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("index"))

    grade = request.form["grade"]
    comments = request.form["faculty_comments"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE submission
        SET grade=%s, faculty_comments=%s, status='Graded'
        WHERE submission_id=%s
    """, (grade, comments, submission_id))
    conn.commit()
    conn.close()

    flash("✅ submission graded successfully!", "success")
    return redirect(url_for("faculty_dashboard"))

# -------------------------------------------------
# 🗂️ Serve Uploaded Files
# -------------------------------------------------
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# -------------------------------------------------
# 🔁 AJAX Endpoint: Live Status (Faculty)
# -------------------------------------------------
@app.route("/live_status")
def live_status():
    if session.get("role") != "faculty":
        return jsonify([])

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT s.submission_id, st.name AS student, p.title AS project,
               s.status, s.submission_date
        FROM submission s
        JOIN Student st ON s.student_id = st.student_id
        JOIN Project p ON s.project_id = p.project_id
        JOIN Faculty f ON p.faculty_id = f.faculty_id
        WHERE f.faculty_id = %s
        ORDER BY s.submission_date DESC
    """, (session["user_id"],))
    data = cur.fetchall()
    conn.close()
    return jsonify(data)

# -------------------------------------------------
# 🧾 Register (Student or Faculty)
# -------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        role = request.form["role"]
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        department_id = request.form["department_id"]

        conn = get_db_connection()
        cur = conn.cursor()

        if role == "student":
            batch = request.form["batch"]
            cur.execute("""
                INSERT INTO Student (name, email, password, batch, department_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, email, password, batch, department_id))
        else:
            phone_no = request.form.get("phone_no", None)
            cur.execute("""
                INSERT INTO Faculty (name, email, password, phone_no, department_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, email, password, phone_no, department_id))

        conn.commit()
        conn.close()

        flash(f"✅ {role.capitalize()} registered successfully! Please log in.", "success")
        return redirect(url_for("index"))

    return render_template("register.html")

# -------------------------------------------------
# Run Flask
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)