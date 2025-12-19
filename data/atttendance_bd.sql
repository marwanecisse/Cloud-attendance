CREATE DATABASE IF NOT EXISTS cloud_attendance
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE cloud_attendance;

CREATE TABLE IF NOT EXISTS classes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS students (
  id INT AUTO_INCREMENT PRIMARY KEY,
  matricule VARCHAR(50) NOT NULL UNIQUE,
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  class_id INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_students_class
    FOREIGN KEY (class_id) REFERENCES classes(id)
    ON DELETE SET NULL
    ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS faces (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  encoding_format ENUM('dlib128_f64') DEFAULT 'dlib128_f64',
  face_encoding LONGBLOB NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_faces_student
    FOREIGN KEY (student_id) REFERENCES students(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  INDEX idx_faces_student (student_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  attendance_date DATE NOT NULL,
  attendance_time TIME NOT NULL,
  source ENUM('FACE') DEFAULT 'FACE',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_attendance_student
    FOREIGN KEY (student_id) REFERENCES students(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  UNIQUE KEY uq_attendance_student_day (student_id, attendance_date),
  INDEX idx_attendance_date (attendance_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS recognition_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  request_id VARCHAR(64) NULL,
  faces_detected INT NOT NULL DEFAULT 0,
  matched_students INT NOT NULL DEFAULT 0,
  payload_meta JSON NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO classes(name) VALUES ('L4 Cybersecurity'), ('L4 Data');

ALTER TABLE faces 
  MODIFY encoding_format VARCHAR(50) DEFAULT 'facenet512_f32';

USE cloud_attendance;

SELECT * FROM students;
SELECT id, student_id, encoding_format, LENGTH(face_encoding) AS bytes FROM faces;
SELECT * FROM attendance;
SELECT * FROM recognition_logs ORDER BY id DESC LIMIT 5;

ALTER TABLE students
  ADD COLUMN profile_image_url VARCHAR(1024) NULL;

CREATE TABLE IF NOT EXISTS sessions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  class_id INT NOT NULL,
  group_image_url VARCHAR(1024) NOT NULL,
  session_date DATE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (class_id) REFERENCES classes(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

ALTER TABLE attendance
  ADD COLUMN session_id INT NULL,
  ADD CONSTRAINT fk_attendance_session
    FOREIGN KEY (session_id) REFERENCES sessions(id)
    ON DELETE SET NULL ON UPDATE CASCADE;


SELECT * FROM attendance ORDER BY id DESC LIMIT 10;
SELECT * FROM recognition_logs ORDER BY id DESC LIMIT 10;