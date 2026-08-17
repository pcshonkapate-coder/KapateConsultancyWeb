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

    // Handle Direct Email & Password Login
    formLogin.addEventListener('submit', async (e) => {
        e.preventDefault();
        alertBox.style.display = 'none';

        const email = document.getElementById('li-email').value.trim();
        const password = document.getElementById('li-password') ? document.getElementById('li-password').value.trim() : '';

        try {
            const res = await fetch('/api/erp/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (data.success) {
                localStorage.setItem('kc_erp_token', data.token || AUTH_TOKEN);
                localStorage.setItem('kc_erp_role', data.role || 'Admin');
                localStorage.setItem('kc_erp_name', data.name || 'Staff Member');
                localStorage.setItem('kc_erp_id', data.emp_id || 'KC-EMP-101');
                
                currentRole = data.role || 'Admin';
                currentEmpId = data.emp_id || 'KC-EMP-101';
                
                loginPage.style.display = 'none';
                erpLayout.classList.remove('hidden');
                setupRoleAccess(data.name);
                loadAllERPData();
            } else {
                alertBox.className = 'auth-alert error';
                alertBox.textContent = data.error || 'Invalid credentials.';
                alertBox.style.display = 'block';
            }
        } catch (err) {
            alertBox.className = 'auth-alert error';
            alertBox.textContent = 'Server connection error: ' + err.message;
            alertBox.style.display = 'block';
        }
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
    fetchClients();
    fetchInvoices();
    fetchProjects();
    fetchTimesheets();
    fetchInquiries();
}

async function confirmResetDatabase() {
    if (!confirm("Are you sure you want to reset the database to a completely fresh state?\n\nThis will clear all sample/stored records and start with empty tables.")) return;
    try {
        const res = await fetch(`/api/admin/reset-database`, {
            method: 'POST',
            headers: { 'Authorization': AUTH_TOKEN }
        });
        const data = await res.json();
        if (data.success) {
            alert("Database reset to fresh state successfully!");
            loadAllERPData();
        } else {
            alert("Reset failed: " + (data.error || "Unknown error"));
        }
    } catch (err) {
        alert("Reset error: " + err.message);
    }
}

window.allEmployees = [];

async function fetchEmployees() {
    try {
        const res = await fetch(`${API_ERP}/employees`, { headers: { 'Authorization': AUTH_TOKEN } });
        const employees = await res.json();
        window.allEmployees = employees || [];
        document.getElementById('dash-staff-count').textContent = employees.length;

        const tbody = document.getElementById('employees-table-body');
        tbody.innerHTML = '';

        if (employees.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="p-12 text-center text-slate-500">
                        <div class="text-3xl mb-2">👤</div>
                        <div class="text-sm font-semibold text-slate-300">No employees registered yet</div>
                        <div class="text-xs text-slate-500 mt-1">Click "+ Register Employee" to onboard your staff.</div>
                    </td>
                </tr>
            `;
            populateAssigneeSelect([]);
            return;
        }

        populateAssigneeSelect(employees);

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
                <td class="p-4 font-semibold text-slate-200">
                    <div>${emp.name}</div>
                    <div class="text-[10px] text-slate-500 font-normal">Joined: ${emp.join_date || 'N/A'}</div>
                </td>
                <td class="p-4 text-xs text-slate-400">${emp.email}</td>
                <td class="p-4 text-xs">${emp.department} / <span class="text-accentBlue font-medium">${emp.role}</span></td>
                <td class="p-4 text-xs text-slate-400">${emp.employment_type}</td>
                <td class="p-4 font-bold text-slate-200">₹${(emp.basic_pay || 0).toLocaleString('en-IN')}</td>
                <td class="p-4">
                    <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold border ${badgeClass}">
                        ${score}% - ${label}
                    </span>
                </td>
                <td class="p-4">
                    <div class="flex items-center gap-3">
                        <button onclick="openEmployeeProfile('${emp.emp_id}')" class="text-xs text-accentCyan hover:text-cyan-300 font-semibold">Profile</button>
                        <button onclick="deleteEmployee(${emp.id})" class="text-xs text-red-400 hover:text-red-300">Remove</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Fetch employees error:", err);
    }
}

function populateAssigneeSelect(employees) {
    const select = document.getElementById('task-assignee-select');
    if (!select) return;
    select.innerHTML = '<option value="">-- Select Employee --</option>';
    if (!employees || employees.length === 0) {
        select.innerHTML += '<option value="General Admin">General Admin (No employees yet)</option>';
        return;
    }
    employees.forEach(emp => {
        const opt = document.createElement('option');
        opt.value = `${emp.name} (${emp.emp_id})`;
        opt.textContent = `${emp.name} — ${emp.role} (${emp.emp_id})`;
        select.appendChild(opt);
    });
}

function toggleProfileModal(show) {
    const modal = document.getElementById('emp-profile-modal');
    if (modal) modal.classList.toggle('hidden', !show);
}

function openEmployeeProfile(empId) {
    const emp = (window.allEmployees || []).find(e => e.emp_id === empId);
    if (!emp) return;
    
    document.getElementById('profile-modal-name').textContent = emp.name;
    document.getElementById('profile-modal-role-dept').textContent = `${emp.role} • ${emp.department}`;
    document.getElementById('profile-modal-id').textContent = emp.emp_id;
    document.getElementById('profile-modal-email').textContent = emp.email;
    document.getElementById('profile-modal-type').textContent = emp.employment_type;
    if (document.getElementById('profile-modal-pass')) {
        document.getElementById('profile-modal-pass').textContent = emp.password || 'Kapate@123';
    }
    document.getElementById('profile-modal-basic').textContent = `₹${(emp.basic_pay || 0).toLocaleString('en-IN')}`;
    document.getElementById('profile-modal-allowances').textContent = `+₹${(emp.allowances || 0).toLocaleString('en-IN')}`;
    document.getElementById('profile-modal-deductions').textContent = `-₹${(emp.deductions || 0).toLocaleString('en-IN')}`;
    
    const initials = emp.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    document.getElementById('profile-modal-avatar').textContent = initials;

    const tasksList = document.getElementById('profile-modal-tasks-list');
    tasksList.innerHTML = '';
    const empTasks = (window.allTasks || []).filter(t => (t.assigned_to && t.assigned_to.includes(emp.emp_id)) || (t.assigned_to === emp.name));
    
    if (empTasks.length === 0) {
        tasksList.innerHTML = '<div class="text-slate-500 text-[11px] italic">No active work assigned to this employee.</div>';
    } else {
        empTasks.forEach(t => {
            const item = document.createElement('div');
            item.className = 'p-2.5 bg-slate-800 rounded-lg border border-darkBorder flex justify-between items-center text-[11px]';
            item.innerHTML = `
                <div>
                    <div class="font-semibold text-white">${t.title}</div>
                    <div class="text-slate-400 text-[10px]">Deadline: ${t.deadline}</div>
                </div>
                <span class="px-2 py-0.5 rounded text-[9px] font-bold ${t.status === 'Done' ? 'bg-emerald-950 text-emerald-400' : 'bg-blue-950 text-accentBlue'}">${t.status}</span>
            `;
            tasksList.appendChild(item);
        });
    }

    toggleProfileModal(true);
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

window.allTasks = [];

async function fetchTasks() {
    try {
        const res = await fetch(`${API_ERP}/tasks`, { headers: { 'Authorization': AUTH_TOKEN } });
        const tasks = await res.json();
        window.allTasks = tasks || [];
        
        document.getElementById('dash-tasks-count').textContent = tasks.length;

        const cols = {
            'To Do': document.getElementById('task-col-todo'),
            'In Progress': document.getElementById('task-col-progress'),
            'QA': document.getElementById('task-col-qa'),
            'Done': document.getElementById('task-col-done')
        };

        Object.values(cols).forEach(col => {
            if (col) col.innerHTML = '';
        });

        const countsPerCol = { 'To Do': 0, 'In Progress': 0, 'QA': 0, 'Done': 0 };

        if (!tasks || tasks.length === 0) {
            Object.keys(cols).forEach(key => {
                if (cols[key]) {
                    cols[key].innerHTML = `
                        <div class="p-6 border border-dashed border-darkBorder/60 rounded-xl text-center text-slate-500 text-xs font-medium">
                            No work assigned yet
                        </div>
                    `;
                }
            });
            return;
        }

        tasks.forEach(t => {
            if (countsPerCol.hasOwnProperty(t.status)) {
                countsPerCol[t.status]++;
            }

            let checklistItems = [];
            try {
                checklistItems = JSON.parse(t.checklist || '[]');
            } catch(e) {
                checklistItems = [];
            }
            const totalItems = checklistItems.length;
            const completedItems = checklistItems.filter(item => item.completed).length;
            const progressPercent = totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;

            let prioBadge = 'bg-slate-800 text-slate-300';
            if (t.priority === 'Urgent') prioBadge = 'bg-red-950/80 text-red-400 border border-red-500/30';
            else if (t.priority === 'High') prioBadge = 'bg-amber-950/80 text-amber-400 border border-amber-500/30';
            else if (t.priority === 'Medium') prioBadge = 'bg-blue-950/80 text-accentBlue border border-accentBlue/30';

            const card = document.createElement('div');
            card.className = 'bg-slate-900 border border-darkBorder p-3.5 rounded-xl space-y-2 hover:border-accentBlue/60 transition duration-150 shadow-md relative group';
            
            card.addEventListener('click', (e) => {
                if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.closest('.delete-task-btn')) return;
                openChecklistModal(t.id, t.title, t.assigned_to, checklistItems);
            });

            card.innerHTML = `
                <div class="flex items-start justify-between gap-2">
                    <div class="text-xs font-bold text-white leading-snug">${t.title}</div>
                    <div class="flex items-center gap-1">
                        <span class="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider ${prioBadge}">${t.priority}</span>
                        <button onclick="deleteTask(${t.id})" class="delete-task-btn text-slate-500 hover:text-red-400 text-xs px-1" title="Delete Task">✕</button>
                    </div>
                </div>

                ${t.description ? `<p class="text-[11px] text-slate-400 line-clamp-2">${t.description}</p>` : ''}
                
                ${totalItems > 0 ? `
                <div class="space-y-1 py-1">
                    <div class="flex justify-between text-[9px] text-slate-400">
                        <span>Subtasks</span>
                        <span>${completedItems}/${totalItems} (${progressPercent}%)</span>
                    </div>
                    <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div class="bg-accentBlue h-full transition-all duration-300" style="width: ${progressPercent}%"></div>
                    </div>
                </div>
                ` : `
                <div class="text-[9px] text-slate-500 py-0.5 italic">Click card to view/add subtasks</div>
                `}

                <div class="flex items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-darkBorder/40">
                    <span class="truncate max-w-[130px]">👤 <strong>${t.assigned_to}</strong></span>
                    <span class="text-[9px] text-slate-500">📅 ${t.deadline}</span>
                </div>
                <div class="pt-1 flex justify-end">
                    <select onchange="updateTaskStatus(${t.id}, this.value)" class="bg-darkBg border border-darkBorder text-slate-300 text-[10px] px-2 py-1 rounded-lg focus:outline-none">
                        <option value="To Do" ${t.status === 'To Do' ? 'selected' : ''}>To Do</option>
                        <option value="In Progress" ${t.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                        <option value="QA" ${t.status === 'QA' ? 'selected' : ''}>QA / Review</option>
                        <option value="Done" ${t.status === 'Done' ? 'selected' : ''}>Done</option>
                    </select>
                </div>
            `;
            if (cols[t.status]) cols[t.status].appendChild(card);
        });

        // Fill empty state for columns with 0 tasks
        Object.keys(cols).forEach(key => {
            if (countsPerCol[key] === 0 && cols[key]) {
                cols[key].innerHTML = `
                    <div class="p-6 border border-dashed border-darkBorder/60 rounded-xl text-center text-slate-600 text-xs font-medium">
                        No work items
                    </div>
                `;
            }
        });
    } catch (err) {
        console.error("Tasks log error:", err);
    }
}

async function deleteTask(taskId) {
    if (!confirm("Are you sure you want to delete this task assignment?")) return;
    try {
        await fetch(`${API_ERP}/tasks/${taskId}`, {
            method: 'DELETE',
            headers: { 'Authorization': AUTH_TOKEN }
        });
        fetchTasks();
    } catch (err) {
        alert("Failed to delete task.");
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
            password: document.getElementById('emp-password') ? document.getElementById('emp-password').value : 'Kapate@123',
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
            const data = await res.json();
            if (res.ok && data.success) {
                toggleEmployeeModal(false);
                document.getElementById('add-employee-form').reset();
                alert(`Employee profile created successfully!\n\nEmail: ${payload.email}\nPassword: ${payload.password}\nEmployee ID: ${data.emp_id}`);
                fetchEmployees();
            } else {
                alert("Failed to register employee: " + (data.error || "Unknown error"));
            }
        } catch (err) {
            alert("Failed to register employee profile: " + err.message);
        }
    });

    // Task Creation / Work Assignment
    document.getElementById('create-task-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const assigneeSelect = document.getElementById('task-assignee-select');
        const assignedToVal = assigneeSelect ? assigneeSelect.value : 'General Admin';
        
        if (!assignedToVal) {
            alert("Please select an employee to assign work to.");
            return;
        }

        const checklistRaw = document.getElementById('task-checklist-input') ? document.getElementById('task-checklist-input').value : '';
        const checklist = checklistRaw
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => ({ title: line, completed: false }));

        const payload = {
            title: document.getElementById('task-title').value,
            description: document.getElementById('task-desc') ? document.getElementById('task-desc').value : '',
            assigned_to: assignedToVal,
            priority: document.getElementById('task-priority').value,
            deadline: document.getElementById('task-deadline').value,
            checklist: checklist
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
                document.getElementById('create-task-form').reset();
                fetchTasks();
            } else {
                alert("Failed to assign work task.");
            }
        } catch (err) {
            alert("Failed to create task: " + err.message);
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

    // Client Creation
    if (document.getElementById('create-client-form')) {
        document.getElementById('create-client-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                name: document.getElementById('cli-name').value,
                company: document.getElementById('cli-company').value,
                email: document.getElementById('cli-email').value,
                phone: document.getElementById('cli-phone').value,
                tag: document.getElementById('cli-tag').value,
                total_spent: parseFloat(document.getElementById('cli-spent').value || 0),
                notes: document.getElementById('cli-notes').value
            };
            try {
                const res = await fetch(`${API_ERP}/clients`, {
                    method: 'POST',
                    headers: { 'Authorization': AUTH_TOKEN, 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    toggleClientModal(false);
                    document.getElementById('create-client-form').reset();
                    fetchClients();
                } else {
                    alert("Failed to create client profile.");
                }
            } catch (err) {
                alert("Failed to create client: " + err.message);
            }
        });
    }

    // Invoice Creation
    if (document.getElementById('create-invoice-form')) {
        document.getElementById('create-invoice-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const clientVal = document.getElementById('inv-client-select').value;
            if (!clientVal) {
                alert("Please select a client to bill.");
                return;
            }
            const parts = clientVal.split('(');
            const clientName = parts[0].strip ? parts[0].strip() : parts[0].trim();
            const clientEmail = parts[1] ? parts[1].replace(')', '').trim() : '';

            const amount = parseFloat(document.getElementById('inv-amount').value || 0);
            const payload = {
                client_name: clientName,
                client_email: clientEmail,
                service: document.getElementById('inv-service').value,
                amount: amount,
                tax_gst: amount * 0.18,
                due_date: document.getElementById('inv-due-date').value,
                status: document.getElementById('inv-status').value
            };
            try {
                const res = await fetch(`${API_ERP}/invoices`, {
                    method: 'POST',
                    headers: { 'Authorization': AUTH_TOKEN, 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    toggleInvoiceModal(false);
                    document.getElementById('create-invoice-form').reset();
                    fetchInvoices();
                } else {
                    alert("Failed to generate invoice.");
                }
            } catch (err) {
                alert("Invoice generation error: " + err.message);
            }
        });
    }

    // Project Creation
    if (document.getElementById('create-project-form')) {
        document.getElementById('create-project-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const clientVal = document.getElementById('proj-client-select').value;
            const clientName = clientVal ? clientVal.split('(')[0].trim() : 'Corporate Client';
            const payload = {
                title: document.getElementById('proj-title').value,
                client_name: clientName,
                service: document.getElementById('proj-service').value,
                budget: parseFloat(document.getElementById('proj-budget').value || 0),
                deadline: document.getElementById('proj-deadline').value,
                status: 'Pending',
                progress: 10
            };
            try {
                const res = await fetch(`${API_ERP}/projects`, {
                    method: 'POST',
                    headers: { 'Authorization': AUTH_TOKEN, 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    toggleProjectModal(false);
                    document.getElementById('create-project-form').reset();
                    fetchProjects();
                } else {
                    alert("Failed to create project.");
                }
            } catch (err) {
                alert("Project creation error: " + err.message);
            }
        });
    }

    // Timesheet Creation
    if (document.getElementById('create-timesheet-form')) {
        document.getElementById('create-timesheet-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const projVal = document.getElementById('ts-project-select').value;
            const projectTitle = projVal ? projVal.split('(')[0].trim() : 'Consulting Services';
            const clientName = (projVal && projVal.includes('Client:')) ? projVal.split('Client:')[1].replace(')', '').trim() : 'Client';
            const payload = {
                emp_id: currentEmpId,
                emp_name: (localStorage.getItem('kc_erp_name') || 'Shon Kapate'),
                project_title: projectTitle,
                client_name: clientName,
                hours_logged: parseFloat(document.getElementById('ts-hours').value || 0),
                billable_rate: parseFloat(document.getElementById('ts-rate').value || 1500),
                description: document.getElementById('ts-desc').value,
                date: new Date().toISOString().substring(0, 10)
            };
            try {
                const res = await fetch(`${API_ERP}/timesheets`, {
                    method: 'POST',
                    headers: { 'Authorization': AUTH_TOKEN, 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    toggleTimesheetModal(false);
                    document.getElementById('create-timesheet-form').reset();
                    fetchTimesheets();
                } else {
                    alert("Failed to log timesheet.");
                }
            } catch (err) {
                alert("Timesheet error: " + err.message);
            }
        });
    }
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


// --------------------------------------------------------------------------
// CONSULTANCY OPERATIONS MODULES (Clients, Invoices, Projects, Timesheets, Inquiries)
// --------------------------------------------------------------------------

window.allClients = [];
window.allInvoices = [];
window.allProjects = [];
window.allTimesheets = [];
window.allInquiries = [];

// 1. CLIENTS CRM
async function fetchClients() {
    try {
        const res = await fetch(`${API_ERP}/clients`, { headers: { 'Authorization': AUTH_TOKEN } });
        const clients = await res.json();
        window.allClients = clients || [];
        renderClientsTable(window.allClients);
        populateClientSelectors(window.allClients);
    } catch (err) {
        console.error("Fetch clients error:", err);
    }
}

function renderClientsTable(clients) {
    const tbody = document.getElementById('clients-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!clients || clients.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-slate-500 italic">No corporate clients registered yet. Click "+ Add Client Profile" to add your first client.</td></tr>`;
        return;
    }
    clients.forEach(cli => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-900/40 transition border-b border-darkBorder/40';
        tr.innerHTML = `
            <td class="p-4">
                <div class="font-bold text-white">${cli.name}</div>
                <div class="text-xs text-accentBlue font-medium">${cli.company || 'N/A'}</div>
            </td>
            <td class="p-4">
                <div class="text-xs text-slate-300 font-mono">${cli.email}</div>
                <div class="text-[11px] text-slate-400 font-mono">${cli.phone || 'N/A'}</div>
            </td>
            <td class="p-4">
                <span class="px-2.5 py-1 text-[10px] font-bold rounded-full bg-accentBlue/10 text-accentBlue border border-accentBlue/20">${cli.tag || 'VIP'}</span>
            </td>
            <td class="p-4 font-mono font-bold text-emerald-400">
                ₹${(cli.total_spent || 0).toLocaleString('en-IN')}
            </td>
            <td class="p-4">
                <span class="px-2 py-0.5 text-[10px] font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${cli.status || 'Active'}</span>
            </td>
            <td class="p-4">
                <button onclick="deleteClient(${cli.id})" class="text-xs text-red-400 hover:text-red-300">Remove</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filterClientsTable() {
    const q = (document.getElementById('client-search-input')?.value || '').toLowerCase();
    const filtered = (window.allClients || []).filter(c => 
        (c.name || '').toLowerCase().includes(q) ||
        (c.company || '').toLowerCase().includes(q) ||
        (c.email || '').toLowerCase().includes(q) ||
        (c.tag || '').toLowerCase().includes(q)
    );
    renderClientsTable(filtered);
}

function populateClientSelectors(clients) {
    const invSelect = document.getElementById('inv-client-select');
    const projSelect = document.getElementById('proj-client-select');
    
    [invSelect, projSelect].forEach(select => {
        if (!select) return;
        select.innerHTML = '<option value="">-- Select Client --</option>';
        clients.forEach(c => {
            const opt = document.createElement('option');
            opt.value = `${c.company || c.name} (${c.email})`;
            opt.textContent = `${c.name} — ${c.company || 'Client'} (${c.email})`;
            select.appendChild(opt);
        });
    });
}

function toggleClientModal(show) {
    const modal = document.getElementById('client-modal');
    if (modal) modal.classList.toggle('hidden', !show);
}

async function deleteClient(id) {
    if (!confirm("Are you sure you want to remove this client profile?")) return;
    try {
        const res = await fetch(`${API_ERP}/clients/${id}`, { method: 'DELETE', headers: { 'Authorization': AUTH_TOKEN } });
        if (res.ok) fetchClients();
    } catch (err) {
        alert("Failed to delete client.");
    }
}

// 2. INVOICING MODULE
async function fetchInvoices() {
    try {
        const res = await fetch(`${API_ERP}/invoices`, { headers: { 'Authorization': AUTH_TOKEN } });
        const invoices = await res.json();
        window.allInvoices = invoices || [];
        renderInvoicesTable(window.allInvoices);
        updateInvoiceStats(window.allInvoices);
    } catch (err) {
        console.error("Fetch invoices error:", err);
    }
}

function renderInvoicesTable(invoices) {
    const tbody = document.getElementById('invoices-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!invoices || invoices.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" class="p-8 text-center text-slate-500 italic">No invoices generated yet. Click "+ Create Invoice / Proposal" to bill a client.</td></tr>`;
        return;
    }
    invoices.forEach(inv => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-900/40 transition border-b border-darkBorder/40';
        const isPaid = inv.status === 'Paid';
        tr.innerHTML = `
            <td class="p-4 font-mono text-xs text-slate-300 font-bold">${inv.invoice_no}</td>
            <td class="p-4">
                <div class="font-bold text-white">${inv.client_name}</div>
                <div class="text-[11px] text-slate-400 font-mono">${inv.client_email || ''}</div>
            </td>
            <td class="p-4 text-xs text-accentBlue font-medium">${inv.service}</td>
            <td class="p-4 font-mono font-bold text-white">₹${(inv.amount || 0).toLocaleString('en-IN')}</td>
            <td class="p-4 font-mono text-slate-400">₹${(inv.tax_gst || 0).toLocaleString('en-IN')}</td>
            <td class="p-4 font-mono font-bold text-emerald-400">₹${(inv.total_amount || 0).toLocaleString('en-IN')}</td>
            <td class="p-4 text-xs text-slate-400">${inv.due_date || 'N/A'}</td>
            <td class="p-4">
                <span class="px-2.5 py-1 text-[10px] font-bold rounded-full ${isPaid ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}">${inv.status}</span>
            </td>
            <td class="p-4">
                <div class="flex items-center gap-2">
                    <button onclick="openInvoicePrintModal(${inv.id})" class="text-xs text-accentBlue hover:text-blue-300 font-semibold">View/Print</button>
                    <button onclick="deleteInvoice(${inv.id})" class="text-xs text-red-400 hover:text-red-300">Delete</button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function updateInvoiceStats(invoices) {
    let total = 0, paid = 0, unpaid = 0;
    (invoices || []).forEach(i => {
        total += (i.total_amount || 0);
        if (i.status === 'Paid') paid += (i.total_amount || 0);
        else unpaid += (i.total_amount || 0);
    });
    if (document.getElementById('inv-stat-total')) document.getElementById('inv-stat-total').textContent = `₹${total.toLocaleString('en-IN')}`;
    if (document.getElementById('inv-stat-paid')) document.getElementById('inv-stat-paid').textContent = `₹${paid.toLocaleString('en-IN')}`;
    if (document.getElementById('inv-stat-unpaid')) document.getElementById('inv-stat-unpaid').textContent = `₹${unpaid.toLocaleString('en-IN')}`;
}

function toggleInvoiceModal(show) {
    const modal = document.getElementById('invoice-modal');
    if (modal) modal.classList.toggle('hidden', !show);
}

function toggleInvoicePrintModal(show) {
    const modal = document.getElementById('invoice-printable-modal');
    if (modal) modal.classList.toggle('hidden', !show);
}

function openInvoicePrintModal(invoiceId) {
    const inv = (window.allInvoices || []).find(i => i.id === invoiceId);
    if (!inv) return;
    
    document.getElementById('inv-pr-no').textContent = inv.invoice_no;
    document.getElementById('inv-pr-client').textContent = inv.client_name;
    document.getElementById('inv-pr-email').textContent = inv.client_email || 'office@client.com';
    document.getElementById('inv-pr-dates').textContent = `Issue: ${inv.issue_date || 'N/A'} | Due: ${inv.due_date || 'N/A'}`;
    document.getElementById('inv-pr-service').textContent = inv.service;
    document.getElementById('inv-pr-subtotal').textContent = `₹${(inv.amount || 0).toLocaleString('en-IN')}`;
    document.getElementById('inv-pr-gst').textContent = `₹${(inv.tax_gst || 0).toLocaleString('en-IN')}`;
    document.getElementById('inv-pr-total').textContent = `₹${(inv.total_amount || 0).toLocaleString('en-IN')}`;
    document.getElementById('inv-pr-status').textContent = (inv.status || 'INVOICE').toUpperCase();
    
    toggleInvoicePrintModal(true);
}

async function deleteInvoice(id) {
    if (!confirm("Are you sure you want to delete this invoice?")) return;
    try {
        const res = await fetch(`${API_ERP}/invoices/${id}`, { method: 'DELETE', headers: { 'Authorization': AUTH_TOKEN } });
        if (res.ok) fetchInvoices();
    } catch (err) {
        alert("Failed to delete invoice.");
    }
}

// 3. CONSULTING PROJECTS
async function fetchProjects() {
    try {
        const res = await fetch(`${API_ERP}/projects`, { headers: { 'Authorization': AUTH_TOKEN } });
        const projects = await res.json();
        window.allProjects = projects || [];
        renderProjectsTable(window.allProjects);
        populateProjectSelectors(window.allProjects);
    } catch (err) {
        console.error("Fetch projects error:", err);
    }
}

function renderProjectsTable(projects) {
    const tbody = document.getElementById('projects-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!projects || projects.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-slate-500 italic">No consulting projects active. Click "+ Create Project" to start a new retainer.</td></tr>`;
        return;
    }
    projects.forEach(p => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-900/40 transition border-b border-darkBorder/40';
        tr.innerHTML = `
            <td class="p-4 font-bold text-white">${p.title}</td>
            <td class="p-4 text-xs text-slate-300">${p.client_name}</td>
            <td class="p-4 text-xs text-accentBlue font-semibold">${p.service}</td>
            <td class="p-4 font-mono font-bold text-emerald-400">₹${(p.budget || 0).toLocaleString('en-IN')}</td>
            <td class="p-4">
                <div class="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-darkBorder">
                    <div class="bg-accentBlue h-full rounded-full" style="width: ${p.progress || 10}%"></div>
                </div>
                <div class="text-[10px] text-slate-400 mt-1">${p.progress || 10}% Complete</div>
            </td>
            <td class="p-4">
                <span class="px-2 py-0.5 text-[10px] font-bold rounded bg-blue-500/10 text-accentBlue border border-blue-500/20">${p.status || 'Pending'}</span>
            </td>
            <td class="p-4 text-xs text-slate-400">${p.deadline || 'N/A'}</td>
        `;
        tbody.appendChild(tr);
    });
}

function populateProjectSelectors(projects) {
    const select = document.getElementById('ts-project-select');
    if (!select) return;
    select.innerHTML = '<option value="">-- Select Project & Client --</option>';
    projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = `${p.title} (${p.client_name})`;
        opt.textContent = `${p.title} — Client: ${p.client_name}`;
        select.appendChild(opt);
    });
}

