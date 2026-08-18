# Kapate Consultancy & Enterprise Workspace Platform

A comprehensive company operating platform and modern public web portal built for **Kapate Consultancy** (Pune, India).

---

## 🏛️ Platform Architecture

```text
                    KAPATE CONSULTANCY
                           │
                 ┌─────────┴─────────┐
                 │                   │
            PUBLIC WEBSITE       WORKSPACE
         (kapateconsultancy.in)  (/workspace)
                                     │
                  ┌──────────────────┼─────────────────┐
                  │                  │                 │
                PEOPLE             WORK            BUSINESS
                  │                  │                 │
             Employees          Projects             CRM
             Managers           Tasks                Clients
             Interns            Milestones           Proposals
             Attendance         Files                Invoices
             Leave              Calendar             Finance
                  │                  │                 │
                  └──────────────────┼─────────────────┘
                                     │
                              COMMUNICATION
                                     │
                             Mail + Chat
                                     │
                              NOTIFICATIONS
                                     │
                               ANALYTICS
                                     │
                                KAPATE AI
```

---

## 🚀 Key Features

### 1. Public Web Portal (`/` & `/index.html`)
- Interactive hero canvas with particle physics animations.
- Public IT services, architecture solutions, client reviews, price estimator, and interactive contact inquiry dispatch.
- Compliance & legal agreements (`/legal.html`).

### 2. Kapate Enterprise Workspace (`/workspace` & `/workspace.html`)
- **4-Tier Role-Based Access Control (RBAC)**:
  - **CEO**: Full company oversight, financial ledger, revenue analytics, staff registration, company health gauges, and audit logs.
  - **Manager**: Project milestones, team task assignment, submission review workflow (Approve / Request Changes), workload balancer, and meetings.
  - **Employee**: "What do I need to do today?" priority backlog, stopwatch time tracker, task stepper & deliverable submitter, internal mail & chat.
  - **Intern**: Curriculum learning modules (8/10 completed), practical project tracks, mentor feedback, and certificate milestones.

- **Integrated Functional Modules**:
  1. **Dashboard** (Role-tailored KPIs, revenue, backlog, and broadcasts)
  2. **Projects** (SLA timelines, milestones, budgets, and team allocations)
  3. **Tasks** (Strict status stepper: `Assigned` &rarr; `In Progress` &rarr; `Submitted` &rarr; `Approved` &rarr; `Completed`)
  4. **Task Discussions** (Comment threads, mentions, and file attachments)
  5. **Internal Mail** (Confidential in-app messaging: Inbox, Sent, Starred, Trash, Compose)
  6. **Real-Time Chat** (Channels `#general`, `#engineering`, `#ai-lab` & 1-on-1 direct messaging)
  7. **Company File Vault** (Hierarchical drive: HR, Finance, Projects, Templates, Internal with RBAC permissions)
  8. **Client CRM** (Accounts pipeline: Lead, Contacted, Proposal Sent, Active, Inactive)
  9. **Proposal Generator** (Commercial drafting with branded PDF export)
  10. **Invoices & Billing** (Itemized billing, tax calculation, payment status tracking)
  11. **Duty Attendance Clock** (Live shift timer, clock in/out, duty logs)
  12. **Leave Management** (Application, categories, Manager/CEO approval/rejection moderation)
  13. **Unified Calendar** (Deadlines, milestones, meetings, leaves, company townhalls)
  14. **Time Tracking & Timesheets** (Stopwatch timer widget and weekly effort breakdown)
  15. **Employee Performance** (Deliverable ratings, on-time scores, qualitative reviews)
  16. **Internship Hub** (Curriculum tracks, practical module scores, and completion certificates)
  17. **Announcements Noticeboard** (Company-wide and department broadcasts)
  18. **Audit Logs & Security** (Immutable activity trail with user, IP, action, entity, timestamp)
  19. **Kapate AI Assistant** (Permission-governed natural language workspace copilot)
  20. **Global Omnibar Search** (`Ctrl+K` omnibar searching across tasks, projects, staff, files)

---

## 🔑 Pre-Seeded Demo Accounts

| Role | Username / Identity | Password | Name | Department |
| :--- | :--- | :--- | :--- | :--- |
| **CEO** | `ceo` | `Kapate@Ceo2026` | Shon Kapate | Executive |
| **Manager** | `manager01` | `Manager@2026` | Rohit Verma | Engineering |
| **Manager** | `manager02` | `Manager@2026` | Ananya Deshmukh | Product & AI |
| **Employee** | `employee01` | `Emp@2026` | Siddharth Patil | Engineering |
| **Employee** | `employee02` | `Emp@2026` | Pooja Kulkarni | Design |
| **Employee** | `employee03` | `Emp@2026` | Aditya Shinde | Cloud & DevOps |
| **Intern** | `intern01` | `Intern@2026` | Tanvi Joshi | Engineering |
| **Intern** | `intern02` | `Intern@2026` | Gaurav More | Product & AI |

---

## ⚙️ Technology Stack

- **Frontend**: HTML5, Vanilla JavaScript (ES6+), Vanilla CSS3, Tailwind CSS (via CDN), Chart.js
- **Backend**: Python 3 (Flask), SQLite3
- **Security**: PBKDF2 Password Hashing (`werkzeug.security`), Session Tokens, Granular RBAC Middleware
- **Deployment**: Gunicorn, Vercel (`vercel.json`), Netlify (`netlify.toml`), Render (`render.yaml`)

---

## 💻 Local Development Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Server**:
   ```bash
   python server.py
   ```

3. **Access the Applications**:
   - Public Website: [http://localhost:8080](http://localhost:8080)
   - Kapate Workspace: [http://localhost:8080/workspace](http://localhost:8080/workspace)
