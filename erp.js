// ==========================================================================
// CORPORATE ERP & HRMS CLIENT LOGIC (Kapate Consultancy)
// ==========================================================================

const API_ERP = '/api/erp';
const AUTH_TOKEN = "Bearer kapate-admin-secure-token-98765";

let currentRole = 'Admin';
let currentEmpId = 'KC-EMP-101'; // Default system administrator ID

document.addEventListener('DOMContentLoaded', () => {
    initAuth();
    initNavigation();
    initMobileSidebar();
    initClock();
    initForms();
    
    // Register PWA Service Worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js')
            .then(reg => console.log('ERP PWA ServiceWorker registered:', reg.scope))
            .catch(err => console.warn('ERP PWA ServiceWorker registration failed:', err));
    }
});


// --------------------------------------------------------------------------
// 1. AUTHENTICATION & SECURITY
// --------------------------------------------------------------------------
let activeTab = 'login'; // login or register
let pendingAuthPayload = {};

function initAuth() {
    const loginPage  = document.getElementById('login-page');
    const erpLayout  = document.getElementById('erp-layout');
    const logoutBtn  = document.getElementById('logout-btn');

    const tabBtnLogin    = document.getElementById('tab-btn-login');
    const tabBtnRegister = document.getElementById('tab-btn-register');
    const formLogin      = document.getElementById('auth-login-form');
    const formRegister   = document.getElementById('auth-register-form');
    const alertBox       = document.getElementById('login-alert');

    // Restore existing session
    const savedToken = localStorage.getItem('kc_erp_token');
    const savedRole  = localStorage.getItem('kc_erp_role');
    const savedName  = localStorage.getItem('kc_erp_name');
    const savedEmpId = localStorage.getItem('kc_erp_id');

    if (savedToken === AUTH_TOKEN) {
        currentRole  = savedRole  || 'Admin';
        currentEmpId = savedEmpId || 'KC-EMP-101';
        loginPage.style.display  = 'none';
        erpLayout.classList.remove('hidden');
        setupRoleAccess(savedName || 'Staff Member');
        loadAllERPData();
    }

    // Tab Switchers
    tabBtnLogin.addEventListener('click', () => {
        activeTab = 'login';
        tabBtnLogin.classList.add('active');
        tabBtnRegister.classList.remove('active');
        formLogin.style.display  = '';
        formRegister.style.display = 'none';
        document.getElementById('auth-form-heading').textContent    = 'Welcome back';
        document.getElementById('auth-form-subheading').textContent = 'Sign in to your Kapate ERP account to continue.';
    });

    tabBtnRegister.addEventListener('click', () => {
        activeTab = 'register';
        tabBtnRegister.classList.add('active');
        tabBtnLogin.classList.remove('active');
        formRegister.style.display = '';
        formLogin.style.display    = 'none';
        document.getElementById('auth-form-heading').textContent    = 'Create Account';
        document.getElementById('auth-form-subheading').textContent = 'Register as a new Kapate ERP staff member.';
    });

    // Handle Login Send OTP
    formLogin.addEventListener('submit', async (e) => {
        e.preventDefault();
        alertBox.style.display = 'none';

        const email = document.getElementById('li-email').value;
        const phone = document.getElementById('li-phone').value;

        pendingAuthPayload = { email, phone, is_registration: false };
        await sendOtpRequest(email, phone, false);
    });

    // Handle Register Send OTP
    formRegister.addEventListener('submit', async (e) => {
        e.preventDefault();
        alertBox.style.display = 'none';

        const name       = document.getElementById('rg-name').value;
        const email      = document.getElementById('rg-email').value;
        const phone      = document.getElementById('rg-phone').value;
        const role       = document.getElementById('rg-role').value;
        const department = document.getElementById('rg-dept').value;

        pendingAuthPayload = {
            name,
            email,
            phone,
            role,
            department,
            employment_type: role === 'Intern' ? 'Intern' : 'Full-time',
            basic_pay: 30000, // Default; admin sets actual pay
            is_registration: true
        };

        await sendOtpRequest(email, phone, true);
    });

    // Verify OTP Button Action
    document.getElementById('verify-otp-btn').addEventListener('click', async () => {
        const code     = document.getElementById('otp-input-code').value;
        const otpAlert = document.getElementById('otp-alert');
        otpAlert.style.display = 'none';

        if (!code || code.length !== 6) {
            otpAlert.textContent   = "Please enter a valid 6-digit security code.";
            otpAlert.style.display = 'block';
            return;
        }

        try {
            const res = await fetch(`${API_ERP}/auth/verify-otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email:            pendingAuthPayload.email,
                    phone:            pendingAuthPayload.phone,
                    code:             code,
                    is_registration:  pendingAuthPayload.is_registration,
                    name:             pendingAuthPayload.name,
                    role:             pendingAuthPayload.role,
                    department:       pendingAuthPayload.department,
                    employment_type:  pendingAuthPayload.employment_type,
                    basic_pay:        pendingAuthPayload.basic_pay
                })
            });

            const data = await res.json();
            if (res.ok && data.success) {
                localStorage.setItem('kc_erp_token', data.token);
                localStorage.setItem('kc_erp_role',  data.role);
                localStorage.setItem('kc_erp_name',  data.name);
                localStorage.setItem('kc_erp_id',    data.emp_id);

                currentRole  = data.role;
                currentEmpId = data.emp_id;

                loginPage.style.display = 'none';
                erpLayout.classList.remove('hidden');

                setupRoleAccess(data.name);
                loadAllERPData();
            } else {
                otpAlert.textContent   = data.error || "Verification failed. Invalid code.";
                otpAlert.style.display = 'block';
            }
        } catch (err) {
            otpAlert.textContent   = "Server communication error. Please try again.";
            otpAlert.style.display = 'block';
        }
    });

    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('kc_erp_token');
        localStorage.removeItem('kc_erp_role');
        localStorage.removeItem('kc_erp_name');
        localStorage.removeItem('kc_erp_id');
        location.reload();
    });
}

async function sendOtpRequest(email, phone, isReg) {
    const alertBox = document.getElementById('login-alert');
    alertBox.textContent   = "⌛ Dispatched security code request... Please wait.";
    alertBox.style.display = 'block';
    alertBox.className     = 'auth-alert info';
    try {
        const res = await fetch(`${API_ERP}/auth/send-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, phone, is_registration: isReg })
        });

        const data = await res.json();
        if (res.ok && data.success) {
            // Switch to OTP screen
            document.getElementById('otp-input-code').value = '';
            document.getElementById('otp-alert').style.display = 'none';
            document.getElementById('auth-main-screen').style.display = 'none';
            document.getElementById('auth-otp-screen').style.display  = 'block';



            const emailStatusEl = document.getElementById('otp-email-status');
            if (emailStatusEl && data.email_status) {
                emailStatusEl.textContent = data.email_sent 
                    ? `✉️ Email OTP: ${data.email_status}`
                    : `⚠️ Email OTP: ${data.email_status}`;
                emailStatusEl.style.color = data.email_sent ? '#34d399' : '#f87171';
            }
        } else {
            alertBox.textContent   = data.error || "Failed to trigger authentication OTP.";
            alertBox.style.display = 'block';
        }
    } catch (err) {
        alertBox.textContent   = "Error connecting to server. Please try again.";
        alertBox.style.display = 'block';
    }
}

