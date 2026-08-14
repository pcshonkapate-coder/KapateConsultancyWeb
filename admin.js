// ==========================================================================
// ENTERPRISE SAAS DASHBOARD & CRM ENGINE (Kapate Consultancy)
// ==========================================================================

const API_BASE = '/api/admin';
const AUTH_TOKEN = "Bearer kapate-admin-secure-token-98765";

let chartRevenue = null;
let chartService = null;
let currentDraggedProjectId = null;

document.addEventListener('DOMContentLoaded', () => {
    initAuth();
    initNavigation();
    initNotifications();
    initModals();
});

// --------------------------------------------------------------------------
// 1. AUTHENTICATION & SESSION MANAGEMENT
// --------------------------------------------------------------------------
function initAuth() {
    const loginForm = document.getElementById('login-form');
    const loginScreen = document.getElementById('login-screen');
    const dashboardScreen = document.getElementById('dashboard-screen');
    const logoutBtn = document.getElementById('logout-btn');

    // Check existing session
    const savedToken = localStorage.getItem('kc_saas_token');
    const savedRole = localStorage.getItem('kc_saas_role') || 'Admin';

    if (savedToken) {
        loginScreen.style.display = 'none';
        dashboardScreen.style.display = 'flex';
        document.getElementById('display-role').textContent = savedRole;
        loadAllData();
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const pass = document.getElementById('login-password').value;
        const role = document.getElementById('login-role').value;
        const alertBox = document.getElementById('login-alert');

        if (pass === 'Admin@KapateConsultancy8421174957') {
            localStorage.setItem('kc_saas_token', AUTH_TOKEN);
            localStorage.setItem('kc_saas_role', role);
            loginScreen.style.display = 'none';
            dashboardScreen.style.display = 'flex';
            document.getElementById('display-role').textContent = role;
            loadAllData();
        } else {
            alertBox.textContent = 'Invalid system password. Please try again.';
            alertBox.style.display = 'block';
        }
    });

    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('kc_saas_token');
        localStorage.removeItem('kc_saas_role');
        location.reload();
    });
}

// --------------------------------------------------------------------------
// 2. SPA NAVIGATION & TABS
// --------------------------------------------------------------------------
function initNavigation() {
    const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
    const tabContents = document.querySelectorAll('.tab-content');
    const pageTitle = document.getElementById('active-tab-title');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');

            navItems.forEach(i => i.classList.remove('active'));
            tabContents.forEach(t => t.classList.remove('active'));

            item.classList.add('active');
            const activeElem = document.getElementById(targetTab);
            if (activeElem) activeElem.classList.add('active');

            // Update Header Title
            const tabNames = {
                'tab-analytics': 'Executive Dashboard',
                'tab-clients': 'Client CRM Management',
                'tab-kanban': 'Projects Kanban Pipeline',
                'tab-leads': 'Lead Generation Engine',
                'tab-inquiries': 'Customer Inquiries',
                'tab-reviews': 'Client Reviews CMS',
                'tab-activity': 'Administrative Activity Log',
                'tab-reports': 'Data Export & Reports',
                'tab-settings': 'System Settings'
            };
            pageTitle.textContent = tabNames[targetTab] || 'Dashboard';
        });
    });
}

// --------------------------------------------------------------------------
// 3. MASTER DATA LOADER
// --------------------------------------------------------------------------
async function loadAllData() {
    await fetchAnalytics();
    await fetchClients();
    await fetchProjects();
    await fetchLeads();
    await fetchInquiries();
    await fetchReviews();
    await fetchActivity();
    await fetchNotifications();
}

// --------------------------------------------------------------------------
// 4. CHART.JS ANALYTICS ENGINE
// --------------------------------------------------------------------------
async function fetchAnalytics() {
    try {
        const res = await fetch(`${API_BASE}/analytics`, {
            headers: { 'Authorization': AUTH_TOKEN }
        });
        const data = await res.json();

        if (data.success) {
            document.getElementById('kpi-revenue').textContent = `₹${data.kpis.total_revenue.toLocaleString('en-IN')}`;
            document.getElementById('kpi-clients').textContent = data.kpis.total_clients;
            document.getElementById('kpi-projects').textContent = data.kpis.active_projects;
            document.getElementById('kpi-conversion').textContent = data.kpis.conversion_rate;

            renderRevenueChart(data.monthly_growth);
            renderServiceChart(data.services_chart);
        }
    } catch (err) {
        console.error('Analytics fetch error:', err);
    }
}

