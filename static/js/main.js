/* ═══════════════════════════════════════════════════════════════
   FakeGuard AI — Main JavaScript (SPA)
   Features: navigation, predict, charts, history, toasts, particles
═══════════════════════════════════════════════════════════════ */

'use strict';

// ══════════════════════════════════════════════════════════════
// CONSTANTS & STATE
// ══════════════════════════════════════════════════════════════
const EXAMPLES = {
  r: { no_of_posts: 28,  followers: 609,  following: 394, bio_len: 43, picture: '1', link: '0' },
  a: { no_of_posts: 61,  followers: 2000, following: 437, bio_len: 25, picture: '1', link: '0' },
  i: { no_of_posts: 1,   followers: 3900, following: 88,  bio_len: 0,  picture: '1', link: '0' },
  s: { no_of_posts: 51,  followers: 1800, following: 357, bio_len: 34, picture: '1', link: '0' },
};

const CLASS_CFG = {
  r: { icon: '✅', color: '#22c55e', badge: 'badge-r', label: 'Real Account'   },
  a: { icon: '⚠️', color: '#facc15', badge: 'badge-a', label: 'Active Fake'    },
  i: { icon: '👻', color: '#60a5fa', badge: 'badge-i', label: 'Inactive Fake'  },
  s: { icon: '🤖', color: '#ef4444', badge: 'badge-s', label: 'Spammer Fake'   },
};

const HISTORY_KEY = 'fakeguard_history';
const MAX_HISTORY = 25;

let dashboardLoaded = false;
let currentScanData = null;         // holds last prediction result + form values
let statsCache      = null;         // cached /api/stats response

// ══════════════════════════════════════════════════════════════
// PARTICLE CANVAS
// ══════════════════════════════════════════════════════════════
function initParticles() {
  const canvas = document.getElementById('particle-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  let W, H, particles;

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function makeParticle() {
    return {
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.5 + 0.4,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      a: Math.random() * 0.4 + 0.1,
    };
  }

  function initParticleArray() {
    const count = Math.min(Math.floor((W * H) / 12000), 90);
    particles = Array.from({ length: count }, makeParticle);
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = W;
      if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H;
      if (p.y > H) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${p.a})`;
      ctx.fill();
    });
    requestAnimationFrame(draw);
  }

  resize();
  initParticleArray();
  draw();
  window.addEventListener('resize', () => { resize(); initParticleArray(); });
}

// ══════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ══════════════════════════════════════════════════════════════
function showToast(message, type = 'info', duration = 3500) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span> ${message}`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('removing');
    toast.addEventListener('animationend', () => toast.remove());
  }, duration);
}

// ══════════════════════════════════════════════════════════════
// SPA NAVIGATION
// ══════════════════════════════════════════════════════════════
function navigate(page) {
  // Update page views
  document.querySelectorAll('.page-view').forEach(v => v.classList.remove('active'));
  const target = document.getElementById(`page-${page}`);
  if (target) target.classList.add('active');

  // Update nav links
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  const activeLink = document.getElementById(`nav-${page}`);
  if (activeLink) activeLink.classList.add('active');

  // Close hamburger
  document.getElementById('nav-links').classList.remove('open');
  document.getElementById('hamburger').classList.remove('open');

  // Lazy-load dashboard
  if (page === 'dashboard' && !dashboardLoaded) {
    loadDashboard();
  }
  if (page === 'history') {
    renderHistory();
  }

  // Animate counters on home hero
  if (page === 'home') {
    animateCounters();
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Set up nav click handlers
document.querySelectorAll('[data-page]').forEach(el => {
  el.addEventListener('click', e => {
    e.preventDefault();
    navigate(el.dataset.page);
  });
});

// Hamburger toggle
document.getElementById('hamburger').addEventListener('click', () => {
  const links = document.getElementById('nav-links');
  const btn   = document.getElementById('hamburger');
  links.classList.toggle('open');
  btn.classList.toggle('open');
});

// ══════════════════════════════════════════════════════════════
// ANIMATED COUNTERS
// ══════════════════════════════════════════════════════════════
function animateCounters() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count, 10);
    const duration = 1600;
    const start = performance.now();
    function step(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3); // ease-out-cubic
      el.textContent = Math.floor(ease * target).toLocaleString();
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });
}

