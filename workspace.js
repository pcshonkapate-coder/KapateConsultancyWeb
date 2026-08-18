// ==========================================================================
// KAPATE WORKSPACE CONTROLLER — CEO & ENTERPRISE CONTROL CENTER
// Professional Enterprise SaaS Architecture (Zero Emojis, Pure SVG Tokens)
// ==========================================================================

const API_BASE = (window.location.protocol === 'file:' || (window.location.port && window.location.port !== '8080')) 
  ? 'http://127.0.0.1:8080/api/workspace' 
  : '/api/workspace';

let currentUser = null;
let currentToken = localStorage.getItem('kw_token') || '';
let activeStopwatchInterval = null;
let stopwatchSeconds = 0;
let activeChatChannel = 'chan-general';
let currentViewingEmpId = null;
let allEmployeesCache = [];
let allTasksCache = [];
let perfChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
  initAuth();
  initNavigation();
  initModals();
  initTheme();
  initOmniSearch();
  initStopwatch();
  initKapateAI();
  initProfileSubtabs();
});

// ==========================================================================
// 1. AUTHENTICATION & ROLE SESSION SETUP
// ==========================================================================
function initAuth() {
  const authScreen = document.getElementById('auth-screen');
  const appShell = document.getElementById('app-shell');
  const loginForm = document.getElementById('login-form');
  const loginAlert = document.getElementById('login-alert');
  const loginAlertMsg = document.getElementById('login-alert-msg');
  const btnLogout = document.getElementById('btn-logout');

  // Demo Profile 1-Click Fill Buttons
  document.querySelectorAll('.demo-fill-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('login-username').value = btn.dataset.user;
      document.getElementById('login-password').value = btn.dataset.pwd;
      loginForm.dispatchEvent(new Event('submit'));
    });
  });

  // Handle Login Submit
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginAlert.classList.add('hidden');
    const submitBtn = document.getElementById('btn-login-submit');
    submitBtn.innerHTML = '<span>Verifying credentials...</span>';
    submitBtn.disabled = true;

    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value.trim();

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();

      if (res.ok && data.success) {
        currentToken = data.token;
        currentUser = data.user;
        localStorage.setItem('kw_token', currentToken);
        localStorage.setItem('kw_user', JSON.stringify(currentUser));

        authScreen.classList.add('hidden');
        appShell.classList.remove('hidden');
        setupRoleSession();
        loadAllWorkspaceData();
        showToast(`Authenticated as ${currentUser.name} (${currentUser.role})`, 'success');
      } else {
        loginAlertMsg.textContent = data.error || 'Authentication failed.';
        loginAlert.classList.remove('hidden');
      }
    } catch (err) {
      loginAlertMsg.textContent = 'Server connection error. Please verify backend service.';
      loginAlert.classList.remove('hidden');
    } finally {
      submitBtn.innerHTML = '<span>Authenticate &amp; Enter Workspace &rarr;</span>';
      submitBtn.disabled = false;
    }
  });

  // Logout
  btnLogout.addEventListener('click', async () => {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${currentToken}` }
      });
    } catch (e) {}
    localStorage.removeItem('kw_token');
    localStorage.removeItem('kw_user');
    location.reload();
  });

  // Restore Session
  if (currentToken) {
    try {
      const savedUser = JSON.parse(localStorage.getItem('kw_user'));
      if (savedUser) {
        currentUser = savedUser;
        authScreen.classList.add('hidden');
        appShell.classList.remove('hidden');
        setupRoleSession();
        loadAllWorkspaceData();
      }
    } catch (e) {
      localStorage.removeItem('kw_token');
    }
  }

  // Password Change
  const changePwdForm = document.getElementById('change-pwd-form');
  if (changePwdForm) {
    changePwdForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const old_password = document.getElementById('pwd-current').value;
      const new_password = document.getElementById('pwd-new').value;
      const res = await apiRequest('/auth/change-password', 'POST', { old_password, new_password });
      if (res.success) {
        showToast('Password updated successfully.', 'success');
        changePwdForm.reset();
      } else {
        showToast(res.error || 'Failed to change password.', 'error');
      }
    });
  }
}

function setupRoleSession() {
  if (!currentUser) return;
  const role = currentUser.role || 'Employee';

  const initials = currentUser.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  document.getElementById('sidebar-user-avatar').textContent = initials;
  document.getElementById('mobile-user-avatar').textContent = initials;
  document.getElementById('sidebar-user-name').textContent = currentUser.name;
  document.getElementById('sidebar-user-role-badge').textContent = role;
  document.getElementById('sidebar-user-dept').textContent = currentUser.department || 'Staff';

  if (document.getElementById('settings-profile-name')) {
    document.getElementById('settings-profile-name').value = currentUser.name;
    document.getElementById('settings-profile-user').value = currentUser.username;
    document.getElementById('settings-profile-role').value = `${role} (${currentUser.department})`;
  }

  // Restrict Tabs Based on Role
  document.querySelectorAll('[data-role-req]').forEach(el => {
    const allowed = el.dataset.roleReq.split(',');
    if (allowed.includes(role)) {
      el.classList.remove('hidden');
    } else {
      el.classList.add('hidden');
    }
  });

  // Hide or Show CEO Needs Attention Widget
  const needsAttWidget = document.getElementById('ceo-needs-attention-widget');
  if (needsAttWidget) {
    if (role === 'CEO' || role === 'Manager') needsAttWidget.classList.remove('hidden');
    else needsAttWidget.classList.add('hidden');
  }

  // Set greeting
  const title = document.getElementById('dash-welcome-title');
  const sub = document.getElementById('dash-welcome-subtitle');
  const greetingBadge = document.getElementById('dash-greeting-badge');
  greetingBadge.textContent = `${role.toUpperCase()} COMMAND CENTER`;
  title.textContent = `Good Morning, ${currentUser.name}`;

  if (role === 'CEO') {
    sub.textContent = 'Operational executive control center. Real-time visibility into finances, engineering projects, staff allocations, and organizational health.';
  } else if (role === 'Manager') {
    sub.textContent = 'Team orchestration console. Manage engineering assignments, review task submissions, and track deliverables.';
  } else if (role === 'Employee') {
    sub.textContent = 'Today\'s priority focus. Complete assigned sprints, log task effort, and submit deliverables for review.';
  } else if (role === 'Intern') {
    sub.textContent = 'Internship learning track. Complete curriculum modules, deliver assigned tasks, and build industry engineering skills.';
  }
}

// API Helper
async function apiRequest(endpoint, method = 'GET', body = null) {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${currentToken}`
    }
  };
  if (body) options.body = JSON.stringify(body);

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, options);
    return await res.json();
  } catch (err) {
    return { success: false, error: 'Network error or server unavailable.' };
  }
}

// ==========================================================================
// 2. SPA NAVIGATION & DRAWER CONTROLLER
// ==========================================================================
function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const tabPanes = document.querySelectorAll('.tab-pane');
  const sidebar = document.getElementById('main-sidebar');
  const backdrop = document.getElementById('mobile-sidebar-backdrop');

  window.switchTab = function(tabId) {
    navItems.forEach(item => {
      if (item.dataset.tab === tabId) item.classList.add('active');
      else item.classList.remove('active');
    });

    tabPanes.forEach(pane => {
      if (pane.id === tabId) {
        pane.classList.remove('hidden');
        pane.classList.add('active');
      } else {
        pane.classList.remove('active');
        pane.classList.add('hidden');
      }
    });

    sidebar.classList.add('-translate-x-full');
    backdrop.classList.add('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  navItems.forEach(item => {
    item.addEventListener('click', () => window.switchTab(item.dataset.tab));
  });

  document.addEventListener('click', (e) => {
    const switchBtn = e.target.closest('.nav-switch-btn');
    if (switchBtn && switchBtn.dataset.target) {
      window.switchTab(switchBtn.dataset.target);
    }
  });

  // Mobile drawer
  document.getElementById('mobile-sidebar-toggle')?.addEventListener('click', () => {
    sidebar.classList.remove('-translate-x-full');
    backdrop.classList.remove('hidden');
  });
  document.getElementById('mobile-sidebar-close')?.addEventListener('click', () => {
    sidebar.classList.add('-translate-x-full');
    backdrop.classList.add('hidden');
  });
  backdrop?.addEventListener('click', () => {
    sidebar.classList.add('-translate-x-full');
    backdrop.classList.add('hidden');
  });
}

