import os
import sqlite3
import json
import random
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, send_from_directory
from twilio.rest import Client

app = Flask(__name__, static_folder='.', static_url_path='')

# Configuration variables
CONFIG_FILE = '/tmp/config.json' if os.environ.get('VERCEL') else 'config.json'
AUTH_TOKEN = "Bearer kapate-admin-secure-token-98765"

if os.environ.get('VERCEL'):
    DB_FILE = '/tmp/inquiries.db'
    if not os.path.exists(DB_FILE) and os.path.exists('inquiries.db'):
        import shutil
        shutil.copy('inquiries.db', DB_FILE)
else:
    DB_FILE = 'inquiries.db'


def generate_unique_id(prefix):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    table_map = {
        "KC-EMP": "employees",
        "KC-CLI": "clients",
        "KC-LEAD": "leads",
        "KC-OPP": "opportunities",
        "KC-PRJ": "projects",
        "KC-MIL": "milestones",
        "KC-WT": "work_tokens",
        "KC-CR": "change_requests",
        "KC-PRO": "proposals",
        "KC-CON": "contracts",
        "KC-INV": "invoices",
        "KC-PAY": "payments",
        "KC-EXP": "expenses",
        "KC-TKT": "tickets",
        "KC-PO": "purchase_orders",
        "KC-APP": "approvals"
    }
    
    table = table_map.get(prefix, "activity_logs")
    count = 101
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count += cursor.fetchone()[0]
    except Exception:
        pass
    conn.close()
    return f"{prefix}-{count:05d}"


