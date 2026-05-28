/**
 * Baby Tracker - Main Application
 * Handles all UI logic, API calls, and state management
 */

const API_BASE = 'api';

/* ════════════════════════════════════════════
   STATE
   ════════════════════════════════════════════ */
/* Server's UTC offset in ms — set during init() via /api/server-time.
   Using the SERVER timezone (not browser timezone) ensures correct time
   display even when HA ingress runs the browser in UTC mode. */
let _tzOffsetMs = 0;

const State = {
  currentSection: 'home',
  lang: 'nl',
  baby: null,
  schedule: null,
  feedingsDay: new Date().toISOString().slice(0, 10), // updated in initServerTime()
  diapersDay:  new Date().toISOString().slice(0, 10),
  clockFormat: localStorage.getItem('bt_clockFormat') || '24h',
  feedingType: 'bottle',
  diaperType: 'wet',
  poopColor: null,
  setupGender: 'boy',
  blockedWindows: [],
  weightChart: null,
  refreshTimer: null,
  countdownTimer: null,
  activeSleep: null,
};

/* ════════════════════════════════════════════
   API UTILITIES
   ════════════════════════════════════════════ */
async function apiFetch(path, options = {}) {
  const url = `${API_BASE}/${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

const api = {
  getConfig:         ()     => apiFetch('config'),
  getBaby:           ()     => apiFetch('baby'),
  updateBaby:        (d)    => apiFetch('baby', { method: 'POST', body: JSON.stringify(d) }),
  getDashboard:      ()     => apiFetch('dashboard'),

  getFeedings:       (day)  => apiFetch(`feedings?day=${day}&limit=50`),
  addFeeding:        (d)    => apiFetch('feedings', { method: 'POST', body: JSON.stringify(d) }),
  deleteFeeding:     (id)   => apiFetch(`feedings/${id}`, { method: 'DELETE' }),

  getDiapers:        (day)  => apiFetch(`diapers?day=${day}&limit=50`),
  addDiaper:         (d)    => apiFetch('diapers', { method: 'POST', body: JSON.stringify(d) }),
  deleteDiaper:      (id)   => apiFetch(`diapers/${id}`, { method: 'DELETE' }),

  getWeights:        ()     => apiFetch('weights?limit=30'),
  addWeight:         (d)    => apiFetch('weights', { method: 'POST', body: JSON.stringify(d) }),
  deleteWeight:      (id)   => apiFetch(`weights/${id}`, { method: 'DELETE' }),

  calculate:         (d)    => apiFetch('calculator', { method: 'POST', body: JSON.stringify(d) }),
  getScheduleSettings: ()   => apiFetch('schedule/settings'),
  saveScheduleSettings:(d)  => apiFetch('schedule/settings', { method: 'POST', body: JSON.stringify(d) }),
  calculateSchedule: (d)    => apiFetch('schedule/calculate', { method: 'POST', body: JSON.stringify(d) }),
  getTodaySchedule:  ()     => apiFetch('schedule/today'),

  getSleepActive:    ()     => apiFetch('sleep/active'),
  startSleep:        ()     => apiFetch('sleep', { method: 'POST', body: JSON.stringify({ started_at: nowLocal() }) }),
  endSleep:          ()     => apiFetch('sleep/end', { method: 'POST', body: '{}' }),
};

/* ════════════════════════════════════════════
   TOAST NOTIFICATIONS
   ════════════════════════════════════════════ */
function toast(msg, type = 'success') {
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icon}</span><span>${msg}</span>`;
  const c = document.getElementById('toast-container');
  c.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

/* ════════════════════════════════════════════
   SERVER-TIME INIT
   Fetches the server's UTC offset once on startup so all time
   calculations use the HA server timezone, not the browser timezone.
   ════════════════════════════════════════════ */
async function initServerTime() {
  try {
    const data = await apiFetch('server-time');
    _tzOffsetMs = (data.utc_offset_minutes || 0) * 60000;
  } catch (e) {
    // Fallback: try browser timezone (may still be wrong in HA ingress)
    _tzOffsetMs = -new Date().getTimezoneOffset() * 60000;
    console.warn('server-time unavailable, using browser offset:', _tzOffsetMs);
  }
  // Update today's date now that offset is known
  const todayStr = new Date(Date.now() + _tzOffsetMs).toISOString().slice(0, 10);
  State.feedingsDay = todayStr;
  State.diapersDay  = todayStr;
}

/* ════════════════════════════════════════════
   TIME UTILITIES
   All functions use _tzOffsetMs (server offset) — NOT browser timezone.
   ════════════════════════════════════════════ */

/** Current server-local datetime as "YYYY-MM-DDTHH:MM:SS" for datetime-local inputs */
function nowLocal() {
  return new Date(Date.now() + _tzOffsetMs).toISOString().slice(0, 19);
}

/** Server-local date as "YYYY-MM-DD". Pass a UTC-based Date to get its server-local date. */
function localDateStr(d) {
  const ms = d ? d.getTime() + _tzOffsetMs : Date.now() + _tzOffsetMs;
  return new Date(ms).toISOString().slice(0, 10);
}

/** Format a stored ISO datetime string (server-local, no Z) for display.
 *  Extracts hours/minutes directly from the string — no timezone math. */
function formatTime(isoStr) {
  if (!isoStr) return '—';
  const timePart = isoStr.split('T')[1] || '';
  const [hrStr, miStr] = timePart.split(':');
  const h = parseInt(hrStr, 10) || 0;
  const m = String(parseInt(miStr, 10) || 0).padStart(2, '0');
  if (State.clockFormat === '12h') {
    const ampm = h >= 12 ? 'PM' : 'AM';
    const h12 = h % 12 || 12;
    return `${h12}:${m} ${ampm}`;
  }
  return `${String(h).padStart(2, '0')}:${m}`;
}

/** Format a stored ISO datetime string with "Today" / "Yesterday" prefix */
function formatDateTime(isoStr) {
  if (!isoStr) return '—';
  const storedDate = isoStr.split('T')[0];
  const serverNowMs = Date.now() + _tzOffsetMs;
  const todayDate     = new Date(serverNowMs).toISOString().slice(0, 10);
  const yesterdayDate = new Date(serverNowMs - 86400000).toISOString().slice(0, 10);
  const time = formatTime(isoStr);
  if (storedDate === todayDate)     return `${t('today')} ${time}`;
  if (storedDate === yesterdayDate) return `${t('yesterday')} ${time}`;
  const [yr, mo, da] = storedDate.split('-').map(Number);
  const d = new Date(Date.UTC(yr, mo - 1, da));
  return d.toLocaleDateString('nl-NL', { day: 'numeric', month: 'short', timeZone: 'UTC' }) + ' ' + time;
}

/** Human-readable "X min ago" using server time as reference */
function timeAgo(isoStr) {
  if (!isoStr) return '';
  // Stored time is server-local (e.g. "13:06" Amsterdam).
  // Append 'Z' so JS treats it as UTC, then compare with server-now
  // (Date.now() + offset = same "shifted" UTC base). The math cancels out correctly.
  const storedMs   = new Date(isoStr + 'Z').getTime();
  const serverNowMs = Date.now() + _tzOffsetMs;
  const diff = serverNowMs - storedMs;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return t('just_now');
  if (mins < 60) return `${mins} ${t('min_ago')}`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} ${hrs === 1 ? t('hour_ago') : t('hours_ago')}`;
  return t('yesterday');
}

function msToHHMM(ms) {
  if (ms < 0) return '00:00';
  const totalMin = Math.floor(ms / 60000);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
}

function calcAge(birthDateStr) {
  if (!birthDateStr) return '';
  const birth = new Date(birthDateStr); // date-only string → UTC midnight (ES spec)
  const totalDays = Math.floor((Date.now() + _tzOffsetMs - birth.getTime()) / 86400000);
  if (totalDays < 0) return '';
  if (totalDays < 14) return `${totalDays} ${t('days')}`;
  const weeks = Math.floor(totalDays / 7);
  if (weeks < 8) return `${weeks} ${t('weeks')}`;
  const months = Math.floor(totalDays / 30.44);
  return `${months} ${t('months')}`;
}

let _clockInterval = null;

/* ════════════════════════════════════════════
   CLOCK
   ════════════════════════════════════════════ */
function startClock() {
  if (_clockInterval) { clearInterval(_clockInterval); _clockInterval = null; }
  function tick() {
    const el = document.getElementById('clock');
    if (!el) return;
    // Use server offset so clock shows server-local time (not browser-local time)
    const shifted = new Date(Date.now() + _tzOffsetMs);
    const h = shifted.getUTCHours();
    const m = String(shifted.getUTCMinutes()).padStart(2, '0');
    if (State.clockFormat === '12h') {
      const ampm = h >= 12 ? 'PM' : 'AM';
      const h12 = h % 12 || 12;
      el.textContent = `${h12}:${m} ${ampm}`;
    } else {
      el.textContent = `${String(h).padStart(2, '0')}:${m}`;
    }
  }
  tick();
  _clockInterval = setInterval(tick, 10000);
}

/* ════════════════════════════════════════════
   NAVIGATION
   ════════════════════════════════════════════ */
function showSection(name) {
  State.currentSection = name;
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

  const sec = document.getElementById(`sec-${name}`);
  const nav = document.getElementById(`nav-${name}`);
  if (sec) sec.classList.add('active');
  if (nav) nav.classList.add('active');

  // FAB visibility
  const fab = document.getElementById('fab');
  if (['feedings', 'diapers', 'weight'].includes(name)) {
    fab.classList.remove('hidden');
  } else {
    fab.classList.add('hidden');
  }

  // Load section data
  if (name === 'home') loadDashboard();
  else if (name === 'feedings') loadFeedings();
  else if (name === 'diapers') loadDiapers();
  else if (name === 'weight') loadWeight();
  else if (name === 'settings') loadSettings();
}

function onFab() {
  const s = State.currentSection;
  if (s === 'feedings') openFeedingModal();
  else if (s === 'diapers') openDiaperModal();
  else if (s === 'weight') openWeightModal();
}

/* ════════════════════════════════════════════
   MODAL HELPERS
   ════════════════════════════════════════════ */
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('open');
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
}

// Close modal on overlay click
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

/* ════════════════════════════════════════════
   DASHBOARD
   ════════════════════════════════════════════ */
async function loadDashboard() {
  try {
    const data = await api.getDashboard();
    renderDashboard(data);
    State.schedule = data.schedule;
    startCountdown(data);
  } catch (e) {
    console.error('Dashboard error:', e);
  }
}

function renderDashboard(data) {
  // Feeding stats
  const feedings = data.feedings_today || [];
  const totalMl = feedings.reduce((s, f) => s + (f.amount_ml || 0), 0);
  document.getElementById('stat-feedings').textContent = feedings.length;
  document.getElementById('stat-total-ml').textContent = `${totalMl} ml`;

  // Diaper stats
  const diapers = data.diapers_today || [];
  const wet = diapers.filter(d => d.diaper_type === 'wet' || d.diaper_type === 'both').length;
  const dirty = diapers.filter(d => d.diaper_type === 'dirty' || d.diaper_type === 'both').length;
  document.getElementById('stat-diapers-wet').textContent = wet;
  document.getElementById('stat-diapers-dirty').textContent = dirty;

  // Progress bar
  const schedule = data.schedule || {};
  const target = schedule.num_feedings || 6;
  const pct = Math.min(100, (feedings.length / target) * 100);
  document.getElementById('progress-bar').style.width = pct + '%';
  document.getElementById('progress-label').textContent = `${feedings.length}/${target}`;

  // Amount pill
  if (schedule.amount_ml) {
    document.getElementById('pill-amount').textContent = schedule.amount_ml;
    document.getElementById('amount-pill').style.display = '';
  }

  // Timeline
  renderTimeline(schedule, feedings);

  // Last feeding
  if (data.last_feeding) {
    const lf = data.last_feeding;
    const amtStr = lf.amount_ml ? ` • ${lf.amount_ml} ml` : '';
    const lfi = document.getElementById('last-feeding-info');
    lfi.removeAttribute('data-i18n'); // prevent applyTranslations from overwriting
    lfi.textContent = `${formatTime(lf.started_at)}${amtStr} — ${timeAgo(lf.started_at)}`;
  } else {
    document.getElementById('last-feeding-info').setAttribute('data-i18n', 'no_feeding_yet');
    document.getElementById('last-feeding-info').textContent = t('no_feeding_yet');
  }

  // Sleep
  State.activeSleep = data.active_sleep;
  updateSleepButton();
  if (data.active_sleep) {
    const sleepStart = new Date(data.active_sleep.started_at);
    const sleepMins = Math.floor((Date.now() - sleepStart) / 60000);
    const sleepH = Math.floor(sleepMins / 60);
    const sleepM = sleepMins % 60;
    document.getElementById('stat-sleep').textContent =
      sleepH > 0 ? `${sleepH}u${String(sleepM).padStart(2,'0')}` : `${sleepM}m`;
  } else {
    document.getElementById('stat-sleep').textContent = '—';
  }

  // Baby header
  if (data.schedule && State.baby) {
    // already set at init
  }
}

function renderTimeline(schedule, feedings) {
  const tl = document.getElementById('timeline');
  const card = document.getElementById('schedule-card');
  if (!schedule || !schedule.feeding_times || !schedule.feeding_times.length) {
    card.style.display = 'none';
    return;
  }
  card.style.display = '';

  const feedingTimes = (feedings || []).map(f => formatTime(f.started_at));
  const serverNow = new Date(Date.now() + _tzOffsetMs);
  const nowMins = serverNow.getUTCHours() * 60 + serverNow.getUTCMinutes();

  let foundNext = false;
  tl.innerHTML = schedule.feeding_times.map((time, i) => {
    const [h, m] = time.split(':').map(Number);
    const slotMins = h * 60 + m;
    // Midnight (00:00) is the LAST feeding of the day, not the first.
    // Treat it as 1440 min so it is never auto-marked "past" during daytime.
    const effectiveMins = slotMins === 0 ? 24 * 60 : slotMins;
    const isDone = feedingTimes.includes(time) || effectiveMins < nowMins - 30;
    const isNext = !isDone && !foundNext && (effectiveMins >= nowMins - 15);
    if (isNext) foundNext = true;
    const cls = isDone ? 'done' : isNext ? 'next' : 'upcoming';
    const icon = isDone ? '✓' : isNext ? '🍼' : (i + 1).toString();
    const amtStr = schedule.amount_ml ? `${schedule.amount_ml}ml` : '';
    return `
      <div class="tl-item ${cls}">
        <div class="tl-dot-wrap"><div class="tl-dot ${cls}">${icon}</div></div>
        <div class="tl-time">${time}</div>
        ${amtStr ? `<div class="tl-amount">${amtStr}</div>` : ''}
      </div>`;
  }).join('');
}

function startCountdown(data) {
  if (State.countdownTimer) clearInterval(State.countdownTimer);

  function update() {
    const schedule = data.schedule || {};
    const times = schedule.feeding_times || [];
    if (!times.length) {
      document.getElementById('countdown').textContent = '—';
      document.getElementById('hero-label').textContent = t('no_feeding_yet');
      return;
    }

    const serverNow = new Date(Date.now() + _tzOffsetMs);
    const nowMins = serverNow.getUTCHours() * 60 + serverNow.getUTCMinutes();

    // Find next scheduled feeding
    let nextMins = null;
    for (const time of times) {
      const [h, m] = time.split(':').map(Number);
      const slotMins = h * 60 + m;
      if (slotMins > nowMins) { nextMins = slotMins; break; }
    }
    // Wrap to next day if past all slots for today
    if (nextMins === null) {
      const [h0, m0] = times[0].split(':').map(Number);
      nextMins = h0 * 60 + m0 + 24 * 60;
    }

    const diffMs = (nextMins - nowMins) * 60000;
    const hero = document.getElementById('hero-card');
    const label = document.getElementById('hero-label');
    const countdown = document.getElementById('countdown');
    const sub = document.getElementById('countdown-sub');

    if (diffMs <= 0) {
      countdown.textContent = t('overdue');
      label.textContent = '⚠️';
      hero.style.background = 'linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%)';
    } else {
      const totalMin = Math.floor(diffMs / 60000);
      const hh = Math.floor(totalMin / 60);
      const mm = String(totalMin % 60).padStart(2, '0');
      countdown.textContent = `${hh}:${mm} uur`;
      label.textContent = t('next_feeding');
      hero.style.background = '';
      // Find the actual next time slot
      const nextSlot = times.find(time => {
        const [sh, sm] = time.split(':').map(Number);
        return (sh * 60 + sm) > nowMins;
      });
      sub.textContent = nextSlot ? `om ${nextSlot}` : '';
    }
  }

  update();
  State.countdownTimer = setInterval(update, 30000);
}

/* ════════════════════════════════════════════
   FEEDINGS
   ════════════════════════════════════════════ */
async function loadFeedings() {
  renderDateTabs('feedings', State.feedingsDay);
  try {
    const items = await api.getFeedings(State.feedingsDay);
    renderFeedingsList(items);
  } catch (e) {
    console.error('Feedings error:', e);
  }
}

function renderFeedingsList(items) {
  const list = document.getElementById('feedings-list');
  const count = items.length;
  const total = items.reduce((s, f) => s + (f.amount_ml || 0), 0);
  const avg = count ? Math.round(total / count) : 0;

  document.getElementById('fs-count').textContent = count;
  document.getElementById('fs-total').textContent = `${total} ml`;
  document.getElementById('fs-avg').textContent = count ? `${avg} ml` : '—';

  if (!count) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🍼</div>
        <div class="empty-state-text">${t('no_feedings')}</div>
      </div>`;
    return;
  }

  const typeEmoji = { bottle: '🍼', breast_left: '🤱', breast_right: '🤱', both_breasts: '🤱', solid: '🥣' };
  const typeBg = { bottle: 'var(--primary-light)', breast_left: 'var(--secondary-light)', breast_right: 'var(--secondary-light)', both_breasts: 'var(--secondary-light)', solid: 'var(--accent-light)' };

  list.innerHTML = [...items].reverse().map(f => `
    <div class="history-item">
      <div class="history-icon" style="background:${typeBg[f.feeding_type] || 'var(--primary-light)'}">
        ${typeEmoji[f.feeding_type] || '🍼'}
      </div>
      <div class="history-body">
        <div class="history-title">${f.amount_ml ? f.amount_ml + ' ml' : t(f.feeding_type || 'bottle')}</div>
        <div class="history-sub">${t(f.feeding_type || 'bottle')}${f.notes ? ' • ' + f.notes : ''}</div>
      </div>
      <div class="history-time">${formatTime(f.started_at)}</div>
      <button class="history-delete" onclick="App.deleteFeeding(${f.id})" title="${t('delete')}">🗑</button>
    </div>`).join('');
}

