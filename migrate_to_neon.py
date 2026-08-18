import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

NEON_URL = "postgresql://neondb_owner:npg_8b4SBlRExyuo@ep-odd-lake-aydjgg9n.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"

print("1. Connecting to Neon PostgreSQL...")
pg_conn = psycopg2.connect(NEON_URL)
pg_cur = pg_conn.cursor()
print("   Connected successfully!")

# Define PostgreSQL DDL
tables_ddl = [
    '''CREATE TABLE IF NOT EXISTS inquiries (
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
    '''CREATE TABLE IF NOT EXISTS reviews (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT,
        company TEXT,
        rating INTEGER DEFAULT 5,
        comment TEXT NOT NULL,
        status TEXT DEFAULT 'Approved',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE IF NOT EXISTS users (
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
        emergency_contact TEXT DEFAULT '+91 9822001100 (Parent)',
        basic_pay REAL DEFAULT 50000,
        performance_score REAL DEFAULT 4.7,
        last_active TEXT DEFAULT 'Just now',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE IF NOT EXISTS departments (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        head_name TEXT NOT NULL,
        head_id INTEGER,
        description TEXT,
        budget REAL DEFAULT 1000000,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE IF NOT EXISTS employee_notes (
        id SERIAL PRIMARY KEY,
        emp_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        author_name TEXT NOT NULL,
        author_role TEXT NOT NULL,
        note_text TEXT NOT NULL,
        is_confidential INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE IF NOT EXISTS employee_documents (
        id SERIAL PRIMARY KEY,
        emp_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,
        doc_name TEXT NOT NULL,
        file_size TEXT DEFAULT '450 KB',
        file_url TEXT DEFAULT '',
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE IF NOT EXISTS roles_permissions (
        id SERIAL PRIMARY KEY,
        permission_key TEXT UNIQUE NOT NULL,
        permission_label TEXT NOT NULL,
        category TEXT NOT NULL,
        ceo_perm TEXT DEFAULT 'Full',
        manager_perm TEXT DEFAULT 'Team',
        employee_perm TEXT DEFAULT 'Own',
        intern_perm TEXT DEFAULT 'Restricted'
    )''',
    '''CREATE TABLE IF NOT EXISTS projects (
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
    '''CREATE TABLE IF NOT EXISTS milestones (
        id SERIAL PRIMARY KEY,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'Pending',
        due_date TEXT,
        order_index INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE IF NOT EXISTS tasks (
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
    '''CREATE TABLE IF NOT EXISTS task_comments (
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
    '''CREATE TABLE IF NOT EXISTS task_time_entries (
        id SERIAL PRIMARY KEY,
        task_id TEXT NOT NULL,
        user_id INTEGER,
        user_name TEXT NOT NULL,
        hours REAL NOT NULL,
        entry_date TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE IF NOT EXISTS internal_messages (
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
    '''CREATE TABLE IF NOT EXISTS chat_channels (
        id SERIAL PRIMARY KEY,
        channel_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        channel_type TEXT DEFAULT 'general',
        members_json TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE IF NOT EXISTS chat_messages (
        id SERIAL PRIMARY KEY,
        channel_id TEXT NOT NULL,
        sender_id INTEGER,
        sender_name TEXT NOT NULL,
        sender_role TEXT NOT NULL,
        message TEXT NOT NULL,
        attachment_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE IF NOT EXISTS notifications (
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
    '''CREATE TABLE IF NOT EXISTS company_files (
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
    '''CREATE TABLE IF NOT EXISTS clients (
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
    '''CREATE TABLE IF NOT EXISTS proposals (
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
    '''CREATE TABLE IF NOT EXISTS invoices (
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
    '''CREATE TABLE IF NOT EXISTS expenses (
        id SERIAL PRIMARY KEY,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        recorded_by TEXT NOT NULL,
        receipt_url TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE IF NOT EXISTS attendance (
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
    '''CREATE TABLE IF NOT EXISTS leave_requests (
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
    '''CREATE TABLE IF NOT EXISTS meetings (
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
    '''CREATE TABLE IF NOT EXISTS performance_reviews (
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
    '''CREATE TABLE IF NOT EXISTS internship_details (
        id SERIAL PRIMARY KEY,
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
    )''',
    '''CREATE TABLE IF NOT EXISTS announcements (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        target_audience TEXT DEFAULT 'All',
        priority TEXT DEFAULT 'Normal',
        author_name TEXT NOT NULL,
        author_role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE IF NOT EXISTS audit_logs (
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

print("2. Creating table schemas on Neon PostgreSQL...")
for ddl in tables_ddl:
    pg_cur.execute(ddl)
pg_conn.commit()
print("   All 28 table schemas created!")

# Migrate data from SQLite
sq_conn = sqlite3.connect('inquiries.db')
sq_conn.row_factory = sqlite3.Row
sq_cur = sq_conn.cursor()

sq_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [r[0] for r in sq_cur.fetchall()]

print(f"3. Migrating records from SQLite to Neon PostgreSQL...")
for table in tables:
    sq_cur.execute(f"SELECT * FROM {table}")
    rows = sq_cur.fetchall()
    if not rows:
        continue
    
    dict_rows = [dict(r) for r in rows]
    cols = list(dict_rows[0].keys())
    cols_str = ", ".join([f'"{c}"' for c in cols])
    placeholders = ", ".join(["%s"] * len(cols))

    pg_cur.execute(f'TRUNCATE TABLE "{table}" CASCADE;')
    insert_sql = f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders})'
    
    for row in dict_rows:
        vals = [row[c] for c in cols]
        pg_cur.execute(insert_sql, vals)

    pg_conn.commit()
    print(f"   - Synced {table}: {len(rows)} records.")

pg_conn.close()
sq_conn.close()
print("\n🎉 COMPLETE: Neon Cloud PostgreSQL Database is fully provisioned and populated!")