// ══════════════════════════════════════════════════════════════
// EXAMPLE LOADER
// ══════════════════════════════════════════════════════════════
window.loadExample = function(cls) {
  const ex = EXAMPLES[cls];
  if (!ex) return;
  document.getElementById('no_of_posts').value = ex.no_of_posts;
  document.getElementById('followers').value   = ex.followers;
  document.getElementById('following').value   = ex.following;
  document.getElementById('bio_len').value     = ex.bio_len;
  document.getElementById('picture').value     = ex.picture;
  document.getElementById('link').value        = ex.link;
  showToast(`Loaded ${CLASS_CFG[cls]?.label || cls} example`, 'info', 2000);
  setTimeout(() => document.getElementById('scan-form').requestSubmit(), 350);
};

// ══════════════════════════════════════════════════════════════
// FORM SUBMIT & PREDICT
// ══════════════════════════════════════════════════════════════
const form       = document.getElementById('scan-form');
const scanBtn    = document.getElementById('scan-btn');
const btnLabel   = document.getElementById('btn-label');
const btnSpinner = document.getElementById('btn-spinner');
const btnIcon    = document.querySelector('.btn-icon');

function setLoading(state) {
  scanBtn.disabled = state;
  btnLabel.textContent = state ? 'Scanning…' : 'Scan Account';
  if (btnIcon) btnIcon.style.opacity = state ? '0' : '1';
  state
    ? btnSpinner.classList.remove('hidden')
    : btnSpinner.classList.add('hidden');
}

form.addEventListener('submit', async e => {
  e.preventDefault();
  setLoading(true);

  const formData   = new FormData(form);
  const formValues = Object.fromEntries(formData.entries());

  try {
    const res = await fetch('/predict', { method: 'POST', body: formData });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    currentScanData = { ...data, formValues, timestamp: new Date().toISOString() };
    showResult(data, formValues);
    showToast('Analysis complete!', 'success');
  } catch (err) {
    console.error('Prediction error:', err);
    showErrorResult();
    showToast('Server error — check the console', 'error');
  } finally {
    setLoading(false);
  }
});

// ─── DOM refs for result panel ─────────────────────────────────
const resultPanel   = document.getElementById('result-panel');
const resultIcon    = document.getElementById('result-icon');
const resultLabel   = document.getElementById('result-label');
const resultClass   = document.getElementById('result-class');
const resultBadge   = document.getElementById('result-badge');
const resultModelTag = document.getElementById('result-model-tag');
const gaugeArc      = document.getElementById('gauge-arc');
const gaugeVal      = document.getElementById('gauge-val');
const signalsList   = document.getElementById('signals-list');