function openFeedingModal(prefillAmount) {
  document.getElementById('f-time').value = nowLocal();
  // Pre-fill recommended amount from schedule
  const schedAmt = State.schedule && State.schedule.amount_ml;
  document.getElementById('f-amount').value = prefillAmount || schedAmt || '';
  document.getElementById('f-notes').value = '';
  selectFeedingType('bottle');
  openModal('modal-feeding');
}

function selectFeedingType(type) {
  State.feedingType = type;
  document.querySelectorAll('#modal-feeding .type-option').forEach(b => {
    b.classList.toggle('selected', b.dataset.type === type);
  });
}

async function saveFeeding() {
  const timeVal = document.getElementById('f-time').value;
  const amount = document.getElementById('f-amount').value;
  if (!timeVal) { toast(t('error'), 'error'); return; }

  try {
    await api.addFeeding({
      started_at: timeVal.length === 16 ? timeVal + ':00' : timeVal,
      amount_ml: amount ? parseFloat(amount) : null,
      feeding_type: State.feedingType,
      notes: document.getElementById('f-notes').value || null,
    });
    closeModal('modal-feeding');
    toast('🍼 ' + (t('add_feeding') || 'Voeding opgeslagen!'));
    confetti();
    if (State.currentSection === 'feedings') loadFeedings();
    else loadDashboard();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function deleteFeeding(id) {
  if (!confirm(t('confirm_delete'))) return;
  try {
    await api.deleteFeeding(id);
    toast(t('delete') + ' ✓');
    loadFeedings();
    if (State.currentSection === 'home') loadDashboard();
  } catch (e) {
    toast(e.message, 'error');
  }
}

// Quick feeding from dashboard
function quickFeeding() {
  showSection('feedings');
  setTimeout(() => openFeedingModal(), 200);
}

/* ════════════════════════════════════════════
   DIAPERS
   ════════════════════════════════════════════ */
async function loadDiapers() {
  renderDateTabs('diapers', State.diapersDay);
  try {
    const items = await api.getDiapers(State.diapersDay);
    renderDiapersList(items);
  } catch (e) {
    console.error('Diapers error:', e);
  }
}

function renderDiapersList(items) {
  const list = document.getElementById('diapers-list');
  const wet = items.filter(d => d.diaper_type === 'wet' || d.diaper_type === 'both').length;
  const dirty = items.filter(d => d.diaper_type === 'dirty' || d.diaper_type === 'both').length;

  document.getElementById('ds-wet').textContent = wet;
  document.getElementById('ds-dirty').textContent = dirty;
  document.getElementById('ds-total').textContent = items.length;

  if (!items.length) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">👶</div>
        <div class="empty-state-text">${t('no_diapers')}</div>
      </div>`;
    return;
  }

  const typeEmoji = { wet: '💧', dirty: '💩', both: '🟢', dry: '✅' };
  const typeBg = { wet: '#EBF8FF', dirty: '#FFFBEB', both: '#F0FFF4', dry: '#F0FFF4' };

  list.innerHTML = [...items].reverse().map(d => {
    const colorDot = (d.poop_color && (d.diaper_type === 'dirty' || d.diaper_type === 'both'))
      ? `<span class="poop-color-dot" style="background:${d.poop_color}" title="${d.poop_color}"></span>`
      : '';
    return `
    <div class="history-item">
      <div class="history-icon" style="background:${typeBg[d.diaper_type] || '#F5F5F5'}">
        ${typeEmoji[d.diaper_type] || '👶'}
      </div>
      <div class="history-body">
        <div class="history-title">${t(d.diaper_type || 'wet')}${colorDot}</div>
        <div class="history-sub">${d.notes || ''}</div>
      </div>
      <div class="history-time">${formatTime(d.changed_at)}</div>
      <button class="history-delete" onclick="App.deleteDiaper(${d.id})" title="${t('delete')}">🗑</button>
    </div>`;
  }).join('');
}

function openDiaperModal(prefillType) {
  document.getElementById('d-time').value = nowLocal();
  document.getElementById('d-notes').value = '';
  // Reset poop color
  State.poopColor = null;
  document.querySelectorAll('.poop-color-btn').forEach(b => b.classList.remove('selected'));
  document.getElementById('poop-color-group').style.display = 'none';
  selectDiaperType(prefillType || 'wet');
  openModal('modal-diaper');
}

function selectDiaperType(type) {
  State.diaperType = type;
  document.querySelectorAll('#modal-diaper .type-option').forEach(b => {
    b.classList.toggle('selected', b.dataset.type === type);
  });
  // Show poop color picker only when type involves dirty
  const showColor = type === 'dirty' || type === 'both';
  document.getElementById('poop-color-group').style.display = showColor ? '' : 'none';
  if (!showColor) State.poopColor = null;
}

function selectPoopColor(color) {
  State.poopColor = color;
  document.querySelectorAll('.poop-color-btn').forEach(btn => {
    btn.classList.toggle('selected', btn.dataset.color === color);
  });
}

async function saveDiaper() {
  const timeVal = document.getElementById('d-time').value;
  if (!timeVal) { toast(t('error'), 'error'); return; }

  try {
    await api.addDiaper({
      changed_at: timeVal.length === 16 ? timeVal + ':00' : timeVal,
      diaper_type: State.diaperType,
      notes: document.getElementById('d-notes').value || null,
      poop_color: State.poopColor || null,
    });
    closeModal('modal-diaper');
    toast('👶 Luier geregistreerd!');
    if (State.currentSection === 'diapers') loadDiapers();
    else loadDashboard();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function deleteDiaper(id) {
  if (!confirm(t('confirm_delete'))) return;
  try {
    await api.deleteDiaper(id);
    toast(t('delete') + ' ✓');
    loadDiapers();
    if (State.currentSection === 'home') loadDashboard();
  } catch (e) {
    toast(e.message, 'error');
  }
}

function quickDiaper(type) {
  showSection('diapers');
  setTimeout(() => openDiaperModal(type), 200);
}

/* ════════════════════════════════════════════
   WEIGHT
   ════════════════════════════════════════════ */
async function loadWeight() {
  try {
    const items = await api.getWeights();
    renderWeightSection(items);
  } catch (e) {
    console.error('Weight error:', e);
  }
}

function renderWeightSection(items) {
  const display = document.getElementById('weight-value');
  const changeEl = document.getElementById('weight-change');
  const list = document.getElementById('weight-list');

  if (items.length) {
    const latest = items[0];
    display.textContent = latest.weight_g >= 1000
      ? (latest.weight_g / 1000).toFixed(2).replace('.', ',') + ' kg'
      : latest.weight_g + ' g';

    if (items.length >= 2) {
      const diff = latest.weight_g - items[1].weight_g;
      const sign = diff >= 0 ? '▲' : '▼';
      const color = diff >= 0 ? 'var(--accent)' : 'var(--danger)';
      changeEl.innerHTML = `<span style="color:${color}">${sign} ${Math.abs(diff)}g</span> t.o.v. vorige meting`;
    }

    // Pre-fill schedule weight from latest measurement
    document.getElementById('sched-weight').value = latest.weight_g;
  } else {
    display.textContent = '—';
  }

  // Render history
  if (!items.length) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚖️</div>
        <div class="empty-state-text">${t('no_weight')}</div>
      </div>`;
  } else {
    list.innerHTML = items.map(w => {
      const kg = w.weight_g >= 1000 ? (w.weight_g / 1000).toFixed(3) + ' kg' : w.weight_g + ' g';
      return `
        <div class="history-item">
          <div class="history-icon" style="background:var(--secondary-light)">⚖️</div>
          <div class="history-body">
            <div class="history-title">${kg}</div>
            <div class="history-sub">${w.notes || ''}</div>
          </div>
          <div class="history-time">${formatDateTime(w.measured_at)}</div>
          <button class="history-delete" onclick="App.deleteWeight(${w.id})" title="${t('delete')}">🗑</button>
        </div>`;
    }).join('');
  }

  // Chart
  renderWeightChart(items);
}

function renderWeightChart(items) {
  const canvas = document.getElementById('weight-chart');
  if (!canvas || typeof Chart === 'undefined') return;

  const sorted = [...items].sort((a, b) => new Date(a.measured_at) - new Date(b.measured_at));

  const labels = sorted.map(w => {
    const d = new Date(w.measured_at);
    return d.toLocaleDateString('nl-NL', { day: 'numeric', month: 'short' });
  });
  const data = sorted.map(w => (w.weight_g / 1000));

  if (State.weightChart) State.weightChart.destroy();

  State.weightChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Gewicht (kg)',
        data,
        borderColor: '#7C6FE8',
        backgroundColor: 'rgba(124, 111, 232, 0.08)',
        borderWidth: 3,
        pointBackgroundColor: '#7C6FE8',
        pointRadius: 5,
        pointHoverRadius: 7,
        fill: true,
        tension: 0.4,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.parsed.y.toFixed(3)} kg`
          }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        y: {
          ticks: { callback: v => v.toFixed(2) + ' kg', font: { size: 11 } },
          grid: { color: 'rgba(0,0,0,0.05)' }
        }
      }
    }
  });
}

function openWeightModal() {
  document.getElementById('w-time').value = nowLocal();
  document.getElementById('w-amount').value = '';
  document.getElementById('w-notes').value = '';
  openModal('modal-weight');
}

async function saveWeight() {
  const timeVal = document.getElementById('w-time').value;
  const amount = document.getElementById('w-amount').value;
  if (!timeVal || !amount) { toast(t('error'), 'error'); return; }

  try {
    await api.addWeight({
      measured_at: timeVal.length === 16 ? timeVal + ':00' : timeVal,
      weight_g: parseFloat(amount),
      notes: document.getElementById('w-notes').value || null,
    });
    closeModal('modal-weight');
    toast('⚖️ Gewicht opgeslagen!');
    loadWeight();
    loadDashboard();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function deleteWeight(id) {
  if (!confirm(t('confirm_delete'))) return;
  try {
    await api.deleteWeight(id);
    toast(t('delete') + ' ✓');
    loadWeight();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function runCalculator() {
  const w = parseFloat(document.getElementById('calc-weight-input').value);
  const n = parseInt(document.getElementById('calc-feedings-input').value);
  if (!w || !n || n < 1) { toast(t('error'), 'error'); return; }

  try {
    const result = await api.calculate({ weight_g: w, num_feedings: n });
    document.getElementById('calc-result-value').textContent = result.per_feeding_rounded;
    document.getElementById('calc-result-sub').textContent =
      `${t('calc_total')}: ${result.daily_total_ml} ml • ${result.formula}`;
    document.getElementById('calc-result').style.display = '';
  } catch (e) {
    toast(e.message, 'error');
  }
}

/* ════════════════════════════════════════════
   SETTINGS & SCHEDULE
   ════════════════════════════════════════════ */
async function loadSettings() {
  // Baby profile
  try {
    const baby = await api.getBaby();
    State.baby = baby;
    document.getElementById('set-name').value = baby.name || '';
    document.getElementById('set-birth').value = baby.birth_date || '';
    document.getElementById('set-gender').value = baby.gender || 'boy';
  } catch (e) { /* new install, no baby yet */ }

  // Schedule settings
  try {
    const sched = await api.getScheduleSettings();
    if (sched.weight_g) document.getElementById('sched-weight').value = sched.weight_g;
    if (sched.num_feedings) document.getElementById('sched-num').value = sched.num_feedings;
    if (sched.first_feeding_time) document.getElementById('sched-first').value = sched.first_feeding_time;
    if (sched.last_feeding_time) document.getElementById('sched-last').value = sched.last_feeding_time;
    if (sched.burp_buffer_minutes) document.getElementById('sched-buf').value = sched.burp_buffer_minutes;

    State.blockedWindows = sched.blocked_windows || [];
    renderBlockedWindows();

    if (sched.calculated_amount_ml) {
      document.getElementById('sched-amount-preview').textContent = sched.calculated_amount_ml;
      document.getElementById('sched-result-preview').style.display = '';
    }
  } catch (e) { console.error('Schedule settings:', e); }

  // Always override weight from latest actual measurement so it stays up-to-date
  try {
    const weights = await api.getWeights();
    if (weights && weights.length) {
      document.getElementById('sched-weight').value = weights[0].weight_g;
    }
  } catch (e) { /* no weights yet, keep stored value */ }

  // Update language buttons
  updateLangButtons();
}

async function saveBaby() {
  const name = document.getElementById('set-name').value.trim();
  const birth = document.getElementById('set-birth').value;
  const gender = document.getElementById('set-gender').value;

  try {
    const baby = await api.updateBaby({ name, birth_date: birth || null, gender });
    State.baby = baby;
    updateHeader();
    toast('👶 ' + t('settings_saved'));
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function saveSchedule() {
  const weight = document.getElementById('sched-weight').value;
  const num = document.getElementById('sched-num').value;
  const first = document.getElementById('sched-first').value;
  const last = document.getElementById('sched-last').value;
  const buf = document.getElementById('sched-buf').value;

  if (!num || !first) { toast(t('error'), 'error'); return; }

  try {
    const result = await api.saveScheduleSettings({
      weight_g: weight ? parseFloat(weight) : null,
      num_feedings: parseInt(num),
      first_feeding_time: first,
      last_feeding_time: last || null,
      blocked_windows: State.blockedWindows,
      burp_buffer_minutes: parseInt(buf) || 20,
    });

    if (result.calculated_amount_ml) {
      document.getElementById('sched-amount-preview').textContent = result.calculated_amount_ml;
      const w = parseFloat(weight);
      const n = parseInt(num);
      const daily = (w * 155 / 1000).toFixed(0);
      document.getElementById('sched-formula-preview').textContent =
        `${w}g × 155 ÷ 1000 ÷ ${n} = ${result.calculated_amount_ml}ml/voeding • ${daily}ml/dag`;
      document.getElementById('sched-result-preview').style.display = '';
    }

    toast('📅 ' + t('schedule_saved'));
    loadDashboard();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function previewSchedule() {
  const num = parseInt(document.getElementById('sched-num').value);
  const first = document.getElementById('sched-first').value;
  const last = document.getElementById('sched-last').value;
  const buf = parseInt(document.getElementById('sched-buf').value) || 20;

  if (!num || !first) { toast(t('error'), 'error'); return; }

  try {
    const result = await api.calculateSchedule({
      num_feedings: num,
      first_feeding_time: first,
      last_feeding_time: last || null,
      blocked_windows: State.blockedWindows,
      burp_buffer_minutes: buf,
    });

    const card = document.getElementById('sched-preview-card');
    const listEl = document.getElementById('sched-preview-list');
    const warningsEl = document.getElementById('sched-warnings');

    listEl.innerHTML = result.feeding_times.map((time, i) => `
      <div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--border-light)">
        <div style="width:32px;height:32px;border-radius:50%;background:var(--primary-light);color:var(--primary);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:13px">${i+1}</div>
        <div style="flex:1;font-size:16px;font-weight:700;color:var(--text)">${time}</div>
        ${i < result.intervals_minutes.length ? `<div style="font-size:12px;color:var(--text-muted)">${result.intervals_minutes[i]} min</div>` : ''}
      </div>`).join('');

    warningsEl.innerHTML = (result.warnings || []).map(w => `
      <div class="schedule-warning">⚠️ ${w}</div>`).join('');

    card.style.display = '';
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (e) {
    toast(e.message, 'error');
  }
}

/* ── Blocked Windows ── */
function renderBlockedWindows() {
  const el = document.getElementById('blocked-list');
  if (!State.blockedWindows.length) {
    el.innerHTML = '';
    return;
  }
  el.innerHTML = State.blockedWindows.map((bw, i) => `
    <div class="blocked-window-row">
      <div class="bw-label">${bw.label || '—'}</div>
      <div class="bw-time">${bw.start} – ${bw.end}</div>
      <button class="bw-delete" onclick="App.removeBlockedWindow(${i})">✕</button>
    </div>`).join('');
}

function showBlockedModal() {
  document.getElementById('bw-label').value = '';
  document.getElementById('bw-start').value = '';
  document.getElementById('bw-end').value = '';
  openModal('modal-blocked');
}

function saveBlockedWindow() {
  const label = document.getElementById('bw-label').value.trim();
  const start = document.getElementById('bw-start').value;
  const end = document.getElementById('bw-end').value;
  if (!start || !end) { toast(t('error'), 'error'); return; }

  State.blockedWindows.push({ label, start, end });
  renderBlockedWindows();
  closeModal('modal-blocked');
}

function removeBlockedWindow(idx) {
  State.blockedWindows.splice(idx, 1);
  renderBlockedWindows();
}

/* ════════════════════════════════════════════
   SLEEP TRACKING
   ════════════════════════════════════════════ */
function updateSleepButton() {
  const icon = document.getElementById('sleep-icon');
  const label = document.getElementById('sleep-label');
  if (State.activeSleep) {
    if (icon) icon.textContent = '☀️';
    if (label) { label.setAttribute('data-i18n', 'awake'); label.textContent = t('awake'); }
  } else {
    if (icon) icon.textContent = '💤';
    if (label) { label.setAttribute('data-i18n', 'btn_sleep'); label.textContent = t('btn_sleep'); }
  }
}

async function toggleSleep() {
  try {
    if (State.activeSleep) {
      await api.endSleep();
      State.activeSleep = null;
      toast('☀️ Slaap beëindigd!');
    } else {
      const s = await api.startSleep();
      State.activeSleep = s;
      toast('💤 Slaap geregistreerd!');
    }
    updateSleepButton();
    loadDashboard();
  } catch (e) {
    toast(e.message, 'error');
  }
}

/* ════════════════════════════════════════════
   DATE TABS
   ════════════════════════════════════════════ */
function renderDateTabs(section, activeDay) {
  const el = document.getElementById(`${section}-date-tabs`);
  const days = [];
  const serverNowMs = Date.now() + _tzOffsetMs;
  const todayDate     = new Date(serverNowMs).toISOString().slice(0, 10);
  const yesterdayDate = new Date(serverNowMs - 86400000).toISOString().slice(0, 10);
  for (let i = 0; i < 5; i++) {
    days.push(new Date(serverNowMs - i * 86400000).toISOString().slice(0, 10));
  }

  el.innerHTML = days.map(day => {
    let label;
    if (day === todayDate)     label = t('today');
    else if (day === yesterdayDate) label = t('yesterday');
    else {
      const [yr, mo, da] = day.split('-').map(Number);
      label = new Date(Date.UTC(yr, mo - 1, da))
        .toLocaleDateString('nl-NL', { day: 'numeric', month: 'short', timeZone: 'UTC' });
    }
    return `<button class="date-tab ${day === activeDay ? 'active' : ''}"
      onclick="App.switchDay('${section}', '${day}')">${label}</button>`;
  }).join('');
}

function switchDay(section, day) {
  if (section === 'feedings') { State.feedingsDay = day; loadFeedings(); }
  else if (section === 'diapers') { State.diapersDay = day; loadDiapers(); }
}

/* ════════════════════════════════════════════
   HEADER UPDATE
   ════════════════════════════════════════════ */
function updateHeader() {
  const baby = State.baby;
  if (!baby) return;
  const nameEl = document.getElementById('hdr-name');
  const ageEl = document.getElementById('hdr-age');
  if (nameEl) nameEl.textContent = baby.name || t('app_title');
  if (ageEl && baby.birth_date) {
    ageEl.textContent = calcAge(baby.birth_date);
  }
}

/* ════════════════════════════════════════════
   LANGUAGE
   ════════════════════════════════════════════ */
function toggleLang() {
  const newLang = State.lang === 'nl' ? 'en' : 'nl';
  setAppLang(newLang);
}

function setAppLang(lang) {
  State.lang = lang;
  setLang(lang); // from i18n.js
  document.getElementById('lang-toggle').textContent = lang === 'nl' ? 'EN' : 'NL';
  updateLangButtons();

  // Re-render active section
  const s = State.currentSection;
  if (s === 'feedings') loadFeedings();
  else if (s === 'diapers') loadDiapers();
  else if (s === 'weight') loadWeight();
  else if (s === 'settings') loadSettings();
  else loadDashboard();
}

function updateLangButtons() {
  const btnNl = document.getElementById('btn-nl');
  const btnEn = document.getElementById('btn-en');
  if (!btnNl || !btnEn) return;
  if (State.lang === 'nl') {
    btnNl.style.cssText = 'background:var(--primary-light);color:var(--primary);border:2px solid var(--primary)';
    btnEn.style.cssText = '';
    btnEn.className = 'btn btn-secondary';
  } else {
    btnEn.style.cssText = 'background:var(--primary-light);color:var(--primary);border:2px solid var(--primary)';
    btnNl.style.cssText = '';
    btnNl.className = 'btn btn-secondary';
  }
}

/* ════════════════════════════════════════════
   CONFETTI (feeding celebration)
   ════════════════════════════════════════════ */
function confetti() {
  const colors = ['#7C6FE8', '#FF6B9D', '#06D6A0', '#FFB347', '#A855F7'];
  for (let i = 0; i < 20; i++) {
    const el = document.createElement('div');
    el.className = 'confetti-piece';
    el.style.cssText = `
      left: ${Math.random() * 100}vw;
      top: -10px;
      background: ${colors[Math.floor(Math.random() * colors.length)]};
      width: ${6 + Math.random() * 8}px;
      height: ${6 + Math.random() * 8}px;
      animation-delay: ${Math.random() * 0.5}s;
      animation-duration: ${1.5 + Math.random()}s;
      border-radius: ${Math.random() > 0.5 ? '50%' : '2px'};
    `;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2500);
  }
}

function setClockFormat(fmt) {
  State.clockFormat = fmt;
  localStorage.setItem('bt_clockFormat', fmt);
  updateClockButtons();
  startClock();
  // Re-render active section to update displayed times
  const s = State.currentSection;
  if (s === 'feedings') loadFeedings();
  else if (s === 'diapers') loadDiapers();
  else if (s === 'weight') loadWeight();
  else loadDashboard();
}

function updateClockButtons() {
  const btn24 = document.getElementById('btn-24h');
  const btn12 = document.getElementById('btn-12h');
  if (!btn24 || !btn12) return;
  if (State.clockFormat === '24h') {
    btn24.style.cssText = 'background:var(--primary-light);color:var(--primary);border:2px solid var(--primary)';
    btn24.className = 'btn';
    btn12.style.cssText = '';
    btn12.className = 'btn btn-secondary';
  } else {
    btn12.style.cssText = 'background:var(--primary-light);color:var(--primary);border:2px solid var(--primary)';
    btn12.className = 'btn';
    btn24.style.cssText = '';
    btn24.className = 'btn btn-secondary';
  }
}

/* ════════════════════════════════════════════
   ════════════════════════════════════════════ */
function startAutoRefresh() {
  // Refresh dashboard every 60 seconds when on home view
  State.refreshTimer = setInterval(() => {
    if (State.currentSection === 'home') loadDashboard();
  }, 60000);
}

/* ════════════════════════════════════════════
   FIRST-TIME SETUP
   ════════════════════════════════════════════ */
function selectSetupGender(gender) {
  State.setupGender = gender;
  document.querySelectorAll('#modal-setup .type-option').forEach(b => {
    b.classList.toggle('selected', b.dataset.gender === gender);
  });
}

async function saveSetup() {
  const name   = document.getElementById('setup-name').value.trim();
  const birth  = document.getElementById('setup-birth').value;
  const weight = parseInt(document.getElementById('setup-weight').value, 10);
  const first  = document.getElementById('setup-first').value;
  const last   = document.getElementById('setup-last').value;
  const num    = parseInt(document.getElementById('setup-num').value, 10) || 6;
  const buf    = parseInt(document.getElementById('setup-buf').value, 10) || 20;

  if (!name) { toast('Vul een naam in', 'error'); return; }
  if (!birth) { toast('Vul een geboortedatum in', 'error'); return; }

  try {
    // Save baby profile
    const baby = await api.updateBaby({ name, birth_date: birth, gender: State.setupGender });
    State.baby = baby;
    updateHeader();

    // Save weight measurement if given
    if (weight && weight >= 500) {
      await api.addWeight({ measured_at: new Date().toISOString().slice(0, 19), weight_g: weight, notes: 'Begingewicht' });
    }

    // Save schedule settings
    await api.saveScheduleSettings({
      weight_g: weight || null,
      num_feedings: num,
      first_feeding_time: first,
      last_feeding_time: last,
      burp_buffer_minutes: buf,
      blocked_windows: [],
    });

    closeModal('modal-setup');
    toast('👶 Welkom, ' + name + '! Alles is ingesteld.');

    // Reload dashboard with the new data
    await loadDashboard();
  } catch (e) {
    toast(e.message, 'error');
  }
}

/* ════════════════════════════════════════════
   INITIALIZATION
   ════════════════════════════════════════════ */
async function init() {
  // Get server timezone offset FIRST — all time functions depend on this
  await initServerTime();

  // Load saved language
  const savedLang = localStorage.getItem('bt_lang') || 'nl';
  State.lang = savedLang;
  setLang(savedLang);
  document.getElementById('lang-toggle').textContent = savedLang === 'nl' ? 'EN' : 'NL';

  // Apply clock format from storage
  updateClockButtons();

  // Load config from HA options
  try {
    const config = await api.getConfig();
    if (config.language && !localStorage.getItem('bt_lang')) {
      State.lang = config.language;
      setLang(config.language);
    }
  } catch (e) { /* ignore */ }

  // Load baby
  try {
    const baby = await api.getBaby();
    State.baby = baby;
    updateHeader();

    // Show first-time setup if baby hasn't been configured yet
    if (baby.name === 'Baby' && !baby.birth_date) {
      openModal('modal-setup');
    }
  } catch (e) { /* ignore */ }

  // Start clock
  startClock();

  // Auto-refresh
  startAutoRefresh();

  // Apply translations BEFORE loading dashboard data so dynamic content isn't overwritten
  applyTranslations();

  // Load initial view
  await loadDashboard();
}

/* ════════════════════════════════════════════
   PUBLIC APP INTERFACE
   ════════════════════════════════════════════ */
window.App = {
  // Navigation
  showSection,
  onFab,

  // Modals
  openModal,
  closeModal,

  // Feedings
  quickFeeding,
  openFeedingModal,
  selectFeedingType,
  saveFeeding,
  deleteFeeding,

  // Diapers
  quickDiaper,
  openDiaperModal,
  selectDiaperType,
  saveDiaper,
  deleteDiaper,
  selectPoopColor,

  // Weight
  openWeightModal,
  saveWeight,
  deleteWeight,
  runCalculator,

  // Settings
  saveBaby,
  saveSchedule,
  previewSchedule,
  showBlockedModal,
  saveBlockedWindow,
  removeBlockedWindow,

  // First-time setup
  saveSetup,
  selectSetupGender,

  // Sleep
  toggleSleep,

  // Date tabs
  switchDay,

  // Language
  toggleLang,
  setLang: setAppLang,

  // Clock format
  setClockFormat,
};

// Boot
document.addEventListener('DOMContentLoaded', init);