// ==========================================================================
// 3. MASTER DATA LOADER & DASHBOARD
// ==========================================================================
async function loadAllWorkspaceData() {
  await Promise.all([
    loadNeedsAttention(),
    loadDashboardMetrics(),
    loadEmployees(),
    loadManagers(),
    loadDepartments(),
    loadRolesPermissions(),
    loadProjects(),
    loadTasks(),
    loadInternalMail(),
    loadChat(),
    loadCompanyFiles(),
    loadCRM(),
    loadProposals(),
    loadInvoices(),
    loadAttendance(),
    loadLeave(),
    loadMeetings(),
    loadPerformance(),
    loadInternships(),
    loadAnnouncements(),
    loadAuditLogs(),
    loadNotifications()
  ]);
  initCompanyPerformanceChart();
}

async function loadNeedsAttention() {
  if (currentUser?.role !== 'CEO' && currentUser?.role !== 'Manager') return;
  const res = await apiRequest('/needs-attention');
  if (!res.success) return;

  const container = document.getElementById('needs-attention-items-list');
  if (!container) return;

  if (!res.items || res.items.length === 0) {
    container.innerHTML = '<div class="p-3 bg-darkSurface border border-darkBorder rounded-xl text-xs text-emerald-400 font-semibold col-span-3">All project milestones, tasks, and financials are on track. No critical risks detected.</div>';
    return;
  }

  container.innerHTML = res.items.map(item => {
    const borderCls = item.level === 'danger' ? 'border-rose-500/30 bg-rose-500/5' : 'border-amber-500/30 bg-amber-500/5';
    const textCls = item.level === 'danger' ? 'text-rose-400' : 'text-amber-400';
    return `
      <div class="p-3 bg-darkSurface border ${borderCls} rounded-xl flex items-center justify-between cursor-pointer hover:border-slate-500 transition" onclick="window.switchTab('${item.tab}')">
        <div>
          <div class="font-bold text-xs ${textCls}">${item.badge} Alert</div>
          <div class="text-[11px] text-slate-300 mt-0.5">${item.title}</div>
        </div>
        <span class="text-xs ${textCls} font-bold">&rarr;</span>
      </div>
    `;
  }).join('');
}

async function loadDashboardMetrics() {
  const res = await apiRequest('/dashboard/metrics');
  if (!res.success) return;
  const m = res.metrics;
  const grid = document.getElementById('dash-metrics-grid');
  const role = currentUser?.role || 'Employee';

  if (role === 'CEO') {
    grid.innerHTML = `
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Total Staff</div>
        <div class="text-2xl font-bold font-mono text-blue-400 mt-1">${m.total_employees || 8}</div>
        <div class="text-[10px] text-slate-500 mt-1">${m.total_managers || 2} Managers &bull; ${m.total_interns || 2} Interns</div>
      </div>
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Active Projects</div>
        <div class="text-2xl font-bold font-mono text-cyan-400 mt-1">${m.active_projects || 3}</div>
        <div class="text-[10px] text-slate-500 mt-1">${m.completed_projects || 1} Delivered Sprints</div>
      </div>
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Realized Revenue</div>
        <div class="text-2xl font-bold font-mono text-emerald-400 mt-1">Rs. ${(m.monthly_revenue || 0).toLocaleString()}</div>
        <div class="text-[10px] text-slate-500 mt-1">Paid Client Invoices</div>
      </div>
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Pending Receivables</div>
        <div class="text-2xl font-bold font-mono text-amber-400 mt-1">Rs. ${(m.pending_payments || 0).toLocaleString()}</div>
        <div class="text-[10px] text-slate-500 mt-1">${m.active_clients || 3} Enterprise Accounts</div>
      </div>
    `;
  } else if (role === 'Manager') {
    grid.innerHTML = `
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Active Projects</div>
        <div class="text-2xl font-bold font-mono text-blue-400 mt-1">${m.active_projects || 2}</div>
      </div>
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Tasks Assigned</div>
        <div class="text-2xl font-bold font-mono text-cyan-400 mt-1">${m.tasks_assigned || 4}</div>
      </div>
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Under Review</div>
        <div class="text-2xl font-bold font-mono text-amber-400 mt-1">${m.tasks_pending_review || 2}</div>
      </div>
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Pending Leaves</div>
        <div class="text-2xl font-bold font-mono text-emerald-400 mt-1">${m.pending_leaves || 1}</div>
      </div>
    `;
  } else if (role === 'Employee') {
    grid.innerHTML = `
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Today's Tasks</div>
        <div class="text-2xl font-bold font-mono text-blue-400 mt-1">${m.today_tasks || 2}</div>
      </div>
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">High Priority</div>
        <div class="text-2xl font-bold font-mono text-rose-400 mt-1">${m.high_priority_tasks || 1}</div>
      </div>
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Under Review</div>
        <div class="text-2xl font-bold font-mono text-amber-400 mt-1">${m.tasks_under_review || 1}</div>
      </div>
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Completed Tasks</div>
        <div class="text-2xl font-bold font-mono text-emerald-400 mt-1">${m.completed_tasks || 6}</div>
      </div>
    `;
  } else if (role === 'Intern') {
    grid.innerHTML = `
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Curriculum Progress</div>
        <div class="text-2xl font-bold font-mono text-purple-400 mt-1">${m.progress_percent || 80}%</div>
      </div>
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Assigned Tasks</div>
        <div class="text-2xl font-bold font-mono text-blue-400 mt-1">${m.assigned_tasks || 1}</div>
      </div>
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Completed</div>
        <div class="text-2xl font-bold font-mono text-emerald-400 mt-1">${m.completed_tasks || 3}</div>
      </div>
      <div class="bg-darkCard border border-darkBorder p-5 rounded-2xl">
        <div class="text-[11px] text-slate-400 font-semibold uppercase tracking-wider font-mono">Certificate Status</div>
        <div class="text-sm font-bold text-cyan-400 mt-2 font-mono">${m.certificate_status || 'In Progress'}</div>
      </div>
    `;
  }
}

function initCompanyPerformanceChart() {
  const ctx = document.getElementById('companyPerformanceChart');
  if (!ctx) return;

  if (perfChartInstance) {
    perfChartInstance.destroy();
  }

  perfChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['May', 'Jun', 'Jul', 'Aug (W1)', 'Aug (W2)', 'Aug (W3)'],
      datasets: [
        {
          label: 'Completed Deliverables',
          data: [14, 22, 38, 45, 58, 71],
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.1)',
          tension: 0.3,
          fill: true
        },
        {
          label: 'SLA Baseline Target',
          data: [15, 25, 35, 48, 60, 75],
          borderColor: '#06b6d4',
          borderDash: [5, 5],
          tension: 0.3,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } }
        }
      },
      scales: {
        x: {
          ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } },
          grid: { color: 'rgba(55, 65, 81, 0.4)' }
        },
        y: {
          ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } },
          grid: { color: 'rgba(55, 65, 81, 0.4)' }
        }
      }
    }
  });
}

// ==========================================================================
// 4. PEOPLE -> ALL EMPLOYEES & FULL DOSSIER
// ==========================================================================
async function loadEmployees() {
  const dept = document.getElementById('emp-filter-dept')?.value || 'All';
  const role = document.getElementById('emp-filter-role')?.value || 'All';
  const status = document.getElementById('emp-filter-status')?.value || 'All';
  const search = document.getElementById('emp-search-input')?.value || '';

  const res = await apiRequest(`/employees?department=${dept}&role=${role}&status=${status}&q=${encodeURIComponent(search)}`);
  if (!res.success) return;
  allEmployeesCache = res.employees || [];

  const badge = document.getElementById('nav-badge-employees');
  if (badge) badge.textContent = allEmployeesCache.length;

  renderEmployeesTable(allEmployeesCache);
}