function toggleProjectModal(show) {
    const modal = document.getElementById('project-modal');
    if (modal) modal.classList.toggle('hidden', !show);
}

// 4. BILLABLE TIMESHEETS
async function fetchTimesheets() {
    try {
        const res = await fetch(`${API_ERP}/timesheets`, { headers: { 'Authorization': AUTH_TOKEN } });
        const timesheets = await res.json();
        window.allTimesheets = timesheets || [];
        renderTimesheetsTable(window.allTimesheets);
    } catch (err) {
        console.error("Fetch timesheets error:", err);
    }
}

function renderTimesheetsTable(timesheets) {
    const tbody = document.getElementById('timesheets-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!timesheets || timesheets.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-slate-500 italic">No billable timesheets logged yet. Click "+ Log Billable Hours" to record consulting work.</td></tr>`;
        return;
    }
    timesheets.forEach(ts => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-900/40 transition border-b border-darkBorder/40';
        const totalAmt = (ts.hours_logged || 0) * (ts.billable_rate || 0);
        tr.innerHTML = `
            <td class="p-4 font-bold text-white">${ts.emp_name}</td>
            <td class="p-4">
                <div class="text-xs text-accentBlue font-medium">${ts.project_title}</div>
                <div class="text-[10px] text-slate-400">${ts.client_name}</div>
            </td>
            <td class="p-4 font-mono font-bold text-white">${ts.hours_logged} hrs</td>
            <td class="p-4 font-mono text-slate-300">₹${(ts.billable_rate || 0).toLocaleString('en-IN')}</td>
            <td class="p-4 font-mono font-bold text-emerald-400">₹${totalAmt.toLocaleString('en-IN')}</td>
            <td class="p-4 text-xs text-slate-400">${ts.date}</td>
            <td class="p-4 text-xs text-slate-300 max-w-xs truncate">${ts.description || ''}</td>
            <td class="p-4">
                <button onclick="deleteTimesheet(${ts.id})" class="text-xs text-red-400 hover:text-red-300">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function toggleTimesheetModal(show) {
    const modal = document.getElementById('timesheet-modal');
    if (modal) modal.classList.toggle('hidden', !show);
}

async function deleteTimesheet(id) {
    if (!confirm("Are you sure you want to delete this timesheet entry?")) return;
    try {
        const res = await fetch(`${API_ERP}/timesheets/${id}`, { method: 'DELETE', headers: { 'Authorization': AUTH_TOKEN } });
        if (res.ok) fetchTimesheets();
    } catch (err) {
        alert("Failed to delete timesheet entry.");
    }
}

// 5. SERVICE INQUIRIES & LEAD CONVERSION
async function fetchInquiries() {
    try {
        const res = await fetch(`${API_ERP}/inquiries`, { headers: { 'Authorization': AUTH_TOKEN } });
        const inquiries = await res.json();
        window.allInquiries = inquiries || [];
        renderInquiriesTable(window.allInquiries);
    } catch (err) {
        console.error("Fetch inquiries error:", err);
    }
}

function renderInquiriesTable(inquiries) {
    const tbody = document.getElementById('inquiries-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!inquiries || inquiries.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-slate-500 italic">No web inquiries received yet. Inquiry form submissions on website will populate here automatically.</td></tr>`;
        return;
    }
    inquiries.forEach(inq => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-900/40 transition border-b border-darkBorder/40';
        const isConverted = inq.status === 'Converted';
        tr.innerHTML = `
            <td class="p-4 font-bold text-white">${inq.name}</td>
            <td class="p-4 font-mono text-xs text-slate-300">${inq.email}<br><span class="text-slate-500">${inq.phone || ''}</span></td>
            <td class="p-4 text-xs text-slate-300">${inq.company || 'N/A'}</td>
            <td class="p-4 text-xs text-accentBlue font-medium">${inq.service || 'General Inquiry'}</td>
            <td class="p-4 text-xs text-slate-300 max-w-xs truncate">${inq.message || ''}</td>
            <td class="p-4 text-xs text-slate-400">${(inq.created_at || '').substring(0, 10)}</td>
            <td class="p-4">
                <span class="px-2 py-0.5 text-[10px] font-bold rounded ${isConverted ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-blue-500/10 text-accentBlue border border-blue-500/20'}">${inq.status || 'New'}</span>
            </td>
            <td class="p-4">
                ${!isConverted ? `<button onclick="convertInquiryToClient(${inq.id})" class="px-3 py-1 bg-accentBlue hover:bg-blue-600 text-white font-semibold text-[11px] rounded transition">Convert to Client</button>` : `<span class="text-[11px] text-emerald-400 font-semibold">Active CRM Client</span>`}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function convertInquiryToClient(inquiryId) {
    try {
        const res = await fetch(`/api/admin/convert-inquiry/${inquiryId}`, { method: 'POST', headers: { 'Authorization': AUTH_TOKEN } });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            fetchInquiries();
            fetchClients();
        } else {
            alert("Conversion failed: " + data.error);
        }
    } catch (err) {
        alert("Conversion error: " + err.message);
    }
}
