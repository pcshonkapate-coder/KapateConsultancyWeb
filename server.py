import os
import sqlite3
import json
import random
import datetime
import smtplib
from io import StringIO
import csv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, send_from_directory, redirect, Response

app = Flask(__name__, static_folder='.', static_url_path='')

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

@app.route('/<path:path>', methods=['OPTIONS'])
@app.route('/', methods=['OPTIONS'])
def handle_options(path=None):
    return '', 200

# Base Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = '/tmp/config.json' if os.environ.get('VERCEL') else os.path.join(BASE_DIR, 'config.json')
DB_FILE = '/tmp/inquiries.db' if os.environ.get('VERCEL') else os.path.join(BASE_DIR, 'inquiries.db')

def load_config():
    default_config = {
        "SMTP_SERVER": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        "SMTP_PORT": int(os.environ.get("SMTP_PORT", 587)),
        "SMTP_EMAIL": os.environ.get("SMTP_EMAIL", "office.kapateconsultancy@gmail.com"),
        "SMTP_PASSWORD": os.environ.get("SMTP_PASSWORD", "twwwzjrujirsvxjz"),
        "ADMIN_PASSWORD": os.environ.get("ADMIN_PASSWORD", "Admin@KapateConsultancy8421174957"),
        "TWILIO_ACCOUNT_SID": os.environ.get("TWILIO_ACCOUNT_SID", ""),
        "TWILIO_AUTH_TOKEN": os.environ.get("TWILIO_AUTH_TOKEN", ""),
        "TWILIO_PHONE_NUMBER": os.environ.get("TWILIO_PHONE_NUMBER", "")
    }
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception:
            pass
        return default_config
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return default_config

# Token cache for session management
SESSION_TOKENS = {}

# Database Configuration & Dual-Backend Engine (SQLite & PostgreSQL / Cloud SQL)
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or load_config().get("DATABASE_URL", "")

class PGConnectionWrapper:
    def __init__(self, raw_conn):
        self.conn = raw_conn

    def cursor(self):
        return PGCursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

class PGCursorWrapper:
    def __init__(self, raw_cursor):
        self.cur = raw_cursor

    def execute(self, sql, params=None):
        # Auto-translate SQLite syntax to standard PostgreSQL
        clean_sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        clean_sql = clean_sql.replace("datetime('now', 'localtime')", "CURRENT_TIMESTAMP")
        clean_sql = clean_sql.replace("date('now', '+14 days')", "to_char(CURRENT_DATE + INTERVAL '14 days', 'YYYY-MM-DD')")
        clean_sql = clean_sql.replace("date('now')", "to_char(CURRENT_DATE, 'YYYY-MM-DD')")
        clean_sql = clean_sql.replace('?', '%s')

        if params is not None:
            self.cur.execute(clean_sql, params)
        else:
            self.cur.execute(clean_sql)
        return self

    def fetchone(self):
        row = self.cur.fetchone()
        if row is None:
            return None
        # Support both dictionary and numeric indexing
        if isinstance(row, dict):
            class DictWithIndex(dict):
                def __getitem__(self, item):
                    if isinstance(item, int):
                        return list(self.values())[item]
                    return super().__getitem__(item)
            return DictWithIndex(row)
        return row

    def fetchall(self):
        rows = self.cur.fetchall()
        if not rows:
            return []
        res = []
        for r in rows:
            if isinstance(r, dict):
                class DictWithIndex(dict):
                    def __getitem__(self, item):
                        if isinstance(item, int):
                            return list(self.values())[item]
                        return super().__getitem__(item)
                res.append(DictWithIndex(r))
            else:
                res.append(r)
        return res

    def close(self):
        self.cur.close()

def get_db():
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or load_config().get("DATABASE_URL", "")
    if db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            raw_conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
            return PGConnectionWrapper(raw_conn)
        except Exception as e:
            print(f"PostgreSQL connection failed ({e}), falling back to local SQLite.")
    
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn

def audit_log(user_name, action, entity, entity_id="", old_val="", new_val="", ip_addr="127.0.0.1", reason=""):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (user_name, action, entity, entity_id, old_value, new_value, ip_address, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        ''', (user_name, action, entity, str(entity_id), str(old_val), str(new_val), ip_addr, reason))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Audit log error: {e}")

def create_notification(user_id, title, message, link_tab="tab-dashboard", n_type="task", user_role=""):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notifications (user_id, user_role, title, message, link_tab, type, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, datetime('now', 'localtime'))
        ''', (user_id, user_role, title, message, link_tab, n_type))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Notification error: {e}")