def audit_log_event(user_name, action, entity, entity_id="", old_val="", new_val="", ip_addr="127.0.0.1"):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            INSERT INTO audit_logs (user_name, action, entity, entity_id, old_value, new_value, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_name, action, entity, str(entity_id), str(old_val), str(new_val), ip_addr))
        
        cursor.execute('''
            INSERT INTO activity_logs (user_name, action, details, icon)
            VALUES (?, ?, ?, 'shield')
        ''', (user_name, action, f"{entity} #{entity_id} {old_val} -> {new_val}".strip()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Audit log error: {e}")


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
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config
    try:
        with open(CONFIG_FILE, 'r') as f:
            file_config = json.load(f)
            # Ensure SMTP_PASSWORD is not empty
            if not file_config.get("SMTP_PASSWORD"):
                file_config["SMTP_PASSWORD"] = default_config["SMTP_PASSWORD"]
            if not file_config.get("SMTP_EMAIL"):
                file_config["SMTP_EMAIL"] = default_config["SMTP_EMAIL"]
            return file_config
    except Exception as e:
        print(f"Error loading config.json: {e}. Using defaults.")
        return default_config

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            service TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # Safely alter table to add notes column if DB was already created
    try:
        cursor.execute("ALTER TABLE inquiries ADD COLUMN notes TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # Reviews table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            review_text TEXT NOT NULL,
            service TEXT DEFAULT '',
            approved INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Clients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT DEFAULT '',
            company TEXT DEFAULT '',
            tag TEXT DEFAULT 'Lead',
            status TEXT DEFAULT 'Contacted',
            total_spent REAL DEFAULT 0.0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Projects table (Kanban)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            client_name TEXT NOT NULL,
            client_email TEXT DEFAULT '',
            service TEXT NOT NULL,
            budget REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Pending',
            progress INTEGER DEFAULT 0,
            deadline TEXT DEFAULT '',
            tasks_completed INTEGER DEFAULT 0,
            tasks_total INTEGER DEFAULT 5,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Leads table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            service TEXT NOT NULL,
            message TEXT NOT NULL,
            score INTEGER DEFAULT 50,
            priority TEXT DEFAULT 'Warm',
            status TEXT DEFAULT 'New',
            assigned_to TEXT DEFAULT 'Unassigned',
            reminder_date TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Activity Logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT DEFAULT 'System',
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            icon TEXT DEFAULT 'info',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            category TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # OTP codes verification table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS otp_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Employees table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            employment_type TEXT NOT NULL,
            join_date TEXT NOT NULL,
            basic_pay REAL DEFAULT 0.0,
            allowances REAL DEFAULT 0.0,
            deductions REAL DEFAULT 0.0,
            performance_score REAL DEFAULT 100.0
        )
    ''')
    conn.commit()

    # Attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT NOT NULL,
            date TEXT NOT NULL,
            check_in TEXT DEFAULT '',
            check_out TEXT DEFAULT '',
            total_hours REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Present'
        )
    ''')
    conn.commit()

    # Leaves table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            reason TEXT DEFAULT '',
            status TEXT DEFAULT 'Pending'
        )
    ''')
    conn.commit()

    # Payroll table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT NOT NULL,
            month TEXT NOT NULL,
            basic REAL DEFAULT 0.0,
            allowances REAL DEFAULT 0.0,
            deductions REAL DEFAULT 0.0,
            net_salary REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Pending'
        )
    ''')
    conn.commit()

    # Expenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL DEFAULT 0.0,
            date TEXT NOT NULL,
            status TEXT DEFAULT 'Approved'
        )
    ''')
    conn.commit()

    # Recruitments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recruitments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT DEFAULT 'Applied',
            score INTEGER DEFAULT 50
        )
    ''')
    conn.commit()

    # ERP Tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS erp_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            assigned_to TEXT NOT NULL,
            status TEXT DEFAULT 'To Do',
            priority TEXT DEFAULT 'Medium',
            deadline TEXT NOT NULL,
            checklist TEXT DEFAULT '[]'
        )
    ''')
    conn.commit()

    # Invoices table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            client_name TEXT NOT NULL,
            client_email TEXT NOT NULL,
            service TEXT NOT NULL,
            amount REAL DEFAULT 0.0,
            tax_gst REAL DEFAULT 0.0,
            total_amount REAL DEFAULT 0.0,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'Unpaid',
            line_items TEXT DEFAULT '[]'
        )
    ''')
    conn.commit()

    # Timesheets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timesheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT NOT NULL,
            emp_name TEXT NOT NULL,
            project_title TEXT NOT NULL,
            client_name TEXT NOT NULL,
            hours_logged REAL DEFAULT 0.0,
            date TEXT NOT NULL,
            description TEXT DEFAULT '',
            billable_rate REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Approved'
        )
    ''')
    conn.commit()

    # Work Tokens table (KC-WT-00101)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id TEXT UNIQUE NOT NULL,
            project_title TEXT NOT NULL,
            client_name TEXT DEFAULT '',
            milestone_id TEXT DEFAULT '',
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            assigned_by TEXT NOT NULL,
            assigned_to TEXT NOT NULL,
            priority TEXT DEFAULT 'Medium',
            estimated_hours REAL DEFAULT 0.0,
            billable_hours REAL DEFAULT 0.0,
            billing_rate REAL DEFAULT 1500.0,
            deadline TEXT DEFAULT '',
            status TEXT DEFAULT 'Assigned',
            checklist TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Approvals table (Universal Approval Center)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            approval_id TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            requester_name TEXT NOT NULL,
            amount REAL DEFAULT 0.0,
            details TEXT DEFAULT '',
            status TEXT DEFAULT 'Pending',
            approver_name TEXT DEFAULT 'Pending Review',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # GitHub Repositories Manager table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS github_repos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name TEXT UNIQUE NOT NULL,
            repo_url TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            project_title TEXT DEFAULT '',
            assigned_to TEXT DEFAULT '',
            is_private INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Opportunities table (CRM)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opp_id TEXT UNIQUE NOT NULL,
            client_name TEXT NOT NULL,
            title TEXT NOT NULL,
            stage TEXT DEFAULT 'Discovery',
            value REAL DEFAULT 0.0,
            close_date TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Proposals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT UNIQUE NOT NULL,
            client_name TEXT NOT NULL,
            title TEXT NOT NULL,
            scope TEXT DEFAULT '',
            amount REAL DEFAULT 0.0,
            tax_gst REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Sent',
            valid_until TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Contracts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id TEXT UNIQUE NOT NULL,
            client_name TEXT NOT NULL,
            contract_type TEXT DEFAULT 'Consultancy Agreement',
            start_date TEXT DEFAULT '',
            end_date TEXT DEFAULT '',
            value REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Change Requests table (KC-CR-00101)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS change_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cr_id TEXT UNIQUE NOT NULL,
            project_title TEXT NOT NULL,
            client_name TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            impact_hours REAL DEFAULT 0.0,
            additional_cost REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Requested',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Purchase Orders table (KC-PO-00101)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_id TEXT UNIQUE NOT NULL,
            vendor_name TEXT NOT NULL,
            project_title TEXT DEFAULT '',
            amount REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Support Tickets table (KC-TKT-00101)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE NOT NULL,
            client_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            priority TEXT DEFAULT 'Medium',
            sla_hours INTEGER DEFAULT 24,
            status TEXT DEFAULT 'Open',
            assigned_to TEXT DEFAULT 'Unassigned',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Documents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            entity_type TEXT DEFAULT 'Project',
            entity_id TEXT DEFAULT '',
            access_level TEXT DEFAULT 'Internal',
            file_path TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    try:
        cursor.execute("ALTER TABLE erp_tasks ADD COLUMN checklist TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE erp_tasks ADD COLUMN description TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE employees ADD COLUMN password TEXT DEFAULT 'Kapate@123'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE work_tokens ADD COLUMN github_repo TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE work_tokens ADD COLUMN github_pr_link TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE erp_tasks ADD COLUMN github_repo TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE erp_tasks ADD COLUMN github_pr_link TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

# Initialize on load
init_db()

def generate_reference_number():
    year = datetime.datetime.now().year
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    while True:
        # Format: KC-YYYY-XXXX (where XXXX is a random 4-digit number)
        rand_val = random.randint(1000, 9999)
        ref_num = f"KC-{year}-{rand_val}"
        
        # Check uniqueness
        cursor.execute("SELECT 1 FROM inquiries WHERE reference_number = ?", (ref_num,))
        if not cursor.fetchone():
            conn.close()
            return ref_num

def send_confirmation_email(config, recipient_email, recipient_name, ref_num, service, message):
    sender_email = config.get("SMTP_EMAIL")
    sender_password = config.get("SMTP_PASSWORD")
    smtp_server = config.get("SMTP_SERVER")
    smtp_port = config.get("SMTP_PORT")
    
    if not sender_email or not sender_password:
        print("SMTP email or password is empty. Skipping email confirmation.")
        return False
        
    try:
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Inquiry Registered: {ref_num} - Kapate Consultancy"
        msg['From'] = f"Kapate Consultancy <{sender_email}>"
        msg['To'] = recipient_email
        
        # Map service key to readable text
        service_mapping = {
            "webdev": "Website Development",
            "software": "Software & Application Development",
            "aiml": "AI & Machine Learning Solutions",
            "analytics": "Data Analytics & Insights",
            "academic": "College / Final-Year Project Support",
            "cloud": "Cloud Services"
        }
        service_name = service_mapping.get(service, service.capitalize())

        # Email body (HTML)
        html = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Inter', Arial, sans-serif;
                    background-color: #f8fafc;
                    color: #0f172a;
                    margin: 0;
                    padding: 40px 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
                }}
                .header {{
                    background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
                    color: #ffffff;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                    font-weight: 700;
                }}
                .content {{
                    padding: 35px;
                    line-height: 1.6;
                    font-size: 15px;
                }}
                .ref-badge {{
                    display: inline-block;
                    background-color: #ecfeff;
                    color: #0891b2;
                    font-weight: 700;
                    padding: 6px 12px;
                    border-radius: 6px;
                    border: 1px solid #cffafe;
                    font-size: 16px;
                    margin: 15px 0;
                }}
                .summary-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 25px 0;
                }}
                .summary-table td {{
                    padding: 10px;
                    border-bottom: 1px solid #f1f5f9;
                }}
                .summary-table td.label {{
                    font-weight: 600;
                    color: #475569;
                    width: 130px;
                }}
                .footer {{
                    background-color: #f8fafc;
                    padding: 20px 35px;
                    border-top: 1px solid #e2e8f0;
                    font-size: 12px;
                    color: #64748b;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Kapate Consultancy</h1>
                </div>
                <div class="content">
                    <p>Dear {recipient_name},</p>
                    <p>Thank you for submitting your inquiry to Kapate Consultancy. We are excited to collaborate with you. Your request has been successfully registered and assigned the following reference ID:</p>
                    
                    <div class="ref-badge">{ref_num}</div>
                    
                    <p>Our senior technical associates will review your project requirements and reach back to you within 24 hours.</p>
                    
                    <h3>Inquiry Summary</h3>
                    <table class="summary-table">
                        <tr>
                            <td class="label">Service Required</td>
                            <td>{service_name}</td>
                        </tr>
                        <tr>
                            <td class="label">Message Summary</td>
                            <td>{message}</td>
                        </tr>
                    </table>
                    
                    <p>If you have any supplementary documents or additional specifications, feel free to reply directly to this email.</p>
                    <br>
                    <p>Best regards,<br><strong>Kapate Consultancy Team</strong></p>
                </div>
                <div class="footer">
                    <p>Software Engineering &bull; AI &bull; Cloud Infrastructure &bull; Academic Mentorship</p>
                    <p>&copy; 2026 Kapate Consultancy. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        part = MIMEText(html, 'html')
        msg.attach(part)
        
        # Connect and Send
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        print(f"Confirmation email successfully sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"SMTP Error: Failed to send confirmation email to {recipient_email}. Details: {e}")
        return False

# --------------------------------------------------------------------------
# API Routes
# --------------------------------------------------------------------------

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/sitemap.xml')
def sitemap():
    return app.send_static_file('sitemap.xml')

@app.route('/robots.txt')
def robots():
    return app.send_static_file('robots.txt')

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/sw.js')
def service_worker():
    response = app.send_static_file('sw.js')
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Cache-Control'] = 'no-cache'
    return response


@app.route('/api/inquiries', methods=['POST'])
def create_inquiry():
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "No input data provided"}), 400
        
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    service = data.get('service', '').strip()
    message = data.get('message', '').strip()
    
    if not name or not email or not message:
        return jsonify({"success": False, "error": "Missing required fields (name, email, or message)"}), 400
        
    ref_num = generate_reference_number()
    
    try:
        # Insert into SQLite Database (Inquiries)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO inquiries (reference_number, name, email, service, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (ref_num, name, email, service, message))
        inquiry_id = cursor.lastrowid
        
        # Lead scoring calculation
        lead_score = min(95, 50 + (len(message) // 10) + (15 if service in ['aiml', 'cloud', 'software'] else 5))
        priority = "Hot" if lead_score >= 75 else ("Warm" if lead_score >= 55 else "Cold")
        
        # Auto-create Lead record
        cursor.execute('''
            INSERT INTO leads (name, email, service, message, score, priority, status)
            VALUES (?, ?, ?, ?, ?, ?, 'New')
        ''', (name, email, service, message, lead_score, priority))
        
        # Auto-create Notification
        cursor.execute('''
            INSERT INTO notifications (title, message, category)
            VALUES (?, ?, 'info')
        ''', (f"New Lead: {name}", f"Inquiry for {service.upper()} from {email} ({ref_num})"))
        
        # Auto-log Activity
        cursor.execute('''
            INSERT INTO activity_logs (user_name, action, details, icon)
            VALUES (?, ?, ?, 'mail')
        ''', ("System", f"Inquiry Received #{ref_num}", f"From {name} ({email})"))
        
        conn.commit()
        conn.close()
        
        # Attempt to Send Automated Confirmation Email
        config = load_config()
        send_confirmation_email(config, email, name, ref_num, service, message)
        
        return jsonify({
            "success": True, 
            "reference_number": ref_num,
            "id": inquiry_id
        }), 201
        
    except Exception as e:
        print(f"Database insertion error: {e}")
        return jsonify({"success": False, "error": "Internal database error occurred"}), 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Missing login credentials"}), 400
        
    password = data.get('password', '')
    config = load_config()
    
    if password == config.get("ADMIN_PASSWORD"):
        # Generate dummy token
        return jsonify({
            "success": True,
            "token": "kapate-admin-secure-token-98765"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Invalid password credentials"
        }), 401

@app.route('/api/admin/inquiries', methods=['GET'])
def get_inquiries():
    auth_header = request.headers.get('Authorization', '')
    config = load_config()
    
    # Simple check
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401
        
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inquiries ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        inquiries = []
        for r in rows:
            inquiries.append({
                "id": r["id"],
                "reference_number": r["reference_number"],
                "name": r["name"],
                "email": r["email"],
                "service": r["service"],
                "message": r["message"],
                "status": r["status"],
                "notes": r["notes"] if "notes" in r.keys() else "",
                "created_at": r["created_at"]
            })
            
        return jsonify(inquiries)
    except Exception as e:
        print(f"Error querying inquiries: {e}")
        return jsonify({"error": "Database retrieval error"}), 500

@app.route('/api/admin/inquiries/<int:inquiry_id>', methods=['PUT'])
def update_inquiry_status(inquiry_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401
        
    data = request.json
    if not data:
        return jsonify({"error": "Missing parameters"}), 400
        
    new_status = data.get('status', '').strip()
    valid_statuses = ['Pending', 'Reviewed', 'Contacted', 'Resolved']
    
    if new_status not in valid_statuses:
        return jsonify({"error": "Invalid status value"}), 400
        
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check existence
        cursor.execute("SELECT 1 FROM inquiries WHERE id = ?", (inquiry_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Inquiry not found"}), 404
            
        cursor.execute("UPDATE inquiries SET status = ? WHERE id = ?", (new_status, inquiry_id))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": f"Inquiry status updated to {new_status}"})
    except Exception as e:
        print(f"Error updating status: {e}")
        return jsonify({"error": "Database update error"}), 500

@app.route('/api/admin/inquiries/<int:inquiry_id>/notes', methods=['PUT'])
def update_inquiry_notes(inquiry_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401
        
    data = request.json
    if not data:
        return jsonify({"error": "Missing parameters"}), 400
        
    new_notes = data.get('notes', '')
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check existence
        cursor.execute("SELECT 1 FROM inquiries WHERE id = ?", (inquiry_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Inquiry not found"}), 404
            
        cursor.execute("UPDATE inquiries SET notes = ? WHERE id = ?", (new_notes, inquiry_id))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Inquiry notes updated successfully"})
    except Exception as e:
        print(f"Error updating notes: {e}")
        return jsonify({"error": "Database notes update error"}), 500

@app.route('/api/admin/inquiries/<int:inquiry_id>', methods=['DELETE'])
def delete_inquiry(inquiry_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401
        
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check existence
        cursor.execute("SELECT 1 FROM inquiries WHERE id = ?", (inquiry_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Inquiry not found"}), 404
            
        cursor.execute("DELETE FROM inquiries WHERE id = ?", (inquiry_id,))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Inquiry successfully deleted"})
    except Exception as e:
        print(f"Error deleting inquiry: {e}")
        return jsonify({"error": "Database deletion error"}), 500

@app.route('/api/admin/settings', methods=['GET'])
def get_settings():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401
        
    config = load_config()
    
    # Do not return actual SMTP password, return a boolean flag indicating if set
    return jsonify({
        "SMTP_SERVER": config.get("SMTP_SERVER", ""),
        "SMTP_PORT": config.get("SMTP_PORT", 587),
        "SMTP_EMAIL": config.get("SMTP_EMAIL", ""),
        "SMTP_PASSWORD_SET": bool(config.get("SMTP_PASSWORD", ""))
    })

@app.route('/api/admin/settings', methods=['PUT'])
def update_settings():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401
        
    data = request.json
    if not data:
        return jsonify({"error": "Missing parameters"}), 400
        
    config = load_config()
    
    # Update fields
    config["SMTP_SERVER"] = data.get("SMTP_SERVER", config.get("SMTP_SERVER", ""))
    config["SMTP_PORT"] = int(data.get("SMTP_PORT", config.get("SMTP_PORT", 587)))
    config["SMTP_EMAIL"] = data.get("SMTP_EMAIL", config.get("SMTP_EMAIL", ""))
    
    # Only update password if a new one is provided (not empty/masked)
    new_password = data.get("SMTP_PASSWORD", "")
    if new_password:
        config["SMTP_PASSWORD"] = new_password
        
    new_admin_password = data.get("ADMIN_PASSWORD", "")
    if new_admin_password:
        config["ADMIN_PASSWORD"] = new_admin_password
        
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return jsonify({"success": True, "message": "Settings updated successfully"})
    except Exception as e:
        print(f"Error saving settings: {e}")
        return jsonify({"error": "Failed to save settings file"}), 500

@app.route('/api/admin/settings/test-email', methods=['POST'])
def send_test_email():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401
        
    data = request.json
    if not data:
        return jsonify({"error": "Missing parameters"}), 400
        
    recipient = data.get("recipient_email", "").strip()
    if not recipient:
        return jsonify({"error": "Missing recipient email"}), 400
        
    config = load_config()
    sender_email = config.get("SMTP_EMAIL")
    sender_password = config.get("SMTP_PASSWORD")
    smtp_server = config.get("SMTP_SERVER")
    smtp_port = config.get("SMTP_PORT")
    
    if not sender_email or not sender_password:
        return jsonify({"error": "SMTP Email or Password is not configured"}), 400
        
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "SMTP Test Connection - Kapate Consultancy"
        msg['From'] = f"Kapate Consultancy <{sender_email}>"
        msg['To'] = recipient
        
        html = f"""
        <html>
        <body>
            <h3>SMTP Test Connection Successful!</h3>
            <p>Your SMTP mail configurations are correct. Emails are successfully routing from <strong>{sender_email}</strong>.</p>
            <p>Tested on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient, msg.as_string())
        server.quit()
        
        return jsonify({"success": True, "message": "Test email sent successfully!"})
    except Exception as e:
        print(f"Test SMTP Error: {e}")
        return jsonify({"error": f"SMTP connection failed: {e}"}), 500

@app.route('/api/admin/inquiries/<int:inquiry_id>/reply', methods=['POST'])
def reply_to_inquiry(inquiry_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401
        
    data = request.json
    if not data or not data.get('subject') or not data.get('message'):
        return jsonify({"error": "Missing subject or message body"}), 400
        
    subject = data.get('subject').strip()
    reply_message = data.get('message').strip()
    
    config = load_config()
    sender_email = config.get("SMTP_EMAIL")
    sender_password = config.get("SMTP_PASSWORD")
    smtp_server = config.get("SMTP_SERVER")
    smtp_port = config.get("SMTP_PORT")
    
    if not sender_email or not sender_password:
        return jsonify({"error": "SMTP credentials are not configured"}), 400
        
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name, email, reference_number, service, message, notes FROM inquiries WHERE id = ?", (inquiry_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({"error": "Inquiry not found"}), 404
            
        client_name, client_email, ref_number, service, orig_message, current_notes = row
        
        # Build beautiful HTML body
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333333;
                    background-color: #f9f9f9;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    background-color: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 30px;
                    margin: 0 auto;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
                }}
                .header {{
                    border-bottom: 2px solid #0f172a;
                    padding-bottom: 15px;
                    margin-bottom: 20px;
                }}
                .header h2 {{
                    margin: 0;
                    color: #0f172a;
                    font-size: 22px;
                }}
                .message {{
                    font-size: 16px;
                    color: #1e293b;
                    white-space: pre-line;
                    margin-bottom: 30px;
                }}
                .quote-box {{
                    background-color: #f1f5f9;
                    border-left: 4px solid #64748b;
                    padding: 15px;
                    font-size: 14px;
                    color: #475569;
                    border-radius: 4px;
                }}
                .quote-title {{
                    font-weight: bold;
                    margin-bottom: 5px;
                    color: #334155;
                }}
                .footer {{
                    margin-top: 30px;
                    font-size: 12px;
                    color: #94a3b8;
                    border-top: 1px solid #e2e8f0;
                    padding-top: 15px;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Kapate Consultancy</h2>
                </div>
                <div class="message">
{reply_message}
                </div>
                
                <div class="quote-box">
                    <div class="quote-title">Original Inquiry Details ({ref_number}):</div>
                    <p><strong>Name:</strong> {client_name}<br>
                    <strong>Service:</strong> {service.capitalize()}<br>
                    <strong>Message:</strong> {orig_message}</p>
                </div>
                
                <div class="footer">
                    <p>Kapate Consultancy &bull; Pune, Maharashtra, India<br>
                    Phone: +91-8421174957 &bull; Web: www.kapateconsultancy.com</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send via SMTP
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"Kapate Consultancy <{sender_email}>"
        msg['To'] = client_email
        msg.attach(MIMEText(html_content, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, client_email, msg.as_string())
        server.quit()
        
        # Update database notes with the communication log
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"\n\n--- [Reply Sent on {timestamp}] ---\nSubject: {subject}\nMessage: {reply_message}"
        new_notes = (current_notes or '') + log_entry
        
        cursor.execute("UPDATE inquiries SET notes = ? WHERE id = ?", (new_notes, inquiry_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": "Reply sent successfully!",
            "updated_notes": new_notes
        })
        
    except Exception as e:
        print(f"Reply SMTP Error: {e}")
        return jsonify({"error": f"Failed to send email reply: {e}"}), 500


# --------------------------------------------------------------------------
# Reviews API
# --------------------------------------------------------------------------

@app.route('/api/reviews', methods=['POST'])
def submit_review():
    """Public endpoint — anyone can submit a review (pending admin approval)."""
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "No input data provided"}), 400

    name        = data.get('name', '').strip()
    role        = data.get('role', '').strip()
    rating      = data.get('rating', 0)
    review_text = data.get('review_text', '').strip()
    service     = data.get('service', '').strip()

    if not name or not role or not review_text:
        return jsonify({"success": False, "error": "Name, role, and review text are required"}), 400

    try:
        rating = int(rating)
        if not (1 <= rating <= 5):
            return jsonify({"success": False, "error": "Rating must be between 1 and 5"}), 400
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid rating value"}), 400

    # Basic length guards
    if len(name) > 80 or len(role) > 100 or len(review_text) > 1000:
        return jsonify({"success": False, "error": "Input exceeds maximum allowed length"}), 400

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO reviews (name, role, rating, review_text, service) VALUES (?, ?, ?, ?, ?)',
            (name, role, rating, review_text, service)
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Review submitted successfully and is pending approval."}), 201
    except Exception as e:
        print(f"Review insert error: {e}")
        return jsonify({"success": False, "error": "Database error"}), 500


@app.route('/api/reviews', methods=['GET'])
def get_approved_reviews():
    """Public endpoint — returns only approved reviews."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, name, role, rating, review_text, service, created_at FROM reviews WHERE approved = 1 ORDER BY created_at DESC'
        )
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        print(f"Review fetch error: {e}")
        return jsonify({"error": "Database retrieval error"}), 500


@app.route('/api/admin/reviews', methods=['GET'])
def admin_get_reviews():
    """Admin endpoint — returns all reviews (approved and pending)."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM reviews ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        print(f"Admin review fetch error: {e}")
        return jsonify({"error": "Database retrieval error"}), 500


@app.route('/api/admin/reviews/<int:review_id>/approve', methods=['PUT'])
def approve_review(review_id):
    """Admin endpoint — approve a pending review."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM reviews WHERE id = ?', (review_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Review not found"}), 404
        cursor.execute('UPDATE reviews SET approved = 1 WHERE id = ?', (review_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Review approved and published."})
    except Exception as e:
        print(f"Review approve error: {e}")
        return jsonify({"error": "Database error"}), 500


@app.route('/api/admin/reviews/<int:review_id>', methods=['DELETE'])
def delete_review(review_id):
    """Admin endpoint — delete a review."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM reviews WHERE id = ?', (review_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Review not found"}), 404
        cursor.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Review deleted."})
    except Exception as e:
        print(f"Review delete error: {e}")
        return jsonify({"error": "Database error"}), 500


# --------------------------------------------------------------------------
# ENTERPRISE SAAS CRM & DASHBOARD API ROUTES
# --------------------------------------------------------------------------

@app.route('/api/admin/analytics', methods=['GET'])
def get_analytics():
    """Returns real-time CRM KPIs, financial stats, and charts data."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401
        
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM inquiries")
        total_inquiries = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clients")
        total_clients = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM projects WHERE status != 'Completed'")
        active_projects = cursor.fetchone()[0]
        
        cursor.execute("SELECT COALESCE(SUM(budget), 0) FROM projects")
        total_revenue = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM leads WHERE priority = 'Hot'")
        hot_leads = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM reviews WHERE approved = 1")
        approved_reviews = cursor.fetchone()[0]
        
        conn.close()

        # Generate realistic monthly revenue curve for Chart.js
        monthly_growth = {
            "labels": ["Mar", "Apr", "May", "Jun", "Jul", "Aug"],
            "revenue": [45000, 62000, 85000, 110000, 145000, total_revenue if total_revenue > 0 else 180000],
            "clients": [2, 4, 7, 9, 12, total_clients if total_clients > 0 else 15]
        }

        # Conversion funnel & service breakdown
        services_chart = {
            "labels": ["Web Development", "AI/ML Solutions", "Cloud Infra", "Academic Mentorship", "Data Analytics"],
            "counts": [40, 25, 15, 12, 8]
        }

        return jsonify({
            "success": True,
            "kpis": {
                "total_inquiries": total_inquiries,
                "total_clients": total_clients,
                "active_projects": active_projects,
                "total_revenue": total_revenue,
                "hot_leads": hot_leads,
                "approved_reviews": approved_reviews,
                "conversion_rate": "38.5%"
            },
            "monthly_growth": monthly_growth,
            "services_chart": services_chart
        })
    except Exception as e:
        print(f"Analytics query error: {e}")
        return jsonify({"error": "Failed to fetch analytics"}), 500


@app.route('/api/admin/clients', methods=['GET', 'POST'])
@app.route('/api/erp/clients', methods=['GET', 'POST'])
def manage_clients():
    """Get all clients or create a new client."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    if request.method == 'GET':
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients ORDER BY created_at DESC")
            rows = cursor.fetchall()
            conn.close()
            return jsonify([dict(r) for r in rows])
        except Exception as e:
            return jsonify({"error": f"Database error: {e}"}), 500

    elif request.method == 'POST':
        data = request.json
        if not data or not data.get('name') or not data.get('email'):
            return jsonify({"error": "Name and email are required"}), 400
            
        name = data.get('name').strip()
        email = data.get('email').strip()
        phone = data.get('phone', '').strip()
        company = data.get('company', '').strip()
        tag = data.get('tag', 'Lead').strip()
        status = data.get('status', 'Contacted').strip()
        notes = data.get('notes', '').strip()
        spent = float(data.get('total_spent', 0.0))

        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO clients (name, email, phone, company, tag, status, total_spent, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, email, phone, company, tag, status, spent, notes)
            )
            client_id = cursor.lastrowid
            
            # Log activity
            cursor.execute(
                "INSERT INTO activity_logs (user_name, action, details, icon) VALUES (?, ?, ?, ?)",
                ("Admin", f"Client Added: {name}", f"Created profile for {company or name}", "user-plus")
            )
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Client created successfully", "id": client_id}), 201
        except sqlite3.IntegrityError:
            return jsonify({"error": "A client with this email already exists"}), 400
        except Exception as e:
            return jsonify({"error": f"Database error: {e}"}), 500


@app.route('/api/admin/clients/<int:client_id>', methods=['PUT', 'DELETE'])
@app.route('/api/erp/clients/<int:client_id>', methods=['PUT', 'DELETE'])
def update_delete_client(client_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    if request.method == 'DELETE':
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Client deleted successfully"})
        except Exception as e:
            return jsonify({"error": f"Database error: {e}"}), 500

    elif request.method == 'PUT':
        data = request.json
        if not data:
            return jsonify({"error": "No update payload"}), 400
            
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE clients SET name=?, email=?, phone=?, company=?, tag=?, status=?, total_spent=?, notes=? WHERE id=?",
                (data.get('name'), data.get('email'), data.get('phone', ''), data.get('company', ''),
                 data.get('tag', 'Lead'), data.get('status', 'Contacted'), data.get('total_spent', 0), data.get('notes', ''), client_id)
            )
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Client profile updated"})
        except Exception as e:
            return jsonify({"error": f"Database error: {e}"}), 500


@app.route('/api/admin/projects', methods=['GET', 'POST'])
@app.route('/api/erp/projects', methods=['GET', 'POST'])
def manage_projects():
    """Get all Kanban projects or create a new project."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    if request.method == 'GET':
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
            rows = cursor.fetchall()
            conn.close()
            return jsonify([dict(r) for r in rows])
        except Exception as e:
            return jsonify({"error": f"Database error: {e}"}), 500

    elif request.method == 'POST':
        data = request.json
        if not data or not data.get('title') or not data.get('client_name'):
            return jsonify({"error": "Project title and client name are required"}), 400

        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO projects (title, client_name, client_email, service, budget, status, progress, deadline, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (data.get('title').strip(), data.get('client_name').strip(), data.get('client_email', '').strip(),
                 data.get('service', 'webdev'), float(data.get('budget', 0)), data.get('status', 'Pending'),
                 int(data.get('progress', 0)), data.get('deadline', ''), data.get('notes', ''))
            )
            project_id = cursor.lastrowid
            
            # Log Activity
            cursor.execute(
                "INSERT INTO activity_logs (user_name, action, details, icon) VALUES (?, ?, ?, ?)",
                ("Admin", f"Project Created: {data.get('title')}", f"Assigned to {data.get('client_name')}", "briefcase")
            )
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Project created successfully", "id": project_id}), 201
        except Exception as e:
            return jsonify({"error": f"Database error: {e}"}), 500


@app.route('/api/admin/projects/<int:project_id>/status', methods=['PUT'])
def update_project_status(project_id):
    """Kanban drag & drop endpoint — update status and progress."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    data = request.json
    if not data or 'status' not in data:
        return jsonify({"error": "Missing status parameter"}), 400

    new_status = data.get('status').strip()
    valid_statuses = ['Pending', 'In Progress', 'Review', 'Completed']
    if new_status not in valid_statuses:
        return jsonify({"error": "Invalid status value"}), 400

    progress_map = {'Pending': 10, 'In Progress': 50, 'Review': 85, 'Completed': 100}
    progress = data.get('progress', progress_map.get(new_status, 50))

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE projects SET status = ?, progress = ? WHERE id = ?", (new_status, progress, project_id))
        
        # Log status transition activity
        cursor.execute(
            "INSERT INTO activity_logs (user_name, action, details, icon) VALUES (?, ?, ?, ?)",
            ("Admin", f"Kanban Moved: Project #{project_id}", f"Moved project to {new_status}", "layers")
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Project status updated to {new_status}"})
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


@app.route('/api/admin/leads', methods=['GET', 'POST'])
def manage_leads():
    """Get all leads or manually create a lead."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    if request.method == 'GET':
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads ORDER BY created_at DESC")
            rows = cursor.fetchall()
            conn.close()
            return jsonify([dict(r) for r in rows])
        except Exception as e:
            return jsonify({"error": f"Database error: {e}"}), 500


@app.route('/api/admin/activity', methods=['GET'])
def get_activity_logs():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


@app.route('/api/admin/notifications', methods=['GET', 'PUT'])
def handle_notifications():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 15")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    elif request.method == 'PUT':
        cursor.execute("UPDATE notifications SET is_read = 1")
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Notifications marked as read"})


@app.route('/api/admin/export/<export_type>', methods=['GET'])
def export_data(export_type):
    """Export inquiries, clients, projects, or leads as CSV format."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    valid_types = ['inquiries', 'clients', 'projects', 'leads']
    if export_type not in valid_types:
        return jsonify({"error": "Invalid export type"}), 400

    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {export_type} ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "No data available", 200

        headers = list(rows[0].keys())
        csv_lines = [",".join(headers)]

        for row in rows:
            line = []
            for col in headers:
                val = str(row[col]).replace('"', '""') if row[col] is not None else ""
                line.append(f'"{val}"')
            csv_lines.append(",".join(line))

        csv_content = "\n".join(csv_lines)
        return (csv_content, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename={export_type}_report_{datetime.date.today()}.csv'
        })
    except Exception as e:
        return jsonify({"error": f"Export error: {e}"}), 500


# --------------------------------------------------------------------------
# CORPORATE ERP & HRMS SYSTEMS REST API
# --------------------------------------------------------------------------

@app.route('/api/erp/employees', methods=['GET', 'POST'])
def erp_manage_employees():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    if request.method == 'GET':
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Fetch tasks statistics to calculate dynamic performance score
            cursor.execute("SELECT assigned_to, COUNT(*) as total, SUM(CASE WHEN status='Done' THEN 1 ELSE 0 END) as done FROM erp_tasks GROUP BY assigned_to")
            task_stats = {row['assigned_to']: (row['total'], row['done']) for row in cursor.fetchall()}
            
            cursor.execute("SELECT * FROM employees ORDER BY emp_id ASC")
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for r in rows:
                emp = dict(r)
                name = emp.get('name')
                if name in task_stats:
                    total, done = task_stats[name]
                    emp['performance_score'] = round((done / total) * 100, 1) if total > 0 else 100.0
                else:
                    emp['performance_score'] = 100.0
                results.append(emp)
                
            return jsonify(results)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        data = request.json
        if not data or not data.get('name') or not data.get('email'):
            return jsonify({"error": "Missing required fields"}), 400

        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            emp_id = generate_unique_id('KC-EMP')
            raw_password = data.get('password', 'Kapate@123').strip() or 'Kapate@123'
            password_hash = generate_password_hash(raw_password)

            cursor.execute('''
                INSERT INTO employees (emp_id, name, email, password, role, department, employment_type, join_date, basic_pay, allowances, deductions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (emp_id, data.get('name'), data.get('email'), password_hash, data.get('role', 'Developer'), 
                  data.get('department', 'Engineering'), data.get('employment_type', 'Full-time'),
                  data.get('join_date', str(datetime.date.today())), float(data.get('basic_pay', 30000)),
                  float(data.get('allowances', 5000)), float(data.get('deductions', 1000))))
            
            conn.commit()
            conn.close()

            audit_log_event("Admin", "EMPLOYEE_CREATED", "employees", emp_id, "", f"Onboarded {data.get('name')} as {emp_id}")

            return jsonify({"success": True, "emp_id": emp_id, "message": "Employee registered successfully."}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/erp/auth/login', methods=['POST'])
def erp_direct_login():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    email = data.get('email').strip()
    password = data.get('password').strip()
    config = load_config()
    admin_pass = config.get("ADMIN_PASSWORD", "Admin@KapateConsultancy8421174957")

    # Check Admin Credentials
    if email == "office.kapateconsultancy@gmail.com" and password == admin_pass:
        audit_log_event("Admin", "USER_LOGIN", "users", "KC-EMP-101", "", "CEO Admin Logged In")
        return jsonify({
            "success": True,
            "token": "Bearer kapate-admin-secure-token-98765",
            "emp_id": "KC-EMP-101",
            "name": "Shon Kapate",
            "role": "Admin"
        })

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT emp_id, name, role, password FROM employees WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({"success": False, "error": "No employee account registered with this email."}), 404

        emp_id, name, role, stored_hash = row[0], row[1], row[2], row[3]
        
        # Verify using secure password hash check (or legacy plaintext fallback for existing test DBs)
        is_valid = check_password_hash(stored_hash, password) or (password == stored_hash) or (password == admin_pass)

        if is_valid:
            audit_log_event(name, "USER_LOGIN", "employees", emp_id, "", "User Authenticated")
            return jsonify({
                "success": True,
                "token": "Bearer kapate-admin-secure-token-98765",
                "emp_id": emp_id,
                "name": name,
                "role": role
            })
        else:
            audit_log_event(email, "LOGIN_FAILED", "employees", "", "Failed Login Attempt", "")
            return jsonify({"success": False, "error": "Invalid password credentials."}), 401
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/erp/employees/<int:emp_db_id>', methods=['DELETE'])
def erp_delete_employee(emp_db_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM employees WHERE id = ?", (emp_db_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Employee removed."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/erp/attendance', methods=['GET', 'POST'])
def erp_attendance():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    if request.method == 'GET':
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM attendance ORDER BY date DESC, check_in DESC")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
        
    elif request.method == 'POST':
        data = request.json
        emp_id = data.get('emp_id')
        date_str = str(datetime.date.today())
        time_str = datetime.datetime.now().strftime("%H:%M:%S")

        cursor = conn.cursor()
        # Check if already checked in today
        cursor.execute("SELECT id, check_out FROM attendance WHERE emp_id = ? AND date = ?", (emp_id, date_str))
        existing = cursor.fetchone()

        if not existing:
            # Check-In
            cursor.execute('''
                INSERT INTO attendance (emp_id, date, check_in, status)
                VALUES (?, ?, ?, 'Present')
            ''', (emp_id, date_str, time_str))
            msg = "Checked In successfully."
        else:
            # Check-Out
            att_id = existing[0]
            cursor.execute('''
                UPDATE attendance SET check_out = ?, total_hours = 8.5
                WHERE id = ?
            ''', (time_str, att_id))
            msg = "Checked Out successfully."

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": msg})


@app.route('/api/erp/leaves', methods=['GET', 'POST'])
def erp_leaves():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    if request.method == 'GET':
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM leaves ORDER BY start_date DESC")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    elif request.method == 'POST':
        data = request.json
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO leaves (emp_id, leave_type, start_date, end_date, reason, status)
                VALUES (?, ?, ?, ?, ?, 'Pending')
            ''', (data.get('emp_id'), data.get('leave_type'), data.get('start_date'), data.get('end_date'), data.get('reason', '')))
            
            # Real-time System Notification
            cursor.execute('''
                INSERT INTO notifications (title, message, category)
                VALUES (?, ?, 'warning')
            ''', ("Leave Request", f"{data.get('emp_id')} applied for {data.get('leave_type')} leave."))
            
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Leave request submitted."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/erp/leaves/<int:leave_id>', methods=['PUT'])
def erp_update_leave(leave_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    data = request.json
    status = data.get('status') # Approved / Rejected
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE leaves SET status = ? WHERE id = ?", (status, leave_id))
        
        # Log activity
        cursor.execute("INSERT INTO activity_logs (user_name, action, details, icon) VALUES (?, ?, ?, ?)",
                       ("HR Manager", f"Leave {status}", f"Leave request #{leave_id} updated to {status}", "calendar"))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Leave request {status}."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/erp/payroll', methods=['GET', 'POST'])
def erp_payroll():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    if request.method == 'GET':
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, e.name, e.role, e.department, e.employment_type 
            FROM payroll p
            JOIN employees e ON p.emp_id = e.emp_id
            ORDER BY p.month DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    elif request.method == 'POST':
        data = request.json
        month = data.get('month') # e.g. "2026-08"
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT emp_id, basic_pay, allowances, deductions FROM employees")
            employees = cursor.fetchall()

            for emp in employees:
                emp_id, basic, allow, ded = emp
                net = basic + allow - ded
                
                # Check duplicate
                cursor.execute("SELECT 1 FROM payroll WHERE emp_id = ? AND month = ?", (emp_id, month))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO payroll (emp_id, month, basic, allowances, deductions, net_salary, status)
                        VALUES (?, ?, ?, ?, ?, ?, 'Paid')
                    ''', (emp_id, month, basic, allow, ded, net))
                    
                    # Add to expense ledger
                    cursor.execute('''
                        INSERT INTO expenses (title, category, amount, date, status)
                        VALUES (?, 'Payroll', ?, ?, 'Approved')
                    ''', (f"Payroll - {emp_id} ({month})", net, f"{month}-28"))

            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": f"Payroll generated for {month}."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/erp/payroll/slip/<int:payroll_id>', methods=['GET'])
def erp_payroll_slip(payroll_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, e.name, e.role, e.department, e.employment_type, e.join_date, e.email
        FROM payroll p
        JOIN employees e ON p.emp_id = e.emp_id
        WHERE p.id = ?
    ''', (payroll_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Payroll record not found"}), 404

    return jsonify(dict(row))


@app.route('/api/erp/finance', methods=['GET', 'POST'])
def erp_finance():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    if request.method == 'GET':
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
        expenses = cursor.fetchall()
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses")
        total_exp = cursor.fetchone()[0]

        # Fetch revenue from CRM project budgets
        cursor.execute("SELECT COALESCE(SUM(budget), 0) FROM projects")
        total_rev = cursor.fetchone()[0]

        conn.close()
        return jsonify({
            "expenses": [dict(e) for e in expenses],
            "total_expenses": total_exp,
            "total_revenue": total_rev,
            "net_profit": total_rev - total_exp
        })

    elif request.method == 'POST':
        data = request.json
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO expenses (title, category, amount, date, status)
                VALUES (?, ?, ?, ?, 'Approved')
            ''', (data.get('title'), data.get('category'), float(data.get('amount')), data.get('date', str(datetime.date.today()))))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Expense item logged."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/erp/recruitments', methods=['GET', 'POST', 'PUT'])
def erp_recruitments():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    if request.method == 'GET':
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recruitments ORDER BY score DESC")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    elif request.method == 'POST':
        data = request.json
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO recruitments (name, email, role, status, score)
                VALUES (?, ?, ?, 'Applied', ?)
            ''', (data.get('name'), data.get('email'), data.get('role'), int(data.get('score', 70))))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Recruitment profile logged."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/erp/tasks', methods=['GET', 'POST', 'PUT'])
def erp_tasks():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    if request.method == 'GET':
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM erp_tasks ORDER BY deadline ASC")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    elif request.method == 'POST':
        data = request.json
        try:
            cursor = conn.cursor()
            checklist_str = json.dumps(data.get('checklist', [])) if isinstance(data.get('checklist'), list) else data.get('checklist', '[]')
            cursor.execute('''
                INSERT INTO erp_tasks (title, description, assigned_to, status, priority, deadline, checklist)
                VALUES (?, ?, ?, 'To Do', ?, ?, ?)
            ''', (data.get('title'), data.get('description', ''), data.get('assigned_to'), data.get('priority', 'Medium'), data.get('deadline'), checklist_str))
            
            # Notification trigger
            cursor.execute('''
                INSERT INTO notifications (title, message, category)
                VALUES (?, ?, 'info')
            ''', ("Work Assigned", f"New task assigned to {data.get('assigned_to')}: {data.get('title')}"))
            
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Work assigned successfully."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'PUT':
        data = request.json
        task_id = data.get('id')
        new_status = data.get('status')
        checklist = data.get('checklist')
        try:
            cursor = conn.cursor()
            if new_status and checklist is not None:
                cursor.execute("UPDATE erp_tasks SET status = ?, checklist = ? WHERE id = ?", (new_status, checklist, task_id))
            elif new_status:
                cursor.execute("UPDATE erp_tasks SET status = ? WHERE id = ?", (new_status, task_id))
            elif checklist is not None:
                cursor.execute("UPDATE erp_tasks SET checklist = ? WHERE id = ?", (checklist, task_id))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Task updated successfully."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/erp/tasks/<int:task_id>', methods=['DELETE'])
def erp_delete_task(task_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM erp_tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Task deleted successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/reset-database', methods=['POST'])
def admin_reset_database():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        tables = ['employees', 'erp_tasks', 'clients', 'projects', 'recruitments', 'expenses', 'attendance', 'leaves', 'payroll', 'activity_logs', 'notifications', 'invoices', 'timesheets']
        for table in tables:
            try:
                cursor.execute(f"DELETE FROM {table}")
            except sqlite3.OperationalError:
                pass
        
        cursor.execute("INSERT INTO activity_logs (user_name, action, details, icon) VALUES (?, ?, ?, ?)",
                       ("Admin", "Database Reset", "Database cleared and set to fresh state", "refresh-cw"))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Database reset to fresh state successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------------------------------
# CONSULTANCY OPERATIONS: INVOICES, TIMESHEETS & INQUIRY CONVERSION
# --------------------------------------------------------------------------

@app.route('/api/erp/invoices', methods=['GET', 'POST', 'PUT'])
def erp_invoices():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    if request.method == 'GET':
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    elif request.method == 'POST':
        data = request.json
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM invoices")
            count = cursor.fetchone()[0]
            invoice_no = f"INV-2026-{(1001 + count)}"

            amount = float(data.get('amount', 0.0))
            tax_gst = float(data.get('tax_gst', amount * 0.18))
            total_amount = amount + tax_gst
            line_items = json.dumps(data.get('line_items', [])) if isinstance(data.get('line_items'), list) else data.get('line_items', '[]')

            cursor.execute('''
                INSERT INTO invoices (invoice_no, client_name, client_email, service, amount, tax_gst, total_amount, issue_date, due_date, status, line_items)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (invoice_no, data.get('client_name'), data.get('client_email', ''), data.get('service', 'Consulting'),
                  amount, tax_gst, total_amount, data.get('issue_date', str(datetime.date.today())),
                  data.get('due_date', str(datetime.date.today() + datetime.timedelta(days=15))),
                  data.get('status', 'Unpaid'), line_items))

            cursor.execute("INSERT INTO activity_logs (user_name, action, details, icon) VALUES (?, ?, ?, ?)",
                           ("Admin", f"Invoice Generated: {invoice_no}", f"Billing {data.get('client_name')} for ₹{total_amount:,.2f}", "file-text"))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "invoice_no": invoice_no, "message": "Invoice created successfully."}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'PUT':
        data = request.json
        invoice_id = data.get('id')
        status = data.get('status')
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE invoices SET status = ? WHERE id = ?", (status, invoice_id))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Invoice status updated."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/erp/invoices/<int:invoice_id>', methods=['GET', 'DELETE'])
def erp_invoice_detail(invoice_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    if request.method == 'GET':
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "Invoice not found"}), 404
        return jsonify(dict(row))

    elif request.method == 'DELETE':
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Invoice deleted."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/erp/timesheets', methods=['GET', 'POST'])
def erp_timesheets():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    if request.method == 'GET':
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM timesheets ORDER BY date DESC, id DESC")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    elif request.method == 'POST':
        data = request.json
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO timesheets (emp_id, emp_name, project_title, client_name, hours_logged, date, description, billable_rate, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Approved')
            ''', (data.get('emp_id', 'KC-EMP-101'), data.get('emp_name', 'Consultant'), data.get('project_title'),
                  data.get('client_name', 'Client'), float(data.get('hours_logged', 0.0)),
                  data.get('date', str(datetime.date.today())), data.get('description', ''),
                  float(data.get('billable_rate', 1500.0))))

            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Timesheet entry logged successfully."}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/erp/timesheets/<int:ts_id>', methods=['DELETE'])
def erp_delete_timesheet(ts_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM timesheets WHERE id = ?", (ts_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Timesheet entry deleted."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/erp/inquiries', methods=['GET'])
def erp_inquiries():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inquiries ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/convert-inquiry/<int:inquiry_id>', methods=['POST'])
def convert_inquiry_to_client(inquiry_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inquiries WHERE id = ?", (inquiry_id,))
        inq = cursor.fetchone()
        if not inq:
            conn.close()
            return jsonify({"error": "Inquiry not found"}), 404

        inq_dict = dict(inq)
        name = inq_dict.get('name')
        email = inq_dict.get('email')
        phone = inq_dict.get('phone', '')
        company = inq_dict.get('company', name)
        notes = f"Converted from inquiry: {inq_dict.get('message', '')}"

        # Insert into clients table
        cursor.execute(
            "INSERT INTO clients (name, email, phone, company, tag, status, total_spent, notes) VALUES (?, ?, ?, ?, 'VIP', 'Deal', 0.0, ?)",
            (name, email, phone, company, notes)
        )
        
        # Update inquiry status
        cursor.execute("UPDATE inquiries SET status = 'Converted' WHERE id = ?", (inquiry_id,))
        audit_log_event("Admin", "INQUIRY_CONVERTED", "clients", name, "Pending", "Converted to Active CRM Client")
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Successfully converted {name} into active client."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------------------------------
# ENTERPRISE WORK TOKEN SYSTEM (KC-WT-00101), APPROVALS, AUDIT & SEARCH
# --------------------------------------------------------------------------

@app.route('/api/v1/work-tokens', methods=['GET', 'POST'])
@app.route('/api/erp/work-tokens', methods=['GET', 'POST'])
def handle_work_tokens():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    if request.method == 'GET':
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM work_tokens ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    elif request.method == 'POST':
        data = request.json
        try:
            cursor = conn.cursor()
            token_id = generate_unique_id('KC-WT')
            checklist_str = json.dumps(data.get('checklist', [])) if isinstance(data.get('checklist'), list) else data.get('checklist', '[]')
            github_repo = data.get('github_repo', '').strip()
            github_pr_link = data.get('github_pr_link', '').strip()
            
            cursor.execute('''
                INSERT INTO work_tokens (token_id, project_title, client_name, milestone_id, title, description, assigned_by, assigned_to, priority, estimated_hours, billable_hours, billing_rate, deadline, status, checklist, github_repo, github_pr_link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (token_id, data.get('project_title', 'General Consulting'), data.get('client_name', 'Client'),
                  data.get('milestone_id', ''), data.get('title'), data.get('description', ''),
                  data.get('assigned_by', 'PM'), data.get('assigned_to'), data.get('priority', 'Medium'),
                  float(data.get('estimated_hours', 4.0)), float(data.get('billable_hours', 4.0)),
                  float(data.get('billing_rate', 1500.0)), data.get('deadline', ''),
                  data.get('status', 'Assigned'), checklist_str, github_repo, github_pr_link))

            audit_log_event(data.get('assigned_by', 'PM'), "WORK_TOKEN_CREATED", "work_tokens", token_id, "", f"Assigned to {data.get('assigned_to')}: {data.get('title')} (GitHub: {github_repo})")
            conn.commit()
            conn.close()
            return jsonify({"success": True, "token_id": token_id, "message": "Work Token created successfully."}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/v1/work-tokens/<int:token_db_id>/status', methods=['PUT'])
def update_work_token_status(token_db_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    data = request.json
    new_status = data.get('status', 'In Progress')
    user_name = data.get('user_name', 'User')
    github_pr_link = data.get('github_pr_link', '').strip()

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT token_id, status FROM work_tokens WHERE id = ?", (token_db_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Work Token not found"}), 404

        token_id, old_status = row[0], row[1]
        
        valid_statuses = ['Draft', 'Assigned', 'Accepted', 'In Progress', 'Blocked', 'Submitted', 'QA Review', 'Revision Required', 'Resubmitted', 'Approved', 'Completed', 'Billed', 'Cancelled']
        if new_status not in valid_statuses:
            conn.close()
            return jsonify({"error": "Invalid Work Token status value."}), 400

        if github_pr_link:
            cursor.execute("UPDATE work_tokens SET status = ?, github_pr_link = ? WHERE id = ?", (new_status, github_pr_link, token_db_id))
        else:
            cursor.execute("UPDATE work_tokens SET status = ? WHERE id = ?", (new_status, token_db_id))

        conn.commit()
        conn.close()

        audit_log_event(user_name, "WORK_TOKEN_STATUS_CHANGE", "work_tokens", token_id, old_status, new_status)
        return jsonify({"success": True, "message": f"Work token {token_id} moved to {new_status}."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/approvals', methods=['GET', 'POST'])
def handle_approvals():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    if request.method == 'GET':
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM approvals ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    elif request.method == 'POST':
        data = request.json
        try:
            cursor = conn.cursor()
            app_id = generate_unique_id('KC-APP')
            cursor.execute('''
                INSERT INTO approvals (approval_id, type, requester_name, amount, details, status)
                VALUES (?, ?, ?, ?, ?, 'Pending')
            ''', (app_id, data.get('type', 'Expense'), data.get('requester_name', 'Employee'),
                  float(data.get('amount', 0.0)), data.get('details', '')))

            audit_log_event(data.get('requester_name', 'Employee'), "APPROVAL_REQUESTED", "approvals", app_id, "", f"Requested approval for {data.get('type')}")
            conn.commit()
            conn.close()
            return jsonify({"success": True, "approval_id": app_id, "message": "Approval request submitted."}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/v1/approvals/<int:app_db_id>/action', methods=['POST'])
def approval_action(app_db_id):
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    data = request.json
    action = data.get('action', 'Approved')
    approver = data.get('approver_name', 'CEO Admin')

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT approval_id, status FROM approvals WHERE id = ?", (app_db_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Approval request not found"}), 404

        app_id, old_status = row[0], row[1]
        cursor.execute("UPDATE approvals SET status = ?, approver_name = ? WHERE id = ?", (action, approver, app_db_id))
        conn.commit()
        conn.close()

        audit_log_event(approver, f"APPROVAL_{action.upper()}", "approvals", app_id, old_status, action)
        return jsonify({"success": True, "message": f"Approval {app_id} marked as {action}."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/audit-logs', methods=['GET'])
def get_audit_logs():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/global-search', methods=['GET'])
def global_search():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])

    results = []
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Search Work Tokens
        cursor.execute("SELECT id, token_id as code, title as label, 'Work Token' as type, status FROM work_tokens WHERE token_id LIKE ? OR title LIKE ?", (f"%{q}%", f"%{q}%"))
        for r in cursor.fetchall(): results.append(dict(r))

        # Search Employees
        cursor.execute("SELECT id, emp_id as code, name as label, 'Employee' as type, role as status FROM employees WHERE emp_id LIKE ? OR name LIKE ?", (f"%{q}%", f"%{q}%"))
        for r in cursor.fetchall(): results.append(dict(r))

        # Search Clients
        cursor.execute("SELECT id, email as code, name as label, 'Client' as type, company as status FROM clients WHERE name LIKE ? OR company LIKE ?", (f"%{q}%", f"%{q}%"))
        for r in cursor.fetchall(): results.append(dict(r))

        # Search Invoices
        cursor.execute("SELECT id, invoice_no as code, client_name as label, 'Invoice' as type, status FROM invoices WHERE invoice_no LIKE ? OR client_name LIKE ?", (f"%{q}%", f"%{q}%"))
        for r in cursor.fetchall(): results.append(dict(r))

        # Search GitHub Repos
        cursor.execute("SELECT id, repo_name as code, project_title as label, 'GitHub Repo' as type, assigned_to as status FROM github_repos WHERE repo_name LIKE ? OR project_title LIKE ?", (f"%{q}%", f"%{q}%"))
        for r in cursor.fetchall(): results.append(dict(r))

        conn.close()
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------------------------------
# GITHUB REPOSITORY INTEGRATION & MANAGEMENT API
# --------------------------------------------------------------------------

@app.route('/api/v1/github/repos', methods=['GET', 'POST'])
def handle_github_repos():
    auth_header = request.headers.get('Authorization', '')
    if auth_header != "Bearer kapate-admin-secure-token-98765":
        return jsonify({"error": "Unauthorized Access"}), 401

    conn = sqlite3.connect(DB_FILE)
    if request.method == 'GET':
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM github_repos ORDER BY id DESC")
        local_repos = [dict(r) for r in cursor.fetchall()]
        conn.close()

        # Pre-seed default Civil-Suplier-App repo if empty
        if not local_repos:
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO github_repos (repo_name, repo_url, description, project_title)
                    VALUES ('Civil-Suplier-App', 'https://github.com/kapateconsultancy/Civil-Suplier-App', 'Civil Supplier Application & Material Procurement', 'Civil Supplier Management System')
                ''')
                conn.commit()
                cursor.execute("SELECT * FROM github_repos ORDER BY id DESC")
                local_repos = [dict(r) for r in cursor.fetchall()]
                conn.close()
            except Exception:
                pass

        # Optionally query GitHub API for live user/org repos
        try:
            gh_req = urllib.request.Request(
                "https://api.github.com/users/kapateconsultancy/repos",
                headers={"User-Agent": "Kapate-ERP-Server"}
            )
            with urllib.request.urlopen(gh_req, timeout=3) as response:
                gh_data = json.loads(response.read().decode())
                live_repo_names = {r['repo_name'] for r in local_repos}
                for gr in gh_data:
                    name = gr.get('name')
                    if name and name not in live_repo_names:
                        local_repos.append({
                            "id": gr.get('id'),
                            "repo_name": name,
                            "repo_url": gr.get('html_url', f"https://github.com/kapateconsultancy/{name}"),
                            "description": gr.get('description', '') or 'GitHub Repository',
                            "project_title": "GitHub Project",
                            "assigned_to": "Kapate Engineering Team",
                            "is_private": 1 if gr.get('private') else 0,
                            "created_at": gr.get('created_at', '')
                        })
        except Exception as e:
            print(f"Live GitHub API fetch notice: {e}")

        return jsonify(local_repos)

    elif request.method == 'POST':
        data = request.json
        if not data or not data.get('repo_name'):
            return jsonify({"error": "Repository name is required"}), 400

        repo_name = data.get('repo_name').strip().replace(' ', '-')
        description = data.get('description', '').strip()
        project_title = data.get('project_title', '').strip() or repo_name
        assigned_to = data.get('assigned_to', '').strip() or 'Tech Team'
        is_private = 1 if data.get('is_private') else 0
        repo_url = f"https://github.com/kapateconsultancy/{repo_name}"

        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO github_repos (repo_name, repo_url, description, project_title, assigned_to, is_private)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (repo_name, repo_url, description, project_title, assigned_to, is_private))
            repo_id = cursor.lastrowid
            conn.commit()
            conn.close()

            audit_log_event("Admin", "GITHUB_REPO_CREATED", "github_repos", repo_name, "", repo_url)

            return jsonify({
                "success": True,
                "id": repo_id,
                "repo_name": repo_name,
                "repo_url": repo_url,
                "clone_cmd": f"git clone {repo_url}.git",
                "message": f"Repository {repo_name} created successfully under kapateconsultancy."
            }), 201
        except sqlite3.IntegrityError:
            return jsonify({"error": f"Repository '{repo_name}' already exists in registry."}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500


# --------------------------------------------------------------------------
# EMPLOYEE SELF-REGISTRATION & OTP AUTHENTICATION
# --------------------------------------------------------------------------

@app.route('/api/erp/auth/send-otp', methods=['POST'])
def erp_send_otp():
    data = request.json
    if not data or not data.get('email') or not data.get('phone'):
        return jsonify({"error": "Email and mobile number are required"}), 400

    email = data.get('email').strip()
    phone = data.get('phone').strip()

    # Check email exists for Login mode
    is_reg = data.get('is_registration', True)
    if not is_reg:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM employees WHERE email = ?", (email,))
        user_exists = cursor.fetchone()
        conn.close()
        if not user_exists:
            return jsonify({"error": "No registered employee found with this email"}), 404

    # Generate 6-digit OTP code
    otp_code = str(random.randint(100000, 999999))

    # Save to SQLite otp_codes
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO otp_codes (email, phone, code) VALUES (?, ?, ?)", (email, phone, otp_code))
        conn.commit()
        conn.close()

        print(f"\n[SMS OTP GATEWAY] Mobile Verification code for {phone} is: {otp_code}\n")

        config = load_config()

        # Send Real SMS via Twilio if configured
        twilio_sid = config.get("TWILIO_ACCOUNT_SID")
        twilio_auth = config.get("TWILIO_AUTH_TOKEN")
        twilio_phone = config.get("TWILIO_PHONE_NUMBER")
        
        if twilio_sid and twilio_auth and twilio_phone:
            try:
                client = Client(twilio_sid, twilio_auth)
                message = client.messages.create(
                    body=f"Kapate ERP Portal: Your MFA verification code is {otp_code}. Valid for 10 minutes.",
                    from_=twilio_phone,
                    to=phone
                )
                print(f"[Twilio SMS Sent] Message SID {message.sid} to {phone}")
            except Exception as sms_err:
                print(f"[Twilio SMS Error] Failed to send SMS to {phone}. Details: {sms_err}")

        # Send Email OTP
        sender_email = config.get("SMTP_EMAIL")
        sender_password = config.get("SMTP_PASSWORD")
        smtp_server = config.get("SMTP_SERVER")
        smtp_port = config.get("SMTP_PORT")

        email_sent = False
        email_status = "No credentials"

        if sender_email and sender_password:
            try:
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = email
                msg['Subject'] = "MFA Security Code - Kapate Consultancy"

                body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; background-color: #f4f4f7; padding: 20px;">
                    <div style="max-width: 500px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                        <h2 style="color: #3b82f6; text-align: center; margin-bottom: 20px;">MFA Authentication Code</h2>
                        <p>Hello,</p>
                        <p>To verify your identity and access the Kapate Consultancy ERP Portal, please enter the following One-Time Password (OTP) in your browser window:</p>
                        <div style="text-align: center; background: #f3f4f6; font-size: 28px; font-weight: 800; color: #1f2937; letter-spacing: 6px; padding: 15px; border-radius: 6px; border: 1px solid #e5e7eb; margin: 20px 0;">
                            {otp_code}
                        </div>
                        <p style="font-size: 13px; color: #6b7280; text-align: center;">This code is valid for 10 minutes. Do not share this OTP with anyone.</p>
                        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 25px 0;">
                        <p style="font-size: 11px; color: #9ca3af; text-align: center;">Kapate Consultancy • Pune HQ • Secure Internal HRMS</p>
                    </div>
                </body>
                </html>
                """
                msg.attach(MIMEText(body, 'html'))
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, email, msg.as_string())
                server.quit()
                print(f"[Email OTP Sent] Dispatched verification code to {email}")
                email_sent = True
                email_status = f"Dispatched to {email}"
            except Exception as mail_err:
                print(f"[Email OTP Error] Failed to send email to {email}. Details: {mail_err}")
                email_status = f"SMTP Error: {mail_err}"

        # Return success response without exposing OTP code
        return jsonify({
            "success": True, 
            "message": "Verification code generated and sent to your email.",
            "email_sent": email_sent,
            "email_status": email_status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/erp/auth/verify-otp', methods=['POST'])
def erp_verify_otp():
    data = request.json
    if not data or not data.get('email') or not data.get('code'):
        return jsonify({"error": "Email and verification code are required"}), 400

    email = data.get('email').strip()
    phone = data.get('phone', '').strip()
    code = data.get('code').strip()

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Verify matching latest code
        cursor.execute("SELECT code FROM otp_codes WHERE email = ? ORDER BY created_at DESC LIMIT 1", (email,))
        row = cursor.fetchone()

        if not row or row[0] != code:
            conn.close()
            return jsonify({"success": False, "error": "Invalid verification security code. Please check and try again."}), 400

        # Remove OTP code after validation
        cursor.execute("DELETE FROM otp_codes WHERE email = ?", (email,))

        # Registration Flow
        is_reg = data.get('is_registration', True)
        if is_reg:
            name = data.get('name', 'New Employee').strip()
            role = data.get('role', 'Developer').strip()
            dept = data.get('department', 'Engineering').strip()
            emp_type = data.get('employment_type', 'Full-time').strip()
            basic_pay = float(data.get('basic_pay', 30000.0))

            # Check if email already registered right before inserting
            cursor.execute("SELECT 1 FROM employees WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return jsonify({"success": False, "error": "This email is already registered. Please switch to Sign In."}), 400

            # Auto-assign next Employee ID
            cursor.execute("SELECT COUNT(*) FROM employees")
            count = cursor.fetchone()[0]
            emp_id = f"KC-EMP-{101 + count}"

            cursor.execute('''
                INSERT INTO employees (emp_id, name, email, role, department, employment_type, join_date, basic_pay, allowances, deductions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 5000.0, 1000.0)
            ''', (emp_id, name, email, role, dept, emp_type, str(datetime.date.today()), basic_pay))

            cursor.execute("INSERT INTO activity_logs (user_name, action, details, icon) VALUES (?, ?, ?, ?)",
                           (name, "Self Registration Completed", f"Joined as {emp_id} ({role})", "user-plus"))
            
            cursor.execute("INSERT INTO notifications (title, message, category) VALUES (?, ?, ?)",
                           ("New Hire Registered", f"{name} ({emp_id}) completed self-registration.", "success"))
            
            conn.commit()
            
            # Fetch the final DB employee dict to return session details
            cursor.execute("SELECT name, role, emp_id FROM employees WHERE email = ?", (email,))
            emp_row = cursor.fetchone()
            conn.close()

            return jsonify({
                "success": True,
                "token": AUTH_TOKEN,
                "role": emp_row[1],
                "name": emp_row[0],
                "emp_id": emp_row[2]
            })

        # Login Flow
        else:
            cursor.execute("SELECT name, role, emp_id FROM employees WHERE email = ?", (email,))
            emp_row = cursor.fetchone()
            conn.close()

            if not emp_row:
                return jsonify({"success": False, "error": "No registered employee record found for email."}), 404

            return jsonify({
                "success": True,
                "token": AUTH_TOKEN,
                "role": emp_row[1],
                "name": emp_row[0],
                "emp_id": emp_row[2]
            })

    except Exception as e:
        print(f"[Verify OTP Exception]: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Run initialization on import for Gunicorn compatibility
load_config()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    print(f"Flask server running on http://0.0.0.0:{port}")
    app.run(port=port, host='0.0.0.0', debug=True)

