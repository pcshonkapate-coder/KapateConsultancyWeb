/* ==========================================================================
   Kapate Consultancy — Premium App Logic v2.0
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {

  /* ========================================================================
     1. THEME TOGGLE
     ====================================================================== */
  const themeBtn = document.getElementById('theme-toggle-btn');
  const body     = document.body;

  const savedTheme = localStorage.getItem('kapate-theme') || 'dark-theme';
  body.className = savedTheme;

  themeBtn.addEventListener('click', () => {
    const isDark = body.classList.contains('dark-theme');
    body.classList.replace(
      isDark ? 'dark-theme' : 'light-theme',
      isDark ? 'light-theme' : 'dark-theme'
    );
    localStorage.setItem('kapate-theme', body.classList.contains('dark-theme') ? 'dark-theme' : 'light-theme');
    if (particles) particles.updateColors();
  });


  /* ========================================================================
     2. SCROLL PROGRESS BAR
     ====================================================================== */
  const progressBar = document.getElementById('scroll-progress');
  window.addEventListener('scroll', () => {
    const scrolled = window.scrollY;
    const total    = document.documentElement.scrollHeight - window.innerHeight;
    progressBar.style.width = `${(scrolled / total) * 100}%`;
  }, { passive: true });


  /* ========================================================================
     3. STICKY HEADER
     ====================================================================== */
  const header = document.getElementById('main-header');
  window.addEventListener('scroll', () => {
    header.classList.toggle('scrolled', window.scrollY > 50);
  }, { passive: true });


  /* ========================================================================
     4. MOBILE NAVIGATION
     ====================================================================== */
  const menuToggle = document.getElementById('menu-toggle');
  const navMenu    = document.getElementById('nav-menu');
  const overlay    = document.getElementById('mobile-nav-overlay');
  const closeBtn   = document.getElementById('mobile-nav-close');
  const navLinks   = document.querySelectorAll('.nav-link');

  const openNav  = () => { menuToggle.classList.add('open'); navMenu.classList.add('open'); overlay.classList.add('show'); body.style.overflow = 'hidden'; };
  const closeNav = () => { menuToggle.classList.remove('open'); navMenu.classList.remove('open'); overlay.classList.remove('show'); body.style.overflow = ''; };

  menuToggle.addEventListener('click', () => navMenu.classList.contains('open') ? closeNav() : openNav());
  if (closeBtn) closeBtn.addEventListener('click', closeNav);
  overlay.addEventListener('click', closeNav);
  navLinks.forEach(link => link.addEventListener('click', closeNav));


  // Scroll spy
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
     5. PARTICLE CANVAS SYSTEM
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

    draw() {
      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      const maxDist = 130;

      for (let i = 0; i < this.particles.length; i++) {
        const p = this.particles[i];

        // Mouse repulsion
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

        // Draw particle
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `${this.pColor}${p.op})`;
        ctx.fill();

        // Draw connections
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
     6. TYPED TEXT ANIMATION
     ====================================================================== */
  const typedEl = document.getElementById('typed-word');
  if (typedEl) {
    const words = [
      'Web Development',
      'AI & ML Solutions',
      'Cloud Architecture',
      'Data Analytics',
      'Software Engineering',
      'Academic Mentorship',
    ];
    let wIdx = 0, cIdx = 0, deleting = false;

    const typeNext = () => {
      const word = words[wIdx % words.length];
      typedEl.textContent = deleting
        ? word.substring(0, cIdx - 1)
        : word.substring(0, cIdx + 1);

      deleting ? cIdx-- : cIdx++;

      let delay = deleting ? 38 : 78;

      if (!deleting && cIdx === word.length) { delay = 1800; deleting = true; }
      else if (deleting && cIdx === 0)       { deleting = false; wIdx++; delay = 280; }

      setTimeout(typeNext, delay);
    };

    setTimeout(typeNext, 900);
  }


  /* ========================================================================
     7. SCROLL-REVEAL ANIMATIONS
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
     8. STATS COUNTER ANIMATION
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
     9. PORTFOLIO FILTER
     ====================================================================== */
  const filterBtns  = document.querySelectorAll('.filter-btn');
  const projectCards = document.querySelectorAll('.project-card');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.getAttribute('data-filter');
      projectCards.forEach(card => {
        const cat = card.getAttribute('data-category');
        const show = filter === 'all' || cat === filter;
        card.classList.toggle('hide', !show);
        if (show) {
          card.style.animation = 'none';
          requestAnimationFrame(() => { card.style.animation = 'fade-up 0.4s ease both'; });
        }
      });
    });
  });


  /* ========================================================================
     10. DYNAMIC REVIEWS — load from API + render
     ====================================================================== */
  const SERVICE_LABELS = {
    webdev:   'Website Development',
    software: 'Software & App Dev',
    aiml:     'AI & ML Solutions',
    analytics: 'Data Analytics',
    academic: 'College Project',
    cloud:    'Cloud Services',
  };

  const AVATAR_COLORS = ['av-0','av-1','av-2','av-3','av-4','av-5'];

  const reviewsLoading   = document.getElementById('reviews-loading');
  const reviewsContainer = document.getElementById('reviews-container');
  const reviewsEmpty     = document.getElementById('reviews-empty');

  const renderStars = (rating) => {
    return Array.from({length: 5}, (_, i) =>
      `<span class="t-star">${i < rating ? '★' : '☆'}</span>`
    ).join('');
  };

  const getInitials = (name) => {
    const parts = name.trim().split(' ');
    return parts.length >= 2
      ? (parts[0][0] + parts[parts.length-1][0]).toUpperCase()
      : name.substring(0, 2).toUpperCase();
  };

  const formatDate = (dateStr) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch { return ''; }
  };

  const buildReviewCard = (review, idx) => {
    const initials  = getInitials(review.name);
    const avatarCls = AVATAR_COLORS[idx % AVATAR_COLORS.length];
    const stars     = renderStars(review.rating);
    const svcBadge  = review.service && SERVICE_LABELS[review.service]
      ? `<span class="t-service-badge">${SERVICE_LABELS[review.service]}</span>` : '';
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
    reviewsLoading.style.display  = 'flex';
    reviewsContainer.style.display = 'none';
    reviewsEmpty.style.display    = 'none';

    fetch('/api/reviews')
      .then(r => r.json())
      .then(data => {
        reviewsLoading.style.display = 'none';
        if (!Array.isArray(data) || data.length === 0) {
          reviewsEmpty.style.display = 'flex';
          return;
        }
        reviewsContainer.innerHTML = '';
        data.forEach((review, idx) => {
          reviewsContainer.appendChild(buildReviewCard(review, idx));
        });
        reviewsContainer.style.display = 'grid';
      })
      .catch(() => {
        reviewsLoading.style.display = 'none';
        reviewsEmpty.style.display   = 'flex';
      });
  };

  loadReviews();


  /* ========================================================================
     10b. REVIEW SUBMISSION FORM
     ====================================================================== */
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

  let selectedRating = 0;

  // Star picker: highlight on hover and select on click
  starBtns.forEach(btn => {
    const val = parseInt(btn.getAttribute('data-value'), 10);

    btn.addEventListener('mouseenter', () => {
      starBtns.forEach((s, i) => s.classList.toggle('hovered', i < val));
    });
    btn.addEventListener('mouseleave', () => {
      starBtns.forEach(s => s.classList.remove('hovered'));
    });
    btn.addEventListener('click', () => {
      selectedRating = val;
      rvRatingHidden.value = val;
      starBtns.forEach((s, i) => s.classList.toggle('selected', i < val));
      if (rvRatingError) rvRatingError.style.display = 'none';
    });
  });

  // Character counter for textarea
  if (rvTextarea && rvCharEl) {
    rvTextarea.addEventListener('input', () => {
      rvCharEl.textContent = rvTextarea.value.length;
    });
  }

  // Live validation clear
  [rvNameInput, rvRoleInput, rvTextarea].forEach(el => {
    if (el) el.addEventListener('input', () => el.classList.remove('invalid'));
  });

  if (reviewForm) {
    reviewForm.addEventListener('submit', (e) => {
      e.preventDefault();

      // Validate
      let valid = true;

      if (!rvNameInput.value.trim()) {
        rvNameInput.classList.add('invalid'); valid = false;
      } else rvNameInput.classList.remove('invalid');

      if (!rvRoleInput.value.trim()) {
        rvRoleInput.classList.add('invalid'); valid = false;
      } else rvRoleInput.classList.remove('invalid');

      if (!rvTextarea.value.trim() || rvTextarea.value.trim().length < 20) {
        rvTextarea.classList.add('invalid'); valid = false;
      } else rvTextarea.classList.remove('invalid');

      if (selectedRating === 0) {
        if (rvRatingError) rvRatingError.style.display = 'block';
        valid = false;
      }

      if (!valid) return;

      // Submit
      rvSubmitBtn.classList.add('loading');
      rvSubmitBtn.disabled = true;

      const serviceEl = document.getElementById('rv-service');
      const payload = {
        name:        rvNameInput.value.trim(),
        role:        rvRoleInput.value.trim(),
        rating:      selectedRating,
        review_text: rvTextarea.value.trim(),
        service:     serviceEl ? serviceEl.value : '',
      };

      fetch('/api/reviews', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
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
          alert('Network error. Please check your connection and try again.');
        });
    });
  }


  /* ========================================================================
     11. CHATBOT WIDGET
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
      "Hello! 👋 Welcome to Kapate Consultancy! I'm your virtual assistant. How can I help you today?",
      "Hi there! Ready to help you explore our services. What would you like to know?"
    ],
    services:  "We offer 6 premium services:\n\n🌐 **Website Development** — SEO-optimized, fast, modern websites\n💻 **Software & App Dev** — Custom desktop & cloud-native apps\n🤖 **AI & ML Solutions** — Predictive models, NLP, computer vision\n📊 **Data Analytics** — Business intelligence dashboards\n🎓 **College Projects** — Full final-year project support\n☁️ **Cloud Services** — AWS & GCP deployment & CI/CD\n\nWhich service are you interested in?",
    pricing:   "Our pricing is fully customized to your project scope. We offer competitive rates that fit startup and SME budgets.\n\n📧 Email: office.kapateconsultancy@gmail.com\n📞 Call: +91-8421174957\n\nReach out for a FREE consultation and quote — no commitments!",
    timeline:  "Typical project timelines:\n\n• Simple websites → 1–2 weeks\n• Web apps → 3–6 weeks\n• AI/ML projects → 4–8 weeks\n• College projects → 1–3 weeks\n• Cloud migrations → 1–4 weeks\n\nWe discuss timelines upfront and always deliver on time! ✅",
    academic:  "We love helping students! 🎓 Our academic support includes:\n\n• Full project implementation\n• Clean code + documentation\n• IoT circuit diagram support\n• PPT & report writing guidance\n• Demo & viva preparation\n• All stacks: Python, Java, React, Arduino, etc.\n\nSource code + explanation sessions are always included!",
    contact:   "You can reach us via:\n\n📧 office.kapateconsultancy@gmail.com\n📞 +91-8421174957\n💬 WhatsApp: wa.me/918421174957\n📍 Pune, Maharashtra, India\n\nOr scroll down to fill our contact form — we reply within 24 hours! 🚀",
    default:   "That's a great question! Our team can give you the best answer.\n\n📧 office.kapateconsultancy@gmail.com\n📞 +91-8421174957\n\nOr use the contact form below — we respond within 24 hours! 🚀"
  };

  let chatOpen = false;
  let greeted  = false;

  const fmt = (text) =>
    text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  const getTime = () =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const appendMsg = (text, role) => {
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;
    div.innerHTML = `<div class="chat-bubble">${role === 'bot' ? fmt(text) : text.replace(/</g,'&lt;')}</div><div class="chat-time">${getTime()}</div>`;
    chatMessages.insertBefore(div, typingDots);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  };

  const showTyping = () => {
    typingDots.classList.add('show');
    chatMessages.scrollTop = chatMessages.scrollHeight;
  };

  const hideTyping = () => typingDots.classList.remove('show');

  const respond = (key) => {
    showTyping();
    setTimeout(() => {
      hideTyping();
      const resp = BOT_RESPONSES[key] || BOT_RESPONSES.default;
      appendMsg(resp, 'bot');
    }, 900 + Math.random() * 700);
  };

  const matchQuery = (text) => {
    const t = text.toLowerCase();
    if (/hello|hi|hey|good/.test(t))               return 'greeting';
    if (/service|offer|what|do you/.test(t))        return 'services';
    if (/price|cost|how much|budget|fee/.test(t))   return 'pricing';
    if (/time|long|week|deadline|when/.test(t))     return 'timeline';
    if (/college|student|project|final|academic/.test(t)) return 'academic';
    if (/contact|email|phone|reach|call/.test(t))   return 'contact';
    return 'default';
  };

  chatToggle.addEventListener('click', () => {
    chatOpen = !chatOpen;
    chatWidget.classList.toggle('open', chatOpen);
    if (chatOpen && !greeted) {
      greeted = true;
      setTimeout(() => {
        appendMsg(BOT_RESPONSES.greeting[0], 'bot');
      }, 350);
    }
  });

  const handleSend = () => {
    const text = chatInput.value.trim();
    if (!text) return;
    appendMsg(text, 'user');
    chatInput.value = '';
    respond(matchQuery(text));
  };

  chatSend.addEventListener('click', handleSend);
  chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleSend(); });

  quickReplies.forEach(btn => {
    btn.addEventListener('click', () => {
      appendMsg(btn.textContent, 'user');
      respond(btn.getAttribute('data-query'));
    });
  });


  /* ========================================================================
     12. NEWSLETTER FORM
     ====================================================================== */
  const newsletterBtn     = document.getElementById('newsletter-btn');
  const newsletterEmail   = document.getElementById('newsletter-email');
  const newsletterSuccess = document.getElementById('newsletter-success');

  if (newsletterBtn) {
    newsletterBtn.addEventListener('click', () => {
      const email = newsletterEmail.value.trim();
      const re    = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!re.test(email)) {
        newsletterEmail.style.borderColor = '#ef4444';
        setTimeout(() => newsletterEmail.style.borderColor = '', 2000);
        return;
      }
      newsletterBtn.textContent = '✓ Done!';
      newsletterBtn.disabled = true;
      newsletterSuccess.style.display = 'flex';
      newsletterEmail.value = '';
    });
  }


  /* ========================================================================
     13. CONTACT FORM — API INTEGRATION (preserved)
     ====================================================================== */
  const contactForm  = document.getElementById('inquiry-contact-form');
  const successOverlay = document.getElementById('success-modal-overlay');
  const successClose   = document.getElementById('success-modal-close-btn');
  const submitBtn      = document.getElementById('form-submit-btn');

  const validateEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email).toLowerCase());

  if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
      e.preventDefault();

      const nameInput    = document.getElementById('form-name');
      const emailInput   = document.getElementById('form-email');
      const messageInput = document.getElementById('form-message');
      let valid = true;

      if (!nameInput.value.trim())          { nameInput.classList.add('invalid');    valid = false; }
      else                                   nameInput.classList.remove('invalid');

      if (!validateEmail(emailInput.value.trim())) { emailInput.classList.add('invalid');   valid = false; }
      else                                          emailInput.classList.remove('invalid');

      if (!messageInput.value.trim())        { messageInput.classList.add('invalid'); valid = false; }
      else                                    messageInput.classList.remove('invalid');

      if (!valid) return;

      // Loading state
      submitBtn.classList.add('loading');
      submitBtn.disabled = true;

      const serviceInput = document.getElementById('form-service');
      const payload = {
        name:    nameInput.value.trim(),
        email:   emailInput.value.trim(),
        service: serviceInput ? serviceInput.value : '',
        message: messageInput.value.trim(),
      };

      const API_BASE = '/api';

      fetch(`${API_BASE}/inquiries`, {
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
            const refBox  = document.getElementById('ref-display-box');
            const refSpan = document.getElementById('success-ref-num');
            if (refBox && refSpan && data.reference_number) {
              refSpan.textContent = data.reference_number;
              refBox.style.display = 'block';
            }
            successOverlay.classList.add('show');
          } else {
            alert('Submission failed: ' + (data.error || 'Unknown error. Please try again.'));
          }
        })
        .catch(err => {
          submitBtn.classList.remove('loading');
          submitBtn.disabled = false;
          console.error('Form submission error:', err);
          alert('Network error. Please check your connection and try again.');
        });
    });

    // Close modal
    successClose.addEventListener('click', () => successOverlay.classList.remove('show'));
    successOverlay.addEventListener('click', (e) => {
      if (e.target === successOverlay) successOverlay.classList.remove('show');
    });

    // Live validation clear
    [document.getElementById('form-name'), document.getElementById('form-email'), document.getElementById('form-message')].forEach(el => {
      if (el) el.addEventListener('input', () => el.classList.remove('invalid'));
    });
  }


  /* ========================================================================
     14. TECH GRID INTERACTIVE HOVER (Why Panel)
     ====================================================================== */
  document.querySelectorAll('.tech-cell').forEach(cell => {
    cell.addEventListener('mouseenter', () => cell.classList.add('active'));
    cell.addEventListener('mouseleave', () => {
      if (!cell.dataset.locked) cell.classList.remove('active');
    });
  });


  /* ========================================================================
     15. SMOOTH SCROLL FOR ANCHOR LINKS
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