function closeOtp() {
    document.getElementById('auth-otp-screen').style.display  = 'none';
    document.getElementById('auth-main-screen').style.display = 'block';
}

function setupRoleAccess(userName) {
    document.getElementById('user-display-role').textContent = currentRole;
    document.getElementById('user-initials').textContent = currentRole.substring(0, 2).toUpperCase();

    // Set name dynamically
    document.getElementById('user-display-name').textContent = userName || 'Staff Member';

    // Role restrictions
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(btn => {
        const tab = btn.getAttribute('data-tab');
        
        // Developer & Intern restrict access
        if (currentRole === 'Intern' || currentRole === 'Developer') {
            if (['tab-payroll', 'tab-finance', 'tab-recruitments'].includes(tab)) {
                btn.classList.add('pointer-events-none', 'opacity-30');
            }
        }
    });
}

// --------------------------------------------------------------------------
// 2. SPA NAVIGATION
// --------------------------------------------------------------------------
function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const views = document.querySelectorAll('.tab-view');
    const headerTitle = document.getElementById('erp-tab-title');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.classList.contains('opacity-30')) return; // Disabled

            const targetTab = btn.getAttribute('data-tab');

            navButtons.forEach(b => b.classList.remove('bg-accentBlue', 'text-white', 'shadow-md', 'shadow-accentBlue/20'));
            views.forEach(v => v.classList.add('hidden'));

            btn.classList.add('bg-accentBlue', 'text-white', 'shadow-md', 'shadow-accentBlue/20');
            document.getElementById(targetTab).classList.remove('hidden');

            const titleMap = {
                'tab-dashboard': 'Executive Control Dashboard',
                'tab-employees': 'Corporate Staff Directory',
                'tab-payroll': 'Salary Disbursements Ledger',
                'tab-attendance': 'Duty Attendance Logs',
                'tab-leaves': 'Leave Applications Portal',
                'tab-tasks': 'Developer Kanban Taskboard',
                'tab-recruitments': 'HR Recruitment Funnel',
                'tab-finance': 'Corporate Finance Ledger'
            };
            headerTitle.textContent = titleMap[targetTab] || 'ERP Center';
        });
    });
}

