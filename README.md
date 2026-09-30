# College Library Management System

A complete, beginner-friendly web application for managing a college library. Built with a lightweight Python Flask backend and a clean vanilla HTML/CSS/JavaScript frontend connected to a MySQL relational database.

---

## 1. Introduction
The **College Library Management System** is designed for college libraries to automate book cataloging, member borrowings, loan renewals, book returns, and overdue penalty fee tracking. It features dedicated portals for both **Student Members** and **Librarians / Administrators**, with business rules strictly enforced on the server.

---

## 2. Key Features

### Member Portal:
- **Registration & Authentication:** Sign up with unique username and email; secure password hashing with `werkzeug.security`.
- **Dashboard:** Instant overview of active loans, overdue books, and fine totals.
- **Catalog Search:** Real-time search by Title, Author, Category, or ISBN with availability filters.
- **Book Details & One-Click Borrowing:** View complete book metadata and borrow available copies.
- **My Borrowed Books:** Track issue dates, return deadlines, and overdue countdowns.
- **Loan Renewals:** Extend borrowing periods with a single click (enforcing max renewal limits).
- **Book Returns:** Immediate return processing with overdue days and fine breakdown modal.
- **Borrowing History:** Permanent record of all completed loans.
- **Fine Details:** Detailed itemized list of all incurred and settled library fines.

### Administrator / Librarian Portal:
- **Dashboard Overview:** 4 primary metrics (Total Books, Registered Members, Issued Books, Overdue Books) plus unpaid fines summary.
- **Book Inventory Management:** Add new books, edit existing copies, and safely delete books (blocks deletion of books with active loans).
- **Member Directory:** Search members, inspect active loan records, add new members, and manage accounts.
- **Issue Books:** Assign books to registered members with automatic due date computation from database settings.
- **Process Returns:** Check in returned books, restore available inventory, calculate overdue days and fines.
- **Fines Collection:** View all pending and collected library fines; mark fines as paid.
- **Transaction Audit Log:** Complete historical audit trail of all library transactions.

---

## 3. Technologies Used
- **Frontend:** Plain HTML5, Vanilla CSS3 (navy/blue accent `#1e3a8a`), Plain JavaScript (ES6+ fetch API). No frameworks, no CDN dependencies.
- **Backend:** Python 3 with Flask, Werkzeug security for password hashing, and Flask server-side sessions.
- **Database:** MySQL 8.0 running at `localhost:3306` with `mysql-connector-python`.
- **Configuration:** `python-dotenv` with `.env` file support.

---

## 4. Project Structure
```text
LibraryManagementSystem/
│
├── backend/
│   ├── app.py                 # Main Flask application and page routing
│   ├── config.py              # Environment and configuration loader
│   ├── database.py            # MySQL database connection & parameterized queries
│   └── routes/
│       ├── auth.py            # Authentication, registration, login/logout, sessions
│       ├── books.py           # Book catalog search and CRUD operations
│       ├── members.py         # Member directory and profile management
│       ├── loans.py           # Issue, return, renew, and loan tracking
│       └── fines.py           # Fine calculation and payment tracking
│
├── frontend/
│   ├── index.html             # Homepage with public catalog search & credentials
│   ├── login.html             # Role-based login (Member / Admin)
│   ├── register.html          # Member registration page
│   ├── css/
│   │   └── style.css          # Clean navy/blue theme stylesheet
│   ├── js/
│   │   └── api.js             # Reusable API fetch wrapper & auth guard
│   ├── member/
│   │   ├── dashboard.html     # Member dashboard
│   │   ├── books.html         # Book catalog search & borrow
│   │   ├── loans.html         # Active loans, return & renewal
│   │   ├── history.html       # Returned books history
│   │   └── fines.html         # Fine details & payment status
│   └── admin/
│       ├── dashboard.html     # Admin dashboard with 4 key metrics
│       ├── books.html         # Book inventory management (Add/Edit/Delete)
│       ├── members.html       # Member directory management
│       ├── issue.html         # Issue book to member
│       ├── returns.html       # Process returns & compute fines
│       ├── fines.html         # Manage & collect library fines
│       └── transactions.html  # Full transaction audit log
│
├── database/
│   ├── library_management.sql # Complete SQL schema and demo dataset
│   └── init_db.py             # Automatic database initialization script
│
├── requirements.txt           # Python package dependencies
├── .env.example               # Template environment configuration
├── .env                       # Local active environment configuration
└── README.md                  # Comprehensive setup and user guide
```

---

## 5. MySQL Database Setup

### Step 1: Verify MySQL is Running
Make sure your MySQL Server (such as MySQL 8.0, XAMPP, or MariaDB) is running on port `3306`.

### Step 2: Configure `.env` File
Create or update the `.env` file in the root project folder:
```ini
# ========================================================
# MySQL Database Configuration
# ========================================================
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_actual_mysql_password
DB_NAME=library_db

# ========================================================
# Flask Server Configuration
# ========================================================
SECRET_KEY=college-library-secret-key-2026
FLASK_PORT=5000
FLASK_DEBUG=True
```
> **Important:** Replace `your_actual_mysql_password` with your real MySQL root password.