function renderRevenueChart(monthlyData) {
    const ctx = document.getElementById('chart-revenue-growth');
    if (!ctx) return;

    if (chartRevenue) chartRevenue.destroy();

    chartRevenue = new Chart(ctx, {
        type: 'line',
        data: {
            labels: monthlyData.labels,
            datasets: [{
                label: 'Monthly Revenue (₹)',
                data: monthlyData.revenue,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.15)',
                borderWidth: 3,
                fill: true,
                tension: 0.35,
                pointRadius: 5,
                pointBackgroundColor: '#3b82f6'
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } }
            }
        }
    });
}

function renderServiceChart(servicesData) {
    const ctx = document.getElementById('chart-service-distribution');
    if (!ctx) return;

    if (chartService) chartService.destroy();

    chartService = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: servicesData.labels,
            datasets: [{
                data: servicesData.counts,
                backgroundColor: ['#3b82f6', '#06b6d4', '#8b5cf6', '#f59e0b', '#10b981'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#9ca3af', font: { size: 11 } } }
            }
        }
    });
}

// --------------------------------------------------------------------------
// 5. CLIENT CRM MANAGEMENT
// --------------------------------------------------------------------------
async function fetchClients() {
    try {
        const res = await fetch(`${API_BASE}/clients`, { headers: { 'Authorization': AUTH_TOKEN } });
        const clients = await res.json();

        document.getElementById('badge-clients-count').textContent = clients.length;
        const tbody = document.getElementById('clients-table-body');
        tbody.innerHTML = '';

        clients.forEach(c => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${c.name}</strong></td>
                <td>${c.company || 'N/A'}</td>
                <td>${c.email}</td>
                <td><span class="badge badge-${c.tag.toLowerCase()}">${c.tag}</span></td>
                <td>${c.status}</td>
                <td style="font-weight:700; color:var(--color-success);">₹${c.total_spent.toLocaleString('en-IN')}</td>
                <td>
                    <button class="btn btn-outline btn-sm" onclick="deleteClient(${c.id})">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Clients fetch error:', err);
    }
}

async function deleteClient(id) {
    if (!confirm('Are you sure you want to delete this client profile?')) return;
    try {
        await fetch(`${API_BASE}/clients/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': AUTH_TOKEN }
        });
        loadAllData();
    } catch (err) {
        console.error('Delete client error:', err);
    }
}

// --------------------------------------------------------------------------
// 6. KANBAN PROJECT BOARD & DRAG AND DROP
// --------------------------------------------------------------------------
async function fetchProjects() {
    try {
        const res = await fetch(`${API_BASE}/projects`, { headers: { 'Authorization': AUTH_TOKEN } });
        const projects = await res.json();

        document.getElementById('badge-projects-count').textContent = projects.length;

        const containers = {
            'Pending': document.getElementById('col-pending-container'),
            'In Progress': document.getElementById('col-progress-container'),
            'Review': document.getElementById('col-review-container'),
            'Completed': document.getElementById('col-completed-container')
        };
        const counts = { 'Pending': 0, 'In Progress': 0, 'Review': 0, 'Completed': 0 };

        Object.values(containers).forEach(c => c.innerHTML = '');

        projects.forEach(p => {
            if (counts.hasOwnProperty(p.status)) counts[p.status]++;

            const card = document.createElement('div');
            card.className = 'kanban-card';
            card.draggable = true;
            card.id = `proj-card-${p.id}`;
            card.setAttribute('ondragstart', `dragStart(event, ${p.id})`);

            card.innerHTML = `
                <div class="kanban-card-title">${p.title}</div>
                <div class="kanban-card-client">Client: <strong>${p.client_name}</strong></div>
                <div class="progress-bar-wrap">
                    <div class="progress-bar-fill" style="width: ${p.progress}%;"></div>
                </div>
                <div class="kanban-card-footer">
                    <span>Deadline: ${p.deadline || 'Flexible'}</span>
                    <span class="kanban-budget">₹${p.budget.toLocaleString('en-IN')}</span>
                </div>
            `;

            if (containers[p.status]) containers[p.status].appendChild(card);
        });

        document.getElementById('count-pending').textContent = counts['Pending'];
        document.getElementById('count-progress').textContent = counts['In Progress'];
        document.getElementById('count-review').textContent = counts['Review'];
        document.getElementById('count-completed').textContent = counts['Completed'];

    } catch (err) {
        console.error('Projects fetch error:', err);
    }
}

function allowDrop(ev) {
    ev.preventDefault();
}

function dragStart(ev, id) {
    currentDraggedProjectId = id;
    ev.dataTransfer.setData("text/plain", id);
}

async function dropKanban(ev) {
    ev.preventDefault();
    let col = ev.target;
    while (col && !col.classList.contains('kanban-col')) {
        col = col.parentElement;
    }
    if (!col) return;

    const newStatus = col.getAttribute('data-status');
    if (currentDraggedProjectId && newStatus) {
        try {
            await fetch(`${API_BASE}/projects/${currentDraggedProjectId}/status`, {
                method: 'PUT',
                headers: {
                    'Authorization': AUTH_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: newStatus })
            });
            fetchProjects();
            fetchAnalytics();
        } catch (err) {
            console.error('Update status error:', err);
        }
    }
}

// --------------------------------------------------------------------------
// 7. LEADS ENGINE & INQUIRIES
// --------------------------------------------------------------------------
async function fetchLeads() {
    try {
        const res = await fetch(`${API_BASE}/leads`, { headers: { 'Authorization': AUTH_TOKEN } });
        const leads = await res.json();

        document.getElementById('badge-leads-count').textContent = leads.length;
        const tbody = document.getElementById('leads-table-body');
        tbody.innerHTML = '';

        leads.forEach(l => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${l.name}</strong></td>
                <td>${l.email}</td>
                <td>${l.service.toUpperCase()}</td>
                <td><strong style="color:var(--color-primary);">${l.score}/100</strong></td>
                <td><span class="badge badge-${l.priority.toLowerCase()}">${l.priority}</span></td>
                <td>${l.created_at ? l.created_at.split(' ')[0] : 'Today'}</td>
                <td>
                    <a href="mailto:${l.email}" class="btn btn-outline btn-sm">Email Lead</a>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Leads fetch error:', err);
    }
}

async function fetchInquiries() {
    try {
        const res = await fetch(`${API_BASE}/inquiries`, { headers: { 'Authorization': AUTH_TOKEN } });
        const inquiries = await res.json();

        document.getElementById('badge-inquiries-count').textContent = inquiries.length;
        const tbody = document.getElementById('inquiries-table-body');
        tbody.innerHTML = '';

        inquiries.forEach(inq => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><code style="color:var(--color-accent); font-weight:700;">${inq.reference_number}</code></td>
                <td><strong>${inq.name}</strong></td>
                <td>${inq.email}</td>
                <td>${inq.service.toUpperCase()}</td>
                <td><span class="badge badge-lead">${inq.status}</span></td>
                <td>
                    <button class="btn btn-outline btn-sm" onclick="deleteInquiry(${inq.id})">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Inquiries fetch error:', err);
    }
}

async function deleteInquiry(id) {
    if (!confirm('Delete inquiry record?')) return;
    try {
        await fetch(`${API_BASE}/inquiries/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': AUTH_TOKEN }
        });
        loadAllData();
    } catch (err) {
        console.error('Delete inquiry error:', err);
    }
}