function initMobileSidebar() {
    const sidebar = document.getElementById('erp-sidebar');
    const overlay = document.getElementById('erp-sidebar-overlay');
    const toggleBtn = document.getElementById('mobile-erp-sidebar-toggle');
    const closeBtn = document.getElementById('mobile-erp-sidebar-close');

    if (!sidebar) return;

    const openSidebar = () => {
        sidebar.classList.remove('-translate-x-full');
        if (overlay) overlay.classList.remove('hidden');
    };

    const closeSidebar = () => {
        sidebar.classList.add('-translate-x-full');
        if (overlay) overlay.classList.add('hidden');
    };

    if (toggleBtn) toggleBtn.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);

    // Auto-close drawer on mobile view when any nav tab is selected
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            if (window.innerWidth < 1024) {
                closeSidebar();
            }
        });
    });
}


// --------------------------------------------------------------------------
// 3. DAILY CLOCK FUNCTIONALITY
// --------------------------------------------------------------------------
function initClock() {
    const statusText = document.getElementById('attendance-status');
    const lastClock = localStorage.getItem(`clock_${currentEmpId}_${new Date().toDateString()}`);
    if (lastClock) {
        statusText.textContent = lastClock;
    }
}

async function triggerClock(type) {
    const statusText = document.getElementById('attendance-status');
    try {
        const res = await fetch(`${API_ERP}/attendance`, {
            method: 'POST',
            headers: {
                'Authorization': AUTH_TOKEN,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ emp_id: currentEmpId })
        });
        const data = await res.json();
        if (data.success) {
            const status = type === 'check_in' ? 'On Duty (Present)' : 'Off Duty';
            statusText.textContent = status;
            localStorage.setItem(`clock_${currentEmpId}_${new Date().toDateString()}`, status);
            alert(data.message);
            fetchAttendance();
        }
    } catch (err) {
        alert("Failed to sync clocking action.");
    }
}

// --------------------------------------------------------------------------
// 4. DATA SYNCHRONIZATION ENGINE
// --------------------------------------------------------------------------
function loadAllERPData() {
    fetchEmployees();
    fetchPayroll();
    fetchAttendance();
    fetchLeaves();
    fetchTasks();
    fetchRecruitments();
    fetchFinance();
}