function renderEmployeesTable(employees) {
  const tbody = document.getElementById('employees-table-body');
  if (!tbody) return;

  if (employees.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" class="p-6 text-center text-slate-500">No employees match filter criteria.</td></tr>';
    return;
  }

  tbody.innerHTML = employees.map(emp => {
    const initials = emp.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    const statusCls = emp.status === 'Active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20';
    return `
      <tr class="hover:bg-darkSurface/50 transition">
        <td class="p-3.5">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-blue-600/30 border border-blue-500/30 text-blue-300 font-bold flex items-center justify-center text-xs">
              ${initials}
            </div>
            <div>
              <div class="font-bold text-white font-sans">${emp.name}</div>
              <div class="text-[10px] text-slate-400">@${emp.username}</div>
            </div>
          </div>
        </td>
        <td class="p-3.5 font-bold text-blue-400">${emp.emp_code}</td>
        <td class="p-3.5 text-slate-300">${emp.department}</td>
        <td class="p-3.5 text-slate-300">${emp.designation || emp.role}</td>
        <td class="p-3.5 text-slate-400">${emp.manager_name || 'Shon Kapate'}</td>
        <td class="p-3.5 text-slate-400 font-mono text-[11px]">${emp.email}<br><span class="text-slate-500">${emp.phone || ''}</span></td>
        <td class="p-3.5">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${statusCls}">${emp.status}</span>
        </td>
        <td class="p-3.5 text-slate-400">${emp.joining_date}</td>
        <td class="p-3.5 font-bold text-yellow-400">${emp.performance_score || '4.8'}</td>
        <td class="p-3.5 text-right">
          <button class="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg text-xs transition" onclick="viewEmployeeProfile(${emp.id})">
            View Profile &rarr;
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

// Wire up search & filter listeners
document.getElementById('emp-search-input')?.addEventListener('input', () => loadEmployees());
document.getElementById('emp-filter-dept')?.addEventListener('change', () => loadEmployees());
document.getElementById('emp-filter-role')?.addEventListener('change', () => loadEmployees());
document.getElementById('emp-filter-status')?.addEventListener('change', () => loadEmployees());

// View Employee Full Dossier
window.viewEmployeeProfile = async function(empId) {
  currentViewingEmpId = empId;
  const res = await apiRequest(`/employees/${empId}/full-profile`);
  if (!res.success) {
    showToast(res.error || 'Failed to load profile.', 'error');
    return;
  }

  const emp = res.employee;
  const stats = res.stats;

  // Header Elements
  const initials = emp.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  document.getElementById('ep-avatar').textContent = initials;
  document.getElementById('ep-name').textContent = emp.name;
  document.getElementById('ep-id').textContent = emp.emp_code;
  document.getElementById('ep-status').textContent = emp.status;
  document.getElementById('ep-designation').innerHTML = `${emp.designation || emp.role} &bull; <span id="ep-department" class="text-blue-400">${emp.department}</span>`;
  document.getElementById('ep-manager').textContent = emp.manager_name || 'Shon Kapate';
  document.getElementById('ep-joined').textContent = emp.joining_date;
  document.getElementById('ep-email').textContent = emp.email;
  document.getElementById('ep-phone').textContent = emp.phone || '+91 9822001100';

  // Stats
  document.getElementById('ep-stat-projects').textContent = stats.projects_count;
  document.getElementById('ep-stat-tasks').textContent = stats.tasks_completed;
  document.getElementById('ep-stat-rating').textContent = stats.performance_rating;

  // Personal
  document.getElementById('ep-in-dob').value = emp.dob || '1996-05-14';
  document.getElementById('ep-in-phone').value = emp.phone || '+91 9422019988';
  document.getElementById('ep-in-address').value = emp.address || 'Baner, Pune, Maharashtra, India';
  document.getElementById('ep-in-emergency').value = emp.emergency_contact || '+91 9422019989 (Parent)';

  // Employment
  document.getElementById('ep-in-designation').value = emp.designation || 'Software Engineer';
  document.getElementById('ep-in-department').value = emp.department;
  document.getElementById('ep-in-role').value = emp.role;
  document.getElementById('ep-in-manager').value = emp.manager_name || 'Rohit Verma';
  document.getElementById('ep-in-employment-type').value = emp.employment_type || 'Full-Time';
  if (emp.basic_pay !== undefined) {
    document.getElementById('ep-in-salary').value = emp.basic_pay;
  }

  // Projects Subtab
  const projectsList = document.getElementById('ep-projects-list');
  if (res.projects.length === 0) {
    projectsList.innerHTML = '<div class="text-slate-500 col-span-2">No projects assigned currently.</div>';
  } else {
    projectsList.innerHTML = res.projects.map(p => `
      <div class="p-4 bg-darkSurface border border-darkBorder rounded-2xl space-y-2">
        <div class="flex justify-between font-bold text-white">
          <span>${p.name}</span>
          <span class="text-blue-400">${p.progress}%</span>
        </div>
        <div class="text-[11px] text-slate-400">Client: ${p.client_name} &bull; Manager: ${p.manager_name}</div>
        <div class="w-full h-2 bg-darkCard rounded-full overflow-hidden">
          <div class="h-full bg-blue-500" style="width: ${p.progress}%"></div>
        </div>
      </div>
    `).join('');
  }

  // Tasks Subtab with CEO Overrides
  const tasksTable = document.getElementById('ep-tasks-table-body');
  if (res.tasks.length === 0) {
    tasksTable.innerHTML = '<tr><td colspan="7" class="p-4 text-center text-slate-500">No tasks assigned.</td></tr>';
  } else {
    tasksTable.innerHTML = res.tasks.map(t => `
      <tr class="hover:bg-darkSurface/50 transition">
        <td class="p-3 text-blue-400 font-bold">${t.task_id}</td>
        <td class="p-3 font-semibold text-white">${t.title}</td>
        <td class="p-3 text-slate-400">${t.project_name}</td>
        <td class="p-3 font-bold ${t.priority === 'High' ? 'text-red-400' : 'text-slate-300'}">${t.priority}</td>
        <td class="p-3 text-slate-400">${t.deadline}</td>
        <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${getBadgeClass(t.status)}">${t.status}</span></td>
        <td class="p-3 text-right">
          ${currentUser?.role === 'CEO' ? `
            <button class="px-2.5 py-1 bg-amber-600/20 text-amber-400 border border-amber-500/30 hover:bg-amber-600/30 rounded text-[11px] font-bold" onclick="openCeoTaskOverrideModal('${t.task_id}', '${t.assigned_to_id}', '${t.status}', '${t.priority}', '${t.deadline}')">
              Override &rarr;
            </button>
          ` : '<span class="text-slate-500 text-[10px]">Standard</span>'}
        </td>
      </tr>
    `).join('');
  }

  // Attendance Subtab
  document.getElementById('ep-att-present').textContent = res.attendance.present_count;
  document.getElementById('ep-att-late').textContent = res.attendance.late_count;
  document.getElementById('ep-att-rate').textContent = `${res.attendance.attendance_rate}%`;
  const attBody = document.getElementById('ep-attendance-table-body');
  if (res.attendance.logs.length === 0) {
    attBody.innerHTML = '<tr><td colspan="5" class="p-3 text-center text-slate-500">No recent logs recorded.</td></tr>';
  } else {
    attBody.innerHTML = res.attendance.logs.map(a => `
      <tr>
        <td class="p-3 text-white">${a.date}</td>
        <td class="p-3 text-emerald-400">${a.clock_in || '--'}</td>
        <td class="p-3 text-rose-400">${a.clock_out || '--'}</td>
        <td class="p-3 text-slate-300 font-bold">${a.total_hours ? a.total_hours + ' hrs' : 'In Shift'}</td>
        <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400">${a.status}</span></td>
      </tr>
    `).join('');
  }

  // Documents Subtab
  const docList = document.getElementById('ep-documents-list');
  if (res.documents.length === 0) {
    docList.innerHTML = '<div class="text-slate-500 col-span-3">No verified documents uploaded yet.</div>';
  } else {
    docList.innerHTML = res.documents.map(d => `
      <div class="p-4 bg-darkSurface border border-darkBorder rounded-2xl flex flex-col justify-between">
        <div>
          <span class="text-[10px] font-mono font-bold text-blue-400 uppercase">${d.doc_type}</span>
          <div class="font-bold text-white text-xs mt-1 truncate">${d.doc_name}</div>
          <div class="text-[10px] text-slate-500 font-mono mt-0.5">${d.file_size} &bull; ${d.uploaded_at}</div>
        </div>
        <div class="pt-3 border-t border-darkBorder mt-3 text-right">
          <button class="text-blue-400 hover:underline font-semibold" onclick="showToast('Downloading verified document...', 'info')">Download &darr;</button>
        </div>
      </div>
    `).join('');
  }

  // Notes Subtab (CEO Notes)
  const notesList = document.getElementById('ep-notes-list');
  if (res.notes && res.notes.length > 0) {
    notesList.innerHTML = res.notes.map(n => `
      <div class="p-3 bg-darkSurface border border-darkBorder rounded-xl space-y-1 text-xs">
        <div class="flex justify-between font-bold text-blue-400 font-mono text-[11px]">
          <span>${n.author_name} (${n.author_role})</span>
          <span class="text-slate-500">${n.created_at}</span>
        </div>
        <p class="text-slate-200">${n.note_text}</p>
      </div>
    `).join('');
  } else {
    notesList.innerHTML = '<div class="text-slate-500 text-xs">No confidential notes recorded yet.</div>';
  }

  // Switch to Employee Profile Pane
  window.switchTab('tab-employee-profile');
};

function initProfileSubtabs() {
  const subtabBtns = document.querySelectorAll('.profile-subtab-btn');
  const panes = document.querySelectorAll('.profile-pane');

  subtabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      subtabBtns.forEach(b => {
        b.classList.remove('active', 'border-b-2', 'border-blue-500', 'text-blue-400');
        b.classList.add('text-slate-400');
      });
      btn.classList.add('active', 'border-b-2', 'border-blue-500', 'text-blue-400');
      btn.classList.remove('text-slate-400');

      const targetPane = btn.dataset.target;
      panes.forEach(pane => {
        if (pane.id === targetPane) {
          pane.classList.remove('hidden');
          pane.classList.add('active');
        } else {
          pane.classList.remove('active');
          pane.classList.add('hidden');
        }
      });
    });
  });

  // Save Personal Details
  document.getElementById('ep-btn-save-personal')?.addEventListener('click', async () => {
    if (!currentViewingEmpId) return;
    const dob = document.getElementById('ep-in-dob').value;
    const phone = document.getElementById('ep-in-phone').value;
    const address = document.getElementById('ep-in-address').value;
    const emergency_contact = document.getElementById('ep-in-emergency').value;

    const res = await apiRequest(`/employees/${currentViewingEmpId}/personal`, 'PUT', { dob, phone, address, emergency_contact });
    if (res.success) showToast(res.message, 'success');
    else showToast(res.error, 'error');
  });

  // Save Employment & Compensation
  document.getElementById('ep-btn-save-employment')?.addEventListener('click', async () => {
    if (!currentViewingEmpId) return;
    const designation = document.getElementById('ep-in-designation').value;
    const department = document.getElementById('ep-in-department').value;
    const role = document.getElementById('ep-in-role').value;
    const manager_name = document.getElementById('ep-in-manager').value;
    const employment_type = document.getElementById('ep-in-employment-type').value;
    const basic_pay = parseFloat(document.getElementById('ep-in-salary').value || 0);

    const res = await apiRequest(`/employees/${currentViewingEmpId}/employment`, 'PUT', {
      designation, department, role, manager_name, employment_type, basic_pay
    });
    if (res.success) {
      showToast(res.message, 'success');
      loadEmployees();
    } else {
      showToast(res.error, 'error');
    }
  });

  // Save Confidential Note
  document.getElementById('ep-btn-save-note')?.addEventListener('click', async () => {
    if (!currentViewingEmpId) return;
    const note_text = document.getElementById('ep-in-new-note').value.trim();
    if (!note_text) return;

    const res = await apiRequest(`/employees/${currentViewingEmpId}/notes`, 'POST', { note_text });
    if (res.success) {
      showToast('Confidential note recorded.', 'success');
      document.getElementById('ep-in-new-note').value = '';
      window.viewEmployeeProfile(currentViewingEmpId);
    } else {
      showToast(res.error, 'error');
    }
  });
}

// ==========================================================================
// 5. CEO TASK OVERRIDE MODAL CONTROLLER
// ==========================================================================
window.openCeoTaskOverrideModal = function(taskId, currentAssigneeId, status, priority, deadline) {
  document.getElementById('override-task-id').value = taskId;
  document.getElementById('override-status-select').value = status || 'Assigned';
  document.getElementById('override-priority-select').value = priority || 'Medium';
  document.getElementById('override-deadline-input').value = deadline || '';

  const assigneeSelect = document.getElementById('override-assignee-select');
  assigneeSelect.innerHTML = allEmployeesCache.map(e => `
    <option value="${e.id}" data-name="${e.name}" ${e.id == currentAssigneeId ? 'selected' : ''}>${e.name} (${e.role})</option>
  `).join('');

  document.getElementById('modal-ceo-task-override').classList.remove('hidden');
};

document.getElementById('form-ceo-task-override')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const taskId = document.getElementById('override-task-id').value;
  const select = document.getElementById('override-assignee-select');
  const assigned_to_id = select.value;
  const assigned_to_name = select.selectedOptions[0]?.dataset.name;
  const status = document.getElementById('override-status-select').value;
  const priority = document.getElementById('override-priority-select').value;
  const deadline = document.getElementById('override-deadline-input').value;
  const reason = document.getElementById('override-reason-input').value.trim();

  const res = await apiRequest(`/tasks/${taskId}/ceo-override`, 'POST', {
    assigned_to_id, assigned_to_name, status, priority, deadline, reason
  });

  if (res.success) {
    showToast(res.message, 'success');
    document.getElementById('modal-ceo-task-override').classList.add('hidden');
    loadTasks();
    if (currentViewingEmpId) window.viewEmployeeProfile(currentViewingEmpId);
  } else {
    showToast(res.error || 'Failed to execute override.', 'error');
  }
});

// ==========================================================================
// 6. MANAGERS, DEPARTMENTS & ROLES MATRIX
// ==========================================================================
async function loadManagers() {
  const res = await apiRequest('/employees?role=Manager');
  if (!res.success) return;
  const managers = res.employees || [];
  const container = document.getElementById('managers-container');
  if (!container) return;

  container.innerHTML = managers.map(m => `
    <div class="bg-darkCard border border-darkBorder rounded-2xl p-6 space-y-4 shadow-lg">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="font-bold text-base text-white font-outfit">${m.name}</h3>
          <div class="text-xs text-blue-400 font-mono">${m.designation || 'Engineering Manager'}</div>
        </div>
        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">${m.department}</span>
      </div>
      <div class="grid grid-cols-3 gap-2 text-center text-xs font-mono bg-darkSurface p-3 rounded-xl border border-darkBorder">
        <div><div class="text-slate-400 text-[10px]">Team Size</div><div class="text-white font-bold mt-0.5">4 Staff</div></div>
        <div><div class="text-slate-400 text-[10px]">Active Sprints</div><div class="text-blue-400 font-bold mt-0.5">2 Sprints</div></div>
        <div><div class="text-slate-400 text-[10px]">Delivery Rate</div><div class="text-emerald-400 font-bold mt-0.5">97%</div></div>
      </div>
      <button class="w-full py-2 bg-darkSurface border border-darkBorder hover:border-slate-500 text-slate-200 text-xs font-semibold rounded-xl transition" onclick="viewEmployeeProfile(${m.id})">
        Inspect Manager Dossier &rarr;
      </button>
    </div>
  `).join('');
}

async function loadDepartments() {
  const res = await apiRequest('/departments');
  if (!res.success) return;
  const depts = res.departments || [];
  const container = document.getElementById('departments-container');
  if (!container) return;

  container.innerHTML = depts.map(d => `
    <div class="bg-darkCard border border-darkBorder rounded-2xl p-6 space-y-3 shadow-lg">
      <div class="flex items-center justify-between">
        <h3 class="font-bold text-base text-white font-outfit">${d.name}</h3>
        <span class="font-mono text-[10px] text-blue-400 font-bold">${d.employee_count || 0} Staff</span>
      </div>
      <p class="text-xs text-slate-400 leading-relaxed">${d.description || 'Organizational business unit.'}</p>
      <div class="pt-2 border-t border-darkBorder text-xs font-mono space-y-1 text-slate-300">
        <div>Department Head: <strong class="text-white">${d.head_name}</strong></div>
        <div>Budget Allocation: <strong class="text-emerald-400">Rs. ${(d.budget || 1000000).toLocaleString()}</strong></div>
      </div>
    </div>
  `).join('');
}

async function loadRolesPermissions() {
  const res = await apiRequest('/roles-permissions');
  if (!res.success) return;
  const perms = res.permissions || [];
  const tbody = document.getElementById('roles-matrix-body');
  if (!tbody) return;

  tbody.innerHTML = perms.map(p => `
    <tr class="hover:bg-darkSurface/50 transition">
      <td class="p-3.5 font-bold text-white">${p.permission_label}</td>
      <td class="p-3.5 text-slate-400">${p.category}</td>
      <td class="p-3.5 text-blue-400 font-bold">${p.ceo_perm}</td>
      <td class="p-3.5 text-cyan-400 font-bold">${p.manager_perm}</td>
      <td class="p-3.5 text-slate-300">${p.employee_perm}</td>
      <td class="p-3.5 text-purple-400">${p.intern_perm}</td>
    </tr>
  `).join('');
}

// ==========================================================================
// 7. PROJECTS, TASKS & WORKFLOWS
// ==========================================================================
async function loadProjects() {
  const res = await apiRequest('/projects');
  if (!res.success) return;
  const projects = res.projects || [];
  const grid = document.getElementById('projects-container');
  if (!grid) return;

  grid.innerHTML = projects.map(p => `
    <div class="bg-darkCard border border-darkBorder rounded-2xl p-6 flex flex-col justify-between shadow-lg">
      <div>
        <div class="flex items-center justify-between mb-2">
          <span class="font-mono text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-bold">${p.project_id}</span>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${p.priority === 'High' ? 'text-red-400 bg-red-500/10' : 'text-slate-400 bg-slate-800'}">${p.priority} Priority</span>
        </div>
        <h3 class="font-bold text-sm text-white mb-1">${p.name}</h3>
        <p class="text-xs text-slate-400 line-clamp-2 mb-4">${p.description || 'Enterprise deliverable.'}</p>
        <div class="space-y-1.5 text-xs font-mono text-slate-300">
          <div class="flex justify-between"><span>Client:</span> <strong class="text-white">${p.client_name}</strong></div>
          <div class="flex justify-between"><span>Manager:</span> <strong class="text-white">${p.manager_name}</strong></div>
          <div class="flex justify-between"><span>Deadline:</span> <strong class="text-slate-200">${p.deadline}</strong></div>
        </div>
      </div>
      <div class="pt-4 mt-4 border-t border-darkBorder">
        <div class="flex justify-between text-xs font-mono mb-1">
          <span class="text-slate-400">Progress</span>
          <span class="text-blue-400 font-bold">${p.progress}%</span>
        </div>
        <div class="w-full h-2 bg-darkSurface rounded-full overflow-hidden">
          <div class="h-full bg-blue-500" style="width: ${p.progress}%"></div>
        </div>
      </div>
    </div>
  `).join('');

  // Populate task modal select
  const projectSelect = document.getElementById('task-in-project');
  if (projectSelect) {
    projectSelect.innerHTML = projects.map(p => `<option value="${p.project_id}" data-name="${p.name}">${p.name} (${p.project_id})</option>`).join('');
  }
}

async function loadTasks() {
  const filter = document.getElementById('task-filter-select')?.value || 'all';
  const res = await apiRequest(`/tasks?filter=${filter}`);
  if (!res.success) return;
  allTasksCache = res.tasks || [];

  const badge = document.getElementById('nav-badge-tasks');
  if (badge) {
    badge.textContent = allTasksCache.filter(t => !['Completed', 'Approved'].includes(t.status)).length;
  }

  const tbody = document.getElementById('tasks-table-body');
  if (!tbody) return;

  if (allTasksCache.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="p-6 text-center text-slate-500">No tasks found.</td></tr>';
    return;
  }

  tbody.innerHTML = allTasksCache.map(t => `
    <tr class="hover:bg-darkSurface/50 transition">
      <td class="p-3.5">
        <div class="font-bold text-white">${t.title}</div>
        <div class="font-mono text-[10px] text-slate-500">${t.task_id}</div>
      </td>
      <td class="p-3.5 text-slate-300">${t.project_name || 'General Sprint'}</td>
      <td class="p-3.5 text-slate-300">${t.assigned_to_name}</td>
      <td class="p-3.5 font-bold ${t.priority === 'High' ? 'text-red-400' : 'text-slate-300'}">${t.priority}</td>
      <td class="p-3.5 font-mono text-slate-400">${t.deadline}</td>
      <td class="p-3.5"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${getBadgeClass(t.status)}">${t.status}</span></td>
      <td class="p-3.5 text-right">
        ${currentUser?.role === 'CEO' ? `
          <button class="px-2.5 py-1 bg-amber-600/20 text-amber-400 border border-amber-500/30 hover:bg-amber-600/30 rounded text-[11px] font-bold" onclick="openCeoTaskOverrideModal('${t.task_id}', '${t.assigned_to_id}', '${t.status}', '${t.priority}', '${t.deadline}')">
            Override &rarr;
          </button>
        ` : `
          <button class="px-2.5 py-1 bg-darkCard border border-darkBorder hover:bg-slate-800 text-blue-400 text-[11px] font-semibold rounded" onclick="updateTaskStatus('${t.task_id}', 'Submitted')">
            Action &rarr;
          </button>
        `}
      </td>
    </tr>
  `).join('');

  // Dashboard active tasks list
  const dashList = document.getElementById('dash-tasks-list');
  if (dashList) {
    dashList.innerHTML = allTasksCache.slice(0, 4).map(t => `
      <div class="p-3 bg-darkSurface border border-darkBorder rounded-xl flex items-center justify-between">
        <div>
          <div class="font-semibold text-xs text-white">${t.title}</div>
          <div class="text-[10px] text-slate-400 font-mono">${t.assigned_to_name} &bull; ${t.project_name}</div>
        </div>
        <span class="px-2 py-0.5 rounded text-[10px] font-bold ${getBadgeClass(t.status)}">${t.status}</span>
      </div>
    `).join('');
  }
}

function getBadgeClass(status) {
  switch (status) {
    case 'Assigned': return 'badge-assigned';
    case 'In Progress': return 'badge-inprogress';
    case 'Submitted': return 'badge-submitted';
    case 'Approved': return 'badge-approved';
    case 'Completed': return 'badge-completed';
    case 'Changes Requested': return 'badge-changes';
    default: return 'badge-assigned';
  }
}

window.updateTaskStatus = async function(taskId, newStatus) {
  const res = await apiRequest(`/tasks/${taskId}/status`, 'PUT', { status: newStatus });
  if (res.success) {
    showToast(`Task status updated to ${newStatus}`, 'success');
    loadTasks();
  } else {
    showToast(res.error || 'Failed to update status', 'error');
  }
};

// ==========================================================================
// 8. DATA EXPORT CONTROLLER (CSV / TEXT)
// ==========================================================================
window.exportData = function(type) {
  showToast(`Preparing ${type} export...`, 'info');
  window.open(`${API_BASE}/export/${type}?token=${currentToken}`, '_blank');
};

// ==========================================================================
// 9. OTHER MODULES (MAIL, CHAT, FILES, CRM, INVOICES, ATTENDANCE, LEAVE)
// ==========================================================================
async function loadInternalMail() {
  const res = await apiRequest('/mail?folder=inbox');
  if (!res.success) return;
  const messages = res.messages || [];

  const badge = document.getElementById('nav-badge-mail');
  if (badge) badge.textContent = messages.filter(m => m.is_read === 0).length;

  const container = document.getElementById('mail-list-container');
  if (!container) return;

  if (messages.length === 0) {
    container.innerHTML = '<div class="text-center text-slate-500 py-8">Inbox is empty.</div>';
    return;
  }

  container.innerHTML = messages.map(m => `
    <div class="p-3 hover:bg-darkSurface/60 rounded-xl transition flex items-center justify-between ${m.is_read === 0 ? 'bg-blue-500/5 font-semibold' : ''}">
      <div>
        <div class="text-white text-xs">${m.sender_name} <span class="text-slate-500 text-[10px]">(${m.sender_username})</span></div>
        <div class="text-slate-300 text-xs font-medium">${m.subject}</div>
        <p class="text-slate-400 text-[11px] line-clamp-1 mt-0.5">${m.body}</p>
      </div>
      <div class="text-[10px] text-slate-500 font-mono">${m.created_at}</div>
    </div>
  `).join('');
}

async function loadChat() {
  const res = await apiRequest('/chat/channels');
  if (!res.success) return;
  const channels = res.channels || [];

  const list = document.getElementById('chat-channels-list');
  if (list) {
    list.innerHTML = channels.map(c => `
      <button class="w-full px-3 py-2 rounded-lg text-left text-xs font-semibold flex items-center gap-2 ${c.channel_id === activeChatChannel ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-darkCard'}" onclick="switchChatChannel('${c.channel_id}', '${c.name}')">
        <span>#</span> <span>${c.name}</span>
      </button>
    `).join('');
  }
  loadChatMessages(activeChatChannel);
}

window.switchChatChannel = function(channelId, name) {
  activeChatChannel = channelId;
  document.getElementById('active-chat-title').textContent = `# ${name}`;
  loadChat();
};

async function loadChatMessages(channelId) {
  const res = await apiRequest(`/chat/messages?channel_id=${channelId}`);
  const stream = document.getElementById('chat-messages-stream');
  if (!stream) return;

  if (res.success && res.messages) {
    stream.innerHTML = res.messages.map(m => `
      <div class="flex items-start gap-2.5">
        <div class="w-7 h-7 rounded-lg bg-slate-800 text-slate-300 font-bold flex items-center justify-center text-xs shrink-0">
          ${m.sender_name.substring(0, 2).toUpperCase()}
        </div>
        <div class="bg-darkSurface p-2.5 rounded-xl border border-darkBorder max-w-lg">
          <div class="flex items-center gap-2 mb-1">
            <span class="font-bold text-white text-[11px]">${m.sender_name}</span>
            <span class="text-[10px] text-blue-400 font-mono">(${m.sender_role})</span>
            <span class="text-[10px] text-slate-500 ml-auto">${m.created_at}</span>
          </div>
          <p class="text-slate-200 text-xs">${m.message}</p>
        </div>
      </div>
    `).join('');
    stream.scrollTop = stream.scrollHeight;
  }
}

async function loadCompanyFiles() {
  const res = await apiRequest('/files');
  if (!res.success) return;
  const files = res.files || [];
  const grid = document.getElementById('files-grid-container');
  if (!grid) return;

  grid.innerHTML = files.map(f => `
    <div class="bg-darkCard border border-darkBorder rounded-2xl p-5 flex flex-col justify-between">
      <div>
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-mono font-bold text-blue-400">[${f.file_type}]</span>
          <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-darkSurface text-slate-400 border border-darkBorder">${f.folder}</span>
        </div>
        <h4 class="font-bold text-xs text-white mb-1 truncate">${f.name}</h4>
        <p class="text-[11px] text-slate-400">Uploaded by ${f.uploaded_by} (${f.uploader_role})</p>
      </div>
      <div class="pt-3 border-t border-darkBorder mt-3 flex items-center justify-between text-xs font-mono">
        <span class="text-slate-500">${f.file_size}</span>
        <button class="text-blue-400 hover:underline font-semibold" onclick="showToast('Downloading encrypted file...', 'info')">Download &darr;</button>
      </div>
    </div>
  `).join('');
}

async function loadCRM() {
  const res = await apiRequest('/crm/clients');
  if (!res.success) return;
  const clients = res.clients || [];
  const container = document.getElementById('clients-container');
  if (!container) return;

  container.innerHTML = clients.map(c => `
    <div class="bg-darkCard border border-darkBorder rounded-2xl p-6 space-y-3">
      <div class="flex items-center justify-between">
        <span class="font-mono text-xs font-bold text-cyan-400">${c.client_id}</span>
        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${c.status}</span>
      </div>
      <h3 class="font-bold text-base text-white font-outfit">${c.company_name}</h3>
      <div class="space-y-1 text-xs text-slate-300 font-mono">
        <div>Contact: <strong class="text-white">${c.contact_person}</strong></div>
        <div>Email: <strong class="text-slate-200">${c.email}</strong></div>
        <div>Phone: <strong class="text-slate-200">${c.phone || 'N/A'}</strong></div>
      </div>
      <p class="text-xs text-slate-400 bg-darkSurface p-2.5 rounded-lg border border-darkBorder">${c.notes || 'Enterprise client account.'}</p>
    </div>
  `).join('');
}

async function loadProposals() {
  const res = await apiRequest('/crm/proposals');
  if (!res.success) return;
  const proposals = res.proposals || [];
  const container = document.getElementById('proposals-container');
  if (!container) return;

  container.innerHTML = proposals.map(p => `
    <div class="bg-darkCard border border-darkBorder rounded-2xl p-6 space-y-4">
      <div class="flex items-center justify-between">
        <span class="font-mono text-xs font-bold text-cyan-400">${p.proposal_id}</span>
        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400">${p.status}</span>
      </div>
      <div>
        <h3 class="font-bold text-base text-white font-outfit">${p.project_name}</h3>
        <p class="text-xs text-slate-400">Client: ${p.client_name}</p>
      </div>
      <div class="p-3 bg-darkSurface border border-darkBorder rounded-xl text-xs space-y-1 font-mono">
        <div>Pricing: <strong class="text-emerald-400">Rs. ${(p.pricing || 0).toLocaleString()} INR</strong></div>
        <div>Timeline: <strong class="text-slate-200">${p.timeline}</strong></div>
      </div>
      <button class="w-full py-2 bg-darkSurface border border-darkBorder hover:border-blue-500 text-blue-400 text-xs font-semibold rounded-lg transition" onclick="showToast('Exporting official proposal PDF...', 'info')">
        Export Proposal PDF &rarr;
      </button>
    </div>
  `).join('');
}

async function loadInvoices() {
  if (currentUser?.role !== 'CEO' && currentUser?.role !== 'Manager') return;
  const res = await apiRequest('/crm/invoices');
  if (!res.success) return;
  const invoices = res.invoices || [];
  const tbody = document.getElementById('invoices-table-body');
  if (!tbody) return;

  tbody.innerHTML = invoices.map(i => `
    <tr class="hover:bg-darkSurface/50 transition font-mono">
      <td class="p-3.5 font-bold text-cyan-400">${i.invoice_no}</td>
      <td class="p-3.5 text-white font-sans">${i.client_name}<br><span class="text-[10px] text-slate-400 font-mono">${i.project_name}</span></td>
      <td class="p-3.5 font-bold text-emerald-400">Rs. ${(i.total || 0).toLocaleString()}</td>
      <td class="p-3.5 text-slate-400">${i.due_date}</td>
      <td class="p-3.5"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${i.status === 'Paid' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}">${i.status}</span></td>
      <td class="p-3.5 text-right"><button class="text-blue-400 hover:underline font-semibold" onclick="showToast('Generating official tax invoice PDF...', 'info')">Print PDF</button></td>
    </tr>
  `).join('');
}

async function loadAttendance() {
  const res = await apiRequest('/hr/attendance');
  if (!res.success) return;
  const logs = res.attendance || [];
  const tbody = document.getElementById('attendance-table-body');
  if (tbody) {
    tbody.innerHTML = logs.map(a => `
      <tr class="hover:bg-darkSurface/50 transition">
        <td class="p-3.5 font-semibold text-white">${a.emp_name}</td>
        <td class="p-3.5 text-slate-400">${a.date}</td>
        <td class="p-3.5 text-emerald-400">${a.clock_in || '--'}</td>
        <td class="p-3.5 text-rose-400">${a.clock_out || '--'}</td>
        <td class="p-3.5 font-bold text-slate-200">${a.total_hours ? a.total_hours + ' hrs' : 'In Shift'}</td>
        <td class="p-3.5"><span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 font-bold">${a.status}</span></td>
      </tr>
    `).join('');
  }
}

async function loadLeave() {
  const res = await apiRequest('/hr/leave');
  if (!res.success) return;
  const leaves = res.leaves || [];
  const tbody = document.getElementById('leave-table-body');
  if (tbody) {
    tbody.innerHTML = leaves.map(l => `
      <tr class="hover:bg-darkSurface/50 transition">
        <td class="p-3.5 font-semibold text-white font-sans">${l.emp_name}</td>
        <td class="p-3.5 text-blue-400 font-bold">${l.leave_type}</td>
        <td class="p-3.5 text-slate-300">${l.start_date} &rarr; ${l.end_date}</td>
        <td class="p-3.5 text-slate-400 max-w-xs truncate font-sans">${l.reason}</td>
        <td class="p-3.5"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${l.status === 'Approved' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}">${l.status}</span></td>
        <td class="p-3.5 text-right">
          ${l.status === 'Pending' && ['CEO', 'Manager'].includes(currentUser?.role) ? `
            <button class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[11px] font-bold" onclick="moderateLeave(${l.id}, 'Approved')">Approve</button>
            <button class="px-2.5 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded text-[11px] font-bold" onclick="moderateLeave(${l.id}, 'Rejected')">Reject</button>
          ` : '<span class="text-slate-500 text-[11px]">Reviewed</span>'}
        </td>
      </tr>
    `).join('');
  }
}

window.moderateLeave = async function(leaveId, action) {
  const res = await apiRequest('/hr/leave', 'PUT', { leave_id: leaveId, action });
  if (res.success) {
    showToast(`Leave request ${action}`, 'success');
    loadLeave();
    loadNeedsAttention();
  }
};

async function loadMeetings() {
  const res = await apiRequest('/meetings');
  if (!res.success) return;
  const meetings = res.meetings || [];
  const list = document.getElementById('calendar-meetings-list');
  if (!list) return;

  list.innerHTML = meetings.map(m => `
    <div class="p-5 bg-darkCard border border-darkBorder rounded-2xl space-y-2">
      <div class="font-bold text-white text-sm font-outfit">${m.title}</div>
      <div class="text-xs text-slate-400 font-mono">Date: ${m.meeting_date} at ${m.meeting_time}</div>
      <p class="text-xs text-slate-300">${m.agenda || 'Technical sync'}</p>
      <div class="pt-2"><a href="${m.location_link}" target="_blank" class="text-blue-400 underline text-xs font-semibold">Join Video Room &rarr;</a></div>
    </div>
  `).join('');
}

async function loadPerformance() {
  const res = await apiRequest('/hr/performance');
  if (!res.success) return;
  const reviews = res.reviews || [];
  const container = document.getElementById('performance-reviews-container');
  if (!container) return;

  container.innerHTML = reviews.map(r => `
    <div class="bg-darkCard border border-darkBorder rounded-2xl p-6 space-y-3">
      <div class="flex items-center justify-between">
        <span class="font-bold text-white text-base">${r.emp_name}</span>
        <span class="font-mono font-bold text-yellow-400 text-sm">Rating: ${r.rating_score} / 5.0</span>
      </div>
      <div class="text-xs text-slate-400 font-mono">Period: ${r.review_period} &bull; Evaluator: ${r.reviewer_name}</div>
      <div class="grid grid-cols-2 gap-2 text-xs font-mono bg-darkSurface p-3 rounded-xl border border-darkBorder">
        <div>Delivered: <strong class="text-white">${r.tasks_completed} Tasks</strong></div>
        <div>On-Time Rate: <strong class="text-emerald-400">${r.on_time_rate}%</strong></div>
      </div>
      <p class="text-xs text-slate-300 bg-darkSurface p-3 rounded-xl border border-darkBorder">${r.feedback}</p>
    </div>
  `).join('');
}

async function loadInternships() {
  const res = await apiRequest('/hr/interns');
  if (!res.success) return;
  const interns = res.interns || [];
  const container = document.getElementById('tab-internships');
  if (!container) return;

  let modulesHtml = interns.map(it => `
    <div class="bg-darkCard border border-darkBorder rounded-2xl p-6 space-y-4 shadow-lg">
      <div class="flex items-center justify-between">
        <span class="font-bold text-base text-white font-outfit">${it.intern_name}</span>
        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">${it.certificate_status}</span>
      </div>
      <div class="text-xs text-slate-400">Mentor: <strong>${it.mentor_name}</strong> &bull; Department: ${it.department}</div>
      <div>
        <div class="flex justify-between text-xs font-mono mb-1">
          <span class="text-slate-400">Curriculum Progress</span>
          <span class="text-purple-400 font-bold">${it.progress_percent}%</span>
        </div>
        <div class="w-full h-2 bg-darkSurface rounded-full overflow-hidden">
          <div class="h-full bg-purple-500" style="width: ${it.progress_percent}%"></div>
        </div>
      </div>
      <div class="p-3 bg-darkSurface border border-darkBorder rounded-xl text-xs text-slate-300">
        <strong>Mentor Evaluation:</strong> ${it.feedback || 'High technical dedication.'}
      </div>
    </div>
  `).join('');

  container.innerHTML = `
    <div>
      <h2 class="text-2xl font-bold font-outfit text-white">People &rarr; Interns</h2>
      <p class="text-xs text-slate-400 mt-0.5">Engineering interns, curriculum module tracks, and practical project evaluations.</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
      ${modulesHtml}
    </div>
  `;
}

async function loadAnnouncements() {
  const res = await apiRequest('/announcements');
  if (!res.success) return;
  const announcements = res.announcements || [];
  const fullList = document.getElementById('announcements-full-list');
  if (fullList) {
    fullList.innerHTML = announcements.map(a => `
      <div class="bg-darkCard border border-darkBorder rounded-2xl p-6 space-y-2">
        <div class="flex items-center justify-between">
          <h3 class="font-bold text-sm text-white">${a.title}</h3>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${a.priority === 'High' ? 'bg-red-500/10 text-red-400' : 'bg-blue-500/10 text-blue-400'}">${a.priority} Priority</span>
        </div>
        <p class="text-xs text-slate-300 leading-relaxed">${a.content}</p>
        <div class="text-[10px] text-slate-500 font-mono pt-2 border-t border-darkBorder">Posted by ${a.author_name} (${a.author_role}) &bull; ${a.created_at}</div>
      </div>
    `).join('');
  }
}

async function loadAuditLogs() {
  if (currentUser?.role !== 'CEO' && currentUser?.role !== 'Manager') return;
  const res = await apiRequest('/audit-logs');
  if (!res.success) return;
  const logs = res.audit_logs || [];
  const tbody = document.getElementById('audit-logs-table-body');
  if (tbody) {
    tbody.innerHTML = logs.map(l => `
      <tr class="hover:bg-darkSurface/50 transition">
        <td class="p-3.5 text-slate-400">${l.created_at}</td>
        <td class="p-3.5 font-bold text-white">${l.user_name}</td>
        <td class="p-3.5 text-blue-400">${l.action}</td>
        <td class="p-3.5 text-slate-300">${l.entity} (${l.entity_id})</td>
        <td class="p-3.5 text-amber-400/90">${l.reason || '--'}</td>
        <td class="p-3.5 text-slate-500">${l.ip_address}</td>
      </tr>
    `).join('');
  }
}

async function loadNotifications() {
  const res = await apiRequest('/notifications');
  if (!res.success) return;
  const notifs = res.notifications || [];
  const list = document.getElementById('notifications-list');
  const dot = document.getElementById('notification-unread-dot');
  
  const unread = notifs.filter(n => n.is_read === 0).length;
  if (dot) {
    if (unread > 0) dot.classList.remove('hidden');
    else dot.classList.add('hidden');
  }

  if (list) {
    if (notifs.length === 0) {
      list.innerHTML = '<div class="text-slate-500 text-center py-4">No notifications.</div>';
    } else {
      list.innerHTML = notifs.map(n => `
        <div class="p-2.5 bg-darkSurface rounded-xl border border-darkBorder ${n.is_read === 0 ? 'border-blue-500/40 bg-blue-500/5' : ''}">
          <div class="font-bold text-white text-[11px]">${n.title}</div>
          <p class="text-slate-400 text-[10px] mt-0.5">${n.message}</p>
        </div>
      `).join('');
    }
  }
}

// ==========================================================================
// 10. MODALS & GLOBAL FORM HANDLERS
// ==========================================================================
function initModals() {
  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('.open-modal-trigger');
    if (trigger && trigger.dataset.modal) {
      document.getElementById(trigger.dataset.modal)?.classList.remove('hidden');
    }

    const closeBtn = e.target.closest('.modal-close-btn');
    if (closeBtn) {
      closeBtn.closest('.modal-backdrop')?.classList.add('hidden');
    }
  });

  // Create Employee Form
  document.getElementById('form-create-employee')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('emp-in-name').value.trim();
    const username = document.getElementById('emp-in-user').value.trim();
    const emp_code = document.getElementById('emp-in-code').value.trim();
    const role = document.getElementById('emp-in-role-select').value;
    const department = document.getElementById('emp-in-dept-select').value;
    const designation = document.getElementById('emp-in-desig').value.trim();
    const basic_pay = parseFloat(document.getElementById('emp-in-sal').value || 75000);

    const res = await apiRequest('/employees', 'POST', {
      name, username, emp_code, role, department, designation, basic_pay
    });

    if (res.success) {
      showToast(res.message, 'success');
      document.getElementById('modal-create-employee').classList.add('hidden');
      document.getElementById('form-create-employee').reset();
      loadEmployees();
    } else {
      showToast(res.error || 'Failed to create employee.', 'error');
    }
  });

  // Create Task Form
  document.getElementById('form-create-task')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('task-in-title').value.trim();
    const project_id = document.getElementById('task-in-project').value;
    const project_name = document.getElementById('task-in-project').selectedOptions[0]?.dataset.name || '';
    const assigned_to_id = document.getElementById('task-in-assignee').value;
    const assigned_to_name = document.getElementById('task-in-assignee').selectedOptions[0]?.dataset.name || '';
    const priority = document.getElementById('task-in-priority').value;
    const deadline = document.getElementById('task-in-deadline').value;
    const description = document.getElementById('task-in-desc').value;

    const res = await apiRequest('/tasks', 'POST', {
      title, project_id, project_name, assigned_to_id, assigned_to_name, priority, deadline, description
    });

    if (res.success) {
      showToast('Task assigned successfully.', 'success');
      document.getElementById('modal-create-task').classList.add('hidden');
      document.getElementById('form-create-task').reset();
      loadTasks();
    } else {
      showToast(res.error || 'Failed to create task.', 'error');
    }
  });

  // Duty Clock Buttons
  document.getElementById('att-btn-in')?.addEventListener('click', async () => {
    const res = await apiRequest('/hr/attendance', 'POST', { action: 'clock_in' });
    if (res.success) showToast(res.message, 'success');
    else showToast(res.error, 'error');
    loadAttendance();
  });
  document.getElementById('att-btn-out')?.addEventListener('click', async () => {
    const res = await apiRequest('/hr/attendance', 'POST', { action: 'clock_out' });
    if (res.success) showToast(res.message, 'info');
    else showToast(res.error, 'error');
    loadAttendance();
  });
  document.getElementById('dash-btn-clock-action')?.addEventListener('click', async () => {
    const res = await apiRequest('/hr/attendance', 'POST', { action: 'clock_in' });
    if (res.success) showToast(res.message, 'success');
    else showToast(res.error || 'Attendance recorded', 'info');
    loadAttendance();
  });

  // Compose Mail Form
  document.getElementById('form-compose-mail')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const to = document.getElementById('mail-to').value.trim();
    const subject = document.getElementById('mail-subject').value.trim();
    const body = document.getElementById('mail-body').value.trim();

    const res = await apiRequest('/mail', 'POST', { to, subject, body });
    if (res.success) {
      showToast('Internal mail dispatched.', 'success');
      document.getElementById('modal-compose-mail').classList.add('hidden');
      document.getElementById('form-compose-mail').reset();
      loadInternalMail();
    } else {
      showToast(res.error || 'Failed to send mail.', 'error');
    }
  });

  // Chat message submit
  document.getElementById('chat-send-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('chat-message-input');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    await apiRequest('/chat/messages', 'POST', { channel_id: activeChatChannel, message });
    loadChatMessages(activeChatChannel);
  });
}

