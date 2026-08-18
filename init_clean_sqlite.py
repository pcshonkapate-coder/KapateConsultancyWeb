import sqlite3
import os
from werkzeug.security import generate_password_hash

SQLITE_DB = 'inquiries.db'
if os.path.exists(SQLITE_DB):
    os.remove(SQLITE_DB)

conn = sqlite3.connect(SQLITE_DB)
cur = conn.cursor()

# Run all table creates
tables = [
    '''CREATE TABLE inquiries (
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
    )''',
    '''CREATE TABLE reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT,
        company TEXT,
        rating INTEGER DEFAULT 5,
        comment TEXT NOT NULL,
        status TEXT DEFAULT 'Approved',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_code TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT NOT NULL,
        designation TEXT,
        manager_name TEXT DEFAULT 'Shon Kapate',
        status TEXT DEFAULT 'Active',
        phone TEXT,
        avatar_url TEXT,
        joining_date TEXT DEFAULT '2026-01-12',
        employment_type TEXT DEFAULT 'Full-Time',
        dob TEXT DEFAULT '1996-05-14',
        address TEXT DEFAULT 'Pune, Maharashtra, India',
        emergency_contact TEXT DEFAULT '+91 8421174957',
        basic_pay REAL DEFAULT 250000,
        performance_score REAL DEFAULT 5.0,
        last_active TEXT DEFAULT 'Just now',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        head_name TEXT NOT NULL,
        head_id INTEGER,
        description TEXT,
        budget REAL DEFAULT 1000000,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE employee_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        author_name TEXT NOT NULL,
        author_role TEXT NOT NULL,
        note_text TEXT NOT NULL,
        is_confidential INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE employee_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,
        doc_name TEXT NOT NULL,
        file_size TEXT DEFAULT '450 KB',
        file_url TEXT DEFAULT '',
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE roles_permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        permission_key TEXT UNIQUE NOT NULL,
        permission_label TEXT NOT NULL,
        category TEXT NOT NULL,
        ceo_perm TEXT DEFAULT 'Full',
        manager_perm TEXT DEFAULT 'Team',
        employee_perm TEXT DEFAULT 'Own',
        intern_perm TEXT DEFAULT 'Restricted'
    )''',
    '''CREATE TABLE projects (
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
    )''',
    '''CREATE TABLE milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'Pending',
        due_date TEXT,
        order_index INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE tasks (
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
    )''',
    '''CREATE TABLE task_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        user_id INTEGER,
        user_name TEXT NOT NULL,
        user_role TEXT NOT NULL,
        comment TEXT NOT NULL,
        attachment_name TEXT,
        attachment_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE task_time_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        user_id INTEGER,
        user_name TEXT NOT NULL,
        hours REAL NOT NULL,
        entry_date TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE internal_messages (
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
    )''',
    '''CREATE TABLE chat_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        channel_type TEXT DEFAULT 'general',
        members_json TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT NOT NULL,
        sender_id INTEGER,
        sender_name TEXT NOT NULL,
        sender_role TEXT NOT NULL,
        message TEXT NOT NULL,
        attachment_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        user_role TEXT DEFAULT '',
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        link_tab TEXT DEFAULT 'tab-dashboard',
        type TEXT DEFAULT 'task',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE company_files (
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
    )''',
    '''CREATE TABLE clients (
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
    )''',
    '''CREATE TABLE proposals (
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
    )''',
    '''CREATE TABLE invoices (
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
    )''',
    '''CREATE TABLE expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        recorded_by TEXT NOT NULL,
        receipt_url TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT NOT NULL,
        emp_name TEXT NOT NULL,
        date TEXT NOT NULL,
        clock_in TEXT,
        clock_out TEXT,
        total_hours REAL DEFAULT 0,
        status TEXT DEFAULT 'Present',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE leave_requests (
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
    )''',
    '''CREATE TABLE meetings (
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
    )''',
    '''CREATE TABLE performance_reviews (
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
    )''',
    '''CREATE TABLE internship_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intern_id TEXT UNIQUE NOT NULL,
        intern_name TEXT NOT NULL,
        mentor_id INTEGER,
        mentor_name TEXT NOT NULL,
        department TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        progress_percent INTEGER DEFAULT 0,
        modules_json TEXT DEFAULT '[]',
        feedback TEXT,
        certificate_status TEXT DEFAULT 'In Progress',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        target_audience TEXT DEFAULT 'All',
        priority TEXT DEFAULT 'Normal',
        author_name TEXT NOT NULL,
        author_role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE audit_logs (
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
    )'''
]

