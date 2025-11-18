-- =================================================================
-- Database Setup: student_project_submission_tracker
-- =================================================================

CREATE DATABASE student_project_submission_tracker;
USE student_project_submission_tracker;

-- DEPARTMENT Table
CREATE TABLE department (
    department_id INT PRIMARY KEY AUTO_INCREMENT,
    department_name VARCHAR(100) NOT NULL
);

-- STUDENT Table
CREATE TABLE Student (
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    phone_no VARCHAR(15),
    batch VARCHAR(20),
    department_id INT,
    FOREIGN KEY (department_id) REFERENCES department(department_id)
);

-- FACULTY Table
CREATE TABLE Faculty (
    faculty_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    phone_no VARCHAR(15),
    department_id INT,
    FOREIGN KEY (department_id) REFERENCES department(department_id)
);

-- COURSE Table
CREATE TABLE course (
    course_id INT PRIMARY KEY AUTO_INCREMENT,
    course_name VARCHAR(100) NOT NULL,
    semester INT,
    faculty_id INT,
    FOREIGN KEY (faculty_id) REFERENCES Faculty(faculty_id)
);


-- PROJECT Table
CREATE TABLE Project (
    project_id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    max_marks INT DEFAULT 100,
    deadline DATE NOT NULL,
    faculty_id INT,
    course_id INT,
    FOREIGN KEY (faculty_id) REFERENCES Faculty(faculty_id),
    FOREIGN KEY (course_id) REFERENCES course(course_id)
);

-- SUBMISSION Table
CREATE TABLE submission (
    submission_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT,
    project_id INT,
    submission_date DATE,
    file_link VARCHAR(255),
    status VARCHAR(20) DEFAULT 'Submitted',
    grade INT,
    faculty_comments TEXT,
    FOREIGN KEY (student_id) REFERENCES Student(student_id),
    FOREIGN KEY (project_id) REFERENCES Project(project_id)
);

-- REVIEW Table
CREATE TABLE review (
    review_id INT PRIMARY KEY AUTO_INCREMENT,
    submission_id INT,
    marks_awarded INT,
    feedback TEXT,
    review_date DATE,
    FOREIGN KEY (submission_id) REFERENCES submission(submission_id)
);


-- Initial Data for Department Table
INSERT INTO department (department_id, department_name) VALUES
(1, 'Computer Science'),
(2, 'Information Science'),
(3, 'Electronics');


-- TRIGGER Implementation
DELIMITER //

CREATE TRIGGER before_project_delete
BEFORE DELETE ON Project
FOR EACH ROW
BEGIN
    DELETE FROM submission WHERE project_id = OLD.project_id;
END; //

DELIMITER ;