// ==========================================================================
// 11. GLOBAL SEARCH (CTRL+K OMNIBAR)
// ==========================================================================
function initOmniSearch() {
  const searchModal = document.getElementById('modal-search');
  const searchInput = document.getElementById('omni-search-input');
  const searchResults = document.getElementById('omni-search-results');

  document.querySelectorAll('.open-search-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      searchModal.classList.remove('hidden');
      searchInput.focus();
    });
  });

  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      searchModal.classList.remove('hidden');
      searchInput.focus();
    }
    if (e.key === 'Escape' && !searchModal.classList.contains('hidden')) {
      searchModal.classList.add('hidden');
    }
  });

  let searchTimeout;
  searchInput?.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const query = searchInput.value.trim();
    if (query.length < 2) {
      searchResults.innerHTML = '<div class="text-slate-500 text-center py-6">Type to query the workspace registry...</div>';
      return;
    }
    searchTimeout = setTimeout(async () => {
      const res = await apiRequest(`/search?q=${encodeURIComponent(query)}`);
      if (res.success && res.results) {
        if (res.results.length === 0) {
          searchResults.innerHTML = '<div class="text-slate-500 text-center py-6">No matching records found.</div>';
        } else {
          searchResults.innerHTML = res.results.map(r => `
            <div class="p-3 bg-darkSurface hover:bg-slate-800 rounded-xl border border-darkBorder cursor-pointer transition flex items-center justify-between" onclick="selectSearchResult('${r.tab}', '${r.id}', '${r.type}')">
              <div>
                <div class="font-bold text-white text-xs">${r.title}</div>
                <div class="text-[11px] text-slate-400">${r.subtitle}</div>
              </div>
              <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-blue-500/10 text-blue-400 font-bold">${r.type}</span>
            </div>
          `).join('');
        }
      }
    }, 200);
  });
}

