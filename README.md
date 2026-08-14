# Kapate Consultancy & Enterprise ERP Platform

A web platform and internal ERP / HRMS system built for Kapate Consultancy (Pune, India).

## 🚀 Features

- **Public Web Portal**:
  - Interactive hero canvas with particle physics animations.
  - Public service offerings, leadership profiles, portfolio showcases, and client reviews.
  - Interactive Contact Inquiry form connected to SQLite database with email confirmation dispatches.
  - Legal & Compliance pages (`legal.html`) for Privacy Policy and Terms of Service.
  - Pill-shaped frosted glass header with light/dark theme switcher.

- **Corporate ERP & HRMS Portal (`/erp.html`)**:
  - Split-screen modern login & registration system.
  - Multi-Factor Authentication (MFA) via 6-digit email OTPs.
  - Executive Control Dashboard & Staff Directory.
  - Printable Salary Slips with full earnings/deductions breakdown (`window.print` PDF engine).
  - Leave Application & HR Moderation approval workflow.
  - Live Attendance Duty Clock-In tracker.
  - Task Kanban board & Recruitment funnel management.

---

## 🛠️ Tech Stack

- **Frontend**: HTML5, Vanilla JavaScript (ES6+), Vanilla CSS3, Tailwind CSS (via CDN for ERP UI), Chart.js
- **Backend**: Python 3 (Flask), SQLite3
- **MFA & Messaging**: Google SMTP (`smtplib`), Twilio API Integration
- **Server Deployment**: Gunicorn

---

## ⚙️ Project Structure

```text
Info-Kapate/
├── server.py              # Main Flask application backend & API endpoints
├── reset_db.py            # Utility script to re-initialize clean database tables
├── config.json            # Configuration settings (SMTP, passwords, API keys)
├── requirements.txt      # Python dependencies for deployment
├── Procfile               # Web process runner configuration
├── .gitignore             # Ignored files for git security
│
├── index.html             # Public consultancy landing page
├── legal.html             # Privacy policy & terms of service page
├── erp.html               # Corporate ERP & HRMS portal interface
├── admin.html             # Legacy admin view
├── letterhead.html        # Official company letterhead template
│
├── style.css              # Custom CSS design system
├── app.js                 # Public website interactive scripts & particle engine
├── erp.js                 # ERP portal client logic & SPA navigation
│
├── assets/                # Media assets (CEO photo & brand logos)
└── scripts/               # Utility & database scripts (reset_db.py)
```

---

## 💻 Local Development Setup

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment settings (`config.json`)**:
   Ensure `SMTP_EMAIL` and `SMTP_PASSWORD` are configured for email dispatches.

3. **Start the Flask Development Server**:
   ```bash
   python server.py
   ```

4. **Access the application**:
   - Main Website: [http://127.0.0.1:8080](http://127.0.0.1:8080)
   - ERP Portal: [http://127.0.0.1:8080/erp.html](http://127.0.0.1:8080/erp.html)

---

## ☁️ Deployment Instructions

### Deploy to Render / Railway / Heroku

1. Push your repository to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit for deployment"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. Log into **Render** or **Railway**, create a new Web Service, and select your GitHub repository.
3. The platform will automatically detect `requirements.txt` and `Procfile` and start your application using Gunicorn.

### Deploy to Netlify (Drag & Drop or Git)

1. **Option A (Drag & Drop)**:
   - Log into **[Netlify.com](https://app.netlify.com/drop)**.
   - Drag and drop your project folder `Info-Kapate` directly into the Netlify upload zone.
2. **Option B (GitHub Integration)**:
   - Connect your GitHub repository to Netlify.
   - Set publish directory to `.` (root).
   - Netlify will read `netlify.toml` and deploy instantly!