// ──────────────────────────────────────────────────────────────
function showResult(data, formValues) {
  const cfg = CLASS_CFG[data.predicted_class] || { icon: '❓', color: '#fff', badge: '', label: 'Unknown' };

  // Re-trigger pop animation
  resultIcon.style.animation = 'none';
  requestAnimationFrame(() => {
    resultIcon.style.animation = '';
    resultIcon.textContent = cfg.icon;
  });

  resultLabel.textContent  = data.meaning;
  resultClass.textContent  = `Predicted class code: "${data.predicted_class}"`;
  resultBadge.textContent  = cfg.label;
  resultBadge.className    = `result-badge ${cfg.badge}`;
  resultModelTag.textContent = `⚡ Powered by ${data.model_used}`;

  // Confidence gauge (SVG arc path)
  animateGauge(data.confidence);

  // 4-class probability bars
  if (data.all_probs) {
    ['r','a','i','s'].forEach(cls => {
      const pct = data.all_probs[cls] || 0;
      document.getElementById(`prob-${cls}`).textContent = `${pct.toFixed(1)}%`;
      requestAnimationFrame(() => {
        document.getElementById(`pfill-${cls}`).style.width = `${pct}%`;
      });
    });
  }

  // Signal pills
  signalsList.innerHTML = '';
  if (data.signals && data.signals.length) {
    data.signals.forEach(sig => {
      const pill = document.createElement('span');
      pill.className = `signal-pill signal-${sig.type}`;
      const icons = { good: '✅', warning: '⚠️', info: 'ℹ️' };
      pill.textContent = `${icons[sig.type] || ''} ${sig.label}`;
      signalsList.appendChild(pill);
    });
  }

  // Show panel
  resultPanel.classList.remove('hidden');
  resultPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showErrorResult() {
  resultPanel.classList.remove('hidden');
  resultIcon.textContent     = '❌';
  resultLabel.textContent    = 'Error';
  resultClass.textContent    = 'Could not connect to the server.';
  resultBadge.textContent    = '';
  resultModelTag.textContent = '';
  signalsList.innerHTML      = '';
  ['r','a','i','s'].forEach(cls => {
    document.getElementById(`prob-${cls}`).textContent = '—';
    document.getElementById(`pfill-${cls}`).style.width = '0%';
  });
}

// ─── SVG Gauge animation ───────────────────────────────────────
// Gauge: M10,65 A55,55 0 0,1 110,65  — arc length ~173
const GAUGE_LEN = 173;

function animateGauge(pct) {
  const fill = (pct / 100) * GAUGE_LEN;
  gaugeArc.setAttribute('stroke-dasharray', `${fill} ${GAUGE_LEN}`);
  // Inject gradient on first call
  injectGaugeSVGDefs();
  // Animate text
  let current = 0;
  const target = pct;
  const start = performance.now();
  function step(now) {
    const progress = Math.min((now - start) / 800, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    current = ease * target;
    gaugeVal.textContent = `${Math.round(current)}%`;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function injectGaugeSVGDefs() {
  const svg = document.getElementById('result-gauge-svg');
  if (svg.querySelector('defs')) return;
  svg.insertAdjacentHTML('afterbegin', `
    <defs>
      <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%"   stop-color="#f09433"/>
        <stop offset="50%"  stop-color="#dc2743"/>
        <stop offset="100%" stop-color="#bc1888"/>
      </linearGradient>
    </defs>
  `);
}

// ══════════════════════════════════════════════════════════════
// SAVE TO HISTORY
// ══════════════════════════════════════════════════════════════
window.saveCurrentScan = function() {
  if (!currentScanData) { showToast('No scan data to save', 'error'); return; }
  const history = getHistory();
  history.unshift(currentScanData);
  if (history.length > MAX_HISTORY) history.splice(MAX_HISTORY);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  showToast('Scan saved to history!', 'success');
};

function getHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) || []; }
  catch { return []; }
}

// ══════════════════════════════════════════════════════════════
// RENDER HISTORY PAGE
// ══════════════════════════════════════════════════════════════
function renderHistory(filter = '') {
  const history = getHistory();
  const filtered = filter
    ? history.filter(h =>
        (h.meaning || '').toLowerCase().includes(filter.toLowerCase()) ||
        (h.predicted_class || '').includes(filter.toLowerCase()) ||
        (h.model_used || '').toLowerCase().includes(filter.toLowerCase())
      )
    : history;

  const emptyEl = document.getElementById('history-empty');
  const tableWrap = document.getElementById('history-table-wrap');
  const tbody = document.getElementById('history-tbody');
  const summary = document.getElementById('history-summary');

  if (history.length === 0) {
    emptyEl.classList.remove('hidden');
    tableWrap.classList.add('hidden');
    return;
  }

  emptyEl.classList.add('hidden');
  tableWrap.classList.remove('hidden');

  summary.textContent = `Showing ${filtered.length} of ${history.length} scans`;

  tbody.innerHTML = filtered.map((scan, i) => {
    const cfg = CLASS_CFG[scan.predicted_class] || {};
    const badgeClass = `h-badge badge-${scan.predicted_class}`;
    const date = scan.timestamp ? new Date(scan.timestamp).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit', month:'short', day:'numeric' }) : '—';
    const fv = scan.formValues || {};
    const idx = history.indexOf(scan);
    return `
      <tr>
        <td>${history.length - idx}</td>
        <td>${date}</td>
        <td>${fv.no_of_posts ?? '—'}</td>
        <td>${fv.followers ?? '—'}</td>
        <td>${fv.following ?? '—'}</td>
        <td><code style="font-family:var(--mono);font-size:.78rem">${scan.model_used || '—'}</code></td>
        <td><span class="${badgeClass}">${cfg.icon || ''} ${cfg.label || scan.predicted_class}</span></td>
        <td><strong style="font-family:var(--mono);font-size:.82rem">${scan.confidence}%</strong></td>
        <td style="display:flex;gap:.4rem;align-items:center">
          <button class="rerun-btn" onclick="rerunScan(${idx})">🔁 Rerun</button>
          <button class="del-btn" onclick="deleteScan(${idx})" title="Delete">🗑</button>
        </td>
      </tr>
    `;
  }).join('');
}

window.rerunScan = function(idx) {
  const history = getHistory();
  const scan = history[idx];
  if (!scan || !scan.formValues) return;
  const fv = scan.formValues;
  document.getElementById('no_of_posts').value = fv.no_of_posts || '';
  document.getElementById('followers').value   = fv.followers   || '';
  document.getElementById('following').value   = fv.following   || '';
  document.getElementById('bio_len').value     = fv.bio_len     || '';
  document.getElementById('picture').value     = fv.picture     || '1';
  document.getElementById('link').value        = fv.link        || '0';
  if (fv.model_choice) document.getElementById('model_choice').value = fv.model_choice;
  navigate('home');
  showToast('Form loaded from history — click Scan!', 'info');
};

window.deleteScan = function(idx) {
  const history = getHistory();
  history.splice(idx, 1);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  renderHistory(document.getElementById('history-search').value);
  showToast('Entry deleted', 'info', 2000);
};

window.clearHistory = function() {
  if (!getHistory().length) { showToast('History is already empty', 'info'); return; }
  localStorage.removeItem(HISTORY_KEY);
  renderHistory();
  showToast('History cleared', 'success');
};

document.getElementById('history-search').addEventListener('input', e => {
  renderHistory(e.target.value);
});

// ══════════════════════════════════════════════════════════════
// DASHBOARD — load stats and render charts
// ══════════════════════════════════════════════════════════════
async function loadDashboard() {
  dashboardLoaded = true;
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    statsCache = await res.json();
    renderMetricCards(statsCache);
    renderDonutChart(statsCache.class_distribution);
    renderFIChart(statsCache.feature_importances);
    renderCompareTable(statsCache.model_accuracy, statsCache.xgb_available);
  } catch (err) {
    console.error('Dashboard load error:', err);
    showToast('Could not load dashboard stats', 'error');
  }
}