### Step 3: Create the Database & Tables
You can set up the database using either of the following two methods:

#### Method A: Using the Automated Python Script (Recommended)
Run the initialization script from the project root:
```bash
python database/init_db.py
```
This reads your `.env` settings, connects to MySQL, creates `library_db`, creates all 5 tables (`settings`, `admins`, `members`, `books`, `loans`), and loads the demo data.

#### Method B: Using MySQL Command Line or MySQL Workbench
Open MySQL command prompt or MySQL Workbench and run:
```bash
mysql -u root -p < database/library_management.sql
```
*(Enter your MySQL password when prompted).*

---

## 6. Dependency Installation

Ensure you are in the project root directory and run:
```bash
pip install -r requirements.txt
```
Installed packages:
- `Flask`
- `mysql-connector-python`
- `python-dotenv`
- `Werkzeug`

---

## 7. Starting the Application

Start the Flask backend server:
```bash
python backend/app.py
```

Open your web browser and navigate to:
```text
http://localhost:5000
```

---

## 8. Demo Credentials

| Role | Username | Password | Full Name / Description |
| :--- | :--- | :--- | :--- |
| **Administrator / Librarian** | `admin` | `admin123` | College Librarian (Full Admin Access) |
| **Student Member** | `member1` | `member123` | John Doe (Sample Student Member) |

*(All passwords are automatically hashed with `werkzeug.security` before storage).*

---

## 9. Testing Steps & Evaluation Guide

### 1. Member Registration & Authentication:
1. Go to `http://localhost:5000/register`.
2. Register a new member (e.g. `jane` / `jane@college.edu` / `jane123`).
3. Log in at `http://localhost:5000/login` selecting the **Student / Member** role.
4. Verify you are redirected to `/member/dashboard`.

### 2. Search, View Details & Borrow Books:
1. Navigate to **Search & Borrow** (`/member/books`).
2. Search by title (e.g. `Algorithms`) or author.
3. Click **Details** on any title to inspect availability and publisher info.
4. Click **Borrow** on an available book.
5. Verify the book available count decreases and the loan appears under **My Borrowed Books**.

### 3. Renew & Return Books:
1. Navigate to **My Borrowed Books** (`/member/loans`).
2. Click **Renew** on an active loan. Notice the due date extends by 14 days and the renewal counter increments.
3. Click **Return** on an active loan. Notice the return summary modal shows:
   - Due Date
   - Actual Return Date
   - Overdue Days
   - Calculated Fine

### 4. Admin Portal & Protection:
1. Try accessing `http://localhost:5000/admin/dashboard` while logged in as a member. Notice you are blocked and redirected to login.
2. Log out and sign in with `admin` / `admin123` selecting **Administrator**.
3. Inspect the **4 Count Cards** on the Admin Dashboard: Total Books, Registered Members, Issued Books, Overdue Books.

### 5. Admin Book Management (Add, Edit, Delete):
1. Navigate to **Books** (`/admin/books`).
2. Click **+ Add New Book**, fill in details, and save.
3. Edit the title or quantity of an existing book.
4. Try deleting a book that has active loans (e.g. Book ID 1 or 7). Notice the system blocks it with: *"Cannot delete book: Book currently has active loans."*

### 6. Admin Issue & Return:
1. Navigate to **Issue Book** (`/admin/issue`).
2. Select member `member1` and select an available book.
3. Check the dynamic due date preview and click **Confirm & Issue Book**.
4. Navigate to **Returns** (`/admin/returns`) and process a return. Notice overdue fines are calculated in real time.

### 7. Manage Fines:
1. Navigate to **Fines** (`/admin/fines`).
2. Find the overdue loan fine for member `member1`.
3. Click **Mark Paid** to collect and clear the fine.

---

## 10. Troubleshooting & Common Issues

| Issue / Error | Cause | Solution |
| :--- | :--- | :--- |
| `Access denied for user 'root'@'localhost'` | Incorrect MySQL password in `.env` | Open `.env` and verify `DB_PASSWORD` matches your local MySQL root password. |
| `Can't connect to MySQL server on 'localhost'` | MySQL service is stopped | Start the `MySQL80` service from Windows Services (`services.msc`) or XAMPP Control Panel. |
| `Unknown database 'library_db'` | Database has not been created yet | Run `python database/init_db.py` to create the schema and initial data. |
| `Port 5000 is already in use` | Another application is running on port 5000 | Change `FLASK_PORT=5001` in `.env` and restart `python backend/app.py`. |
| `Cannot delete book: Book currently has active loans` | Business rule protection | A book cannot be deleted while a student has a copy checked out. Return all copies first. |
| `Maximum renewal limit reached` | Exceeded `max_renewals` setting | Business rule limits renewals (default: 2 times). The book must be returned. |