// --------------------------------------------------------------------------
// 8. REVIEWS MODERATION & ACTIVITY LOGS
// --------------------------------------------------------------------------
async function fetchReviews() {
    try {
        const res = await fetch(`${API_BASE}/reviews`, { headers: { 'Authorization': AUTH_TOKEN } });
        const reviews = await res.json();
        const tbody = document.getElementById('reviews-table-body');
        tbody.innerHTML = '';

        reviews.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${r.name}</strong></td>
                <td>${r.role}</td>
                <td>⭐ ${r.rating}/5</td>
                <td><em>"${r.review_text}"</em></td>
                <td>${r.approved ? '<span class="badge badge-vip">Published</span>' : '<span class="badge badge-warm">Pending</span>'}</td>
                <td>
                    ${!r.approved ? `<button class="btn btn-primary btn-sm" onclick="approveReview(${r.id})">Approve</button>` : ''}
                    <button class="btn btn-outline btn-sm" onclick="deleteReview(${r.id})">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Reviews fetch error:', err);
    }
}

async function approveReview(id) {
    try {
        await fetch(`${API_BASE}/reviews/${id}/approve`, {
            method: 'PUT',
            headers: { 'Authorization': AUTH_TOKEN }
        });
        fetchReviews();
        fetchAnalytics();
    } catch (err) {
        console.error('Approve review error:', err);
    }
}

