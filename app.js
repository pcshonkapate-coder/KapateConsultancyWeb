/* ==========================================================================
   Kapate Consultancy — Enterprise App Logic & Interactivity v3.0
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {

  /* ========================================================================
     1. THEME TOGGLE (Dark / Light Mode)
     ====================================================================== */
  const themeBtn = document.getElementById('theme-toggle-btn');
  const body     = document.body;

  const savedTheme = localStorage.getItem('kapate-theme') || 'dark-theme';
  body.className = savedTheme;

  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const isDark = body.classList.contains('dark-theme');
      body.classList.replace(
        isDark ? 'dark-theme' : 'light-theme',
        isDark ? 'light-theme' : 'dark-theme'
      );
      localStorage.setItem('kapate-theme', body.classList.contains('dark-theme') ? 'dark-theme' : 'light-theme');
      if (particles) particles.updateColors();
    });
  }


  /* ========================================================================
     2. SCROLL PROGRESS BAR
     ====================================================================== */
  const progressBar = document.getElementById('scroll-progress');
  if (progressBar) {
    window.addEventListener('scroll', () => {
      const scrolled = window.scrollY;
      const total    = document.documentElement.scrollHeight - window.innerHeight;
      progressBar.style.width = total > 0 ? `${(scrolled / total) * 100}%` : '0%';
    }, { passive: true });
  }


  /* ========================================================================
     3. STICKY HEADER
     ====================================================================== */
  const header = document.getElementById('main-header');
  if (header) {
    window.addEventListener('scroll', () => {
      header.classList.toggle('scrolled', window.scrollY > 50);
    }, { passive: true });
  }


  /* ========================================================================
     4. MOBILE NAVIGATION DRAWER
     ====================================================================== */
  const menuToggle = document.getElementById('menu-toggle');
  const navMenu    = document.getElementById('nav-menu');
  const overlay    = document.getElementById('mobile-nav-overlay');
  const closeBtn   = document.getElementById('mobile-nav-close');
  const navLinks   = document.querySelectorAll('.nav-link');

  const openNav  = () => { menuToggle.classList.add('open'); navMenu.classList.add('open'); overlay.classList.add('show'); body.style.overflow = 'hidden'; };
  const closeNav = () => { menuToggle.classList.remove('open'); navMenu.classList.remove('open'); overlay.classList.remove('show'); body.style.overflow = ''; };

  if (menuToggle && navMenu && overlay) {
    menuToggle.addEventListener('click', () => navMenu.classList.contains('open') ? closeNav() : openNav());
    if (closeBtn) closeBtn.addEventListener('click', closeNav);
    overlay.addEventListener('click', closeNav);
    navLinks.forEach(link => link.addEventListener('click', closeNav));
  }

  // Scroll spy active link tracking
  const sections = document.querySelectorAll('section[id]');
  window.addEventListener('scroll', () => {
    let current = '';
    sections.forEach(section => {
      if (window.scrollY >= section.offsetTop - 140) current = section.id;
    });
    navLinks.forEach(link => {
      link.classList.toggle('active', link.getAttribute('href') === `#${current}`);
    });
  }, { passive: true });


  /* ========================================================================
     5. PARTICLE PHYSICS CANVAS SYSTEM
     ====================================================================== */
  class ParticleSystem {
    constructor() {
      this.canvas = document.getElementById('particle-canvas');
      if (!this.canvas) return;
      this.ctx     = this.canvas.getContext('2d');
      this.particles = [];
      this.mouse   = { x: null, y: null };
      this.raf     = null;
      this.pColor  = this.getParticleColor();
      this.resize();
      this.addListeners();
      this.animate();
    }

    getParticleColor() {
      return body.classList.contains('dark-theme')
        ? 'rgba(96, 165, 250, '
        : 'rgba(37, 99, 235, ';
    }

    updateColors() {
      this.pColor = this.getParticleColor();
    }

    resize() {
      this.canvas.width  = this.canvas.offsetWidth  || window.innerWidth;
      this.canvas.height = this.canvas.offsetHeight || window.innerHeight;
      this.spawnParticles();
    }

    spawnParticles() {
      this.particles = [];
      const count = Math.min(Math.floor((this.canvas.width * this.canvas.height) / 14000), 80);
      for (let i = 0; i < count; i++) {
        this.particles.push({
          x:  Math.random() * this.canvas.width,
          y:  Math.random() * this.canvas.height,
          vx: (Math.random() - 0.5) * 0.45,
          vy: (Math.random() - 0.5) * 0.45,
          r:  Math.random() * 1.4 + 0.5,
          op: Math.random() * 0.5 + 0.15,
        });
      }
    }

    addListeners() {
      window.addEventListener('resize', () => this.resize(), { passive: true });
      if (this.canvas.parentElement) {
        this.canvas.parentElement.addEventListener('mousemove', (e) => {
          const rect = this.canvas.getBoundingClientRect();
          this.mouse.x = e.clientX - rect.left;
          this.mouse.y = e.clientY - rect.top;
        });
        this.canvas.parentElement.addEventListener('mouseleave', () => {
          this.mouse.x = null;
          this.mouse.y = null;
        });
      }
    }

    draw() {
      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      const maxDist = 130;

      for (let i = 0; i < this.particles.length; i++) {
        const p = this.particles[i];

        if (this.mouse.x !== null) {
          const dx   = p.x - this.mouse.x;
          const dy   = p.y - this.mouse.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) {
            p.vx += (dx / dist) * 0.04;
            p.vy += (dy / dist) * 0.04;
          }
        }

        p.vx *= 0.992;
        p.vy *= 0.992;
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > this.canvas.width)  { p.vx *= -1; p.x = Math.max(0, Math.min(this.canvas.width, p.x)); }
        if (p.y < 0 || p.y > this.canvas.height)  { p.vy *= -1; p.y = Math.max(0, Math.min(this.canvas.height, p.y)); }

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `${this.pColor}${p.op})`;
        ctx.fill();

        for (let j = i + 1; j < this.particles.length; j++) {
          const q  = this.particles[j];
          const dx = p.x - q.x;
          const dy = p.y - q.y;
          const d  = Math.sqrt(dx * dx + dy * dy);
          if (d < maxDist) {
            ctx.beginPath();
            ctx.strokeStyle = `${this.pColor}${((1 - d / maxDist) * 0.14).toFixed(3)})`;
            ctx.lineWidth = 0.7;
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(q.x, q.y);
            ctx.stroke();
          }
        }
      }
    }

    animate() {
      this.draw();
      this.raf = requestAnimationFrame(() => this.animate());
    }
  }

  const particles = new ParticleSystem();


  /* ========================================================================
     6. HERO TYPED ANIMATION
     ====================================================================== */
  const typedEl = document.getElementById('typed-word');
  if (typedEl) {
    const words = [
      'Fullstack Web Platforms',
      'Custom AI & ML Solutions',
      'Enterprise Software & ERP',
      'Cloud Architecture & DevOps',
      'Academic R&D Mentorship',
    ];
    let wIdx = 0, cIdx = 0, deleting = false;

    const typeNext = () => {
      const word = words[wIdx % words.length];
      typedEl.textContent = deleting
        ? word.substring(0, cIdx - 1)
        : word.substring(0, cIdx + 1);

      deleting ? cIdx-- : cIdx++;

      let delay = deleting ? 35 : 70;

      if (!deleting && cIdx === word.length) { delay = 1800; deleting = true; }
      else if (deleting && cIdx === 0)       { deleting = false; wIdx++; delay = 280; }

      setTimeout(typeNext, delay);
    };

    setTimeout(typeNext, 800);
  }


  /* ========================================================================
     7. HERO CODE TAB SWITCHER
     ====================================================================== */
  const dcTabs  = document.querySelectorAll('.dc-tab');
  const tabPanes = document.querySelectorAll('.tab-pane');

  dcTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      dcTabs.forEach(t => t.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab');
      const pane = document.getElementById(targetId);
      if (pane) pane.classList.add('active');
    });
  });


  /* ========================================================================
     8. SCROLL REVEAL ANIMATIONS
     ====================================================================== */
  const revealEls = document.querySelectorAll('.reveal-up, .reveal-left, .reveal-right');
  const revealObs = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('active');
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  revealEls.forEach(el => revealObs.observe(el));


  /* ========================================================================
     9. STATS COUNTER ANIMATION
     ====================================================================== */
  const statItems   = document.querySelectorAll('.stat-item');
  let   statsAnimated = false;
  const easeOut = (t) => 1 - Math.pow(1 - t, 3);

  const animateCounter = (el, target) => {
    if (target === 0) return;
    const duration = 1800;
    const start    = performance.now();
    const update   = (now) => {
      const t       = Math.min((now - start) / duration, 1);
      el.textContent = Math.floor(easeOut(t) * target);
      if (t < 1) requestAnimationFrame(update);
      else el.textContent = target;
    };
    requestAnimationFrame(update);
  };

  const statsObs = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting && !statsAnimated) {
      statsAnimated = true;
      statItems.forEach(item => {
        const counter = item.querySelector('.counter');
        const target  = parseInt(item.getAttribute('data-target'), 10) || 0;
        animateCounter(counter, target);
      });
    }
  }, { threshold: 0.3 });

  const statsSection = document.querySelector('.stats-section');
  if (statsSection) statsObs.observe(statsSection);


  /* ========================================================================
     10. INTERACTIVE PROJECT SCOPE & COST ESTIMATOR
     ====================================================================== */
  const ESTIMATOR_DATA = {
    webdev: {
      name: 'Web & Mobile Development',
      basePrice: 15000,
      baseDays: 10,
      highlights: [
        '✓ Custom Responsive Layout (Mobile & Desktop)',
        '✓ SEO Optimization & Meta Tags',
        '✓ Modern Vanilla HTML/CSS/JS or React Engine',
        '✓ Contact Form with Email Notification'
      ]
    },
    aiml: {
      name: 'Custom AI & ML System',
      basePrice: 35000,
      baseDays: 20,
      highlights: [
        '✓ Data Preprocessing & Model Architecture',
        '✓ Supervised / Unsupervised Machine Learning',
        '✓ Flask / FastApi Inference Endpoint',
        '✓ Accuracy Evaluation & Confusion Matrix'
      ]
    },
    software: {
      name: 'Enterprise Software & ERP',
      basePrice: 40000,
      baseDays: 25,
      highlights: [
        '✓ Modular Database Architecture (SQLite / PostgreSQL)',
        '✓ Role-Based Access Control & Auth',
        '✓ Executive Control Dashboard & Reports',
        '✓ Printable Receipts & Data Export'
      ]
    },
    analytics: {
      name: 'Data Analytics & BI Dashboard',
      basePrice: 20000,
      baseDays: 12,
      highlights: [
        '✓ Automated Data Pipeline (ETL)',
        '✓ Interactive Charting Engine (Chart.js)',
        '✓ KPI Summary Metrics & Filtering',
        '✓ Exportable CSV / PDF Reports'
      ]
    },
    academic: {
      name: 'Academic & Final-Year Project',
      basePrice: 12000,
      baseDays: 7,
      highlights: [
        '✓ Complete Working Source Code',
        '✓ IEEE Format Report Documentation',
        '✓ PPT Presentation & Circuit Diagrams',
        '✓ 1-on-1 Code Explanation & Viva Prep'
      ]
    },
    cloud: {
      name: 'Cloud Architecture & DevOps',
      basePrice: 25000,
      baseDays: 14,
      highlights: [
        '✓ AWS / GCP Cloud Infrastructure Setup',
        '✓ CI/CD Pipeline (GitHub Actions)',
        '✓ Docker Containerization',
        '✓ Auto-scaling & Monitoring SLA'
      ]
    }
  };

  const TIER_MULTIPLIERS = {
    mvp: { priceMult: 1.0, timeMult: 1.0, label: 'MVP / Essential' },
    growth: { priceMult: 1.8, timeMult: 1.4, label: 'Growth Standard' },
    enterprise: { priceMult: 3.0, timeMult: 2.2, label: 'Custom Enterprise' }
  };

  const SPEED_MULTIPLIERS = {
    standard: { priceMult: 1.0, timeMult: 1.0 },
    express: { priceMult: 1.25, timeMult: 0.6 }
  };

  let currentEstState = {
    service: 'webdev',
    tier: 'mvp',
    speed: 'standard',
    addons: []
  };

  const calculateEstimate = () => {
    const sData = ESTIMATOR_DATA[currentEstState.service] || ESTIMATOR_DATA.webdev;
    const tData = TIER_MULTIPLIERS[currentEstState.tier] || TIER_MULTIPLIERS.mvp;
    const spData = SPEED_MULTIPLIERS[currentEstState.speed] || SPEED_MULTIPLIERS.standard;

    let addonCost = 0;
    currentEstState.addons.forEach(cost => addonCost += cost);

    let minPrice = Math.round((sData.basePrice * tData.priceMult * spData.priceMult) + addonCost);
    let maxPrice = Math.round(minPrice * 1.3);

    let minDays = Math.max(3, Math.round(sData.baseDays * tData.timeMult * spData.timeMult));
    let maxDays = Math.round(minDays * 1.4);

    // Format displays
    const priceDisplay = document.getElementById('est-price-display');
    const usdDisplay   = document.getElementById('est-usd-display');
    const timeDisplay  = document.getElementById('est-time-display');
    const scopeList    = document.getElementById('est-scope-list');

    if (priceDisplay) {
      priceDisplay.textContent = `₹${minPrice.toLocaleString('en-IN')} – ₹${maxPrice.toLocaleString('en-IN')}`;
    }
    if (usdDisplay) {
      const minUsd = Math.round(minPrice / 83);
      const maxUsd = Math.round(maxPrice / 83);
      usdDisplay.textContent = `($${minUsd.toLocaleString()} – $${maxUsd.toLocaleString()} USD approx.)`;
    }
    if (timeDisplay) {
      if (minDays <= 7) timeDisplay.textContent = `${minDays} – ${maxDays} Days`;
      else {
        const minW = Math.round(minDays / 7);
        const maxW = Math.round(maxDays / 7);
        timeDisplay.textContent = `${minW} – ${maxW} Weeks`;
      }
    }

    if (scopeList) {
      scopeList.innerHTML = sData.highlights.map(h => `<li>${h}</li>`).join('');
    }
  };

  // Wire up Estimator Pill Click Handlers
  const bindPillGroup = (groupId, stateKey) => {
    const groupEl = document.getElementById(groupId);
    if (!groupEl) return;
    const pills = groupEl.querySelectorAll('.est-pill');
    pills.forEach(pill => {
      pill.addEventListener('click', () => {
        pills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        currentEstState[stateKey] = pill.getAttribute('data-val');
        calculateEstimate();
      });
    });
  };

  bindPillGroup('est-service-group', 'service');
  bindPillGroup('est-tier-group', 'tier');
  bindPillGroup('est-speed-group', 'speed');

  // Add-on checkboxes
  const addonBoxes = document.querySelectorAll('.est-addon');
  addonBoxes.forEach(box => {
    box.addEventListener('change', () => {
      currentEstState.addons = Array.from(addonBoxes)
        .filter(cb => cb.checked)
        .map(cb => parseInt(cb.getAttribute('data-cost'), 10) || 0);
      calculateEstimate();
    });
  });

  // Proposal Button Handler (Scroll & Pre-fill Inquiry)
  const proposalBtn = document.getElementById('est-proposal-btn');
  if (proposalBtn) {
    proposalBtn.addEventListener('click', () => {
      const contactSec = document.getElementById('contact');
      if (contactSec) {
        const top = contactSec.getBoundingClientRect().top + window.scrollY - 80;
        window.scrollTo({ top, behavior: 'smooth' });
      }

      // Pre-fill form details
      const formService = document.getElementById('form-service');
      const formMessage = document.getElementById('form-message');
      const formName    = document.getElementById('form-name');

      if (formService) formService.value = currentEstState.service;
      if (formMessage) {
        const priceText = document.getElementById('est-price-display')?.textContent || '';
        const timeText  = document.getElementById('est-time-display')?.textContent || '';
        const sName     = ESTIMATOR_DATA[currentEstState.service]?.name || currentEstState.service;

        formMessage.value = `[OFFICIAL ESTIMATOR QUOTE REQUEST]\nService: ${sName}\nScope Tier: ${TIER_MULTIPLIERS[currentEstState.tier]?.label}\nSpeed: ${currentEstState.speed === 'express' ? 'Express Rush' : 'Standard'}\nCalculated Price Range: ${priceText}\nEstimated Delivery: ${timeText}\n\nAdditional Requirements: `;
      }
      if (formName) setTimeout(() => formName.focus(), 600);
    });
  }

  calculateEstimate(); // Initial run


  /* ========================================================================
     11. FAQ ACCORDION & SEARCH FILTER ENGINE
     ====================================================================== */
  const faqItems    = document.querySelectorAll('.faq-item');
  const faqSearch   = document.getElementById('faq-search-input');
  const faqCatBtns  = document.querySelectorAll('.faq-cat-btn');

  // Accordion toggle
  faqItems.forEach(item => {
    const questionBtn = item.querySelector('.faq-question');
    if (questionBtn) {
      questionBtn.addEventListener('click', () => {
        const isOpen = item.classList.contains('open');
        faqItems.forEach(i => i.classList.remove('open'));
        if (!isOpen) item.classList.add('open');
      });
    }
  });

  // Filter FAQ items
  const filterFaqs = () => {
    const query  = faqSearch ? faqSearch.value.toLowerCase().trim() : '';
    const activeCatBtn = document.querySelector('.faq-cat-btn.active');
    const activeCat    = activeCatBtn ? activeCatBtn.getAttribute('data-cat') : 'all';

    faqItems.forEach(item => {
      const cat = item.getAttribute('data-cat');
      const text = item.textContent.toLowerCase();

      const matchCat   = activeCat === 'all' || cat === activeCat;
      const matchQuery = !query || text.includes(query);

      item.style.display = (matchCat && matchQuery) ? 'block' : 'none';
    });
  };

  if (faqSearch) faqSearch.addEventListener('input', filterFaqs);

  faqCatBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      faqCatBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filterFaqs();
    });
  });


  /* ========================================================================
     12. CONSULTATION BOOKING MODAL LOGIC
     ====================================================================== */
  const bookingOverlay = document.getElementById('booking-modal-overlay');
  const bookingClose   = document.getElementById('booking-modal-close');
  const openBookingBtns = document.querySelectorAll('.open-booking-modal');
  const bookingForm    = document.getElementById('booking-form');
  const bkDateInput    = document.getElementById('bk-date');

  // Set minimum date to today
  if (bkDateInput) {
    const today = new Date().toISOString().split('T')[0];
    bkDateInput.min = today;
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    bkDateInput.value = tomorrow.toISOString().split('T')[0];
  }

  // Open modal triggers
  openBookingBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      if (bookingOverlay) bookingOverlay.classList.add('show');
    });
  });

  // Close modal
  if (bookingClose) bookingClose.addEventListener('click', () => bookingOverlay.classList.remove('show'));
  if (bookingOverlay) {
    bookingOverlay.addEventListener('click', (e) => {
      if (e.target === bookingOverlay) bookingOverlay.classList.remove('show');
    });
  }

  // Time slot buttons
  const slotBtns = document.querySelectorAll('.slot-btn');
  let selectedSlot = '10:00 AM';
  slotBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      slotBtns.forEach(s => s.classList.remove('active'));
      btn.classList.add('active');
      selectedSlot = btn.getAttribute('data-slot');
    });
  });

  // Booking Form Submission
  if (bookingForm) {
    bookingForm.addEventListener('submit', (e) => {
      e.preventDefault();

      const bkName  = document.getElementById('bk-name').value.trim();
      const bkEmail = document.getElementById('bk-email').value.trim();
      const bkPhone = document.getElementById('bk-phone').value.trim();
      const bkDate  = document.getElementById('bk-date').value;
      const bkTopic = document.getElementById('bk-topic').value;

      if (!bkName || !bkEmail || !bkPhone || !bkDate) {
        alert('Please fill out all required fields for consultation booking.');
        return;
      }

      const submitBtn = document.getElementById('bk-submit-btn');
      submitBtn.classList.add('loading');
      submitBtn.disabled = true;

      const payload = {
        name: bkName,
        email: bkEmail,
        service: 'consultation',
        message: `[CONSULTATION BOOKING SCHEDULED]\nTopic: ${bkTopic}\nRequested Date: ${bkDate}\nTime Slot: ${selectedSlot}\nPhone: ${bkPhone}`
      };

      fetch('/api/inquiries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
        .then(r => r.json())
        .then(data => {
          submitBtn.classList.remove('loading');
          submitBtn.disabled = false;
          bookingOverlay.classList.remove('show');

          if (data.success) {
            const refSpan = document.getElementById('success-ref-num');
            if (refSpan && data.reference_number) refSpan.textContent = data.reference_number;
            document.getElementById('success-modal-overlay').classList.add('show');
            bookingForm.reset();
          } else {
            alert('Booking failed: ' + (data.error || 'Please try again.'));
          }
        })
        .catch(err => {
          submitBtn.classList.remove('loading');
          submitBtn.disabled = false;
          console.error(err);
          alert('Network error. Please try again.');
        });
    });
  }


  /* ========================================================================
     13. SERVICE & CASE STUDY POPUP MODALS
     ====================================================================== */
  const SERVICE_MODAL_DATA = {
    webdev: {
      title: 'Web & Mobile Development Deliverables',
      icon: '🌐',
      deliverables: [
        'High-Speed Modern Frontend (React / Next.js / Vanilla ES6+)',
        'SEO Metadata, OpenGraph Cards, and Schema.org Structured Data',
        'PWA Support with ServiceWorker & Offline Capabilities',
        'Custom Backend Integration (Flask / Node.js REST API)',
        'Cross-Browser Testing & PageSpeed Optimization (90+ Score)'
      ],
      stack: ['React', 'Next.js', 'Flask', 'HTML5/CSS3', 'PWA'],
      timeline: '1 – 3 Weeks'
    },
    software: {
      title: 'Enterprise Software & ERP Deliverables',
      icon: '💼',
      deliverables: [
        'Custom Desktop & Web-based Executive Dashboards',
        'Multi-Factor Auth (OTP) & Role-Based Access Control (RBAC)',
        'SQLite / PostgreSQL Database Engine with Migrations',
        'Automated HRMS Modules (Payroll, Salary Slips, Duty Tracker)',
        'Kanban Task Boards & Candidate Recruitment Funnel'
      ],
      stack: ['Python', 'SQLite3', 'PostgreSQL', 'Tailwind/CSS', 'Chart.js'],
      timeline: '3 – 6 Weeks'
    },
    aiml: {
      title: 'AI & Machine Learning Solutions',
      icon: '🤖',
      deliverables: [
        'Data Pipeline & Preprocessing Workflows',
        'Custom Deep Learning & Scikit-Learn Model Training',
        'NLP Sentiment Processors & Document Text Classifiers',
        'REST API Endpoint Deployment for Real-Time Inference',
        'Model Accuracy Metrics, Confusion Matrix, and Evaluation Report'
      ],
      stack: ['Python', 'PyTorch', 'Scikit-Learn', 'Flask', 'OpenCV'],
      timeline: '4 – 8 Weeks'
    },
    analytics: {
      title: 'Data Analytics & Business Intelligence',
      icon: '📊',
      deliverables: [
        'Interactive Dynamic Analytics Dashboards (Chart.js)',
        'Automated ETL Pipelines & Data Cleaning Scripts',
        'KPI Metric Counters & Custom Filter Views',
        'Exportable Executive PDF & CSV Analytics Reports'
      ],
      stack: ['Pandas', 'NumPy', 'Chart.js', 'SQL Pipelines'],
      timeline: '1 – 3 Weeks'
    },
    academic: {
      title: 'Academic R&D Project Mentorship',
      icon: '🎓',
      deliverables: [
        'Full Production-Ready Source Code with Comments',
        'IEEE Format Synopsis, Report Documentation, & PPT Slides',
        'Circuit Diagram & Component Guides (IoT / Hardware)',
        '1-on-1 Code Walkthrough & Viva Question Prep Sessions'
      ],
      stack: ['BE / BTech', 'Diploma AI/ML', 'Python', 'Arduino', 'Documentation'],
      timeline: '1 – 2 Weeks'
    },
    cloud: {
      title: 'Cloud Architecture & DevOps Services',
      icon: '☁️',
      deliverables: [
        'Elastic AWS / GCP Infrastructure Provisioning',
        'GitHub Actions CI/CD Automated Build & Deploy Pipelines',
        'Docker Containerization & Serverless Microservices',
        'SSL Certificates, DNS Config, & 24/7 Health Monitoring'
      ],
      stack: ['AWS', 'GCP', 'Docker', 'Terraform', 'CI/CD'],
      timeline: '1 – 4 Weeks'
    }
  };

  const serviceModalOverlay = document.getElementById('service-modal-overlay');
  const serviceModalClose   = document.getElementById('service-modal-close');
  const serviceModalContent = document.getElementById('service-modal-content');

  document.querySelectorAll('.open-service-modal').forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.getAttribute('data-service');
      const data = SERVICE_MODAL_DATA[key];
      if (!data || !serviceModalContent) return;

      serviceModalContent.innerHTML = `
        <div class="modal-header">
          <div class="modal-icon">${data.icon}</div>
          <div>
            <h3 class="modal-title">${data.title}</h3>
            <p class="modal-subtitle">Estimated Delivery SLA: ${data.timeline}</p>
          </div>
        </div>
        <div style="margin-bottom:20px;">
          <h4 style="font-size:0.9rem;font-weight:700;margin-bottom:10px;text-transform:uppercase;color:var(--accent-lt);">Included Scope &amp; Deliverables:</h4>
          <ul style="display:flex;flex-direction:column;gap:8px;">
            ${data.deliverables.map(d => `<li style="font-size:0.88rem;color:var(--text);">&#10003; ${d}</li>`).join('')}
          </ul>
        </div>
        <div style="margin-bottom:24px;">
          <h4 style="font-size:0.9rem;font-weight:700;margin-bottom:10px;text-transform:uppercase;color:var(--accent-lt);">Technology Stack:</h4>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            ${data.stack.map(s => `<span class="stag" style="background:var(--accent-dim);color:var(--accent-lt);border-color:var(--border-accent);">${s}</span>`).join('')}
          </div>
        </div>
        <button class="btn btn-primary btn-block open-booking-modal" onclick="document.getElementById('service-modal-overlay').classList.remove('show');">Request Custom Proposal for this Service &rarr;</button>
      `;

      serviceModalOverlay.classList.add('show');
    });
  });

  if (serviceModalClose) serviceModalClose.addEventListener('click', () => serviceModalOverlay.classList.remove('show'));
  if (serviceModalOverlay) {
    serviceModalOverlay.addEventListener('click', (e) => {
      if (e.target === serviceModalOverlay) serviceModalOverlay.classList.remove('show');
    });
  }

  // Case Study Modals
  const CASESTUDY_DATA = {
    p1: {
      title: 'B2B E-Commerce & Inventory Portal',
      client: 'InnovateTech Solutions',
      challenge: 'Legacy manual order processing and inventory mismatch caused shipping delays and lost sales.',
      solution: 'Built a full-stack automated marketplace with real-time stock sync, payment gateways, and automated invoice PDF dispatches.',
      metrics: '3.4x Faster Order Processing · Zero Inventory Discrepancies',
      stack: ['React', 'Node.js', 'PostgreSQL', 'Stripe API']
    },
    p2: {
      title: 'Real-Time Sentiment Analysis Dashboard',
      client: 'RetailAI Labs',
      challenge: 'Processing thousands of raw customer feedback comments across platforms required costly manual tagging.',
      solution: 'Trained a PyTorch NLP transformer model integrated into a Flask API dashboard delivering instant sentiment classification and alert triggers.',
      metrics: '96.4% Model Precision · 12ms Inference Latency',
      stack: ['Python', 'PyTorch', 'Flask', 'Chart.js']
    },
    p3: {
      title: 'Multi-Tenant Cloud Migration',
      client: 'LogiTrack Systems',
      challenge: 'High server downtime during peak load and rigid on-premise hardware constraints.',
      solution: 'Architected serverless AWS auto-scaling clusters using Terraform Infrastructure-as-Code and automated CI/CD pipeline dispatches.',
      metrics: '99.99% Uptime SLA · 42% Reduction in Cloud Server Costs',
      stack: ['AWS', 'Terraform', 'Docker', 'GitHub Actions']
    },
    p4: {
      title: 'Smart IoT Automation Suite for COEP Tech R&D',
      client: 'COEP Technological University',
      challenge: 'Final-year robotics research required high-frequency sensor telemetry logging and low-power microcontrollers.',
      solution: 'Designed an ESP32 MQTT cloud data logger paired with a web control dashboard and comprehensive IEEE documentation.',
      metrics: 'Published IEEE Paper · 100% Viva Grade Score',
      stack: ['Python', 'Arduino/ESP32', 'MQTT', 'Documentation']
    }
  };

  const casestudyOverlay = document.getElementById('casestudy-modal-overlay');
  const casestudyClose   = document.getElementById('casestudy-modal-close');
  const casestudyContent = document.getElementById('casestudy-modal-content');

  document.querySelectorAll('.open-casestudy-modal').forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.getAttribute('data-project');
      const data = CASESTUDY_DATA[key];
      if (!data || !casestudyContent) return;

      casestudyContent.innerHTML = `
        <div class="modal-header">
          <div class="modal-icon">📁</div>
          <div>
            <h3 class="modal-title">${data.title}</h3>
            <p class="modal-subtitle">Client: ${data.client}</p>
          </div>
        </div>
        <div style="margin-bottom:16px;">
          <h4 style="font-size:0.85rem;font-weight:700;text-transform:uppercase;color:var(--accent-lt);margin-bottom:4px;">The Challenge:</h4>
          <p style="font-size:0.88rem;color:var(--text-muted);">${data.challenge}</p>
        </div>
        <div style="margin-bottom:16px;">
          <h4 style="font-size:0.85rem;font-weight:700;text-transform:uppercase;color:var(--accent-lt);margin-bottom:4px;">Our Engineering Solution:</h4>
          <p style="font-size:0.88rem;color:var(--text-muted);">${data.solution}</p>
        </div>
        <div style="background:var(--accent-dim);border:1px solid var(--border-accent);padding:14px;border-radius:var(--r-md);margin-bottom:20px;">
          <h4 style="font-size:0.85rem;font-weight:700;text-transform:uppercase;color:var(--accent-lt);margin-bottom:2px;">Measurable Impact &amp; Results:</h4>
          <div style="font-family:var(--font-heading);font-weight:700;color:var(--text);font-size:0.95rem;">${data.metrics}</div>
        </div>
        <div style="margin-bottom:20px;">
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            ${data.stack.map(s => `<span class="stag">${s}</span>`).join('')}
          </div>
        </div>
      `;

      casestudyOverlay.classList.add('show');
    });
  });

  if (casestudyClose) casestudyClose.addEventListener('click', () => casestudyOverlay.classList.remove('show'));
  if (casestudyOverlay) {
    casestudyOverlay.addEventListener('click', (e) => {
      if (e.target === casestudyOverlay) casestudyOverlay.classList.remove('show');
    });
  }


  /* ========================================================================
     14. PORTFOLIO FILTER
     ====================================================================== */
  const filterBtns   = document.querySelectorAll('.filter-btn');
  const projectCards = document.querySelectorAll('.project-card');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.getAttribute('data-filter');
      projectCards.forEach(card => {
        const cat = card.getAttribute('data-category');
        const show = filter === 'all' || cat === filter;
        card.style.display = show ? 'block' : 'none';
      });
    });
  });


  /* ========================================================================
     15. DYNAMIC REVIEWS & SUBMISSION FORM
     ====================================================================== */
  const SERVICE_LABELS = {
    webdev: 'Web & Mobile Dev',
    software: 'Enterprise ERP',
    aiml: 'AI & ML Solutions',
    analytics: 'Data Analytics',
    academic: 'Academic Mentorship',
    cloud: 'Cloud Services',
  };

  const AVATAR_COLORS = ['av-0','av-1','av-2','av-3','av-4','av-5'];

  const reviewsLoading   = document.getElementById('reviews-loading');
  const reviewsContainer = document.getElementById('reviews-container');
  const reviewsEmpty     = document.getElementById('reviews-empty');

  const renderStars = (rating) => Array.from({length: 5}, (_, i) => `<span class="t-star">${i < rating ? '★' : '☆'}</span>`).join('');

  const getInitials = (name) => {
    const parts = name.trim().split(' ');
    return parts.length >= 2 ? (parts[0][0] + parts[parts.length-1][0]).toUpperCase() : name.substring(0, 2).toUpperCase();
  };

  const formatDate = (dateStr) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch { return ''; }
  };

  const buildReviewCard = (review, idx) => {
    const initials  = getInitials(review.name);
    const avatarCls = AVATAR_COLORS[idx % AVATAR_COLORS.length];
    const stars     = renderStars(review.rating);
    const svcBadge  = review.service && SERVICE_LABELS[review.service] ? `<span class="t-service-badge">${SERVICE_LABELS[review.service]}</span>` : '';
    const dateStr   = formatDate(review.created_at);

    const card = document.createElement('div');
    card.className = 'tcard';
    card.style.animationDelay = `${idx * 0.07}s`;
    card.innerHTML = `
      <div class="t-stars">${stars}</div>
      ${svcBadge}
      <p class="t-text">&ldquo;${review.review_text.replace(/</g,'&lt;')}&rdquo;</p>
      <div class="t-author">
        <div class="t-avatar ${avatarCls}">${initials}</div>
        <div>
          <div class="t-name">${review.name.replace(/</g,'&lt;')}</div>
          <div class="t-role">${review.role.replace(/</g,'&lt;')}</div>
        </div>
        <span class="t-date">${dateStr}</span>
      </div>
    `;
    return card;
  };

  const loadReviews = () => {
    if (!reviewsLoading) return;
    reviewsLoading.style.display   = 'flex';
    reviewsContainer.style.display = 'none';
    reviewsEmpty.style.display     = 'none';

    fetch('/api/reviews')
      .then(r => r.json())
      .then(data => {
        reviewsLoading.style.display = 'none';
        if (!Array.isArray(data) || data.length === 0) {
          reviewsEmpty.style.display = 'flex';
          return;
        }
        reviewsContainer.innerHTML = '';
        data.forEach((review, idx) => reviewsContainer.appendChild(buildReviewCard(review, idx)));
        reviewsContainer.style.display = 'grid';
      })
      .catch(() => {
        reviewsLoading.style.display = 'none';
        reviewsEmpty.style.display   = 'flex';
      });
  };

  loadReviews();

  // Review Form
  const reviewForm     = document.getElementById('review-submit-form');
  const rvSubmitBtn    = document.getElementById('rv-submit-btn');
  const rvSuccessEl    = document.getElementById('rv-success');
  const rvNameInput    = document.getElementById('rv-name');
  const rvRoleInput    = document.getElementById('rv-role');
  const rvTextarea     = document.getElementById('rv-text');
  const rvCharEl       = document.getElementById('rv-char');
  const rvRatingHidden = document.getElementById('rv-rating');
  const rvRatingError  = document.getElementById('rv-rating-error');
  const starBtns       = document.querySelectorAll('.star-btn');
  let selectedRating   = 0;

  starBtns.forEach(btn => {
    const val = parseInt(btn.getAttribute('data-value'), 10);
    btn.addEventListener('mouseenter', () => starBtns.forEach((s, i) => s.classList.toggle('hovered', i < val)));
    btn.addEventListener('mouseleave', () => starBtns.forEach(s => s.classList.remove('hovered')));
    btn.addEventListener('click', () => {
      selectedRating = val;
      rvRatingHidden.value = val;
      starBtns.forEach((s, i) => s.classList.toggle('selected', i < val));
      if (rvRatingError) rvRatingError.style.display = 'none';
    });
  });

  if (rvTextarea && rvCharEl) {
    rvTextarea.addEventListener('input', () => rvCharEl.textContent = rvTextarea.value.length);
  }

  if (reviewForm) {
    reviewForm.addEventListener('submit', (e) => {
      e.preventDefault();
      let valid = true;

      if (!rvNameInput.value.trim()) { rvNameInput.classList.add('invalid'); valid = false; }
      else rvNameInput.classList.remove('invalid');

      if (!rvRoleInput.value.trim()) { rvRoleInput.classList.add('invalid'); valid = false; }
      else rvRoleInput.classList.remove('invalid');

      if (!rvTextarea.value.trim() || rvTextarea.value.trim().length < 15) { rvTextarea.classList.add('invalid'); valid = false; }
      else rvTextarea.classList.remove('invalid');

      if (selectedRating === 0) { if (rvRatingError) rvRatingError.style.display = 'block'; valid = false; }

      if (!valid) return;

      rvSubmitBtn.classList.add('loading');
      rvSubmitBtn.disabled = true;

      const serviceEl = document.getElementById('rv-service');
      const payload = {
        name: rvNameInput.value.trim(),
        role: rvRoleInput.value.trim(),
        rating: selectedRating,
        review_text: rvTextarea.value.trim(),
        service: serviceEl ? serviceEl.value : ''
      };

      fetch('/api/reviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
        .then(r => r.json())
        .then(data => {
          rvSubmitBtn.classList.remove('loading');
          rvSubmitBtn.disabled = false;
          if (data.success) {
            reviewForm.style.display  = 'none';
            rvSuccessEl.style.display = 'flex';
          } else {
            alert('Submission failed: ' + (data.error || 'Please try again.'));
          }
        })
        .catch(err => {
          rvSubmitBtn.classList.remove('loading');
          rvSubmitBtn.disabled = false;
          console.error(err);
          alert('Network error. Please try again.');
        });
    });
  }


  /* ========================================================================
     16. CHATBOT WIDGET
     ====================================================================== */
  const chatWidget   = document.getElementById('chatbot-widget');
  const chatToggle   = document.getElementById('chatbot-toggle');
  const chatMessages = document.getElementById('chatbot-messages');
  const chatInput    = document.getElementById('chatbot-input');
  const chatSend     = document.getElementById('chatbot-send');
  const typingDots   = document.getElementById('typing-dots');
  const quickReplies = document.querySelectorAll('.qr-btn');

  const BOT_RESPONSES = {
    greeting: [
      "Hello! 👋 Welcome to Kapate Consultancy. I'm your technical assistant. How can I help you today?",
      "Hi there! Ready to assist with software scoping, AI solutions, or consultation bookings. What would you like to know?"
    ],
    services:  "We provide 6 core service offerings:\n\n🌐 **Web & Mobile Development** — SEO & fast platforms\n💼 **Enterprise Software & ERP** — Custom HRMS & portals\n🤖 **Custom AI & ML Solutions** — Models, NLP, computer vision\n📊 **Data Analytics** — BI dashboards & pipelines\n🎓 **Academic Mentorship** — Final-year project code & viva prep\n☁️ **Cloud & DevOps** — AWS/GCP deployment dispatches\n\nWhich area fits your project?",
    pricing:   "Use our interactive **Project Estimator** on the page to calculate immediate price ranges! MVP services start at ₹12,000.\n\nFor official custom proposals:\n📧 Email: office.kapateconsultancy@gmail.com\n📞 Phone: +91-8421174957",
    timeline:  "Our standard delivery SLAs:\n\n• Web Platforms → 1–3 Weeks\n• Software & ERP → 3–6 Weeks\n• AI/ML Systems → 4–8 Weeks\n• Academic Projects → 1–2 Weeks\n• Cloud Migrations → 1–4 Weeks\n\nExpress Rush delivery options are also available! ⚡",
    academic:  "We mentor Engineering & Diploma students! 🎓 Our academic support includes:\n\n• Full working source code with comments\n• IEEE format synopsis & report\n• Circuit diagrams & PPT slides\n• 1-on-1 code explanation sessions\n• Complete viva question prep",
    contact:   "Connect with our leadership:\n\n📧 office.kapateconsultancy@gmail.com\n📞 +91-8421174957\n💬 WhatsApp: wa.me/918421174957\n📍 Pune, Maharashtra, India",
    default:   "Thank you for your question! Our technical lead will be glad to assist.\n\n📧 office.kapateconsultancy@gmail.com\n📞 +91-8421174957\n\nOr click 'Book Consultation' in the top bar to schedule a 1-on-1 meeting!"
  };

  let chatOpen = false, greeted = false;

  const fmt = (text) => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  const getTime = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const appendMsg = (text, role) => {
    if (!chatMessages) return;
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;
    div.innerHTML = `<div class="chat-bubble">${role === 'bot' ? fmt(text) : text.replace(/</g,'&lt;')}</div><div class="chat-time">${getTime()}</div>`;
    chatMessages.insertBefore(div, typingDots);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  };

  const showTyping = () => { if (typingDots) typingDots.classList.add('show'); };
  const hideTyping = () => { if (typingDots) typingDots.classList.remove('show'); };

  const respond = (key) => {
    showTyping();
    setTimeout(() => {
      hideTyping();
      const resp = BOT_RESPONSES[key] || BOT_RESPONSES.default;
      appendMsg(resp, 'bot');
    }, 800 + Math.random() * 600);
  };

  const matchQuery = (text) => {
    const t = text.toLowerCase();
    if (/hello|hi|hey|good/.test(t))                     return 'greeting';
    if (/service|offer|what|do you/.test(t))              return 'services';
    if (/price|cost|how much|budget|estimate/.test(t))    return 'pricing';
    if (/time|long|week|sla|speed/.test(t))              return 'timeline';
    if (/college|student|project|final|academic/.test(t)) return 'academic';
    if (/contact|email|phone|reach|call/.test(t))         return 'contact';
    return 'default';
  };

  if (chatToggle && chatWidget) {
    chatToggle.addEventListener('click', () => {
      chatOpen = !chatOpen;
      chatWidget.classList.toggle('open', chatOpen);
      if (chatOpen && !greeted) {
        greeted = true;
        setTimeout(() => appendMsg(BOT_RESPONSES.greeting[0], 'bot'), 300);
      }
    });
  }

  const handleSend = () => {
    if (!chatInput) return;
    const text = chatInput.value.trim();
    if (!text) return;
    appendMsg(text, 'user');
    chatInput.value = '';
    respond(matchQuery(text));
  };

  if (chatSend) chatSend.addEventListener('click', handleSend);
  if (chatInput) chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleSend(); });

  quickReplies.forEach(btn => {
    btn.addEventListener('click', () => {
      appendMsg(btn.textContent, 'user');
      respond(btn.getAttribute('data-query'));
    });
  });


  /* ========================================================================
     17. NEWSLETTER FORM
     ====================================================================== */
  const newsletterBtn     = document.getElementById('newsletter-btn');
  const newsletterEmail   = document.getElementById('newsletter-email');
  const newsletterSuccess = document.getElementById('newsletter-success');

  if (newsletterBtn) {
    newsletterBtn.addEventListener('click', () => {
      const email = newsletterEmail ? newsletterEmail.value.trim() : '';
      const re    = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!re.test(email)) {
        newsletterEmail.style.borderColor = '#ef4444';
        setTimeout(() => newsletterEmail.style.borderColor = '', 2000);
        return;
      }
      newsletterBtn.textContent = '✓ Subscribed!';
      newsletterBtn.disabled = true;
      if (newsletterSuccess) newsletterSuccess.style.display = 'flex';
      if (newsletterEmail) newsletterEmail.value = '';
    });
  }


  /* ========================================================================
     18. MAIN CONTACT INQUIRY FORM SUBMISSION
     ====================================================================== */
  const contactForm    = document.getElementById('inquiry-contact-form');
  const successOverlay = document.getElementById('success-modal-overlay');
  const successClose   = document.getElementById('success-modal-close-btn');

  const validateEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email).toLowerCase());

  if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
      e.preventDefault();

      const nameInput    = document.getElementById('form-name');
      const emailInput   = document.getElementById('form-email');
      const messageInput = document.getElementById('form-message');
      const submitBtn    = document.getElementById('form-submit-btn');
      let valid = true;

      if (!nameInput.value.trim()) { nameInput.classList.add('invalid'); valid = false; }
      else nameInput.classList.remove('invalid');

      if (!validateEmail(emailInput.value.trim())) { emailInput.classList.add('invalid'); valid = false; }
      else emailInput.classList.remove('invalid');

      if (!messageInput.value.trim()) { messageInput.classList.add('invalid'); valid = false; }
      else messageInput.classList.remove('invalid');

      if (!valid) return;

      submitBtn.classList.add('loading');
      submitBtn.disabled = true;

      const serviceInput = document.getElementById('form-service');
      const payload = {
        name:    nameInput.value.trim(),
        email:   emailInput.value.trim(),
        service: serviceInput ? serviceInput.value : '',
        message: messageInput.value.trim(),
      };

      fetch('/api/inquiries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
        .then(r => r.json())
        .then(data => {
          submitBtn.classList.remove('loading');
          submitBtn.disabled = false;

          if (data.success) {
            contactForm.reset();
            const refSpan = document.getElementById('success-ref-num');
            if (refSpan && data.reference_number) refSpan.textContent = data.reference_number;
            if (successOverlay) successOverlay.classList.add('show');
          } else {
            alert('Submission failed: ' + (data.error || 'Please try again.'));
          }
        })
        .catch(err => {
          submitBtn.classList.remove('loading');
          submitBtn.disabled = false;
          console.error('Form submission error:', err);
          alert('Network error. Please try again.');
        });
    });

    if (successClose && successOverlay) {
      successClose.addEventListener('click', () => successOverlay.classList.remove('show'));
      successOverlay.addEventListener('click', (e) => {
        if (e.target === successOverlay) successOverlay.classList.remove('show');
      });
    }

    [document.getElementById('form-name'), document.getElementById('form-email'), document.getElementById('form-message')].forEach(el => {
      if (el) el.addEventListener('input', () => el.classList.remove('invalid'));
    });
  }


  /* ========================================================================
     19. SMOOTH SCROLL FOR ANCHOR LINKS
     ====================================================================== */
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        const top = target.getBoundingClientRect().top + window.scrollY - 80;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    });
  });

}); // end DOMContentLoaded
