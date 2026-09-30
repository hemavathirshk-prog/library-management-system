-- =======================================================
-- Library Management System Database Schema & Initial Data
-- Database Name: library_db
-- =======================================================

CREATE DATABASE IF NOT EXISTS library_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE library_db;

-- Drop tables in reverse order of foreign key dependency if re-running
DROP TABLE IF EXISTS loans;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS members;
DROP TABLE IF EXISTS admins;
DROP TABLE IF EXISTS settings;

-- 1. System Settings Table
CREATE TABLE settings (
    setting_id INT AUTO_INCREMENT PRIMARY KEY,
    fine_per_day DECIMAL(10, 2) NOT NULL DEFAULT 5.00,
    loan_days INT NOT NULL DEFAULT 14,
    max_renewals INT NOT NULL DEFAULT 2
) ENGINE=InnoDB;

-- 2. Administrators Table
CREATE TABLE admins (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

-- 3. Members Table
CREATE TABLE members (
    member_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 4. Books Table
CREATE TABLE books (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    author VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    isbn VARCHAR(30) NOT NULL UNIQUE,
    publisher VARCHAR(150) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    available_quantity INT NOT NULL DEFAULT 1,
    status ENUM('Available', 'Unavailable') NOT NULL DEFAULT 'Available',
    CONSTRAINT chk_quantities CHECK (available_quantity >= 0 AND available_quantity <= quantity)
) ENGINE=InnoDB;

-- 5. Loans Table
CREATE TABLE loans (
    loan_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    book_id INT NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE NULL,
    renewal_count INT NOT NULL DEFAULT 0,
    fine_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    fine_paid BOOLEAN NOT NULL DEFAULT FALSE,
    status ENUM('Issued', 'Returned') NOT NULL DEFAULT 'Issued',
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE RESTRICT,
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- =======================================================
-- Insert Default System Settings (Never hard-code in logic)
-- Standard rate: ₹5.00 per day, 14 days loan period, 2 max renewals
-- =======================================================
INSERT INTO settings (setting_id, fine_per_day, loan_days, max_renewals)
VALUES (1, 5.00, 14, 2);

-- =======================================================
-- Insert Demo Administrator
-- Username: admin / Password: admin123
-- =======================================================
INSERT INTO admins (admin_id, name, username, password_hash)
VALUES (
    1,
    'College Librarian',
    'admin',
    'scrypt:32768:8:1$8fbYtFZFh0tykEj9$41ad8cc8a216d140241cc7ddcba73db9cc431c4a36211346ccaf5218aa4f3cdc14b93f5aee8f22a08cb2f4ff6251bcd12a1d648bf329268121fc4b06548a69d7'
);

-- =======================================================
-- Insert Demo Member
-- Username: member1 / Password: member123
-- =======================================================
INSERT INTO members (member_id, name, email, phone, username, password_hash, registration_date)
VALUES (
    1,
    'John Doe',
    'john.doe@college.edu',
    '9876543210',
    'member1',
    'scrypt:32768:8:1$FHC5PkawgkOeg4at$5439471fb2e474d94fba78d9874de3fb3624de783d48f789f46586dd6df2816de3356fb83c3fff182ee8f497eb4b4096e7616b9c5c4d0d7abda2f1a8bf694807',
    DATE_SUB(NOW(), INTERVAL 30 DAY)
);

-- =======================================================
-- Insert Books (10 books with varied availability)
-- =======================================================
INSERT INTO books (book_id, title, author, category, isbn, publisher, quantity, available_quantity, status)
VALUES
(1, 'Introduction to Algorithms', 'Thomas H. Cormen', 'Computer Science', '978-0262033848', 'MIT Press', 5, 4, 'Available'),
(2, 'Clean Code: A Handbook of Agile Software Craftsmanship', 'Robert C. Martin', 'Software Engineering', '978-0132350884', 'Prentice Hall', 3, 2, 'Available'),
(3, 'Operating System Concepts', 'Abraham Silberschatz', 'Computer Science', '978-1118063330', 'Wiley', 4, 4, 'Available'),
(4, 'Database System Concepts', 'Abraham Silberschatz', 'Database', '978-0073523323', 'McGraw-Hill', 2, 1, 'Available'),
(5, 'Artificial Intelligence: A Modern Approach', 'Stuart Russell & Peter Norvig', 'Artificial Intelligence', '978-0136042594', 'Pearson', 3, 3, 'Available'),
(6, 'Computer Networks', 'Andrew S. Tanenbaum', 'Networking', '978-0132126953', 'Pearson', 2, 2, 'Available'),
(7, 'Design Patterns: Elements of Reusable Object-Oriented Software', 'Erich Gamma et al.', 'Software Engineering', '978-0201633610', 'Addison-Wesley', 1, 0, 'Unavailable'),
(8, 'Structure and Interpretation of Computer Programs', 'Harold Abelson & Gerald Jay Sussman', 'Computer Science', '978-0262510875', 'MIT Press', 1, 0, 'Unavailable'),
(9, 'Digital Logic and Computer Design', 'M. Morris Mano', 'Electronics', '978-9332542525', 'Pearson', 4, 4, 'Available'),
(10, 'Modern Operating Systems', 'Andrew S. Tanenbaum', 'Computer Science', '978-0133591620', 'Pearson', 3, 3, 'Available');

-- =======================================================
-- Insert Demo Loans (including an active overdue loan and returned loan)
-- =======================================================
INSERT INTO loans (loan_id, member_id, book_id, issue_date, due_date, return_date, renewal_count, fine_amount, fine_paid, status)
VALUES
-- Loan 1: Active, regular issue (5 days ago, due in 9 days)
(1, 1, 1, DATE_SUB(CURDATE(), INTERVAL 5 DAY), DATE_ADD(CURDATE(), INTERVAL 9 DAY), NULL, 0, 0.00, FALSE, 'Issued'),

-- Loan 2: Active, OVERDUE loan! (issued 22 days ago, was due 8 days ago; overdue by 8 days -> fine 8 * ₹5 = ₹40.00)
(2, 1, 7, DATE_SUB(CURDATE(), INTERVAL 22 DAY), DATE_SUB(CURDATE(), INTERVAL 8 DAY), NULL, 0, 40.00, FALSE, 'Issued'),

-- Loan 3: Active, regular issue (issued 4 days ago, due in 10 days)
(3, 1, 2, DATE_SUB(CURDATE(), INTERVAL 4 DAY), DATE_ADD(CURDATE(), INTERVAL 10 DAY), NULL, 0, 0.00, FALSE, 'Issued'),

-- Loan 4: Active, another book (issued 20 days ago, due 6 days ago -> overdue by 6 days -> fine 6 * ₹5 = ₹30.00)
(4, 1, 8, DATE_SUB(CURDATE(), INTERVAL 20 DAY), DATE_SUB(CURDATE(), INTERVAL 6 DAY), NULL, 0, 30.00, FALSE, 'Issued');