// ─── Metric cards ──────────────────────────────────────────────
function renderMetricCards(stats) {
  const acc = stats.model_accuracy;
  const ds  = stats.dataset;

  function setCard(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = value;
  }

  setCard('mc-accuracy', acc.rf_accuracy ? `${(acc.rf_accuracy * 100).toFixed(1)}%` : '94.0%');
  setCard('mc-balanced', acc.rf_balanced ? `${(acc.rf_balanced * 100).toFixed(1)}%` : '93.0%');
  setCard('mc-samples',  ds.total_samples.toLocaleString());
  setCard('mc-features', ds.total_features);
}

// ─── Donut chart (SVG) ─────────────────────────────────────────
function renderDonutChart(classData) {
  const svg = document.getElementById('donut-svg');
  const legend = document.getElementById('donut-legend');
  if (!svg || !classData) return;

  const cx = 100, cy = 100, r = 70;
  const circumference = 2 * Math.PI * r;
  const colorMap = { r: '#22c55e', a: '#facc15', i: '#60a5fa', s: '#ef4444' };
  const total = classData.reduce((s, d) => s + d.count, 0);

  // Order: r, a, i, s
  const order = ['r','a','i','s'];
  const sorted = order.map(code => classData.find(d => d.code === code)).filter(Boolean);

  let cumulPct = 0;
  const gaps = 2; // gap in degrees between segments

  sorted.forEach(cls => {
    const pct = cls.count / total;
    const stroke = (pct * circumference) - (gaps * Math.PI * r / 180);
    const offset = -circumference * cumulPct - (circumference / 4);

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', cx);
    circle.setAttribute('cy', cy);
    circle.setAttribute('r', r);
    circle.setAttribute('fill', 'none');
    circle.setAttribute('stroke', colorMap[cls.code] || '#888');
    circle.setAttribute('stroke-width', '28');
    circle.setAttribute('stroke-dasharray', `${stroke} ${circumference}`);
    circle.setAttribute('stroke-dashoffset', offset);
    circle.setAttribute('stroke-linecap', 'butt');
    circle.style.transition = `stroke-dasharray 1s ease ${cumulPct * 0.4}s`;
    svg.appendChild(circle);

    cumulPct += pct;
  });

  // Center text
  const text1 = document.createElementNS('http://www.w3.org/2000/svg','text');
  text1.setAttribute('x', cx); text1.setAttribute('y', cy - 5);
  text1.setAttribute('text-anchor', 'middle');
  text1.setAttribute('font-size', '16'); text1.setAttribute('font-weight', '800');
  text1.setAttribute('fill', '#eeeef8'); text1.setAttribute('font-family', 'Inter,sans-serif');
  text1.textContent = total.toLocaleString();
  const text2 = document.createElementNS('http://www.w3.org/2000/svg','text');
  text2.setAttribute('x', cx); text2.setAttribute('y', cy + 14);
  text2.setAttribute('text-anchor', 'middle');
  text2.setAttribute('font-size', '8'); text2.setAttribute('fill', '#606080');
  text2.setAttribute('font-family', 'Inter,sans-serif');
  text2.textContent = 'total samples';
  svg.appendChild(text1); svg.appendChild(text2);

  // Legend
  legend.innerHTML = sorted.map(cls => `
    <div class="dl-item">
      <div class="dl-dot" style="background:${colorMap[cls.code]}"></div>
      <span class="dl-name">${CLASS_CFG[cls.code]?.label || cls.label}</span>
      <span class="dl-pct" style="color:${colorMap[cls.code]}">${cls.pct}%</span>
    </div>
  `).join('');
}