async function deleteReview(id) {
    if (!confirm('Delete review?')) return;
    try {
        await fetch(`${API_BASE}/reviews/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': AUTH_TOKEN }
        });
        fetchReviews();
    } catch (err) {
        console.error('Delete review error:', err);
    }
}

async function fetchActivity() {
    try {
        const res = await fetch(`${API_BASE}/activity`, { headers: { 'Authorization': AUTH_TOKEN } });
        const logs = await res.json();
        const tbody = document.getElementById('activity-table-body');
        tbody.innerHTML = '';

        logs.forEach(log => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${log.user_name}</strong></td>
                <td>${log.action}</td>
                <td style="color:var(--color-text-muted);">${log.details}</td>
                <td style="font-size:0.75rem;">${log.created_at}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Activity logs fetch error:', err);
    }
}

// --------------------------------------------------------------------------
// 9. NOTIFICATIONS & EXPORT ENGINE
// --------------------------------------------------------------------------
function initNotifications() {
    const bell = document.getElementById('notif-bell-btn');
    const dropdown = document.getElementById('notif-dropdown');
    const markReadBtn = document.getElementById('mark-notif-read-btn');

    bell.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('show');
    });

    document.addEventListener('click', () => dropdown.classList.remove('show'));

    markReadBtn.addEventListener('click', async () => {
        try {
            await fetch(`${API_BASE}/notifications`, {
                method: 'PUT',
                headers: { 'Authorization': AUTH_TOKEN }
            });
            document.getElementById('notif-unread-count').textContent = '0';
            fetchNotifications();
        } catch (err) {
            console.error('Mark read error:', err);
        }
    });
}

async function fetchNotifications() {
    try {
        const res = await fetch(`${API_BASE}/notifications`, { headers: { 'Authorization': AUTH_TOKEN } });
        const notifs = await res.json();
        const container = document.getElementById('notif-list-container');
        container.innerHTML = '';

        let unread = 0;
        notifs.forEach(n => {
            if (!n.is_read) unread++;
            const item = document.createElement('div');
            item.className = 'notif-item';
            item.innerHTML = `
                <div class="notif-item-title">${n.title}</div>
                <div class="notif-item-desc">${n.message}</div>
                <div class="notif-item-time">${n.created_at}</div>
            `;
            container.appendChild(item);
        });

        document.getElementById('notif-unread-count').textContent = unread;
    } catch (err) {
        console.error('Notifications fetch error:', err);
    }
}

function downloadExport(type) {
    window.open(`${API_BASE}/export/${type}?token=kapate-admin-secure-token-98765`, '_blank');
}

// --------------------------------------------------------------------------
// 10. MODALS & FORMS
// --------------------------------------------------------------------------
function initModals() {
    document.getElementById('add-client-modal-btn').addEventListener('click', () => {
        document.getElementById('add-client-modal').classList.add('show');
    });

    document.getElementById('add-project-modal-btn').addEventListener('click', () => {
        document.getElementById('add-project-modal').classList.add('show');
    });

    document.getElementById('add-client-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            name: document.getElementById('nc-name').value,
            email: document.getElementById('nc-email').value,
            company: document.getElementById('nc-company').value,
            phone: document.getElementById('nc-phone').value,
            tag: document.getElementById('nc-tag').value,
            total_spent: parseFloat(document.getElementById('nc-spent').value || 0)
        };

        try {
            const res = await fetch(`${API_BASE}/clients`, {
                method: 'POST',
                headers: {
                    'Authorization': AUTH_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                closeModals();
                loadAllData();
            }
        } catch (err) {
            console.error('Add client error:', err);
        }
    });

    document.getElementById('add-project-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            title: document.getElementById('np-title').value,
            client_name: document.getElementById('np-client').value,
            service: document.getElementById('np-service').value,
            budget: parseFloat(document.getElementById('np-budget').value || 0),
            status: document.getElementById('np-status').value
        };

        try {
            const res = await fetch(`${API_BASE}/projects`, {
                method: 'POST',
                headers: {
                    'Authorization': AUTH_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                closeModals();
                loadAllData();
            }
        } catch (err) {
            console.error('Add project error:', err);
        }
    });
}

function closeModals() {
    document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('show'));
}