for t in tables:
    cur.execute(t)

ceo_pwd = generate_password_hash("Kapate@Ceo2026")
cur.execute('''
    INSERT INTO users (emp_code, username, email, password_hash, name, role, department, designation, manager_name, status, phone, basic_pay, performance_score)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', ('EMP-001', 'ceo', 'office.kapateconsultancy@gmail.com', ceo_pwd, 'Shon Kapate', 'CEO', 'Executive Leadership', 'Chief Executive Officer', 'Board of Directors', 'Active', '+91 8421174957', 250000, 5.0))

departments = [
    ('Executive Leadership', 'Shon Kapate', 1, 'Strategic planning and corporate governance', 2500000),
    ('Software & Web Engineering', 'Shon Kapate', 1, 'Full-stack web, SaaS and mobile app engineering', 1500000),
    ('AI & Machine Learning', 'Shon Kapate', 1, 'Deep learning models, NLP, and intelligent business automation', 2000000),
    ('Operations & HR', 'Shon Kapate', 1, 'Talent acquisition, workforce development, and compliance', 800000),
    ('Sales & Client Relations', 'Shon Kapate', 1, 'Enterprise sales, client CRM and consulting partnerships', 1200000)
]
for d in departments:
    cur.execute('INSERT INTO departments (name, head_name, head_id, description, budget) VALUES (?, ?, ?, ?, ?)', d)

roles_perms = [
    ('view_all_employees', 'View Full Organization Directory', 'People', 'Full', 'Team', 'Own', 'Restricted'),
    ('edit_salaries', 'Edit Compensation & Payroll', 'Finance', 'Full', 'Restricted', 'Restricted', 'Restricted'),
    ('ceo_task_override', 'CEO Master Task Override & Reassignment', 'Tasks', 'Full', 'Restricted', 'Restricted', 'Restricted'),
    ('view_financial_invoices', 'Access Financial Billing & Invoices', 'Finance', 'Full', 'ViewOnly', 'Restricted', 'Restricted'),
    ('approve_leaves', 'Approve / Reject Leave Requests', 'Operations', 'Full', 'Team', 'Restricted', 'Restricted'),
    ('manage_departments', 'Create & Manage Departments', 'Organization', 'Full', 'Restricted', 'Restricted', 'Restricted'),
    ('view_audit_logs', 'Access Immutable Audit Trails', 'Security', 'Full', 'Restricted', 'Restricted', 'Restricted'),
    ('manage_company_files', 'Upload & Delete Company Documents', 'Files', 'Full', 'Team', 'Own', 'Restricted'),
    ('broadcast_announcements', 'Publish Company Announcements', 'Communications', 'Full', 'Team', 'Restricted', 'Restricted')
]
for rp in roles_perms:
    cur.execute('INSERT INTO roles_permissions (permission_key, permission_label, category, ceo_perm, manager_perm, employee_perm, intern_perm) VALUES (?, ?, ?, ?, ?, ?, ?)', rp)

cur.execute('INSERT INTO chat_channels (channel_id, name, channel_type, members_json) VALUES (?, ?, ?, ?)', ('chan-general', 'General Team Channel', 'general', '["all"]'))

conn.commit()
conn.close()
print("Clean Local SQLite database ready!")