// ─── Feature importance bars ───────────────────────────────────
function renderFIChart(features) {
  const container = document.getElementById('fi-chart');
  if (!container || !features || !features.length) return;

  // Nicer feature name labels
  const pretty = {
    ff_ratio: 'Follower/Following Ratio',
    followers: 'Followers',
    following: 'Following',
    no_of_posts: 'No. of Posts',
    bio_len: 'Bio Length',
    engagement_total: 'Engagement Total',
    engagement_per_post: 'Engagement / Post',
    followers_per_post: 'Followers / Post',
    has_bio: 'Has Bio',
    picture: 'Profile Picture',
    has_profile_pic: 'Profile Picture',
    link: 'External Link',
    has_link: 'Has Link',
    following_heavy: 'Following Heavy',
    low_followers: 'Low Followers',
    high_following: 'High Following',
    irregular_posts: 'Irregular Posts',
    follower_following_ratio: 'FF Ratio',
  };

  container.innerHTML = features.slice(0,12).map((f, i) => `
    <div class="fi-row">
      <span class="fi-name">${pretty[f.feature] || f.feature}</span>
      <div class="fi-bar-wrap">
        <div class="fi-bar-fill" id="fibar-${i}" style="width:0%"></div>
      </div>
      <span class="fi-pct">${f.pct}%</span>
    </div>
  `).join('');

  // Animate bars after paint
  requestAnimationFrame(() => {
    features.slice(0,12).forEach((f, i) => {
      setTimeout(() => {
        const bar = document.getElementById(`fibar-${i}`);
        if (bar) bar.style.width = `${f.pct}%`;
      }, i * 60);
    });
  });
}

// ─── Model comparison table ────────────────────────────────────
function renderCompareTable(accuracy, xgbAvailable) {
  const tbody = document.getElementById('compare-body');
  if (!tbody) return;

  const rf_acc  = accuracy.rf_accuracy  ? `${(accuracy.rf_accuracy  * 100).toFixed(1)}%` : '~94%';
  const rf_bal  = accuracy.rf_balanced  ? `${(accuracy.rf_balanced  * 100).toFixed(1)}%` : '~93%';
  const xgb_acc = accuracy.xgb_accuracy ? `${(accuracy.xgb_accuracy * 100).toFixed(1)}%` : (xgbAvailable ? '~95%' : 'N/A');
  const xgb_bal = accuracy.xgb_balanced ? `${(accuracy.xgb_balanced * 100).toFixed(1)}%` : (xgbAvailable ? '~94%' : 'N/A');

  tbody.innerHTML = `
    <tr><td>Accuracy</td>         <td>${rf_acc}</td>  <td>${xgb_acc}</td></tr>
    <tr><td>Balanced Accuracy</td><td>${rf_bal}</td>  <td>${xgb_bal}</td></tr>
    <tr><td>Estimators</td>       <td>500 trees</td>  <td>${xgbAvailable ? '500 estimators' : 'N/A'}</td></tr>
    <tr><td>Speed</td>            <td>⚡ Fast</td>    <td>${xgbAvailable ? '⚡⚡ Very Fast' : 'N/A'}</td></tr>
    <tr><td>Interpretability</td> <td>✅ High</td>    <td>${xgbAvailable ? '⚠️ Medium' : 'N/A'}</td></tr>
    <tr><td>Recommendation</td>   <td>✅ Default</td> <td>${xgbAvailable ? '⚡ Best Accuracy' : 'Not installed'}</td></tr>
  `;
}

// ══════════════════════════════════════════════════════════════
// INPUT VALIDATION INDICATORS
// ══════════════════════════════════════════════════════════════
document.querySelectorAll('.field-input[type="number"]').forEach(inp => {
  inp.addEventListener('input', () => {
    const v = parseFloat(inp.value);
    if (inp.value === '') {
      inp.classList.remove('valid','invalid');
    } else if (!isNaN(v) && v >= 0) {
      inp.classList.add('valid'); inp.classList.remove('invalid');
    } else {
      inp.classList.add('invalid'); inp.classList.remove('valid');
    }
  });
});

// ══════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  initParticles();
  animateCounters();

  // Scroll-triggered nav shadow
  window.addEventListener('scroll', () => {
    const nav = document.getElementById('main-nav');
    if (window.scrollY > 10) {
      nav.style.boxShadow = '0 4px 24px rgba(0,0,0,.4)';
    } else {
      nav.style.boxShadow = 'none';
    }
  });
});