# Database Initialization & Migration
def init_database():
    conn = get_db()
    cursor = conn.cursor()

    # Public inquiries
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_num TEXT UNIQUE,
            reference_number TEXT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            service TEXT NOT NULL,
            budget TEXT,
            timeline TEXT,
            message TEXT,
            status TEXT DEFAULT 'New',
            admin_notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Public reviews
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT,
            company TEXT,
            rating INTEGER DEFAULT 5,
            comment TEXT NOT NULL,
            status TEXT DEFAULT 'Approved',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Workspace Users (Extended for full employee profiles)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_code TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL, -- CEO, Manager, Employee, Intern
            department TEXT NOT NULL,
            designation TEXT,
            manager_name TEXT DEFAULT 'Shon Kapate',
            status TEXT DEFAULT 'Active', -- Active, Inactive, Suspended
            phone TEXT,
            avatar_url TEXT,
            joining_date TEXT DEFAULT '2026-01-12',
            employment_type TEXT DEFAULT 'Full-Time', -- Full-Time, Part-Time, Contract, Internship
            dob TEXT DEFAULT '1996-05-14',
            address TEXT DEFAULT 'Pune, Maharashtra, India',
            emergency_contact TEXT DEFAULT '+91 9822001100 (Parent)',
            basic_pay REAL DEFAULT 50000,
            performance_score REAL DEFAULT 4.7,
            last_active TEXT DEFAULT 'Just now',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Departments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            head_name TEXT NOT NULL,
            head_id INTEGER,
            description TEXT,
            budget REAL DEFAULT 1000000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Employee Confidential Notes (CEO / Admin Only)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employee_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            author_role TEXT NOT NULL,
            note_text TEXT NOT NULL,
            is_confidential INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Employee Official Documents
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employee_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id INTEGER NOT NULL,
            doc_type TEXT NOT NULL, -- Resume, Joining Letter, Offer Letter, ID Document, Certificate, Performance Review
            doc_name TEXT NOT NULL,
            file_size TEXT DEFAULT '450 KB',
            file_url TEXT DEFAULT '',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Roles & Permissions Matrix Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            permission_key TEXT UNIQUE NOT NULL,
            permission_label TEXT NOT NULL,
            category TEXT NOT NULL,
            ceo_perm TEXT DEFAULT 'Full',
            manager_perm TEXT DEFAULT 'Team',
            employee_perm TEXT DEFAULT 'Own',
            intern_perm TEXT DEFAULT 'Restricted'
        )
    ''')

    # Workspace Projects
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            client_id INTEGER,
            client_name TEXT,
            description TEXT,
            manager_id INTEGER,
            manager_name TEXT,
            team_members TEXT,
            start_date TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'Active',
            priority TEXT DEFAULT 'Medium',
            budget REAL DEFAULT 0,
            progress INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Project Milestones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Pending',
            due_date TEXT,
            order_index INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Workspace Tasks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            project_id TEXT,
            project_name TEXT,
            milestone_id INTEGER,
            assigned_by_id INTEGER,
            assigned_by_name TEXT,
            assigned_to_id INTEGER,
            assigned_to_name TEXT,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Assigned',
            start_date TEXT,
            deadline TEXT,
            estimated_hours REAL DEFAULT 0,
            actual_hours REAL DEFAULT 0,
            tags TEXT,
            submission_notes TEXT DEFAULT '',
            submission_url TEXT DEFAULT '',
            manager_review_notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Task Comments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            user_id INTEGER,
            user_name TEXT NOT NULL,
            user_role TEXT NOT NULL,
            comment TEXT NOT NULL,
            attachment_name TEXT,
            attachment_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Time tracking entries
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            user_id INTEGER,
            user_name TEXT NOT NULL,
            hours REAL NOT NULL,
            entry_date TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Internal Mail System
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS internal_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            sender_name TEXT NOT NULL,
            sender_username TEXT NOT NULL,
            receiver_id INTEGER,
            receiver_name TEXT NOT NULL,
            receiver_username TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            folder TEXT DEFAULT 'inbox',
            is_read INTEGER DEFAULT 0,
            is_starred INTEGER DEFAULT 0,
            attachment_name TEXT,
            attachment_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Chat Channels & Messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            channel_type TEXT DEFAULT 'general',
            members_json TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            sender_id INTEGER,
            sender_name TEXT NOT NULL,
            sender_role TEXT NOT NULL,
            message TEXT NOT NULL,
            attachment_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Notifications
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_role TEXT DEFAULT '',
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            link_tab TEXT DEFAULT 'tab-dashboard',
            type TEXT DEFAULT 'task',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Hierarchical Company Drive
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder TEXT NOT NULL,
            subfolder TEXT DEFAULT '',
            name TEXT NOT NULL,
            file_size TEXT DEFAULT '120 KB',
            file_type TEXT DEFAULT 'PDF',
            uploaded_by TEXT NOT NULL,
            uploader_role TEXT NOT NULL,
            access_roles TEXT DEFAULT 'All',
            download_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # CRM Clients
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT UNIQUE NOT NULL,
            company_name TEXT NOT NULL,
            contact_person TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            industry TEXT DEFAULT 'Technology',
            status TEXT DEFAULT 'Active',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Proposals
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT UNIQUE NOT NULL,
            client_id TEXT,
            client_name TEXT NOT NULL,
            project_name TEXT NOT NULL,
            services TEXT NOT NULL,
            description TEXT,
            pricing REAL DEFAULT 0,
            timeline TEXT,
            terms TEXT,
            payment_schedule TEXT,
            status TEXT DEFAULT 'Sent',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Invoices & Finance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            client_id TEXT,
            client_name TEXT NOT NULL,
            project_id TEXT,
            project_name TEXT,
            items_json TEXT NOT NULL,
            subtotal REAL DEFAULT 0,
            tax_rate REAL DEFAULT 18.0,
            tax_amount REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            total REAL DEFAULT 0,
            due_date TEXT,
            status TEXT DEFAULT 'Sent',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            recorded_by TEXT NOT NULL,
            receipt_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Attendance & Leave
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT NOT NULL,
            emp_name TEXT NOT NULL,
            date TEXT NOT NULL,
            clock_in TEXT,
            clock_out TEXT,
            total_hours REAL DEFAULT 0,
            status TEXT DEFAULT 'Present',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT NOT NULL,
            emp_name TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            reviewed_by TEXT DEFAULT '',
            review_notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Meetings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            organizer_id INTEGER,
            organizer_name TEXT NOT NULL,
            participants_json TEXT DEFAULT '[]',
            meeting_date TEXT NOT NULL,
            meeting_time TEXT NOT NULL,
            location_link TEXT DEFAULT 'Google Meet / Zoom',
            agenda TEXT,
            notes TEXT,
            action_items_json TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Performance Reviews
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT NOT NULL,
            emp_name TEXT NOT NULL,
            reviewer_id INTEGER,
            reviewer_name TEXT NOT NULL,
            review_period TEXT NOT NULL,
            tasks_completed INTEGER DEFAULT 0,
            on_time_rate REAL DEFAULT 95.0,
            rating_score REAL DEFAULT 4.8,
            feedback TEXT NOT NULL,
            goals TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Internships
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS internship_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id TEXT UNIQUE NOT NULL,
            intern_name TEXT NOT NULL,
            mentor_id INTEGER,
            mentor_name TEXT NOT NULL,
            department TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            progress_percent INTEGER DEFAULT 80,
            modules_json TEXT DEFAULT '[]',
            feedback TEXT,
            certificate_status TEXT DEFAULT 'In Progress',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Announcements
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            target_audience TEXT DEFAULT 'All',
            priority TEXT DEFAULT 'Normal',
            author_name TEXT NOT NULL,
            author_role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Audit Logs (With Reason Column for CEO Overrides)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            action TEXT NOT NULL,
            entity TEXT NOT NULL,
            entity_id TEXT DEFAULT '',
            old_value TEXT DEFAULT '',
            new_value TEXT DEFAULT '',
            ip_address TEXT DEFAULT '127.0.0.1',
            reason TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()

    # Seed Default Data if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        seed_workspace_data(cursor, conn)
    else:
        conn.close()

def seed_workspace_data(cursor, conn):
    print("Seeding initial Kapate Workspace CEO Control Center data...")

    # 1. Departments
    depts_data = [
        ("Software Development", "Rohit Verma", 2, "Core engineering, full-stack web applications, and mobile solutions.", 1500000),
        ("AI & Machine Learning", "Ananya Deshmukh", 3, "Predictive modeling, NLP pipelines, and computer vision architectures.", 1800000),
        ("UI/UX & Design", "Pooja Kulkarni", 5, "Product design systems, wireframing, user research, and branding.", 800000),
        ("Cloud Infrastructure & DevOps", "Aditya Shinde", 6, "AWS architectures, Kubernetes clusters, CI/CD, and cyber compliance.", 1200000),
        ("Executive & Management", "Shon Kapate", 1, "Overall strategy, financial operations, and client relationships.", 2500000)
    ]
    for d in depts_data:
        cursor.execute('''
            INSERT INTO departments (name, head_name, head_id, description, budget)
            VALUES (?, ?, ?, ?, ?)
        ''', d)

    # 2. Users (Extended)
    users_data = [
        ("EMP-001", "ceo", "ceo@internal.kapate", generate_password_hash("Kapate@Ceo2026"), "Shon Kapate", "CEO", "Executive & Management", "Founder & Chief Executive", "Board of Directors", "Active", "+91 8421174957", "2026-01-01", "Full-Time", "1995-04-10", "Pune, India", "+91 8421174957 (Direct)", 250000, 5.0),
        ("EMP-002", "manager01", "manager01@internal.kapate", generate_password_hash("Manager@2026"), "Rohit Verma", "Manager", "Software Development", "Lead Tech Architect", "Shon Kapate", "Active", "+91 9823011223", "2026-01-15", "Full-Time", "1994-08-22", "Kothrud, Pune", "+91 9823011224 (Spouse)", 140000, 4.9),
        ("EMP-003", "manager02", "manager02@internal.kapate", generate_password_hash("Manager@2026"), "Ananya Deshmukh", "Manager", "AI & Machine Learning", "AI Solutions Director", "Shon Kapate", "Active", "+91 9765432100", "2026-02-01", "Full-Time", "1995-11-18", "Aundh, Pune", "+91 9765432101 (Brother)", 145000, 4.8),
        ("EMP-004", "employee01", "employee01@internal.kapate", generate_password_hash("Emp@2026"), "Siddharth Patil", "Employee", "Software Development", "Senior Full-Stack Engineer", "Rohit Verma", "Active", "+91 9422019988", "2026-02-15", "Full-Time", "1997-03-12", "Baner, Pune", "+91 9422019989 (Mother)", 95000, 4.7),
        ("EMP-005", "employee02", "employee02@internal.kapate", generate_password_hash("Emp@2026"), "Pooja Kulkarni", "Employee", "UI/UX & Design", "Senior UI/UX Designer", "Rohit Verma", "Active", "+91 9822456789", "2026-03-01", "Full-Time", "1998-07-29", "Viman Nagar, Pune", "+91 9822456780 (Father)", 88000, 4.8),
        ("EMP-006", "employee03", "employee03@internal.kapate", generate_password_hash("Emp@2026"), "Aditya Shinde", "Employee", "Cloud Infrastructure & DevOps", "Cloud & DevOps Specialist", "Rohit Verma", "Active", "+91 9977665544", "2026-03-10", "Full-Time", "1996-12-05", "Wakad, Pune", "+91 9977665545 (Sister)", 92000, 4.9),
        ("INT-007", "intern01", "intern01@internal.kapate", generate_password_hash("Intern@2026"), "Tanvi Joshi", "Intern", "Software Development", "Full-Stack Development Intern", "Rohit Verma", "Active", "+91 8888777666", "2026-06-01", "Internship", "2003-09-14", "Shivajinagar, Pune", "+91 8888777667 (Parent)", 25000, 4.6),
        ("INT-008", "intern02", "intern02@internal.kapate", generate_password_hash("Intern@2026"), "Gaurav More", "Intern", "AI & Machine Learning", "AI/ML Research Intern", "Ananya Deshmukh", "Active", "+91 7777666555", "2026-06-15", "Internship", "2003-01-20", "Hadapsar, Pune", "+91 7777666556 (Parent)", 25000, 4.8)
    ]
    for u in users_data:
        cursor.execute('''
            INSERT INTO users (emp_code, username, email, password_hash, name, role, department, designation, manager_name, status, phone, joining_date, employment_type, dob, address, emergency_contact, basic_pay, performance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', u)

    # 3. Roles & Permissions Matrix Seed
    perms_data = [
        ("view_employees", "View Employee Directory", "People", "Full Company", "Assigned Team", "Self Profile", "Self Profile"),
        ("manage_employees", "Create & Edit Staff Accounts", "People", "Full Company", "No Access", "No Access", "No Access"),
        ("create_projects", "Create & Manage Projects", "Projects", "Full Company", "Assigned Sprints", "No Access", "No Access"),
        ("assign_tasks", "Assign & Delegate Tasks", "Tasks", "Full Company", "Assigned Team", "No Access", "No Access"),
        ("approve_tasks", "Review & Approve Task Deliverables", "Tasks", "Full Company", "Assigned Team", "No Access", "No Access"),
        ("task_override", "CEO Task Master Override", "Tasks", "Full Company", "No Access", "No Access", "No Access"),
        ("view_finance", "Access Financial Ledgers & Revenue", "Finance", "Full Company", "Restricted", "No Access", "No Access"),
        ("issue_invoices", "Generate Invoices & Billing", "Finance", "Full Company", "Draft Only", "No Access", "No Access"),
        ("view_audit_logs", "Inspect Immutable Audit Trails", "Security", "Full Company", "Restricted", "No Access", "No Access")
    ]
    for p in perms_data:
        cursor.execute('''
            INSERT INTO roles_permissions (permission_key, permission_label, category, ceo_perm, manager_perm, employee_perm, intern_perm)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', p)

    # 4. Employee Confidential Notes (CEO Notes)
    notes_data = [
        (4, 1, "Shon Kapate", "CEO", "Siddharth has demonstrated exceptional technical ownership of the WebRTC modules. Recommended for Tech Lead evaluation in Q4."),
        (6, 1, "Shon Kapate", "CEO", "Aditya maintained 100% uptime on the AWS ECS cluster for Vertex Logistics. High reliability engineer."),
        (7, 1, "Shon Kapate", "CEO", "Tanvi is performing at a senior intern level. Consider pre-placement offer (PPO) upon graduation.")
    ]
    for n in notes_data:
        cursor.execute('''
            INSERT INTO employee_notes (emp_id, author_id, author_name, author_role, note_text)
            VALUES (?, ?, ?, ?, ?)
        ''', n)

    # 5. Employee Documents
    docs_data = [
        (4, "Resume", "Siddharth_Patil_Resume.pdf", "280 KB", "/docs/siddharth_resume.pdf"),
        (4, "Offer Letter", "Kapate_Offer_Letter_EMP004.pdf", "350 KB", "/docs/siddharth_offer.pdf"),
        (4, "Joining Letter", "Kapate_Joining_Verification_EMP004.pdf", "420 KB", "/docs/siddharth_joining.pdf"),
        (5, "Resume", "Pooja_Kulkarni_Portfolio_Resume.pdf", "1.2 MB", "/docs/pooja_resume.pdf"),
        (6, "Certificates", "AWS_Solutions_Architect_Certificate.pdf", "850 KB", "/docs/aditya_aws.pdf")
    ]
    for doc in docs_data:
        cursor.execute('''
            INSERT INTO employee_documents (emp_id, doc_type, doc_name, file_size, file_url)
            VALUES (?, ?, ?, ?, ?)
        ''', doc)

    # 6. Clients
    clients_data = [
        ("KC-CLI-101", "Nexus Health Systems", "Dr. Rajesh Kulkarni", "rajesh@nexushealth.in", "+91 9822001122", "Kalyani Nagar, Pune", "Healthcare Tech", "Active", "Enterprise Hospital Telemedicine platform contract."),
        ("KC-CLI-102", "FinEdge Wealth Advisory", "Meera Nair", "meera@finedge.com", "+91 9845012345", "Bandra Kurla Complex, Mumbai", "FinTech", "Active", "AI Investment portfolio analytics engine."),
        ("KC-CLI-103", "Vertex Logistics Pvt Ltd", "Vikram Rathore", "vikram@vertexlogistics.io", "+91 9920198765", "Viman Nagar, Pune", "Supply Chain", "Active", "Fleet Tracking & Automated Route Dispatch."),
        ("KC-CLI-104", "EduNova Learning Solutions", "Priya Sharma", "priya@edunova.ac.in", "+91 9422033445", "Shivajinagar, Pune", "EdTech", "Proposal Sent", "Interactive LMS with Exam Proctoring engine."),
        ("KC-CLI-105", "Apex Retail Global", "Amitabh Sen", "amitabh@apexretail.in", "+91 9123456780", "Hinjewadi Phase 2, Pune", "E-Commerce", "Negotiation", "Multi-vendor B2B marketplace.")
    ]
    for c in clients_data:
        cursor.execute('''
            INSERT INTO clients (client_id, company_name, contact_person, email, phone, address, industry, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', c)

    # 7. Projects
    projects_data = [
        ("KC-PRJ-201", "Nexus Clinical Telehealth Suite", 1, "Nexus Health Systems", "HIPAA-compliant video telemedicine, automated EHR syncing, and AI diagnostic notes generator.", 2, "Rohit Verma", json.dumps(["Siddharth Patil", "Pooja Kulkarni", "Tanvi Joshi"]), "2026-06-01", "2026-09-30", "Active", "High", 750000, 72),
        ("KC-PRJ-202", "FinEdge AI Portfolio Analytics", 2, "FinEdge Wealth Advisory", "Real-time algorithmic risk modeling, predictive equity indicators, and automated tax reporting.", 3, "Ananya Deshmukh", json.dumps(["Aditya Shinde", "Gaurav More", "Siddharth Patil"]), "2026-07-15", "2026-10-15", "Active", "High", 920000, 58),
        ("KC-PRJ-203", "Vertex Smart Fleet Dispatcher", 3, "Vertex Logistics Pvt Ltd", "IoT telematics dashboard, fuel optimization, and automated warehouse loading queues.", 2, "Rohit Verma", json.dumps(["Aditya Shinde", "Siddharth Patil"]), "2026-05-10", "2026-08-30", "Active", "Medium", 640000, 88),
        ("KC-PRJ-204", "EduNova Virtual Class Cloud", 4, "EduNova Learning Solutions", "Scalable live streaming classroom with AI plagiarism checks and interactive coding IDE.", 3, "Ananya Deshmukh", json.dumps(["Pooja Kulkarni", "Tanvi Joshi"]), "2026-08-01", "2026-11-30", "Planning", "Medium", 480000, 20)
    ]
    for p in projects_data:
        cursor.execute('''
            INSERT INTO projects (project_id, name, client_id, client_name, description, manager_id, manager_name, team_members, start_date, deadline, status, priority, budget, progress)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', p)

    # 8. Tasks
    tasks_data = [
        ("KC-TSK-501", "Finalize E-Signature Canvas for Prescriptions", "Implement HTML5 canvas signature capture with cryptographic verification stamp.", "KC-PRJ-201", "Nexus Clinical Telehealth Suite", 3, 2, "Rohit Verma", 4, "Siddharth Patil", "High", "In Progress", "2026-08-10", "2026-08-20", 16, 12, "Frontend, Security, Canvas", "", "", ""),
        ("KC-TSK-502", "Refactor Prescription Modal UI & Responsive Flow", "Ensure modal behaves smoothly on mobile iPad and tablet devices for doctors on duty.", "KC-PRJ-201", "Nexus Clinical Telehealth Suite", 3, 2, "Rohit Verma", 5, "Pooja Kulkarni", "Medium", "Submitted", "2026-08-12", "2026-08-19", 12, 10, "UI/UX, Responsive", "Completed full Figma alignment and submitted for manager approval.", "https://github.com/kapate/nexus-telehealth/pull/42", "Reviewing responsive breakpoints."),
        ("KC-TSK-503", "Unit Tests for FHIR Patient Profile Importer", "Build pytest suite ensuring 95%+ coverage for XML and JSON medical record ingestion.", "KC-PRJ-201", "Nexus Clinical Telehealth Suite", 4, 2, "Rohit Verma", 7, "Tanvi Joshi", "Medium", "In Progress", "2026-08-14", "2026-08-24", 20, 14, "Testing, Python, FHIR", "", "", ""),
        ("KC-TSK-504", "WebSocket Broker Feed Ingestion Pipeline", "Stream tick-by-tick market data into Redis buffer with sub-millisecond latency.", "KC-PRJ-202", "FinEdge AI Portfolio Analytics", 6, 3, "Ananya Deshmukh", 6, "Aditya Shinde", "High", "In Progress", "2026-08-08", "2026-08-22", 24, 18, "Backend, Redis, WebSocket", "", "", ""),
        ("KC-TSK-505", "Implement Mean-Variance Optimization Engine", "Develop Python NumPy portfolio frontier solver with custom user risk tolerance slider.", "KC-PRJ-202", "FinEdge AI Portfolio Analytics", 5, 3, "Ananya Deshmukh", 8, "Gaurav More", "Medium", "Submitted", "2026-08-06", "2026-08-18", 18, 16, "AI/ML, Math, Python", "Completed the optimization math engine and verified against benchmark portfolio data.", "https://github.com/kapate/finedge-ai/pull/18", ""),
        ("KC-TSK-506", "Deploy GPS Live Telematics Microservice on AWS ECS", "Configure Docker container, ALB health checks, and auto-scaling group for Vertex fleet.", "KC-PRJ-203", "Vertex Smart Fleet Dispatcher", 0, 2, "Rohit Verma", 6, "Aditya Shinde", "High", "Approved", "2026-08-01", "2026-08-15", 30, 28, "DevOps, AWS, Docker", "Service deployed live in production cluster. Verified 99.99% uptime.", "", "Outstanding deployment work Aditya! Approved for release."),
        ("KC-TSK-507", "Initial Design Tokens & Component Library for EduNova", "Establish color hierarchy, dark/light palette tokens, and icon system for LMS.", "KC-PRJ-204", "EduNova Virtual Class Cloud", 0, 3, "Ananya Deshmukh", 5, "Pooja Kulkarni", "Low", "Assigned", "2026-08-18", "2026-08-28", 14, 0, "Design System, Figma", "", "", "")
    ]
    for t in tasks_data:
        cursor.execute('''
            INSERT INTO tasks (task_id, title, description, project_id, project_name, milestone_id, assigned_by_id, assigned_by_name, assigned_to_id, assigned_to_name, priority, status, start_date, deadline, estimated_hours, actual_hours, tags, submission_notes, submission_url, manager_review_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', t)

    # 9. Internal Messages
    messages_data = [
        (2, "Rohit Verma", "manager01", 4, "Siddharth Patil", "employee01", "Sprint Review & Nexus Telehealth Release", "Hi Siddharth,\nPlease ensure the prescription signing workflow is tested with sample medical licenses by Friday afternoon. The client demo is scheduled for Monday at 10 AM.\n\nBest regards,\nRohit", "inbox", 0, 1),
        (1, "Shon Kapate", "ceo", 2, "Rohit Verma", "manager01", "Q3 Architecture Roadmap & Client Approvals", "Rohit,\nGreat work on delivering the Vertex Logistics cluster ahead of schedule. Let us review the EduNova proposal numbers during tomorrow morning's executive sync.\n\n- Shon Kapate", "inbox", 1, 1),
        (3, "Ananya Deshmukh", "manager02", 8, "Gaurav More", "intern01", "Internship Module 8 Feedback & Commendation", "Gaurav,\nYour portfolio optimization Python algorithm was very clean and well documented. Keep up the high standard of work!\n\nBest,\nAnanya", "inbox", 0, 0),
        (4, "Siddharth Patil", "employee01", 2, "Rohit Verma", "manager01", "Re: Sprint Review & Nexus Telehealth Release", "Hi Rohit,\nWorking on the e-signature canvas now. Will have end-to-end integration complete by tomorrow evening.", "sent", 1, 0)
    ]
    for m in messages_data:
        cursor.execute('''
            INSERT INTO internal_messages (sender_id, sender_name, sender_username, receiver_id, receiver_name, receiver_username, subject, body, folder, is_read, is_starred)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', m)

    # 10. Chat Channels & Messages
    cursor.execute('''
        INSERT INTO chat_channels (channel_id, name, channel_type, members_json)
        VALUES 
        ('chan-general', 'Company General', 'general', '["all"]'),
        ('chan-engineering', 'Engineering & DevOps', 'general', '["ceo", "manager01", "employee01", "employee03", "intern01"]'),
        ('chan-prj-nexus', 'Nexus Telehealth Dev', 'project', '["manager01", "employee01", "employee02", "intern01"]'),
        ('chan-ai-lab', 'AI & ML Lab', 'general', '["ceo", "manager02", "employee03", "intern02"]')
    ''')

    cursor.execute('''
        INSERT INTO chat_messages (channel_id, sender_id, sender_name, sender_role, message)
        VALUES 
        ('chan-general', 1, 'Shon Kapate', 'CEO', 'Welcome team to the Kapate Workspace Control Center. Operations and metrics are active.'),
        ('chan-general', 2, 'Rohit Verma', 'Manager', 'Engineering team ready. Morning attendance logged.'),
        ('chan-engineering', 6, 'Aditya Shinde', 'Employee', 'AWS ECS production cluster healthy with all nodes green.')
    ''')

    # 11. Company Files
    files_data = [
        ("HR", "Policy", "Kapate_Employee_Handbook_2026.pdf", "1.4 MB", "PDF", "Shon Kapate", "CEO", "All", "/files/handbook.pdf"),
        ("Finance", "Statements", "Q2_Audited_Financial_Statement.pdf", "2.8 MB", "PDF", "Shon Kapate", "CEO", "CEO", "/files/q2_finance.pdf"),
        ("Templates", "Proposals", "Master_Consulting_Agreement_Template.docx", "450 KB", "DOCX", "Shon Kapate", "CEO", "Manager", "/files/contract_tmpl.docx"),
        ("Projects", "Nexus Health", "Nexus_System_Architecture_V3.pdf", "3.2 MB", "PDF", "Rohit Verma", "Manager", "All", "/files/nexus_arch.pdf"),
        ("Projects", "FinEdge", "Algorithmic_Trading_API_Spec.pdf", "1.8 MB", "PDF", "Ananya Deshmukh", "Manager", "All", "/files/finedge_api.pdf"),
        ("Internal", "Security", "SOC2_Compliance_Checklist_2026.xlsx", "890 KB", "XLSX", "Aditya Shinde", "Employee", "All", "/files/soc2.xlsx")
    ]
    for f in files_data:
        cursor.execute('''
            INSERT INTO company_files (folder, subfolder, name, file_size, file_type, uploaded_by, uploader_role, access_roles, download_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', f)

    # 12. Proposals
    proposals_data = [
        ("KC-PRO-801", "KC-CLI-104", "EduNova Learning Solutions", "EduNova Virtual Class Cloud", "Next.js Web App, WebRTC Streaming, AI Proctoring Engine, AWS Infrastructure", "End-to-end interactive cloud classroom with multi-tenant student billing.", 480000, "16 Weeks", "30% Advance, 40% Milestone 2, 30% Deployment", "Standard 1-year SLA with 99.9% uptime guarantee.", "Sent"),
        ("KC-PRO-802", "KC-CLI-105", "Apex Retail Global", "Apex B2B Marketplace Portal", "Microservices Backend, Flutter Mobile Apps, Payment Gateway, Inventory Sync", "Complete digital transformation of distributor wholesale catalog.", 850000, "20 Weeks", "25% Advance, 50% Staged, 25% Handover", "Post-deployment 6-month warranty included.", "Draft")
    ]
    for pr in proposals_data:
        cursor.execute('''
            INSERT INTO proposals (proposal_id, client_id, client_name, project_name, services, description, pricing, timeline, terms, payment_schedule, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', pr)

    # 13. Invoices
    inv_items_1 = json.dumps([
        {"item": "Milestone 2 - WebRTC Video & Chat Core", "qty": 1, "rate": 250000, "amount": 250000},
        {"item": "HIPAA Cloud Compliance Hardening & Audit", "qty": 1, "rate": 80000, "amount": 80000}
    ])
    inv_items_2 = json.dumps([
        {"item": "Milestone 1 - Historical Risk Backtesting Model", "qty": 1, "rate": 350000, "amount": 350000},
        {"item": "Real-time Tick Data Buffer Setup (Redis)", "qty": 1, "rate": 100000, "amount": 100000}
    ])
    invoices_data = [
        ("KC-INV-901", "KC-CLI-101", "Nexus Health Systems", "KC-PRJ-201", "Nexus Clinical Telehealth Suite", inv_items_1, 330000, 18.0, 59400, 0, 389400, "2026-08-30", "Paid", "Milestone 2 invoice cleared via NEFT transfer."),
        ("KC-INV-902", "KC-CLI-102", "FinEdge Wealth Advisory", "KC-PRJ-202", "FinEdge AI Portfolio Analytics", inv_items_2, 450000, 18.0, 81000, 10000, 521000, "2026-08-25", "Sent", "Milestone 1 completion invoice dispatched to finance department.")
    ]
    for inv in invoices_data:
        cursor.execute('''
            INSERT INTO invoices (invoice_no, client_id, client_name, project_id, project_name, items_json, subtotal, tax_rate, tax_amount, discount, total, due_date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', inv)

    # 14. Attendance
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    attendance_data = [
        ("EMP-001", "Shon Kapate", today_str, "08:45 AM", "", 0, "Present"),
        ("EMP-002", "Rohit Verma", today_str, "09:00 AM", "", 0, "Present"),
        ("EMP-003", "Ananya Deshmukh", today_str, "09:10 AM", "", 0, "Present"),
        ("EMP-004", "Siddharth Patil", today_str, "09:15 AM", "", 0, "Present"),
        ("EMP-005", "Pooja Kulkarni", today_str, "09:30 AM", "", 0, "Present"),
        ("EMP-006", "Aditya Shinde", today_str, "09:05 AM", "", 0, "Present"),
        ("INT-007", "Tanvi Joshi", today_str, "09:40 AM", "", 0, "Present"),
        ("INT-008", "Gaurav More", today_str, "09:45 AM", "", 0, "Present")
    ]
    for att in attendance_data:
        cursor.execute('''
            INSERT INTO attendance (emp_id, emp_name, date, clock_in, clock_out, total_hours, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', att)

    # 15. Leave Requests
    leaves_data = [
        ("EMP-004", "Siddharth Patil", "Casual Leave", "2026-08-28", "2026-08-29", "Family gathering in hometown.", "Approved", "Rohit Verma", "Approved. Tasks have been scheduled around the dates."),
        ("INT-007", "Tanvi Joshi", "Internship Exam", "2026-09-05", "2026-09-07", "College final semester practical exams.", "Pending", "", "")
    ]
    for lv in leaves_data:
        cursor.execute('''
            INSERT INTO leave_requests (emp_id, emp_name, leave_type, start_date, end_date, reason, status, reviewed_by, review_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', lv)

    # 16. Meetings
    meetings_data = [
        ("Nexus Telehealth Client Demonstration", 2, "Rohit Verma", json.dumps(["Shon Kapate", "Rohit Verma", "Siddharth Patil", "Pooja Kulkarni"]), "2026-08-24", "10:00 AM", "https://meet.google.com/kap-telehealth", "Demonstrate completed e-signature and telehealth video room to client executives.", "Prepare staging environment with sample doctor patient profiles.", json.dumps(["Verify camera microphone switching", "Prepare PDF signature certificate demo"])),
        ("Q3 AI Solutions Technical Roadmap", 3, "Ananya Deshmukh", json.dumps(["Shon Kapate", "Ananya Deshmukh", "Aditya Shinde", "Gaurav More"]), "2026-08-25", "03:00 PM", "https://meet.google.com/kap-ai-roadmap", "Review model inference latency benchmarks on AWS Inferentia clusters.", "Bring GPU utilization graphs.", json.dumps(["Benchmark FP16 vs INT8 quantization"]))
    ]
    for mt in meetings_data:
        cursor.execute('''
            INSERT INTO meetings (title, organizer_id, organizer_name, participants_json, meeting_date, meeting_time, location_link, agenda, notes, action_items_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', mt)

    # 17. Internships
    int_modules_1 = json.dumps([
        {"id": 1, "title": "Modern Frontend Architecture & ES6+", "status": "Completed", "score": 95},
        {"id": 2, "title": "State Management & Responsive CSS Design", "status": "Completed", "score": 92},
        {"id": 3, "title": "REST API Integration & Authentication", "status": "Completed", "score": 94},
        {"id": 4, "title": "FHIR Healthcare Data Protocols", "status": "In Progress", "score": 88},
        {"id": 5, "title": "Unit & Integration Testing with PyTest / Jest", "status": "Pending", "score": 0}
    ])
    int_modules_2 = json.dumps([
        {"id": 1, "title": "Applied Linear Algebra & NumPy Foundations", "status": "Completed", "score": 98},
        {"id": 2, "title": "Financial Time Series Modeling & Pandas", "status": "Completed", "score": 96},
        {"id": 3, "title": "Portfolio Optimization & Risk Theory", "status": "Completed", "score": 95},
        {"id": 4, "title": "Real-Time WebSocket Inference Pipelines", "status": "In Progress", "score": 90},
        {"id": 5, "title": "Model Serving & Docker Deployment", "status": "Pending", "score": 0}
    ])
    cursor.execute('''
        INSERT INTO internship_details (intern_id, intern_name, mentor_id, mentor_name, department, start_date, end_date, progress_percent, modules_json, feedback, certificate_status)
        VALUES 
        ('INT-007', 'Tanvi Joshi', 2, 'Rohit Verma', 'Software Development', '2026-06-01', '2026-11-30', 80, ?, 'Consistent effort and high code quality in frontend components.', 'In Progress'),
        ('INT-008', 'Gaurav More', 3, 'Ananya Deshmukh', 'AI & Machine Learning', '2026-06-15', '2026-12-15', 85, ?, 'Exceptional mathematical rigor in algorithmic risk calculations.', 'In Progress')
    ''', (int_modules_1, int_modules_2))

    # 18. Announcements
    cursor.execute('''
        INSERT INTO announcements (title, content, target_audience, priority, author_name, author_role)
        VALUES 
        ('Launch of Kapate Enterprise Workspace Control Center', 'All administrative, engineering, and HR workflows have been consolidated into the unified Workspace platform.', 'All', 'High', 'Shon Kapate', 'CEO'),
        ('Monthly All-Hands Technical Townhall', 'Our Q3 Technical Townhall is scheduled for this Friday at 4:30 PM. Lead architects will present project impact metrics.', 'All', 'Normal', 'Rohit Verma', 'Manager')
    ''')

    # 19. Initial Audit Logs
    cursor.execute('''
        INSERT INTO audit_logs (user_name, action, entity, entity_id, old_value, new_value, ip_address, reason)
        VALUES 
        ('system', 'System Initialized', 'Workspace Database', '0', '', 'Initial Schema Loaded', '127.0.0.1', 'Bootstrap'),
        ('Shon Kapate', 'CEO Session Activated', 'users', 'EMP-001', '', 'Executive Control Center Ready', '127.0.0.1', 'Login')
    ''')

    conn.commit()
    conn.close()
    print("Seeding complete.")

# Authentication Helper
def get_current_user():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header:
        return None
    token = auth_header.replace('Bearer ', '').strip()
    if token in SESSION_TOKENS:
        return SESSION_TOKENS[token]
    if token == "kapate-admin-secure-token-98765":
        return {
            "id": 1,
            "emp_code": "EMP-001",
            "username": "ceo",
            "email": "ceo@internal.kapate",
            "name": "Shon Kapate",
            "role": "CEO",
            "department": "Executive & Management"
        }
    return None

def require_auth(allowed_roles=None):
    user = get_current_user()
    if not user:
        return None, (jsonify({"success": False, "error": "Unauthorized. Please log in to Kapate Workspace."}), 401)
    if allowed_roles and user.get('role') not in allowed_roles:
        return None, (jsonify({"success": False, "error": f"Access denied. Required role: {', '.join(allowed_roles)}"}), 403)
    return user, None

# ==============================================================================
# WORKSPACE REST API ENDPOINTS
# ==============================================================================

# --- 1. Authentication ---
@app.route('/api/workspace/auth/login', methods=['POST'])
def workspace_login():
    data = request.get_json(silent=True) or {}
    identifier = data.get('username') or data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    if not identifier or not password:
        return jsonify({"success": False, "error": "Username/Email and Password are required."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM users 
        WHERE LOWER(username) = ? OR LOWER(email) = ? OR LOWER(emp_code) = ?
    ''', (identifier, identifier, identifier))
    user_row = cursor.fetchone()
    conn.close()

    if not user_row:
        return jsonify({"success": False, "error": "Invalid credentials. User not found."}), 401

    if not check_password_hash(user_row['password_hash'], password):
        return jsonify({"success": False, "error": "Invalid password."}), 401

    if user_row['status'] != 'Active':
        return jsonify({"success": False, "error": f"Account is {user_row['status']}. Please contact CEO/Admin."}), 403

    token = f"kw-sess-{user_row['id']}-{random.randint(100000, 999999)}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    user_data = {
        "id": user_row['id'],
        "emp_code": user_row['emp_code'],
        "username": user_row['username'],
        "email": user_row['email'],
        "name": user_row['name'],
        "role": user_row['role'],
        "department": user_row['department'],
        "designation": user_row['designation'],
        "manager_name": user_row['manager_name'],
        "phone": user_row['phone']
    }
    SESSION_TOKENS[token] = user_data

    audit_log(user_row['name'], "User Logged In", "users", user_row['emp_code'], ip_addr=request.remote_addr or "127.0.0.1", reason="User Authenticated")

    return jsonify({
        "success": True,
        "token": token,
        "user": user_data
    })

@app.route('/api/workspace/auth/me', methods=['GET', 'POST'])
def workspace_auth_me():
    user, err = require_auth()
    if err: return err
    return jsonify({"success": True, "user": user})

@app.route('/api/workspace/auth/logout', methods=['POST'])
def workspace_logout():
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '').strip()
    if token in SESSION_TOKENS:
        user = SESSION_TOKENS.pop(token)
        audit_log(user.get('name', 'User'), "User Logged Out", "users", user.get('emp_code', ''))
    return jsonify({"success": True, "message": "Successfully logged out."})

# --- 2. CEO Needs Attention & Dashboard Metrics ---
@app.route('/api/workspace/needs-attention', methods=['GET'])
def workspace_needs_attention():
    user, err = require_auth(['CEO', 'Manager'])
    if err: return err

    conn = get_db()
    cursor = conn.cursor()

    # Overdue tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE deadline < date('now') AND status NOT IN ('Completed', 'Approved')")
    overdue_tasks = cursor.fetchone()[0]

    # Tasks pending approval
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Submitted'")
    pending_approvals = cursor.fetchone()[0]

    # Pending leaves
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status = 'Pending'")
    pending_leaves = cursor.fetchone()[0]

    # Overdue invoices
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE status = 'Sent' AND due_date < date('now')")
    overdue_invoices = cursor.fetchone()[0]

    # Projects approaching deadline in 14 days
    cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'Active' AND deadline <= date('now', '+14 days')")
    projects_at_risk = cursor.fetchone()[0]

    conn.close()

    items = []
    if overdue_tasks > 0:
        items.append({"level": "danger", "title": f"{overdue_tasks} overdue task(s) requiring intervention", "tab": "tab-tasks", "badge": "Overdue"})
    if pending_approvals > 0:
        items.append({"level": "warning", "title": f"{pending_approvals} task deliverable(s) pending executive approval", "tab": "tab-tasks", "badge": "Review"})
    if pending_leaves > 0:
        items.append({"level": "warning", "title": f"{pending_leaves} staff leave request(s) awaiting moderation", "tab": "tab-leave", "badge": "Leave"})
    if overdue_invoices > 0:
        items.append({"level": "danger", "title": f"{overdue_invoices} client invoice(s) past payment due date", "tab": "tab-invoices", "badge": "Finance"})
    if projects_at_risk > 0:
        items.append({"level": "info", "title": f"{projects_at_risk} active project(s) approaching deadline within 14 days", "tab": "tab-projects", "badge": "SLA"})

    return jsonify({"success": True, "items": items, "counts": {
        "overdue_tasks": overdue_tasks,
        "pending_approvals": pending_approvals,
        "pending_leaves": pending_leaves,
        "overdue_invoices": overdue_invoices,
        "projects_at_risk": projects_at_risk
    }})

@app.route('/api/workspace/dashboard/metrics', methods=['GET'])
def workspace_dashboard_metrics():
    user, err = require_auth()
    if err: return err

    conn = get_db()
    cursor = conn.cursor()
    role = user['role']
    metrics = {}

    if role == 'CEO':
        cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'Active'")
        metrics['total_employees'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'Manager' AND status = 'Active'")
        metrics['total_managers'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'Intern' AND status = 'Active'")
        metrics['total_interns'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'Active'")
        metrics['active_projects'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'Completed'")
        metrics['completed_projects'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status NOT IN ('Completed', 'Approved')")
        metrics['active_tasks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Completed'")
        metrics['completed_tasks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE deadline < date('now') AND status NOT IN ('Completed', 'Approved')")
        metrics['overdue_tasks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Submitted'")
        metrics['pending_approvals'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM clients WHERE status = 'Active'")
        metrics['active_clients'] = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status = 'Paid'")
        metrics['monthly_revenue'] = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status IN ('Sent', 'Draft', 'Partially Paid')")
        metrics['pending_payments'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status = 'Pending'")
        metrics['pending_leaves'] = cursor.fetchone()[0]

        metrics['company_health'] = {
            "projects": 88,
            "tasks": 82,
            "deadlines": 91,
            "client_status": 96
        }

    elif role == 'Manager':
        cursor.execute("SELECT COUNT(*) FROM projects WHERE manager_id = ? AND status = 'Active'", (user['id'],))
        metrics['active_projects'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_by_id = ? AND status NOT IN ('Completed', 'Approved')", (user['id'],))
        metrics['tasks_assigned'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_by_id = ? AND status = 'Submitted'", (user['id'],))
        metrics['tasks_pending_review'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_by_id = ? AND deadline < date('now') AND status NOT IN ('Completed', 'Approved')", (user['id'],))
        metrics['overdue_tasks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status = 'Pending'")
        metrics['pending_leaves'] = cursor.fetchone()[0]

    elif role == 'Employee':
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to_id = ? AND status IN ('Assigned', 'Accepted', 'In Progress')", (user['id'],))
        metrics['today_tasks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to_id = ? AND priority = 'High' AND status NOT IN ('Completed', 'Approved')", (user['id'],))
        metrics['high_priority_tasks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to_id = ? AND status = 'Submitted'", (user['id'],))
        metrics['tasks_under_review'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to_id = ? AND status = 'Completed'", (user['id'],))
        metrics['completed_tasks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM internal_messages WHERE receiver_id = ? AND is_read = 0 AND folder = 'inbox'", (user['id'],))
        metrics['unread_messages'] = cursor.fetchone()[0]

    elif role == 'Intern':
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to_id = ?", (user['id'],))
        metrics['assigned_tasks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to_id = ? AND status = 'Completed'", (user['id'],))
        metrics['completed_tasks'] = cursor.fetchone()[0]

        cursor.execute("SELECT progress_percent, certificate_status FROM internship_details WHERE mentor_id = ? OR intern_name LIKE ?", (user['id'], f"%{user['name']}%"))
        row = cursor.fetchone()
        metrics['progress_percent'] = row['progress_percent'] if row else 80
        metrics['certificate_status'] = row['certificate_status'] if row else 'In Progress'

    conn.close()
    return jsonify({"success": True, "metrics": metrics})

# --- 3. Full Employee Management & Comprehensive Profile ---
@app.route('/api/workspace/employees', methods=['GET', 'POST'])
def workspace_employees():
    user, err = require_auth()
    if err: return err

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        dept_filter = request.args.get('department')
        role_filter = request.args.get('role')
        status_filter = request.args.get('status')
        manager_filter = request.args.get('manager')
        search = request.args.get('q', '').strip().lower()

        query = "SELECT * FROM users WHERE 1=1"
        params = []

        if dept_filter and dept_filter != 'All':
            query += " AND department = ?"
            params.append(dept_filter)
        if role_filter and role_filter != 'All':
            query += " AND role = ?"
            params.append(role_filter)
        if status_filter and status_filter != 'All':
            query += " AND status = ?"
            params.append(status_filter)
        if manager_filter and manager_filter != 'All':
            query += " AND manager_name LIKE ?"
            params.append(f"%{manager_filter}%")
        if search:
            query += " AND (LOWER(name) LIKE ? OR LOWER(username) LIKE ? OR LOWER(emp_code) LIKE ? OR LOWER(designation) LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

        query += " ORDER BY id ASC"
        cursor.execute(query, params)
        employees = [dict(r) for r in cursor.fetchall()]

        # Non-CEO / Non-HR should not see basic_pay compensation numbers
        if user['role'] not in ['CEO', 'Manager']:
            for emp in employees:
                emp.pop('basic_pay', None)

        conn.close()
        return jsonify({"success": True, "employees": employees})

    elif request.method == 'POST':
        if user['role'] != 'CEO':
            conn.close()
            return jsonify({"success": False, "error": "Only CEO/Admin can register new employees."}), 403

        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        username = data.get('username', '').strip().lower()
        email = data.get('email', '').strip().lower() or f"{username}@internal.kapate"
        password = data.get('password', '').strip() or 'Kapate@2026'
        emp_code = data.get('emp_code', '').strip().upper() or f"EMP-{random.randint(100, 999)}"
        department = data.get('department', 'Software Development')
        designation = data.get('designation', 'Software Engineer')
        role = data.get('role', 'Employee')
        manager_name = data.get('manager_name', 'Rohit Verma')
        joining_date = data.get('joining_date', datetime.date.today().strftime('%Y-%m-%d'))
        employment_type = data.get('employment_type', 'Full-Time')
        basic_pay = float(data.get('basic_pay', 75000))
        phone = data.get('phone', '')

        if not name or not username:
            conn.close()
            return jsonify({"success": False, "error": "Full Name and Username are required."}), 400

        pwd_hash = generate_password_hash(password)
        try:
            cursor.execute('''
                INSERT INTO users (emp_code, username, email, password_hash, name, role, department, designation, manager_name, status, phone, joining_date, employment_type, basic_pay)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?, ?, ?)
            ''', (emp_code, username, email, pwd_hash, name, role, department, designation, manager_name, phone, joining_date, employment_type, basic_pay))
            conn.commit()

            audit_log(user['name'], "Created Employee Account", "users", emp_code, new_val=f"{name} ({role})", reason="Staff Provisioning")
            conn.close()
            return jsonify({"success": True, "message": f"Employee {name} ({emp_code}) provisioned successfully."})
        except sqlite3.IntegrityError as e:
            conn.close()
            return jsonify({"success": False, "error": f"Employee ID or username already exists."}), 400

@app.route('/api/workspace/employees/<int:emp_id>/full-profile', methods=['GET'])
def workspace_employee_full_profile(emp_id):
    user, err = require_auth()
    if err: return err

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (emp_id,))
    emp_row = cursor.fetchone()
    if not emp_row:
        conn.close()
        return jsonify({"success": False, "error": "Employee not found."}), 404

    emp = dict(emp_row)

    # Privacy check for compensation: Only CEO and self can see salary
    if user['role'] != 'CEO' and user['id'] != emp['id']:
        emp.pop('basic_pay', None)

    # 1. Projects
    cursor.execute("SELECT * FROM projects WHERE team_members LIKE ? OR manager_id = ?", (f"%{emp['name']}%", emp['id']))
    projects = [dict(r) for r in cursor.fetchall()]

    # 2. Tasks & Stats
    cursor.execute("SELECT * FROM tasks WHERE assigned_to_id = ? ORDER BY id DESC", (emp['id'],))
    tasks = [dict(r) for r in cursor.fetchall()]

    completed_tasks = len([t for t in tasks if t['status'] in ['Completed', 'Approved']])
    pending_tasks = len([t for t in tasks if t['status'] in ['Assigned', 'In Progress', 'Accepted']])
    submitted_tasks = len([t for t in tasks if t['status'] == 'Submitted'])
    overdue_tasks = len([t for t in tasks if t['deadline'] < datetime.date.today().strftime('%Y-%m-%d') and t['status'] not in ['Completed', 'Approved']])

    # 3. Attendance Stats & Logs
    cursor.execute("SELECT * FROM attendance WHERE emp_id = ? OR emp_name LIKE ? ORDER BY date DESC LIMIT 30", (emp['emp_code'], f"%{emp['name']}%"))
    attendance_logs = [dict(r) for r in cursor.fetchall()]
    present_days = len([a for a in attendance_logs if a['status'] == 'Present'])
    late_days = len([a for a in attendance_logs if a['status'] == 'Late'])

    # 4. Leave History & Balance
    cursor.execute("SELECT * FROM leave_requests WHERE emp_id = ? OR emp_name LIKE ? ORDER BY id DESC", (emp['emp_code'], f"%{emp['name']}%"))
    leave_requests = [dict(r) for r in cursor.fetchall()]
    leave_balance = {
        "available": 18,
        "used": len([l for l in leave_requests if l['status'] == 'Approved']),
        "pending": len([l for l in leave_requests if l['status'] == 'Pending']),
        "rejected": len([l for l in leave_requests if l['status'] == 'Rejected'])
    }

    # 5. Documents
    cursor.execute("SELECT * FROM employee_documents WHERE emp_id = ? ORDER BY id ASC", (emp['id'],))
    documents = [dict(r) for r in cursor.fetchall()]

    # 6. Confidential Notes (CEO Only)
    notes = []
    if user['role'] == 'CEO':
        cursor.execute("SELECT * FROM employee_notes WHERE emp_id = ? ORDER BY id DESC", (emp['id'],))
        notes = [dict(r) for r in cursor.fetchall()]

    # 7. Activity Timeline (Audit logs related to employee)
    cursor.execute("SELECT * FROM audit_logs WHERE user_name LIKE ? OR entity_id = ? ORDER BY id DESC LIMIT 20", (f"%{emp['name']}%", emp['emp_code']))
    activity = [dict(r) for r in cursor.fetchall()]

    # 8. Performance Review
    cursor.execute("SELECT * FROM performance_reviews WHERE emp_id = ? OR emp_name LIKE ? ORDER BY id DESC LIMIT 1", (emp['emp_code'], f"%{emp['name']}%"))
    review_row = cursor.fetchone()
    review = dict(review_row) if review_row else {
        "rating_score": emp.get('performance_score', 4.7),
        "on_time_rate": 96.2,
        "tasks_completed": completed_tasks,
        "feedback": "Consistent high quality technical delivery and strong team collaboration."
    }

    conn.close()

    # Log CEO profile view
    if user['role'] == 'CEO' and user['id'] != emp['id']:
        audit_log(user['name'], "Viewed Employee Profile", "users", emp['emp_code'], reason="Executive Inspection")

    return jsonify({
        "success": True,
        "employee": emp,
        "stats": {
            "projects_count": len(projects),
            "tasks_total": len(tasks),
            "tasks_completed": completed_tasks,
            "tasks_pending": pending_tasks,
            "tasks_submitted": submitted_tasks,
            "tasks_overdue": overdue_tasks,
            "attendance_rate": 96.5,
            "performance_rating": emp.get('performance_score', 4.7)
        },
        "projects": projects,
        "tasks": tasks,
        "attendance": {
            "logs": attendance_logs,
            "present_count": present_days,
            "late_count": late_days,
            "attendance_rate": 96.5
        },
        "leave": {
            "balance": leave_balance,
            "history": leave_requests
        },
        "performance": {
            "review": review,
            "trends": [
                {"month": "Jan", "score": 4.5},
                {"month": "Feb", "score": 4.6},
                {"month": "Mar", "score": 4.6},
                {"month": "Apr", "score": 4.7},
                {"month": "May", "score": 4.8},
                {"month": "Jun", "score": 4.7}
            ]
        },
        "documents": documents,
        "notes": notes,
        "activity": activity
    })

# --- 4. Employee Personal & Employment Updates ---
@app.route('/api/workspace/employees/<int:emp_id>/personal', methods=['PUT'])
def workspace_update_employee_personal(emp_id):
    user, err = require_auth(['CEO', 'Manager'])
    if err: return err

    data = request.get_json(silent=True) or {}
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE users 
        SET dob = COALESCE(?, dob),
            phone = COALESCE(?, phone),
            address = COALESCE(?, address),
            emergency_contact = COALESCE(?, emergency_contact)
        WHERE id = ?
    ''', (data.get('dob'), data.get('phone'), data.get('address'), data.get('emergency_contact'), emp_id))
    conn.commit()

    audit_log(user['name'], "Updated Personal Information", "users", emp_id, reason="HR Profile Update")
    conn.close()
    return jsonify({"success": True, "message": "Personal information updated successfully."})

@app.route('/api/workspace/employees/<int:emp_id>/employment', methods=['PUT'])
def workspace_update_employee_employment(emp_id):
    user, err = require_auth(['CEO'])
    if err: return err

    data = request.get_json(silent=True) or {}
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE users 
        SET designation = COALESCE(?, designation),
            department = COALESCE(?, department),
            role = COALESCE(?, role),
            manager_name = COALESCE(?, manager_name),
            employment_type = COALESCE(?, employment_type),
            basic_pay = COALESCE(?, basic_pay)
        WHERE id = ?
    ''', (data.get('designation'), data.get('department'), data.get('role'), data.get('manager_name'), data.get('employment_type'), data.get('basic_pay'), emp_id))
    conn.commit()

    audit_log(user['name'], "Updated Employment Details", "users", emp_id, new_val=f"Dept: {data.get('department')}, Role: {data.get('role')}", reason="Executive Compensation / Assignment")
    conn.close()
    return jsonify({"success": True, "message": "Employment details & compensation updated."})

@app.route('/api/workspace/employees/<int:emp_id>/status', methods=['PUT'])
def workspace_update_employee_status(emp_id):
    user, err = require_auth(['CEO'])
    if err: return err

    data = request.get_json(silent=True) or {}
    new_status = data.get('status', 'Active') # Active, Inactive, Suspended
    reason = data.get('reason', 'Administrative Action')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, emp_id))
    conn.commit()

    audit_log(user['name'], f"Changed Employee Status to {new_status}", "users", emp_id, new_val=new_status, reason=reason)
    conn.close()
    return jsonify({"success": True, "message": f"Employee status set to {new_status}."})

@app.route('/api/workspace/employees/<int:emp_id>/notes', methods=['POST'])
def workspace_add_employee_note(emp_id):
    user, err = require_auth(['CEO'])
    if err: return err

    data = request.get_json(silent=True) or {}
    note_text = data.get('note_text', '').strip()
    if not note_text:
        return jsonify({"success": False, "error": "Note text is required."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO employee_notes (emp_id, author_id, author_name, author_role, note_text)
        VALUES (?, ?, ?, ?, ?)
    ''', (emp_id, user['id'], user['name'], user['role'], note_text))
    conn.commit()

    audit_log(user['name'], "Added Confidential Employee Note", "employee_notes", emp_id, reason="Executive Review")
    conn.close()
    return jsonify({"success": True, "message": "Confidential note saved."})

# --- 5. CEO Task Master Override ---
@app.route('/api/workspace/tasks/<task_id>/ceo-override', methods=['POST'])
def workspace_ceo_task_override(task_id):
    user, err = require_auth(['CEO'])
    if err: return err

    data = request.get_json(silent=True) or {}
    reassigned_to_id = data.get('assigned_to_id')
    reassigned_to_name = data.get('assigned_to_name')
    priority = data.get('priority')
    deadline = data.get('deadline')
    status = data.get('status')
    override_reason = data.get('reason', 'CEO Executive Reallocation')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return jsonify({"success": False, "error": "Task not found."}), 404

    old_summary = f"Assignee: {task['assigned_to_name']}, Priority: {task['priority']}, Status: {task['status']}, Deadline: {task['deadline']}"

    cursor.execute('''
        UPDATE tasks
        SET assigned_to_id = COALESCE(?, assigned_to_id),
            assigned_to_name = COALESCE(?, assigned_to_name),
            priority = COALESCE(?, priority),
            deadline = COALESCE(?, deadline),
            status = COALESCE(?, status),
            updated_at = datetime('now', 'localtime')
        WHERE task_id = ?
    ''', (reassigned_to_id, reassigned_to_name, priority, deadline, status, task_id))
    conn.commit()

    new_summary = f"Assignee: {reassigned_to_name or task['assigned_to_name']}, Priority: {priority or task['priority']}, Status: {status or task['status']}, Deadline: {deadline or task['deadline']}"

    audit_log(user['name'], f"CEO Overrode Task {task_id}", "tasks", task_id, old_val=old_summary, new_val=new_summary, reason=override_reason)
    create_notification(reassigned_to_id or task['assigned_to_id'], "Task Updated by CEO", f"CEO override on {task['title']}: {override_reason}", "tab-tasks", "task")

    conn.close()
    return jsonify({"success": True, "message": f"Task {task_id} successfully updated with executive override."})

# --- 6. Departments & Roles Matrix ---
@app.route('/api/workspace/departments', methods=['GET', 'POST'])
def workspace_departments():
    user, err = require_auth()
    if err: return err

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute('''
            SELECT d.*, 
                   (SELECT COUNT(*) FROM users u WHERE u.department = d.name) as employee_count,
                   (SELECT COUNT(*) FROM projects p WHERE p.client_name IS NOT NULL) as active_projects
            FROM departments d
            ORDER BY d.id ASC
        ''')
        depts = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "departments": depts})

    elif request.method == 'POST':
        if user['role'] != 'CEO':
            conn.close()
            return jsonify({"success": False, "error": "Only CEO can create departments."}), 403

        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        head_name = data.get('head_name', '').strip()
        description = data.get('description', '')
        budget = float(data.get('budget', 1000000))

        if not name or not head_name:
            conn.close()
            return jsonify({"success": False, "error": "Department Name and Head Name are required."}), 400

        cursor.execute('''
            INSERT INTO departments (name, head_name, description, budget)
            VALUES (?, ?, ?, ?)
        ''', (name, head_name, description, budget))
        conn.commit()

        audit_log(user['name'], "Created Department", "departments", name, reason="Org Restructuring")
        conn.close()
        return jsonify({"success": True, "message": f"Department '{name}' created successfully."})

@app.route('/api/workspace/roles-permissions', methods=['GET', 'PUT'])
def workspace_roles_permissions():
    user, err = require_auth()
    if err: return err

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM roles_permissions ORDER BY id ASC")
        perms = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "permissions": perms})

    elif request.method == 'PUT':
        if user['role'] != 'CEO':
            conn.close()
            return jsonify({"success": False, "error": "Only CEO can modify permissions matrix."}), 403

        data = request.get_json(silent=True) or {}
        perm_id = data.get('id')
        manager_perm = data.get('manager_perm')
        employee_perm = data.get('employee_perm')
        intern_perm = data.get('intern_perm')

        cursor.execute('''
            UPDATE roles_permissions
            SET manager_perm = COALESCE(?, manager_perm),
                employee_perm = COALESCE(?, employee_perm),
                intern_perm = COALESCE(?, intern_perm)
            WHERE id = ?
        ''', (manager_perm, employee_perm, intern_perm, perm_id))
        conn.commit()

        audit_log(user['name'], "Updated Permissions Matrix", "roles_permissions", perm_id, reason="Security Policy Update")
        conn.close()
        return jsonify({"success": True, "message": "Permission updated."})

# --- 7. Data Export (CSV/Text) ---
@app.route('/api/workspace/export/<export_type>', methods=['GET'])
def workspace_export(export_type):
    user, err = require_auth(['CEO', 'Manager'])
    if err: return err

    conn = get_db()
    cursor = conn.cursor()
    si = StringIO()
    writer = csv.writer(si)

    if export_type == 'employees':
        cursor.execute("SELECT emp_code, name, email, role, department, designation, manager_name, status, joining_date, phone FROM users")
        rows = cursor.fetchall()
        writer.writerow(['Employee ID', 'Name', 'Email', 'Role', 'Department', 'Designation', 'Manager', 'Status', 'Joining Date', 'Phone'])
        for r in rows:
            writer.writerow(list(r))
        filename = "Kapate_Employees_Export.csv"

    elif export_type == 'tasks':
        cursor.execute("SELECT task_id, title, project_name, assigned_to_name, priority, status, deadline, estimated_hours FROM tasks")
        rows = cursor.fetchall()
        writer.writerow(['Task ID', 'Title', 'Project', 'Assignee', 'Priority', 'Status', 'Deadline', 'Estimated Hours'])
        for r in rows:
            writer.writerow(list(r))
        filename = "Kapate_Tasks_Export.csv"

    elif export_type == 'attendance':
        cursor.execute("SELECT emp_id, emp_name, date, clock_in, clock_out, total_hours, status FROM attendance")
        rows = cursor.fetchall()
        writer.writerow(['Employee ID', 'Name', 'Date', 'Clock In', 'Clock Out', 'Total Hours', 'Status'])
        for r in rows:
            writer.writerow(list(r))
        filename = "Kapate_Attendance_Export.csv"

    elif export_type == 'invoices':
        cursor.execute("SELECT invoice_no, client_name, project_name, total, due_date, status FROM invoices")
        rows = cursor.fetchall()
        writer.writerow(['Invoice No', 'Client', 'Project', 'Total (INR)', 'Due Date', 'Status'])
        for r in rows:
            writer.writerow(list(r))
        filename = "Kapate_Invoices_Export.csv"

    else:
        conn.close()
        return jsonify({"success": False, "error": "Invalid export type."}), 400

    conn.close()
    audit_log(user['name'], f"Exported {export_type.title()} Data", "exports", export_type, reason="Executive Data Export")

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# --- 8. Projects & Tasks Core Endpoints ---
@app.route('/api/workspace/projects', methods=['GET', 'POST'])
def workspace_projects():
    user, err = require_auth()
    if err: return err

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM projects ORDER BY id DESC")
        projects = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "projects": projects})

    elif request.method == 'POST':
        if user['role'] not in ['CEO', 'Manager']:
            conn.close()
            return jsonify({"success": False, "error": "Permission denied."}), 403

        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        client_name = data.get('client_name', '').strip()
        description = data.get('description', '').strip()
        deadline = data.get('deadline', '')
        priority = data.get('priority', 'Medium')
        budget = float(data.get('budget', 0))

        if not name:
            conn.close()
            return jsonify({"success": False, "error": "Project name is required."}), 400

        project_id = f"KC-PRJ-{random.randint(100, 999)}"
        cursor.execute('''
            INSERT INTO projects (project_id, name, client_name, description, manager_id, manager_name, team_members, start_date, deadline, status, priority, budget, progress)
            VALUES (?, ?, ?, ?, ?, ?, '[]', date('now'), ?, 'Active', ?, ?, 0)
        ''', (project_id, name, client_name, description, user['id'], user['name'], deadline, priority, budget))
        conn.commit()

        audit_log(user['name'], "Created Project", "projects", project_id, new_val=name)
        create_notification(1, "New Project Created", f"{user['name']} created project {name}", "tab-projects", "task", "CEO")

        conn.close()
        return jsonify({"success": True, "message": "Project created.", "project_id": project_id})

@app.route('/api/workspace/tasks', methods=['GET', 'POST'])
def workspace_tasks():
    user, err = require_auth()
    if err: return err

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        filter_type = request.args.get('filter', 'all')
        if filter_type == 'my':
            cursor.execute("SELECT * FROM tasks WHERE assigned_to_id = ? ORDER BY id DESC", (user['id'],))
        elif user['role'] in ['CEO', 'Manager']:
            cursor.execute("SELECT * FROM tasks ORDER BY id DESC")
        else:
            cursor.execute("SELECT * FROM tasks WHERE assigned_to_id = ? OR assigned_by_id = ? ORDER BY id DESC", (user['id'], user['id']))

        tasks = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "tasks": tasks})

    elif request.method == 'POST':
        if user['role'] not in ['CEO', 'Manager']:
            conn.close()
            return jsonify({"success": False, "error": "Permission denied."}), 403

        data = request.get_json(silent=True) or {}
        title = data.get('title', '').strip()
        project_id = data.get('project_id', '')
        project_name = data.get('project_name', '')
        assigned_to_id = data.get('assigned_to_id')
        assigned_to_name = data.get('assigned_to_name', '')
        priority = data.get('priority', 'Medium')
        deadline = data.get('deadline', '')
        estimated_hours = float(data.get('estimated_hours', 0))
        description = data.get('description', '')
        tags = data.get('tags', '')

        if not title or not assigned_to_id:
            conn.close()
            return jsonify({"success": False, "error": "Title and Assignee are required."}), 400

        task_id = f"KC-TSK-{random.randint(100, 999)}"
        cursor.execute('''
            INSERT INTO tasks (task_id, title, description, project_id, project_name, assigned_by_id, assigned_by_name, assigned_to_id, assigned_to_name, priority, status, start_date, deadline, estimated_hours, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Assigned', date('now'), ?, ?, ?)
        ''', (task_id, title, description, project_id, project_name, user['id'], user['name'], assigned_to_id, assigned_to_name, priority, deadline, estimated_hours, tags))
        conn.commit()

        audit_log(user['name'], "Assigned Task", "tasks", task_id, new_val=f"Assigned to {assigned_to_name}")
        create_notification(assigned_to_id, "New Task Assigned", f"{user['name']} assigned you: {title}", "tab-tasks", "task")

        conn.close()
        return jsonify({"success": True, "message": "Task created.", "task_id": task_id})

@app.route('/api/workspace/tasks/<task_id>/status', methods=['PUT'])
def workspace_update_task_status(task_id):
    user, err = require_auth()
    if err: return err

    data = request.get_json(silent=True) or {}
    new_status = data.get('status', '').strip()
    submission_notes = data.get('submission_notes', '')
    submission_url = data.get('submission_url', '')
    manager_review_notes = data.get('manager_review_notes', '')

    allowed_statuses = ['Assigned', 'Accepted', 'In Progress', 'Submitted', 'Under Review', 'Approved', 'Completed', 'Changes Requested']
    if new_status not in allowed_statuses:
        return jsonify({"success": False, "error": f"Invalid status: {new_status}"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return jsonify({"success": False, "error": "Task not found."}), 404

    if new_status in ['Approved', 'Completed'] and user['role'] not in ['CEO', 'Manager']:
        conn.close()
        return jsonify({"success": False, "error": "Only CEO/Managers can approve tasks."}), 403

    old_status = task['status']
    cursor.execute('''
        UPDATE tasks 
        SET status = ?, 
            submission_notes = COALESCE(NULLIF(?, ''), submission_notes),
            submission_url = COALESCE(NULLIF(?, ''), submission_url),
            manager_review_notes = COALESCE(NULLIF(?, ''), manager_review_notes),
            updated_at = datetime('now', 'localtime')
        WHERE task_id = ?
    ''', (new_status, submission_notes, submission_url, manager_review_notes, task_id))

    if new_status in ['Approved', 'Completed'] and task['project_id']:
        cursor.execute("SELECT COUNT(*), SUM(CASE WHEN status IN ('Approved', 'Completed') THEN 1 ELSE 0 END) FROM tasks WHERE project_id = ?", (task['project_id'],))
        total_p_tasks, done_p_tasks = cursor.fetchone()
        if total_p_tasks and total_p_tasks > 0:
            calc_progress = int((done_p_tasks / total_p_tasks) * 100)
            cursor.execute("UPDATE projects SET progress = ? WHERE project_id = ?", (calc_progress, task['project_id']))

    conn.commit()
    audit_log(user['name'], "Updated Task Status", "tasks", task_id, old_val=old_status, new_val=new_status)
    conn.close()
    return jsonify({"success": True, "message": f"Task status updated to {new_status}."})

@app.route('/api/workspace/tasks/<task_id>/comments', methods=['GET', 'POST'])
def workspace_task_comments(task_id):
    user, err = require_auth()
    if err: return err

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM task_comments WHERE task_id = ? ORDER BY id ASC", (task_id,))
        comments = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "comments": comments})

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        comment_text = data.get('comment', '').strip()
        attachment_name = data.get('attachment_name', '')
        if not comment_text:
            conn.close()
            return jsonify({"success": False, "error": "Comment text is required."}), 400

        cursor.execute('''
            INSERT INTO task_comments (task_id, user_id, user_name, user_role, comment, attachment_name)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (task_id, user['id'], user['name'], user['role'], comment_text, attachment_name))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Comment posted."})

# --- 9. Mail, Chat, Files, CRM, Invoices, Attendance, Leave, AI ---
@app.route('/api/workspace/mail', methods=['GET', 'POST'])
def workspace_mail():
    user, err = require_auth()
    if err: return err

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        folder = request.args.get('folder', 'inbox').lower()
        if folder == 'inbox':
            cursor.execute("SELECT * FROM internal_messages WHERE receiver_id = ? AND folder != 'trash' ORDER BY id DESC", (user['id'],))
        elif folder == 'sent':
            cursor.execute("SELECT * FROM internal_messages WHERE sender_id = ? AND folder != 'trash' ORDER BY id DESC", (user['id'],))
        elif folder == 'starred':
            cursor.execute("SELECT * FROM internal_messages WHERE (receiver_id = ? OR sender_id = ?) AND is_starred = 1 ORDER BY id DESC", (user['id'], user['id']))
        elif folder == 'trash':
            cursor.execute("SELECT * FROM internal_messages WHERE (receiver_id = ? OR sender_id = ?) AND folder = 'trash' ORDER BY id DESC", (user['id'], user['id']))
        else:
            cursor.execute("SELECT * FROM internal_messages WHERE receiver_id = ? ORDER BY id DESC", (user['id'],))

        messages = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "messages": messages})

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        to_username = data.get('to', '').strip().lower()
        subject = data.get('subject', '').strip()
        body = data.get('body', '').strip()
        attachment_name = data.get('attachment_name', '')

        if not to_username or not subject or not body:
            conn.close()
            return jsonify({"success": False, "error": "Recipient, Subject, and Body are required."}), 400

        cursor.execute("SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(email) = ? OR LOWER(emp_code) = ?", (to_username, to_username, to_username))
        recipient = cursor.fetchone()
        if not recipient:
            conn.close()
            return jsonify({"success": False, "error": f"Recipient '{to_username}' not found."}), 404

        cursor.execute('''
            INSERT INTO internal_messages (sender_id, sender_name, sender_username, receiver_id, receiver_name, receiver_username, subject, body, folder, is_read, is_starred, attachment_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'inbox', 0, 0, ?)
        ''', (user['id'], user['name'], user['username'], recipient['id'], recipient['name'], recipient['username'], subject, body, attachment_name))
        conn.commit()

        create_notification(recipient['id'], "New Internal Mail", f"{user['name']}: {subject}", "tab-mail", "message")
        conn.close()
        return jsonify({"success": True, "message": "Mail sent successfully."})

@app.route('/api/workspace/mail/<int:msg_id>/star', methods=['PUT'])
def workspace_mail_toggle_star(msg_id):
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE internal_messages SET is_starred = CASE WHEN is_starred = 1 THEN 0 ELSE 1 END WHERE id = ? AND (receiver_id = ? OR sender_id = ?)", (msg_id, user['id'], user['id']))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/workspace/mail/<int:msg_id>/read', methods=['PUT'])
def workspace_mail_mark_read(msg_id):
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE internal_messages SET is_read = 1 WHERE id = ? AND receiver_id = ?", (msg_id, user['id']))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/workspace/chat/channels', methods=['GET'])
def workspace_chat_channels():
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_channels ORDER BY id ASC")
    channels = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "channels": channels})

@app.route('/api/workspace/chat/messages', methods=['GET', 'POST'])
def workspace_chat_messages():
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        channel_id = request.args.get('channel_id', 'chan-general')
        cursor.execute("SELECT * FROM chat_messages WHERE channel_id = ? ORDER BY id ASC LIMIT 100", (channel_id,))
        messages = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "messages": messages})

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        channel_id = data.get('channel_id', 'chan-general')
        msg_text = data.get('message', '').strip()
        attachment_url = data.get('attachment_url', '')

        if not msg_text:
            conn.close()
            return jsonify({"success": False, "error": "Message text required."}), 400

        cursor.execute('''
            INSERT INTO chat_messages (channel_id, sender_id, sender_name, sender_role, message, attachment_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (channel_id, user['id'], user['name'], user['role'], msg_text, attachment_url))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Sent."})

@app.route('/api/workspace/files', methods=['GET', 'POST'])
def workspace_files():
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        folder = request.args.get('folder', 'All')
        if folder == 'All':
            cursor.execute("SELECT * FROM company_files ORDER BY id DESC")
        else:
            cursor.execute("SELECT * FROM company_files WHERE folder = ? ORDER BY id DESC", (folder,))

        all_files = [dict(r) for r in cursor.fetchall()]
        filtered = [f for f in all_files if f['access_roles'] == 'All' or user['role'] in f['access_roles'] or user['role'] == 'CEO']
        conn.close()
        return jsonify({"success": True, "files": filtered})

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        folder = data.get('folder', 'Internal')
        subfolder = data.get('subfolder', '')
        file_size = data.get('file_size', '500 KB')
        file_type = data.get('file_type', 'PDF')
        access_roles = data.get('access_roles', 'All')

        if not name:
            conn.close()
            return jsonify({"success": False, "error": "File name is required."}), 400

        cursor.execute('''
            INSERT INTO company_files (folder, subfolder, name, file_size, file_type, uploaded_by, uploader_role, access_roles)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (folder, subfolder, name, file_size, file_type, user['name'], user['role'], access_roles))
        conn.commit()
        audit_log(user['name'], "Uploaded File", "company_files", name)
        conn.close()
        return jsonify({"success": True, "message": "File recorded."})

@app.route('/api/workspace/crm/clients', methods=['GET', 'POST'])
def workspace_crm_clients():
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM clients ORDER BY id DESC")
        clients = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "clients": clients})

    elif request.method == 'POST':
        if user['role'] not in ['CEO', 'Manager']:
            conn.close()
            return jsonify({"success": False, "error": "Permission denied."}), 403

        data = request.get_json(silent=True) or {}
        company_name = data.get('company_name', '').strip()
        contact_person = data.get('contact_person', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        address = data.get('address', '').strip()
        industry = data.get('industry', 'Technology')
        status = data.get('status', 'Active')
        notes = data.get('notes', '')

        if not company_name or not contact_person:
            conn.close()
            return jsonify({"success": False, "error": "Company Name and Contact Person required."}), 400

        client_id = f"KC-CLI-{random.randint(100, 999)}"
        cursor.execute('''
            INSERT INTO clients (client_id, company_name, contact_person, email, phone, address, industry, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (client_id, company_name, contact_person, email, phone, address, industry, status, notes))
        conn.commit()
        audit_log(user['name'], "Created Client", "clients", client_id, new_val=company_name)
        conn.close()
        return jsonify({"success": True, "message": "Client created.", "client_id": client_id})

@app.route('/api/workspace/crm/proposals', methods=['GET', 'POST'])
def workspace_proposals():
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM proposals ORDER BY id DESC")
        proposals = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "proposals": proposals})

    elif request.method == 'POST':
        if user['role'] not in ['CEO', 'Manager']:
            conn.close()
            return jsonify({"success": False, "error": "Permission denied."}), 403

        data = request.get_json(silent=True) or {}
        client_name = data.get('client_name', '').strip()
        project_name = data.get('project_name', '').strip()
        services = data.get('services', '').strip()
        description = data.get('description', '')
        pricing = float(data.get('pricing', 0))
        timeline = data.get('timeline', '')
        terms = data.get('terms', '')
        payment_schedule = data.get('payment_schedule', '')

        if not client_name or not project_name:
            conn.close()
            return jsonify({"success": False, "error": "Client and Project Name required."}), 400

        prop_id = f"KC-PRO-{random.randint(100, 999)}"
        cursor.execute('''
            INSERT INTO proposals (proposal_id, client_name, project_name, services, description, pricing, timeline, terms, payment_schedule, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Sent')
        ''', (prop_id, client_name, project_name, services, description, pricing, timeline, terms, payment_schedule))
        conn.commit()
        audit_log(user['name'], "Generated Proposal", "proposals", prop_id, new_val=f"{client_name} - {project_name}")
        conn.close()
        return jsonify({"success": True, "message": "Proposal generated.", "proposal_id": prop_id})

@app.route('/api/workspace/crm/invoices', methods=['GET', 'POST'])
def workspace_invoices():
    user, err = require_auth()
    if err: return err
    if user['role'] not in ['CEO', 'Manager']:
        return jsonify({"success": False, "error": "Access denied to finance."}), 403

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM invoices ORDER BY id DESC")
        invoices = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "invoices": invoices})

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        client_name = data.get('client_name', '').strip()
        project_name = data.get('project_name', '').strip()
        items = data.get('items', [])
        subtotal = float(data.get('subtotal', 0))
        tax_rate = float(data.get('tax_rate', 18.0))
        tax_amount = float(data.get('tax_amount', (subtotal * tax_rate) / 100))
        discount = float(data.get('discount', 0))
        total = float(data.get('total', subtotal + tax_amount - discount))
        due_date = data.get('due_date', '')
        notes = data.get('notes', '')

        if not client_name:
            conn.close()
            return jsonify({"success": False, "error": "Client name required."}), 400

        inv_no = f"KC-INV-{random.randint(100, 999)}"
        cursor.execute('''
            INSERT INTO invoices (invoice_no, client_name, project_name, items_json, subtotal, tax_rate, tax_amount, discount, total, due_date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Sent', ?)
        ''', (inv_no, client_name, project_name, json.dumps(items), subtotal, tax_rate, tax_amount, discount, total, due_date, notes))
        conn.commit()
        audit_log(user['name'], "Issued Invoice", "invoices", inv_no, new_val=f"Rs. {total}")
        conn.close()
        return jsonify({"success": True, "message": "Invoice issued.", "invoice_no": inv_no})

@app.route('/api/workspace/hr/attendance', methods=['GET', 'POST'])
def workspace_attendance():
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        if user['role'] in ['CEO', 'Manager']:
            cursor.execute("SELECT * FROM attendance ORDER BY id DESC LIMIT 50")
        else:
            cursor.execute("SELECT * FROM attendance WHERE emp_name LIKE ? ORDER BY id DESC LIMIT 30", (f"%{user['name']}%",))
        logs = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "attendance": logs})

    elif request.method == 'POST':
        action_type = request.json.get('action', 'clock_in') if request.json else 'clock_in'
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        now_time = datetime.datetime.now().strftime('%I:%M %p')

        cursor.execute("SELECT * FROM attendance WHERE emp_name LIKE ? AND date = ?", (f"%{user['name']}%", today_str))
        record = cursor.fetchone()

        if action_type == 'clock_in':
            if record:
                conn.close()
                return jsonify({"success": False, "error": "Already clocked in today."}), 400
            cursor.execute('''
                INSERT INTO attendance (emp_id, emp_name, date, clock_in, status)
                VALUES (?, ?, ?, ?, 'Present')
            ''', (user.get('emp_code', f"EMP-{user['id']}"), user['name'], today_str, now_time))
            conn.commit()
            audit_log(user['name'], "Clocked In", "attendance", today_str)
            conn.close()
            return jsonify({"success": True, "message": f"Clocked in at {now_time}."})

        elif action_type == 'clock_out':
            if not record:
                conn.close()
                return jsonify({"success": False, "error": "You must clock in first."}), 400
            cursor.execute('''
                UPDATE attendance SET clock_out = ?, total_hours = 8.5 WHERE id = ?
            ''', (now_time, record['id']))
            conn.commit()
            audit_log(user['name'], "Clocked Out", "attendance", today_str)
            conn.close()
            return jsonify({"success": True, "message": f"Clocked out at {now_time} (8.5 hrs)."})

@app.route('/api/workspace/hr/leave', methods=['GET', 'POST', 'PUT'])
def workspace_leave():
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        if user['role'] in ['CEO', 'Manager']:
            cursor.execute("SELECT * FROM leave_requests ORDER BY id DESC")
        else:
            cursor.execute("SELECT * FROM leave_requests WHERE emp_name LIKE ? ORDER BY id DESC", (f"%{user['name']}%",))
        leaves = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "leaves": leaves})

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        leave_type = data.get('leave_type', 'Casual')
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')
        reason = data.get('reason', '').strip()

        if not start_date or not end_date or not reason:
            conn.close()
            return jsonify({"success": False, "error": "Dates and reason required."}), 400

        cursor.execute('''
            INSERT INTO leave_requests (emp_id, emp_name, leave_type, start_date, end_date, reason, status)
            VALUES (?, ?, ?, ?, ?, ?, 'Pending')
        ''', (user.get('emp_code', f"EMP-{user['id']}"), user['name'], leave_type, start_date, end_date, reason))
        conn.commit()
        audit_log(user['name'], "Applied For Leave", "leave_requests", f"{start_date} to {end_date}")
        create_notification(1, "New Leave Request", f"{user['name']} applied for {leave_type} leave", "tab-leave", "approval", "Manager")
        conn.close()
        return jsonify({"success": True, "message": "Leave submitted."})

    elif request.method == 'PUT':
        if user['role'] not in ['CEO', 'Manager']:
            conn.close()
            return jsonify({"success": False, "error": "Permission denied."}), 403

        data = request.get_json(silent=True) or {}
        leave_id = data.get('leave_id')
        action = data.get('action', 'Approved')
        review_notes = data.get('review_notes', '')

        cursor.execute('''
            UPDATE leave_requests SET status = ?, reviewed_by = ?, review_notes = ? WHERE id = ?
        ''', (action, user['name'], review_notes, leave_id))
        conn.commit()
        audit_log(user['name'], f"Leave {action}", "leave_requests", leave_id)
        conn.close()
        return jsonify({"success": True, "message": f"Leave marked {action}."})

@app.route('/api/workspace/meetings', methods=['GET', 'POST'])
def workspace_meetings():
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM meetings ORDER BY meeting_date ASC")
        meetings = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "meetings": meetings})

    elif request.method == 'POST':
        if user['role'] not in ['CEO', 'Manager']:
            conn.close()
            return jsonify({"success": False, "error": "Permission denied."}), 403

        data = request.get_json(silent=True) or {}
        title = data.get('title', '').strip()
        meeting_date = data.get('meeting_date', '')
        meeting_time = data.get('meeting_time', '')
        location_link = data.get('location_link', 'Google Meet / Zoom')
        agenda = data.get('agenda', '')
        participants = data.get('participants', [])
        action_items = data.get('action_items', [])

        if not title or not meeting_date:
            conn.close()
            return jsonify({"success": False, "error": "Title and date required."}), 400

        cursor.execute('''
            INSERT INTO meetings (title, organizer_id, organizer_name, participants_json, meeting_date, meeting_time, location_link, agenda, action_items_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, user['id'], user['name'], json.dumps(participants), meeting_date, meeting_time, location_link, agenda, json.dumps(action_items)))
        conn.commit()
        audit_log(user['name'], "Scheduled Meeting", "meetings", title)
        conn.close()
        return jsonify({"success": True, "message": "Meeting scheduled."})

@app.route('/api/workspace/hr/interns', methods=['GET'])
def workspace_interns():
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM internship_details ORDER BY id ASC")
    interns = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "interns": interns})

@app.route('/api/workspace/hr/performance', methods=['GET'])
def workspace_performance():
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM performance_reviews ORDER BY id DESC")
    reviews = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "reviews": reviews})

@app.route('/api/workspace/announcements', methods=['GET', 'POST'])
def workspace_announcements():
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM announcements ORDER BY id DESC LIMIT 20")
        announcements = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "announcements": announcements})

    elif request.method == 'POST':
        if user['role'] not in ['CEO', 'Manager']:
            conn.close()
            return jsonify({"success": False, "error": "Permission denied."}), 403

        data = request.get_json(silent=True) or {}
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        target = data.get('target_audience', 'All')
        priority = data.get('priority', 'Normal')

        if not title or not content:
            conn.close()
            return jsonify({"success": False, "error": "Title and content required."}), 400

        cursor.execute('''
            INSERT INTO announcements (title, content, target_audience, priority, author_name, author_role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, content, target, priority, user['name'], user['role']))
        conn.commit()
        audit_log(user['name'], "Published Announcement", "announcements", title)
        conn.close()
        return jsonify({"success": True, "message": "Announcement published."})

@app.route('/api/workspace/notifications', methods=['GET', 'PUT'])
def workspace_notifications():
    user, err = require_auth()
    if err: return err
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute('''
            SELECT * FROM notifications 
            WHERE user_id = ? OR user_role = ? OR user_role = 'All' OR user_id = 0
            ORDER BY id DESC LIMIT 25
        ''', (user['id'], user['role']))
        notifications = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "notifications": notifications})

    elif request.method == 'PUT':
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ? OR user_role = ?", (user['id'], user['role']))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Marked read."})

@app.route('/api/workspace/audit-logs', methods=['GET'])
def workspace_audit_logs():
    user, err = require_auth(['CEO', 'Manager'])
    if err: return err
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100")
    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "audit_logs": logs})

@app.route('/api/workspace/search', methods=['GET'])
def workspace_global_search():
    user, err = require_auth()
    if err: return err

    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify({"success": True, "results": []})

    conn = get_db()
    cursor = conn.cursor()
    term = f"%{q}%"
    results = []

    # Search People
    cursor.execute("SELECT id, emp_code, name, role, department, designation FROM users WHERE name LIKE ? OR username LIKE ? OR emp_code LIKE ? OR department LIKE ?", (term, term, term, term))
    for r in cursor.fetchall():
        results.append({"type": "People", "id": str(r['id']), "title": f"{r['name']} ({r['emp_code']})", "subtitle": f"{r['role']} • {r['department']}", "tab": "tab-team"})

    # Search Tasks
    cursor.execute("SELECT task_id, title, status, project_name FROM tasks WHERE title LIKE ? OR task_id LIKE ? OR description LIKE ? OR tags LIKE ?", (term, term, term, term))
    for r in cursor.fetchall():
        results.append({"type": "Task", "id": r['task_id'], "title": f"[{r['task_id']}] {r['title']}", "subtitle": f"{r['project_name']} • {r['status']}", "tab": "tab-tasks"})

    # Search Projects
    cursor.execute("SELECT project_id, name, client_name, status FROM projects WHERE name LIKE ? OR project_id LIKE ? OR description LIKE ?", (term, term, term))
    for r in cursor.fetchall():
        results.append({"type": "Project", "id": r['project_id'], "title": r['name'], "subtitle": f"{r['client_name']} • {r['status']}", "tab": "tab-projects"})

    # Search Clients
    if user['role'] in ['CEO', 'Manager']:
        cursor.execute("SELECT client_id, company_name, contact_person, status FROM clients WHERE company_name LIKE ? OR contact_person LIKE ? OR client_id LIKE ?", (term, term, term))
        for r in cursor.fetchall():
            results.append({"type": "Client", "id": r['client_id'], "title": r['company_name'], "subtitle": f"Contact: {r['contact_person']} • {r['status']}", "tab": "tab-clients"})

        cursor.execute("SELECT invoice_no, client_name, total, status FROM invoices WHERE invoice_no LIKE ? OR client_name LIKE ?", (term, term))
        for r in cursor.fetchall():
            results.append({"type": "Invoice", "id": r['invoice_no'], "title": f"Invoice {r['invoice_no']}", "subtitle": f"{r['client_name']} • Rs. {r['total']}", "tab": "tab-invoices"})

    conn.close()
    return jsonify({"success": True, "results": results[:20]})

@app.route('/api/workspace/ai/query', methods=['POST'])
def workspace_ai_query():
    user, err = require_auth()
    if err: return err

    data = request.get_json(silent=True) or {}
    query = data.get('query', '').strip().lower()
    if not query:
        return jsonify({"success": False, "error": "Query cannot be empty."}), 400

    conn = get_db()
    cursor = conn.cursor()
    role = user['role']
    name = user['name']
    response_text = ""

    if "task" in query and ("my" in query or "today" in query or "do" in query):
        cursor.execute("SELECT task_id, title, priority, deadline, status FROM tasks WHERE assigned_to_id = ? AND status NOT IN ('Completed', 'Approved')", (user['id'],))
        tasks = cursor.fetchall()
        if tasks:
            task_list = "\n".join([f"- [{t['task_id']}] {t['title']} (Priority: {t['priority']}, Deadline: {t['deadline']}, Status: {t['status']})" for t in tasks])
            response_text = f"Hello {name}, you currently have {len(tasks)} active tasks assigned to you:\n\n{task_list}\n\nYou can update status or start your time tracker anytime."
        else:
            response_text = f"All clear, {name}! You have zero pending tasks assigned for today."

    elif "overdue" in query:
        if role in ['CEO', 'Manager']:
            cursor.execute("SELECT task_id, title, assigned_to_name, deadline FROM tasks WHERE deadline < date('now') AND status NOT IN ('Completed', 'Approved')")
        else:
            cursor.execute("SELECT task_id, title, assigned_to_name, deadline FROM tasks WHERE assigned_to_id = ? AND deadline < date('now') AND status NOT IN ('Completed', 'Approved')", (user['id'],))
        overdue = cursor.fetchall()
        if overdue:
            od_list = "\n".join([f"- [{t['task_id']}] {t['title']} (Assignee: {t['assigned_to_name']}, Deadline was {t['deadline']})" for t in overdue])
            response_text = f"Attention Required: Found {len(overdue)} overdue task(s):\n\n{od_list}"
        else:
            response_text = "Zero tasks are currently overdue. All project milestones are on schedule."

    elif "workload" in query or "team" in query:
        if role not in ['CEO', 'Manager']:
            response_text = "Access Restricted: Team workload analytics are reserved for Managers and the CEO."
        else:
            cursor.execute("SELECT assigned_to_name, COUNT(*) as task_count FROM tasks WHERE status NOT IN ('Completed', 'Approved') GROUP BY assigned_to_name")
            wl = cursor.fetchall()
            wl_str = "\n".join([f"- {r['assigned_to_name']}: {r['task_count']} active tasks" for r in wl])
            response_text = f"Current Team Workload Distribution:\n\n{wl_str}\n\nOverall engineering capacity is operating at ~78% bandwidth."

    elif "summary" in query or "health" in query or "company" in query:
        if role != 'CEO':
            response_text = f"Company operations are progressing normally across active client milestones."
        else:
            cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'Active'")
            act_p = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Completed'")
            cmp_t = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status = 'Paid'")
            rev = cursor.fetchone()[0]
            response_text = f"Executive Company Briefing (CEO Overview):\n\n- Active Client Projects: {act_p}\n- Total Completed Deliverables: {cmp_t}\n- Realized Revenue: Rs. {rev:,.2f}\n- Milestone On-Time Rate: 92.4%\n- Client Satisfaction Rating: 4.9 / 5.0\n\nAll cloud infrastructure nodes and database clusters are operating in green health."

    elif "invoice" in query or "revenue" in query or "finance" in query:
        if role != 'CEO':
            response_text = "Access Restricted: Financial and invoice data is strictly accessible to the CEO."
        else:
            cursor.execute("SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status = 'Paid'")
            paid = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status IN ('Sent', 'Draft')")
            pending = cursor.fetchone()[0]
            response_text = f"Financial Snapshot:\n\n- Collected Revenue: Rs. {paid:,.2f}\n- Pending Receivables: Rs. {pending:,.2f}\n- Cashflow Status: Balanced across all enterprise accounts."

    else:
        response_text = f"Hello {name}. I am Kapate AI, your workspace assistant. You can ask queries regarding:\n- What are my tasks today?\n- Which tasks are overdue?\n- Summarize team workload\n- Executive company summary (CEO)\n- Financial snapshot (CEO)"

    conn.close()
    return jsonify({"success": True, "response": response_text})

# ==============================================================================
# PUBLIC WEBSITE ENDPOINTS
# ==============================================================================

@app.route('/api/inquiries', methods=['POST'])
def submit_public_inquiry():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    service = data.get('service', 'Custom Software Development')
    budget = data.get('budget', '')
    timeline = data.get('timeline', '')
    message = data.get('message', '')

    if not name or not email or not phone:
        return jsonify({"success": False, "error": "Name, email, and phone number are required."}), 400

    conn = get_db()
    cursor = conn.cursor()
    ref_num = f"KC-{datetime.datetime.now().year}-{random.randint(1000, 9999)}"

    try:
        cursor.execute('''
            INSERT INTO inquiries (reference_num, reference_number, name, email, phone, service, budget, timeline, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ref_num, ref_num, name, email, phone, service, budget, timeline, message))
    except Exception:
        cursor.execute('''
            INSERT INTO inquiries (name, email, phone, service, budget, timeline, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, phone, service, budget, timeline, message))
    conn.commit()
    conn.close()

    create_notification(1, "New Public Web Inquiry", f"From {name} ({email}) for {service} [Ref: {ref_num}]", "tab-clients", "alert", "CEO")
    audit_log("Public Visitor", "Submitted Web Inquiry", "inquiries", ref_num, new_val=f"{name} - {service}")

    return jsonify({"success": True, "reference_num": ref_num, "message": "Inquiry submitted successfully."})

@app.route('/api/reviews', methods=['GET', 'POST'])
def public_reviews():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM reviews WHERE status = 'Approved' ORDER BY id DESC")
        reviews = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "reviews": reviews})

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        role = data.get('role', 'Client')
        company = data.get('company', '')
        rating = int(data.get('rating', 5))
        comment = data.get('comment', '').strip()

        if not name or not comment:
            conn.close()
            return jsonify({"success": False, "error": "Name and review comment are required."}), 400

        cursor.execute('''
            INSERT INTO reviews (name, role, company, rating, comment, status)
            VALUES (?, ?, ?, ?, ?, 'Approved')
        ''', (name, role, company, rating, comment))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Review published successfully."})

# ==============================================================================
# WORKSPACE & STATIC ROUTE HANDLERS
# ==============================================================================

@app.route('/workspace')
@app.route('/workspace/')
def serve_workspace():
    return send_from_directory('.', 'workspace.html')

@app.route('/erp.html')
@app.route('/admin.html')
def redirect_to_workspace():
    return redirect('/workspace.html', code=301)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static_files(filename):
    return send_from_directory('.', filename)

# Initialize on boot
load_config()
init_database()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    print(f"Kapate Consultancy Server running on http://0.0.0.0:{port}")
    app.run(port=port, host='0.0.0.0', debug=True)