window.selectSearchResult = function(tabId, itemId, type) {
  document.getElementById('modal-search').classList.add('hidden');
  if (type === 'People') {
    window.viewEmployeeProfile(parseInt(itemId));
  } else {
    window.switchTab(tabId);
  }
};

// ==========================================================================
// 12. KAPATE AI COPILOT
// ==========================================================================
function initKapateAI() {
  const form = document.getElementById('ai-query-form');
  const input = document.getElementById('ai-query-input');
  const stream = document.getElementById('ai-chat-stream');

  document.querySelectorAll('.ai-prompt-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const text = chip.textContent.replaceAll('"', '').trim();
      input.value = text;
      form.dispatchEvent(new Event('submit'));
    });
  });

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;

    input.value = '';
    stream.innerHTML += `
      <div class="flex gap-3 bg-darkCard p-3.5 rounded-xl border border-darkBorder">
        <div class="w-7 h-7 rounded-lg bg-slate-800 flex-shrink-0 flex items-center justify-center text-white font-bold text-xs">
          ${currentUser?.name.substring(0, 2).toUpperCase() || 'ME'}
        </div>
        <div class="text-white text-xs font-medium pt-1">${query}</div>
      </div>
    `;
    stream.scrollTop = stream.scrollHeight;

    const tempId = `ai-load-${Date.now()}`;
    stream.innerHTML += `
      <div id="${tempId}" class="flex gap-3 bg-darkCard p-3.5 rounded-xl border border-darkBorder">
        <div class="w-7 h-7 rounded-lg bg-blue-600 flex-shrink-0 flex items-center justify-center text-white font-bold text-xs">AI</div>
        <div class="text-slate-400 text-xs flex items-center gap-2"><span>Evaluating permissions &amp; workspace registry...</span></div>
      </div>
    `;
    stream.scrollTop = stream.scrollHeight;

    const res = await apiRequest('/ai/query', 'POST', { query });
    const loadEl = document.getElementById(tempId);
    if (loadEl) loadEl.remove();

    if (res.success) {
      stream.innerHTML += `
        <div class="flex gap-3 bg-darkCard p-4 rounded-xl border border-darkBorder">
          <div class="w-7 h-7 rounded-lg bg-blue-600 flex-shrink-0 flex items-center justify-center text-white font-bold text-xs">AI</div>
          <div class="text-slate-200 text-xs leading-relaxed space-y-2 whitespace-pre-line">${res.response}</div>
        </div>
      `;
    } else {
      stream.innerHTML += `
        <div class="flex gap-3 bg-darkCard p-4 rounded-xl border border-red-500/30">
          <div class="w-7 h-7 rounded-lg bg-red-600 flex-shrink-0 flex items-center justify-center text-white font-bold text-xs">!</div>
          <div class="text-red-400 text-xs">${res.error || 'Failed to process AI query.'}</div>
        </div>
      `;
    }
    stream.scrollTop = stream.scrollHeight;
  });
}

