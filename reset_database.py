import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash

NEON_URL = "postgresql://neondb_owner:npg_8b4SBlRExyuo@ep-odd-lake-aydjgg9n.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"
SQLITE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inquiries.db')

tables_ddl_pg = [
    '''DROP SCHEMA public CASCADE; CREATE SCHEMA public;''',
    '''CREATE TABLE inquiries (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT,
        company TEXT,
        rating INTEGER DEFAULT 5,
        comment TEXT NOT NULL,
        status TEXT DEFAULT 'Approved',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE users (
        id SERIAL PRIMARY KEY,
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
        basic_pay REAL DEFAULT 150000,
        performance_score REAL DEFAULT 5.0,
        last_active TEXT DEFAULT 'Just now',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE departments (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        head_name TEXT NOT NULL,
        head_id INTEGER,
        description TEXT,
        budget REAL DEFAULT 1000000,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE employee_notes (
        id SERIAL PRIMARY KEY,
        emp_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        author_name TEXT NOT NULL,
        author_role TEXT NOT NULL,
        note_text TEXT NOT NULL,
        is_confidential INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE employee_documents (
        id SERIAL PRIMARY KEY,
        emp_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,
        doc_name TEXT NOT NULL,
        file_size TEXT DEFAULT '450 KB',
        file_url TEXT DEFAULT '',
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE roles_permissions (
        id SERIAL PRIMARY KEY,
        permission_key TEXT UNIQUE NOT NULL,
        permission_label TEXT NOT NULL,
        category TEXT NOT NULL,
        ceo_perm TEXT DEFAULT 'Full',
        manager_perm TEXT DEFAULT 'Team',
        employee_perm TEXT DEFAULT 'Own',
        intern_perm TEXT DEFAULT 'Restricted'
    )''',
    '''CREATE TABLE projects (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'Pending',
        due_date TEXT,
        order_index INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE tasks (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        task_id TEXT NOT NULL,
        user_id INTEGER,
        user_name TEXT NOT NULL,
        hours REAL NOT NULL,
        entry_date TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE internal_messages (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        channel_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        channel_type TEXT DEFAULT 'general',
        members_json TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE chat_messages (
        id SERIAL PRIMARY KEY,
        channel_id TEXT NOT NULL,
        sender_id INTEGER,
        sender_name TEXT NOT NULL,
        sender_role TEXT NOT NULL,
        message TEXT NOT NULL,
        attachment_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE notifications (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        recorded_by TEXT NOT NULL,
        receipt_url TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE attendance (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        target_audience TEXT DEFAULT 'All',
        priority TEXT DEFAULT 'Normal',
        author_name TEXT NOT NULL,
        author_role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE audit_logs (
        id SERIAL PRIMARY KEY,
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

def seed_fresh_database(cursor, is_postgres=True):
    ph = "%s" if is_postgres else "?"
    
    # 1. Clean Core Users (CEO only or Initial Core Staff)
    ceo_pwd = generate_password_hash("Kapate@Ceo2026")
    cursor.execute(f'''
        INSERT INTO users (emp_code, username, email, password_hash, name, role, department, designation, manager_name, status, phone, basic_pay, performance_score)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    ''', ('EMP-001', 'ceo', 'office.kapateconsultancy@gmail.com', ceo_pwd, 'Shon Kapate', 'CEO', 'Executive Leadership', 'Chief Executive Officer', 'Board of Directors', 'Active', '+91 8421174957', 250000, 5.0))

    # 2. Fresh Core Departments
    departments = [
        ('Executive Leadership', 'Shon Kapate', 1, 'Strategic planning and corporate governance', 2500000),
        ('Software & Web Engineering', 'Shon Kapate', 1, 'Full-stack web, SaaS and mobile app engineering', 1500000),
        ('AI & Machine Learning', 'Shon Kapate', 1, 'Deep learning models, NLP, and intelligent business automation', 2000000),
        ('Operations & HR', 'Shon Kapate', 1, 'Talent acquisition, workforce development, and compliance', 800000),
        ('Sales & Client Relations', 'Shon Kapate', 1, 'Enterprise sales, client CRM and consulting partnerships', 1200000)
    ]
    for d in departments:
        cursor.execute(f'''
            INSERT INTO departments (name, head_name, head_id, description, budget)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
        ''', d)

    # 3. Standard Roles & Permissions Matrix
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
        cursor.execute(f'''
            INSERT INTO roles_permissions (permission_key, permission_label, category, ceo_perm, manager_perm, employee_perm, intern_perm)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        ''', rp)

    # 4. Default General Chat Channel
    cursor.execute(f'''
        INSERT INTO chat_channels (channel_id, name, channel_type, members_json)
        VALUES ({ph}, {ph}, {ph}, {ph})
    ''', ('chan-general', 'General Team Channel', 'general', '["all"]'))

    # 5. Initial Welcome Announcement
    cursor.execute(f'''
        INSERT INTO announcements (title, content, target_audience, priority, author_name, author_role)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    ''', (
        'Welcome to Kapate Workspace',
        'Welcome to the Kapate Consultancy centralized operating platform. Use this workspace for project delivery, task reviews, client billing, and real-time collaboration.',
        'All',
        'High',
        'Shon Kapate',
        'CEO'
    ))

def reset_all_databases():
    print("1. Clearing & resetting Neon Cloud PostgreSQL Database...")
    try:
        pg_conn = psycopg2.connect(NEON_URL)
        pg_cur = pg_conn.cursor()
        for ddl in tables_ddl_pg:
            pg_cur.execute(ddl)
        pg_conn.commit()

        print("2. Seeding clean initial state on Neon Cloud Database...")
        seed_fresh_database(pg_cur, is_postgres=True)
        pg_conn.commit()
        pg_conn.close()
        print("   Neon Cloud Database has been freshly initialized and cleaned!")
    except Exception as e:
        print(f"   Neon DB Reset error: {e}")

    print("\n3. Clearing & resetting local SQLite database...")
    try:
        if os.path.exists(SQLITE_DB):
            os.remove(SQLITE_DB)
        from server import init_database
        # Temporarily clear DATABASE_URL to initialize SQLite
        old_env = os.environ.get('DATABASE_URL')
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
        
        sq_conn = sqlite3.connect(SQLITE_DB)
        sq_cur = sq_conn.cursor()
        
        # Run standard SQLite DDL from server
        init_database()
        
        # Clear mock entries and seed pristine state
        for t in ['inquiries', 'reviews', 'tasks', 'projects', 'clients', 'invoices', 'attendance', 'leave_requests', 'meetings', 'employee_notes', 'employee_documents', 'audit_logs']:
            sq_cur.execute(f"DELETE FROM {t}")
        
        sq_cur.execute("DELETE FROM users")
        sq_cur.execute("DELETE FROM departments")
        sq_cur.execute("DELETE FROM roles_permissions")
        sq_cur.execute("DELETE FROM chat_channels")
        sq_cur.execute("DELETE FROM announcements")

        seed_fresh_database(sq_cur, is_postgres=False)
        sq_conn.commit()
        sq_conn.close()
        
        if old_env:
            os.environ['DATABASE_URL'] = old_env

        print("   Local SQLite Database has been freshly initialized and cleaned!")
    except Exception as e:
        print(f"   SQLite Reset error: {e}")

    print("\nDATABASE RESET COMPLETE: Both Neon Cloud DB and Local DB are brand new, clean, and ready for production!")

if __name__ == '__main__':
    reset_all_databases()