async function fetchEmployees() {
    try {
        const res = await fetch(`${API_ERP}/employees`, { headers: { 'Authorization': AUTH_TOKEN } });
        const employees = await res.json();
        document.getElementById('dash-staff-count').textContent = employees.length;

        const tbody = document.getElementById('employees-table-body');
        tbody.innerHTML = '';

        employees.forEach(emp => {
            const score = emp.performance_score || 100.0;
            let badgeClass = 'bg-emerald-950 text-emerald-400 border-emerald-500/20';
            let label = 'Leader';
            if (score < 75) {
                badgeClass = 'bg-amber-950/40 text-amber-400 border-amber-500/25';
                label = 'Under Review';
            } else if (score < 90) {
                badgeClass = 'bg-blue-950 text-accentBlue border-accentBlue/20';
                label = 'On Track';
            }

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="p-4 font-bold text-white text-xs">${emp.emp_id}</td>
                <td class="p-4 font-semibold text-slate-200">${emp.name}</td>
                <td class="p-4 text-xs text-slate-400">${emp.email}</td>
                <td class="p-4 text-xs">${emp.department} / <span class="text-accentBlue font-medium">${emp.role}</span></td>
                <td class="p-4 text-xs text-slate-400">${emp.employment_type}</td>
                <td class="p-4 font-bold text-slate-200">₹${emp.basic_pay.toLocaleString('en-IN')}</td>
                <td class="p-4">
                    <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold border ${badgeClass}">
                        ${score}% - ${label}
                    </span>
                </td>
                <td class="p-4">
                    <button onclick="deleteEmployee(${emp.id})" class="text-xs text-red-400 hover:text-red-300">Remove</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Fetch employees error:", err);
    }
}

async function deleteEmployee(id) {
    if (!confirm("Are you sure you want to remove this employee profile?")) return;
    try {
        await fetch(`${API_ERP}/employees/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': AUTH_TOKEN }
        });
        fetchEmployees();
    } catch (err) {
        alert("Delete failed.");
    }
}

async function fetchPayroll() {
    try {
        const res = await fetch(`${API_ERP}/payroll`, { headers: { 'Authorization': AUTH_TOKEN } });
        const payroll = await res.json();
        const tbody = document.getElementById('payroll-table-body');
        tbody.innerHTML = '';

        payroll.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="p-4 font-bold text-xs text-slate-300">${p.emp_id}</td>
                <td class="p-4 font-semibold">${p.name}</td>
                <td class="p-4 text-xs text-slate-400">${p.month}</td>
                <td class="p-4">₹${p.basic.toLocaleString('en-IN')}</td>
                <td class="p-4 text-emerald-400">+₹${p.allowances.toLocaleString('en-IN')}</td>
                <td class="p-4 text-red-400">-₹${p.deductions.toLocaleString('en-IN')}</td>
                <td class="p-4 font-bold text-white">₹${p.net_salary.toLocaleString('en-IN')}</td>
                <td class="p-4"><span class="px-2 py-0.5 bg-emerald-950 text-emerald-400 text-[10px] font-bold rounded">${p.status}</span></td>
                <td class="p-4">
                    ${p.status === 'Paid' ? `
                        <button onclick="openPayslip('${p.emp_id}', '${p.name}', '${p.month}', ${p.basic}, ${p.allowances}, ${p.deductions}, ${p.net_salary})" class="text-[11px] font-bold text-accentCyan hover:text-cyan-300 transition">View Payslip</button>
                    ` : '<span class="text-slate-500 text-xs">-</span>'}
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Payroll fetch error:", err);
    }
}

async function generatePayroll() {
    const month = document.getElementById('payroll-month-input').value;
    if (!month) {
        alert("Please enter a month (YYYY-MM).");
        return;
    }
    try {
        const res = await fetch(`${API_ERP}/payroll`, {
            method: 'POST',
            headers: {
                'Authorization': AUTH_TOKEN,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ month })
        });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            fetchPayroll();
            fetchFinance();
        }
    } catch (err) {
        alert("Disbursement generation failed.");
    }
}

let attendanceChartInstance = null;

async function fetchAttendance() {
    try {
        const res = await fetch(`${API_ERP}/attendance`, { headers: { 'Authorization': AUTH_TOKEN } });
        const attendance = await res.json();
        const tbody = document.getElementById('attendance-table-body');
        tbody.innerHTML = '';

        const dateLabels = [];
        const hoursData = [];

        attendance.forEach(att => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="p-4 font-bold text-slate-300 text-xs">${att.emp_id}</td>
                <td class="p-4 text-xs">${att.date}</td>
                <td class="p-4 text-xs text-emerald-400 font-semibold">${att.check_in || 'N/A'}</td>
                <td class="p-4 text-xs text-amber-400 font-semibold">${att.check_out || 'N/A'}</td>
                <td class="p-4 text-xs">${att.total_hours} hrs</td>
                <td class="p-4"><span class="px-2.5 py-0.5 bg-emerald-950 text-emerald-400 text-[10px] font-bold rounded-full">${att.status}</span></td>
            `;
            tbody.appendChild(tr);

            // Chart data preparation (latest 8 logs)
            dateLabels.push(`${att.emp_id.replace('KC-EMP-', '#')}`);
            hoursData.push(parseFloat(att.total_hours || 0));
        });

        renderAttendanceChart(dateLabels.slice(-8), hoursData.slice(-8));
    } catch (err) {
        console.error("Attendance log error:", err);
    }
}

async function fetchLeaves() {
    try {
        const res = await fetch(`${API_ERP}/leaves`, { headers: { 'Authorization': AUTH_TOKEN } });
        const leaves = await res.json();
        
        let pendingCount = 0;
        const tbody = document.getElementById('leaves-table-body');
        tbody.innerHTML = '';

        leaves.forEach(l => {
            if (l.status === 'Pending') pendingCount++;
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="p-4 font-bold text-slate-300 text-xs">${l.emp_id}</td>
                <td class="p-4 text-xs"><span class="px-2 py-0.5 bg-slate-900 border border-slate-800 text-white text-[10px] font-bold rounded">${l.leave_type}</span></td>
                <td class="p-4 text-xs text-slate-400">${l.start_date}</td>
                <td class="p-4 text-xs text-slate-400">${l.end_date}</td>
                <td class="p-4 text-xs max-w-xs truncate">${l.reason}</td>
                <td class="p-4 text-xs"><span class="font-bold ${l.status === 'Approved' ? 'text-emerald-400' : (l.status === 'Rejected' ? 'text-red-400' : 'text-amber-400')}">${l.status}</span></td>
                <td class="p-4 flex gap-2">
                    ${l.status === 'Pending' ? `
                        <button onclick="updateLeave(${l.id}, 'Approved')" class="text-xs text-emerald-400 hover:text-emerald-300">Approve</button>
                        <button onclick="updateLeave(${l.id}, 'Rejected')" class="text-xs text-red-400 hover:text-red-300">Reject</button>
                    ` : '<span class="text-slate-500 text-xs">-</span>'}
                </td>
            `;
            tbody.appendChild(tr);
        });
        document.getElementById('dash-leaves-count').textContent = pendingCount;
    } catch (err) {
        console.error("Leaves log error:", err);
    }
}

async function updateLeave(id, status) {
    try {
        await fetch(`${API_ERP}/leaves/${id}`, {
            method: 'PUT',
            headers: {
                'Authorization': AUTH_TOKEN,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status })
        });
        fetchLeaves();
    } catch (err) {
        alert("Leave status update failed.");
    }
}

async function fetchTasks() {
    try {
        const res = await fetch(`${API_ERP}/tasks`, { headers: { 'Authorization': AUTH_TOKEN } });
        const tasks = await res.json();
        
        document.getElementById('dash-tasks-count').textContent = tasks.length;

        const cols = {
            'To Do': document.getElementById('task-col-todo'),
            'In Progress': document.getElementById('task-col-progress'),
            'QA': document.getElementById('task-col-qa'),
            'Done': document.getElementById('task-col-done')
        };

        Object.values(cols).forEach(col => col.innerHTML = '');

        tasks.forEach(t => {
            let checklistItems = [];
            try {
                checklistItems = JSON.parse(t.checklist || '[]');
            } catch(e) {
                checklistItems = [];
            }
            const totalItems = checklistItems.length;
            const completedItems = checklistItems.filter(item => item.completed).length;
            const progressPercent = totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;

            const card = document.createElement('div');
            card.className = 'bg-slate-900 border border-darkBorder p-3 rounded-lg space-y-2 hover:border-accentBlue/60 transition duration-150 cursor-pointer';
            
            // Card click opens checklist details modal
            card.addEventListener('click', (e) => {
                if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION') return;
                openChecklistModal(t.id, t.title, t.assigned_to, checklistItems);
            });

            card.innerHTML = `
                <div class="flex items-start justify-between gap-2">
                    <div class="text-xs font-bold text-white">${t.title}</div>
                    <span class="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider ${t.priority === 'High' ? 'bg-red-950/40 text-red-400' : 'bg-slate-800 text-slate-300'}">${t.priority}</span>
                </div>
                
                ${totalItems > 0 ? `
                <div class="space-y-1 py-1">
                    <div class="flex justify-between text-[9px] text-slate-400">
                        <span>Subtasks</span>
                        <span>${completedItems}/${totalItems} (${progressPercent}%)</span>
                    </div>
                    <div class="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
                        <div class="bg-accentBlue h-full" style="width: ${progressPercent}%"></div>
                    </div>
                </div>
                ` : `
                <div class="text-[9px] text-slate-500 py-1 italic">Click card to create checklist</div>
                `}

                <div class="flex items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-darkBorder/40">
                    <span>Assignee: <strong>${t.assigned_to}</strong></span>
                </div>
                <div class="flex justify-between items-center pt-1.5">
                    <span class="text-[9px] text-slate-500">Due: ${t.deadline}</span>
                    <select onchange="updateTaskStatus(${t.id}, this.value)" class="bg-darkBg border border-darkBorder text-slate-300 text-[10px] p-0.5 rounded">
                        <option value="To Do" ${t.status === 'To Do' ? 'selected' : ''}>To Do</option>
                        <option value="In Progress" ${t.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                        <option value="QA" ${t.status === 'QA' ? 'selected' : ''}>QA</option>
                        <option value="Done" ${t.status === 'Done' ? 'selected' : ''}>Done</option>
                    </select>
                </div>
            `;
            if (cols[t.status]) cols[t.status].appendChild(card);
        });
    } catch (err) {
        console.error("Tasks log error:", err);
    }
}

async function updateTaskStatus(id, status) {
    try {
        await fetch(`${API_ERP}/tasks`, {
            method: 'PUT',
            headers: {
                'Authorization': AUTH_TOKEN,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ id, status })
        });
        fetchTasks();
    } catch (err) {
        alert("Task status update failed.");
    }
}

async function fetchRecruitments() {
    try {
        const res = await fetch(`${API_ERP}/recruitments`, { headers: { 'Authorization': AUTH_TOKEN } });
        const applicants = await res.json();
        const tbody = document.getElementById('recruitments-table-body');
        tbody.innerHTML = '';

        applicants.forEach(app => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="p-4 font-bold text-white">${app.name}</td>
                <td class="p-4 text-xs text-slate-400">${app.email}</td>
                <td class="p-4 text-xs text-slate-300 font-semibold">${app.role}</td>
                <td class="p-4 font-bold text-accentCyan">${app.score}/100</td>
                <td class="p-4"><span class="px-2 py-0.5 bg-slate-900 border border-slate-800 text-white text-[10px] font-bold rounded">${app.status}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Recruitments fetch error:", err);
    }
}

async function fetchFinance() {
    try {
        const res = await fetch(`${API_ERP}/finance`, { headers: { 'Authorization': AUTH_TOKEN } });
        const data = await res.json();

        document.getElementById('fin-expenses').textContent = `₹${data.total_expenses.toLocaleString('en-IN')}`;
        document.getElementById('fin-revenue').textContent = `₹${data.total_revenue.toLocaleString('en-IN')}`;
        document.getElementById('fin-profit').textContent = `₹${data.net_profit.toLocaleString('en-IN')}`;
        document.getElementById('dash-net-profit').textContent = `₹${data.net_profit.toLocaleString('en-IN')}`;

        const tbody = document.getElementById('expenses-table-body');
        tbody.innerHTML = '';

        data.expenses.forEach(exp => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="p-4 font-semibold text-slate-200">${exp.title}</td>
                <td class="p-4 text-xs"><span class="px-2 py-0.5 bg-slate-900 text-slate-300 border border-darkBorder rounded text-[10px]">${exp.category}</span></td>
                <td class="p-4 font-bold text-red-400">₹${exp.amount.toLocaleString('en-IN')}</td>
                <td class="p-4 text-xs text-slate-400">${exp.date}</td>
                <td class="p-4"><span class="px-2.5 py-0.5 bg-emerald-950 text-emerald-400 text-[10px] font-bold rounded-full">${exp.status}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Finance fetch error:", err);
    }
}

// --------------------------------------------------------------------------
// 5. DIALOGS & FORMS PROCESSING
// --------------------------------------------------------------------------
function initForms() {
    // Leave Application Form
    document.getElementById('apply-leave-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            emp_id: document.getElementById('leave-emp-id').value,
            leave_type: document.getElementById('leave-type').value,
            start_date: document.getElementById('leave-start').value,
            end_date: document.getElementById('leave-end').value,
            reason: document.getElementById('leave-reason').value
        };

        try {
            const res = await fetch(`${API_ERP}/leaves`, {
                method: 'POST',
                headers: {
                    'Authorization': AUTH_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                alert("Leave request submitted successfully!");
                document.getElementById('apply-leave-form').reset();
                fetchLeaves();
            }
        } catch (err) {
            alert("Submission error.");
        }
    });

    // Employee Creation
    document.getElementById('add-employee-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            name: document.getElementById('emp-name').value,
            email: document.getElementById('emp-email').value,
            role: document.getElementById('emp-role').value,
            department: document.getElementById('emp-dept').value,
            employment_type: document.getElementById('emp-type').value,
            basic_pay: parseFloat(document.getElementById('emp-pay').value)
        };

        try {
            const res = await fetch(`${API_ERP}/employees`, {
                method: 'POST',
                headers: {
                    'Authorization': AUTH_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                toggleEmployeeModal(false);
                fetchEmployees();
            }
        } catch (err) {
            alert("Failed to register employee profile.");
        }
    });

    // Task Creation
    document.getElementById('create-task-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            title: document.getElementById('task-title').value,
            assigned_to: document.getElementById('task-assignee').value,
            priority: document.getElementById('task-priority').value,
            deadline: document.getElementById('task-deadline').value
        };

        try {
            const res = await fetch(`${API_ERP}/tasks`, {
                method: 'POST',
                headers: {
                    'Authorization': AUTH_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                toggleTaskModal(false);
                fetchTasks();
            }
        } catch (err) {
            alert("Failed to create task.");
        }
    });

    // Expense Creation
    document.getElementById('create-expense-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            title: document.getElementById('exp-title').value,
            category: document.getElementById('exp-cat').value,
            amount: parseFloat(document.getElementById('exp-amount').value)
        };

        try {
            const res = await fetch(`${API_ERP}/finance`, {
                method: 'POST',
                headers: {
                    'Authorization': AUTH_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                toggleExpenseModal(false);
                fetchFinance();
            }
        } catch (err) {
            alert("Failed to log expense.");
        }
    });

    // Recruitment Creation
    document.getElementById('create-rec-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            name: document.getElementById('rec-name').value,
            email: document.getElementById('rec-email').value,
            role: document.getElementById('rec-role').value,
            score: parseInt(document.getElementById('rec-score').value)
        };

        try {
            const res = await fetch(`${API_ERP}/recruitments`, {
                method: 'POST',
                headers: {
                    'Authorization': AUTH_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                toggleRecModal(false);
                fetchRecruitments();
            }
        } catch (err) {
            alert("Failed to register candidate.");
        }
    });
}

function toggleEmployeeModal(show) {
    const modal = document.getElementById('emp-modal');
    if (show) modal.classList.remove('hidden');
    else modal.classList.add('hidden');
}

function toggleTaskModal(show) {
    const modal = document.getElementById('task-modal');
    if (show) modal.classList.remove('hidden');
    else modal.classList.add('hidden');
}

function toggleExpenseModal(show) {
    const modal = document.getElementById('expense-modal');
    if (show) modal.classList.remove('hidden');
    else modal.classList.add('hidden');
}

function toggleRecModal(show) {
    const modal = document.getElementById('rec-modal');
    if (show) modal.classList.remove('hidden');
    else modal.classList.add('hidden');
}

// --------------------------------------------------------------------------
// PAYSLIP GENERATOR & VIEW PANEL
// --------------------------------------------------------------------------
function openPayslip(empId, name, month, basic, allowances, deductions, netSalary) {
    document.getElementById('ps-emp-name').textContent = name;
    document.getElementById('ps-emp-id').textContent = empId;
    document.getElementById('ps-period').textContent = month;
    
    document.getElementById('ps-ref-id').textContent = `REF: KC-PS-${Math.floor(100000 + Math.random() * 900000)}`;

    document.getElementById('ps-basic').textContent = `₹${basic.toLocaleString('en-IN')}`;
    
    // Split allowances & deductions realistically for layout preview
    const travel = Math.round(allowances * 0.6);
    const bonus = Math.round(allowances * 0.4);
    const pf = Math.round(deductions * 0.5);
    const tax = Math.round(deductions * 0.5);

    document.getElementById('ps-allow-travel').textContent = `₹${travel.toLocaleString('en-IN')}`;
    document.getElementById('ps-allow-bonus').textContent = `₹${bonus.toLocaleString('en-IN')}`;
    document.getElementById('ps-ded-pf').textContent = `₹${pf.toLocaleString('en-IN')}`;
    document.getElementById('ps-ded-tax').textContent = `₹${tax.toLocaleString('en-IN')}`;

    document.getElementById('ps-total-allow').textContent = `₹${allowances.toLocaleString('en-IN')}`;
    document.getElementById('ps-total-ded').textContent = `₹${deductions.toLocaleString('en-IN')}`;
    document.getElementById('ps-net-salary').textContent = `₹${netSalary.toLocaleString('en-IN')}`;

    document.getElementById('ps-net-words').textContent = numberToWords(netSalary);

    togglePayslipModal(true);
}

function togglePayslipModal(show) {
    const modal = document.getElementById('payslip-modal');
    if (show) modal.classList.remove('hidden');
    else modal.classList.add('hidden');
}

function numberToWords(num) {
    const a = ['', 'One ', 'Two ', 'Three ', 'Four ', 'Five ', 'Six ', 'Seven ', 'Eight ', 'Nine ', 'Ten ', 'Eleven ', 'Twelve ', 'Thirteen ', 'Fourteen ', 'Fifteen ', 'Sixteen ', 'Seventeen ', 'Eighteen ', 'Nineteen '];
    const b = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];

    if ((num = num.toString()).length > 9) return 'overflow';
    let n = ('000000000' + num).substr(-9).match(/^(\d{2})(\d{2})(\d{2})(\d{1})(\d{2})$/);
    if (!n) return ''; 
    let str = '';
    str += (n[1] != 0) ? (a[Number(n[1])] || b[n[1][0]] + ' ' + a[n[1][1]]) + 'Crore ' : '';
    str += (n[2] != 0) ? (a[Number(n[2])] || b[n[2][0]] + ' ' + a[n[2][1]]) + 'Lakh ' : '';
    str += (n[3] != 0) ? (a[Number(n[3])] || b[n[3][0]] + ' ' + a[n[3][1]]) + 'Thousand ' : '';
    str += (n[4] != 0) ? (a[Number(n[4])] || b[n[4][0]] + ' ' + a[n[4][1]]) + 'Hundred ' : '';
    str += (n[5] != 0) ? ((str != '') ? 'and ' : '') + (a[Number(n[5])] || b[n[5][0]] + ' ' + a[n[5][1]]) + 'Rupees Only' : 'Rupees Only';
    return str;
}

// --------------------------------------------------------------------------
// CHARTJS VISUALIZATION RENDERER
// --------------------------------------------------------------------------
function renderAttendanceChart(labels, dataPoints) {
    const ctx = document.getElementById('attendance-hours-chart');
    if (!ctx) return;

    if (attendanceChartInstance) {
        attendanceChartInstance.destroy();
    }

    attendanceChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Logged Hours',
                data: dataPoints,
                backgroundColor: 'rgba(59, 130, 246, 0.45)',
                borderColor: '#3b82f6',
                borderWidth: 2,
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', font: { size: 9 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { size: 8 } }
                }
            }
        }
    });
}

// --------------------------------------------------------------------------
// KANBAN CARD SUBTASK CHECKLIST SYSTEM
// --------------------------------------------------------------------------
let currentChecklistTaskId = null;
let currentChecklistItems = [];

function openChecklistModal(taskId, title, assignee, items) {
    currentChecklistTaskId = taskId;
    currentChecklistItems = [...items];
    
    document.getElementById('cl-task-title').textContent = title;
    document.getElementById('cl-task-assignee').textContent = assignee;
    
    renderChecklistItems();
    toggleChecklistModal(true);
}

function renderChecklistItems() {
    const container = document.getElementById('cl-items-container');
    container.innerHTML = '';
    
    if (currentChecklistItems.length === 0) {
        container.innerHTML = `<p class="text-xs text-slate-500 italic py-2">No subtasks logged. Add one below.</p>`;
        return;
    }
    
    currentChecklistItems.forEach((item, index) => {
        const row = document.createElement('div');
        row.className = 'flex items-center justify-between p-2 bg-slate-900/40 border border-darkBorder/40 rounded';
        row.innerHTML = `
            <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input type="checkbox" class="rounded border-slate-700 bg-darkBg text-accentBlue" ${item.completed ? 'checked' : ''} onchange="toggleChecklistItemStatus(${index})">
                <span class="${item.completed ? 'line-through text-slate-500' : ''}">${item.text}</span>
            </label>
            <button onclick="removeChecklistItem(${index})" class="text-red-400 hover:text-red-300 text-xs px-1">&times;</button>
        `;
        container.appendChild(row);
    });
}

function toggleChecklistItemStatus(index) {
    currentChecklistItems[index].completed = !currentChecklistItems[index].completed;
    renderChecklistItems();
}

function addChecklistItem() {
    const input = document.getElementById('cl-new-item-input');
    const text = input.value.trim();
    if (!text) return;
    
    currentChecklistItems.push({ text: text, completed: false });
    input.value = '';
    renderChecklistItems();
}

function removeChecklistItem(index) {
    currentChecklistItems.splice(index, 1);
    renderChecklistItems();
}

async function saveChecklist() {
    try {
        const res = await fetch(`${API_ERP}/tasks`, {
            method: 'PUT',
            headers: {
                'Authorization': AUTH_TOKEN,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                id: currentChecklistTaskId,
                checklist: JSON.stringify(currentChecklistItems)
            })
        });
        if (res.ok) {
            toggleChecklistModal(false);
            fetchTasks();
            fetchEmployees(); // Live reload performance scores
        }
    } catch (err) {
        alert("Failed to save subtasks checklist.");
    }
}

function toggleChecklistModal(show) {
    const modal = document.getElementById('checklist-modal');
    if (show) modal.classList.remove('hidden');
    else modal.classList.add('hidden');
}

function toggleLeaveModal(show) {
    const modal = document.getElementById('leave-apply-modal');
    if (show) modal.classList.remove('hidden');
    else modal.classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    const leaveForm = document.getElementById('leave-apply-form');
    if (leaveForm) {
        leaveForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const type = document.getElementById('leave-type-input').value;
            const start = document.getElementById('leave-start-input').value;
            const end = document.getElementById('leave-end-input').value;
            const reason = document.getElementById('leave-reason-input').value;

            try {
                const res = await fetch(`${API_ERP}/leaves`, {
                    method: 'POST',
                    headers: {
                        'Authorization': AUTH_TOKEN,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        emp_id: currentEmpId,
                        leave_type: type,
                        start_date: start,
                        end_date: end,
                        reason: reason
                    })
                });

                const data = await res.json();
                if (data.success) {
                    toggleLeaveModal(false);
                    leaveForm.reset();
                    fetchLeaves();
                } else {
                    alert(data.error || "Failed to submit leave request.");
                }
            } catch (err) {
                alert("Server error submitting leave application.");
            }
        });
    }
});

async function handleClockInOut() {
    try {
        const res = await fetch(`${API_ERP}/attendance`, {
            method: 'POST',
            headers: {
                'Authorization': AUTH_TOKEN,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ emp_id: currentEmpId })
        });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            fetchAttendance();
        } else {
            alert(data.error || "Clocking failed.");
        }
    } catch (err) {
        alert("Attendance clocking error.");
    }
}