// ==========================================================================
// 13. TIME TRACKER & UTILITIES
// ==========================================================================
function initStopwatch() {
  const toggleBtn = document.getElementById('btn-toggle-timer');
  const mainBtn = document.getElementById('btn-stopwatch-action');
  const display = document.getElementById('timer-display');
  const mainDisplay = document.getElementById('main-stopwatch-display');
  const indicator = document.getElementById('timer-indicator');

  function updateDisplay() {
    const hrs = String(Math.floor(stopwatchSeconds / 3600)).padStart(2, '0');
    const mins = String(Math.floor((stopwatchSeconds % 3600) / 60)).padStart(2, '0');
    const secs = String(stopwatchSeconds % 60).padStart(2, '0');
    const str = `${hrs}:${mins}:${secs}`;
    if (display) display.textContent = str;
    if (mainDisplay) mainDisplay.textContent = str;
  }

  function toggleStopwatch() {
    if (activeStopwatchInterval) {
      clearInterval(activeStopwatchInterval);
      activeStopwatchInterval = null;
      if (toggleBtn) toggleBtn.textContent = 'Start Timer';
      if (mainBtn) mainBtn.textContent = 'Start Session';
      if (indicator) indicator.className = 'w-2 h-2 rounded-full bg-slate-500';
      showToast(`Stopwatch recorded at ${display.textContent}. Saved to timesheet.`, 'info');
    } else {
      activeStopwatchInterval = setInterval(() => {
        stopwatchSeconds++;
        updateDisplay();
      }, 1000);
      if (toggleBtn) toggleBtn.textContent = 'Stop';
      if (mainBtn) mainBtn.textContent = 'Stop Session';
      if (indicator) indicator.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-pulse';
      showToast('Session stopwatch started.', 'success');
    }
  }

  toggleBtn?.addEventListener('click', toggleStopwatch);
  mainBtn?.addEventListener('click', toggleStopwatch);
}

function initTheme() {
  const toggle = document.getElementById('theme-toggle-workspace');
  if (toggle) {
    toggle.addEventListener('click', () => {
      document.documentElement.classList.toggle('light');
      document.documentElement.classList.toggle('dark');
    });
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast-msg';
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
