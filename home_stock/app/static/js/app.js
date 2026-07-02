/**
 * Home Stock - Main Application
 * Low-friction household stock tracker. Vanilla JS SPA served under HA ingress.
 */

const API_BASE = 'api';

/* Server UTC offset (ms), set on boot so the clock uses the HA server timezone
   rather than the browser timezone (which is often UTC under ingress). */
let _tzOffsetMs = 0;

const State = {
  section: 'stock',
  lang: 'nl',
  settings: null,
  items: [],
  catFilter: 'all',
  editId: null,          // null => custom-add mode; number => editing existing item
  haConnected: false,
};

/* ════════ API ════════ */
async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}/${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    const e = new Error(err.detail || `HTTP ${res.status}`);
    e.status = res.status;
    e.detail = err.detail;
    throw e;
  }
  if (res.status === 204) return null;
  return res.json();
}

const api = {
  getConfig:      ()    => apiFetch('config'),
  getSettings:    ()    => apiFetch('settings'),
  saveSettings:   (d)   => apiFetch('settings', { method: 'POST', body: JSON.stringify(d) }),
  getItems:       ()    => apiFetch('items'),
  addItem:        (d)   => apiFetch('items', { method: 'POST', body: JSON.stringify(d) }),
  updateItem:     (id, d) => apiFetch(`items/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
  deleteItem:     (id)  => apiFetch(`items/${id}`, { method: 'DELETE' }),
  adjustItem:     (id, delta) => apiFetch(`items/${id}/adjust`, { method: 'POST', body: JSON.stringify({ delta }) }),
  getShopping:    ()    => apiFetch('shopping-list'),
  syncShopping:   ()    => apiFetch('shopping-list/sync', { method: 'POST', body: '{}' }),
  getTodoLists:   ()    => apiFetch('ha/todo-lists'),
};

/* ════════ Toast ════════ */
function toast(msg, type = 'success') {
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icon}</span><span>${msg}</span>`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

/* ════════ Helpers ════════ */
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}
function catLabel(id) {
  const c = window.categoryMeta(id);
  return c[State.lang] || c.en;
}
function catEmoji(id) { return window.categoryMeta(id).emoji; }

/* ════════ Server time / clock ════════ */
async function initServerTime() {
  try {
    const d = await apiFetch('server-time');
    _tzOffsetMs = (d.utc_offset_minutes || 0) * 60000;
  } catch (e) {
    _tzOffsetMs = -new Date().getTimezoneOffset() * 60000;
  }
}
function tickClock() {
  const now = new Date(Date.now() + _tzOffsetMs);
  const hh = String(now.getUTCHours()).padStart(2, '0');
  const mm = String(now.getUTCMinutes()).padStart(2, '0');
  const el = document.getElementById('clock');
  if (el) el.textContent = `${hh}:${mm}`;
}

/* ════════ Navigation ════════ */
function showSection(name) {
  State.section = name;
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById(`sec-${name}`).classList.add('active');
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`nav-${name}`).classList.add('active');
  // FAB only on stock section
  document.getElementById('fab').classList.toggle('hidden', name !== 'stock');
  if (name === 'stock') loadStock();
  if (name === 'shopping') loadShopping();
  if (name === 'settings') loadSettings();
}

/* ════════ Modals ════════ */
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) e.target.classList.remove('open');
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
});

/* ════════ STOCK ════════ */
async function loadStock() {
  try {
    const items = await api.getItems();
    State.items = items;
    renderStats();
    renderChips();
    renderStock();
    updateShoppingBadge();
  } catch (e) {
    document.getElementById('stock-list').innerHTML = emptyState('⚠️', t('error'), '');
  }
}

function renderStats() {
  const items = State.items;
  const out = items.filter(i => i.quantity === 0).length;
  const low = items.filter(i => i.is_low && i.quantity > 0).length;
  document.getElementById('stat-total').textContent = items.length;
  document.getElementById('stat-low').textContent = low;
  document.getElementById('stat-out').textContent = out;
}

function renderChips() {
  const present = [...new Set(State.items.map(i => i.category))];
  const ordered = window.CATEGORIES.map(c => c.id).filter(id => present.includes(id));
  let html = `<button class="chip ${State.catFilter === 'all' ? 'active' : ''}" onclick="setCatFilter('all')">🗂️ ${esc(t('all_categories'))}</button>`;
  html += ordered.map(id =>
    `<button class="chip ${State.catFilter === id ? 'active' : ''}" onclick="setCatFilter('${id}')">${catEmoji(id)} ${esc(catLabel(id))}</button>`
  ).join('');
  document.getElementById('cat-chips').innerHTML = html;
}

function setCatFilter(id) {
  State.catFilter = id;
  renderChips();
  renderStock();
}

function renderStock() {
  const list = document.getElementById('stock-list');
  if (!State.items.length) {
    list.innerHTML = emptyState('🧺', t('empty_stock'), t('empty_stock_sub'),
      `<button class="btn btn-primary" onclick="openCatalog()">➕ ${esc(t('add_products'))}</button>`);
    return;
  }
  let items = State.items;
  if (State.catFilter !== 'all') items = items.filter(i => i.category === State.catFilter);

  // Group by category (keep catalog order)
  const groups = {};
  items.forEach(i => { (groups[i.category] = groups[i.category] || []).push(i); });
  const orderedCats = window.CATEGORIES.map(c => c.id).filter(id => groups[id]);

  list.innerHTML = orderedCats.map(cat => `
    <div class="cat-group">
      ${State.catFilter === 'all' ? `<div class="cat-heading">${catEmoji(cat)} ${esc(catLabel(cat))}</div>` : ''}
      ${groups[cat].map(itemRow).join('')}
    </div>
  `).join('');
}

function itemRow(i) {
  const cls = i.quantity === 0 ? 'is-out' : (i.is_low ? 'is-low' : '');
  const badge = i.quantity === 0
    ? `<span class="mini-badge out">${esc(t('out_badge'))}</span>`
    : (i.is_low ? `<span class="mini-badge low">${esc(t('low_badge'))}</span>` : '');
  return `
    <div class="stock-item ${cls}" id="item-${i.id}">
      <div class="stock-emoji" onclick="openItemEdit(${i.id})">${esc(i.emoji || '📦')}</div>
      <div class="stock-tap" onclick="openItemEdit(${i.id})">
        <div class="stock-name">${esc(i.name)} ${badge}</div>
        <div class="stock-sub">${esc(catLabel(i.category))}</div>
      </div>
      <div class="stepper">
        <button class="step-btn minus" onclick="adjustItem(${i.id}, -1)" ${i.quantity === 0 ? 'disabled' : ''}>−</button>
        <span class="step-qty" id="qty-${i.id}">${i.quantity}</span>
        <button class="step-btn plus" onclick="adjustItem(${i.id}, 1)">+</button>
      </div>
    </div>`;
}

async function adjustItem(id, delta) {
  try {
    const updated = await api.adjustItem(id, delta);
    const idx = State.items.findIndex(i => i.id === id);
    if (idx >= 0) State.items[idx] = updated;
    // Re-render just this row + stats + badges
    const row = document.getElementById(`item-${id}`);
    if (row) row.outerHTML = itemRow(updated);
    renderStats();
    updateShoppingBadge();
  } catch (e) {
    toast(t('error'), 'error');
  }
}

/* ════════ Shopping ════════ */
async function loadShopping() {
  const list = document.getElementById('shopping-list');
  const bar = document.getElementById('sync-bar');
  try {
    const items = await api.getShopping();
    if (!items.length) {
      list.innerHTML = emptyState('✅', t('empty_shopping'), t('empty_shopping_sub'));
      bar.style.display = 'none';
      return;
    }
    list.innerHTML = items.map(i => `
      <div class="shop-item" id="shop-${i.id}">
        <button class="shop-check" onclick="restockItem(${i.id})" title="${esc(t('got_it'))}">✓</button>
        <span class="shop-emoji">${esc(i.emoji || '📦')}</span>
        <div class="shop-body">
          <div class="shop-name">${esc(i.name)}</div>
          <div class="shop-sub">${esc(catLabel(i.category))} · ${i.quantity} ${esc(t('items'))}</div>
        </div>
      </div>`).join('');
    bar.style.display = State.haConnected ? 'block' : 'none';
  } catch (e) {
    list.innerHTML = emptyState('⚠️', t('error'), '');
  }
}

async function restockItem(id) {
  const item = State.items.find(i => i.id === id);
  const threshold = item ? item.low_threshold : 1;
  const qty = item ? item.quantity : 0;
  const delta = Math.max(1, (threshold + 1) - qty);
  try {
    const updated = await api.adjustItem(id, delta);
    const idx = State.items.findIndex(i => i.id === id);
    if (idx >= 0) State.items[idx] = updated; else await loadStock();
    const el = document.getElementById(`shop-${id}`);
    if (el) el.remove();
    updateShoppingBadge();
    const remaining = document.querySelectorAll('#shopping-list .shop-item').length;
    if (remaining === 0) loadShopping();
  } catch (e) {
    toast(t('error'), 'error');
  }
}

async function sendToHA() {
  const btn = document.getElementById('sync-btn');
  btn.disabled = true;
  try {
    const r = await api.syncShopping();
    if (r.synced > 0) toast(`${r.synced} ${t('sync_done')}`, 'success');
    else toast(t('sync_none_new'), 'info');
  } catch (e) {
    if (e.status === 503) toast(t('sync_not_connected'), 'error');
    else toast(t('error'), 'error');
  } finally {
    btn.disabled = false;
  }
}

function updateShoppingBadge() {
  const count = State.items.filter(i => i.is_low).length;
  const badge = document.getElementById('shopping-badge');
  badge.textContent = count;
  badge.classList.toggle('hidden', count === 0);
}

/* ════════ Catalog / add ════════ */
function openCatalog() {
  document.getElementById('catalog-search').value = '';
  renderCatalog();
  openModal('modal-catalog');
}

function renderCatalog() {
  const term = (document.getElementById('catalog-search').value || '').trim().toLowerCase();
  const existing = new Set(State.items.map(i => i.name.toLowerCase()));
  const matches = window.CATALOG.filter(p => {
    if (!term) return true;
    return p.nl.toLowerCase().includes(term) || p.en.toLowerCase().includes(term);
  });
  // group by category
  const groups = {};
  matches.forEach(p => { (groups[p.cat] = groups[p.cat] || []).push(p); });
  const cats = window.CATEGORIES.map(c => c.id).filter(id => groups[id]);
  const grid = document.getElementById('catalog-grid');
  if (!cats.length) { grid.innerHTML = `<div class="empty-state-sub" style="text-align:center;padding:20px">—</div>`; return; }
  grid.innerHTML = cats.map(cat => `
    <div class="catalog-cat-heading">${catEmoji(cat)} ${esc(catLabel(cat))}</div>
    <div class="catalog-grid">
      ${groups[cat].map(p => {
        const name = p[State.lang] || p.en;
        const added = existing.has(name.toLowerCase());
        return `<button class="catalog-item ${added ? 'added' : ''}"
                   onclick='addFromCatalog(${JSON.stringify(p).replace(/'/g, "&#39;")})'>
                  <span class="ci-emoji">${p.emoji}</span>
                  <span class="ci-name">${esc(name)}${added ? ' ✓' : ''}</span>
                </button>`;
      }).join('')}
    </div>`).join('');
}

async function addFromCatalog(p) {
  const name = p[State.lang] || p.en;
  if (State.items.some(i => i.name.toLowerCase() === name.toLowerCase())) {
    toast(`${name} ${t('already_added')}`, 'info');
    return;
  }
  try {
    const item = await api.addItem({
      name, emoji: p.emoji, category: p.cat,
      quantity: (p.th || 0) + 1, low_threshold: p.th ?? 1,
    });
    State.items.push(item);
    renderStats();
    renderChips();
    renderStock();
    updateShoppingBadge();
    renderCatalog();
    toast(`${name} ${t('item_added')}`, 'success');
  } catch (e) {
    toast(t('error'), 'error');
  }
}

/* ════════ Custom add / edit ════════ */
function fillCategorySelect(selected) {
  const sel = document.getElementById('edit-category');
  sel.innerHTML = window.CATEGORIES.map(c =>
    `<option value="${c.id}" ${c.id === selected ? 'selected' : ''}>${c.emoji} ${esc(c[State.lang] || c.en)}</option>`
  ).join('');
}

function openCustom() {
  closeModal('modal-catalog');
  State.editId = null;
  document.getElementById('edit-title').textContent = t('custom_item');
  document.getElementById('edit-icon').textContent = '✏️';
  document.getElementById('edit-emoji').value = '📦';
  document.getElementById('edit-name').value = '';
  document.getElementById('edit-threshold').value = 1;
  fillCategorySelect('other');
  document.getElementById('edit-delete').style.display = 'none';
  openModal('modal-edit');
}

function openItemEdit(id) {
  const item = State.items.find(i => i.id === id);
  if (!item) return;
  State.editId = id;
  document.getElementById('edit-title').textContent = t('edit_title');
  document.getElementById('edit-icon').textContent = item.emoji || '📦';
  document.getElementById('edit-emoji').value = item.emoji || '📦';
  document.getElementById('edit-name').value = item.name;
  document.getElementById('edit-threshold').value = item.low_threshold;
  fillCategorySelect(item.category);
  document.getElementById('edit-delete').style.display = 'block';
  openModal('modal-edit');
}

async function saveEdit() {
  const name = document.getElementById('edit-name').value.trim();
  if (!name) { toast(t('item_name'), 'error'); return; }
  const payload = {
    name,
    emoji: document.getElementById('edit-emoji').value.trim() || '📦',
    category: document.getElementById('edit-category').value,
    low_threshold: Math.max(0, parseInt(document.getElementById('edit-threshold').value, 10) || 0),
  };
  try {
    if (State.editId === null) {
      payload.quantity = payload.low_threshold + 1;
      await api.addItem(payload);
      toast(`${name} ${t('item_added')}`, 'success');
    } else {
      await api.updateItem(State.editId, payload);
      toast(t('saved'), 'success');
    }
    closeModal('modal-edit');
    await loadStock();
  } catch (e) {
    toast(t('error'), 'error');
  }
}

async function deleteEditItem() {
  if (State.editId === null) return;
  if (!confirm(t('confirm_delete'))) return;
  try {
    await api.deleteItem(State.editId);
    closeModal('modal-edit');
    toast(t('deleted'), 'info');
    await loadStock();
  } catch (e) {
    toast(t('error'), 'error');
  }
}

/* ════════ Settings ════════ */
async function loadSettings() {
  try {
    const s = State.settings || await api.getSettings();
    State.settings = s;
    document.getElementById('set-household').value = s.household_name || '';
    document.getElementById('set-language').value = s.language || 'nl';
    document.getElementById('set-autosync').checked = !!s.auto_sync_todo;
    document.getElementById('set-sensors').checked = !!s.expose_sensors;

    // Populate to-do list dropdown from HA
    const todoSel = document.getElementById('set-todo');
    const statusEl = document.getElementById('ha-status');
    const res = await api.getTodoLists();
    State.haConnected = !!res.available;
    if (!res.available) {
      statusEl.innerHTML = `<div class="form-hint" style="margin-bottom:12px">⚠️ ${esc(t('not_connected'))}</div>`;
      todoSel.innerHTML = `<option value="${esc(s.todo_entity_id || 'todo.shopping_list')}">${esc(s.todo_entity_id || 'todo.shopping_list')}</option>`;
    } else {
      statusEl.innerHTML = '';
      const lists = res.lists || [];
      if (!lists.length) {
        todoSel.innerHTML = `<option value="${esc(s.todo_entity_id || 'todo.shopping_list')}">${esc(t('no_todo_lists'))}</option>`;
      } else {
        const hasCurrent = lists.some(l => l.entity_id === s.todo_entity_id);
        todoSel.innerHTML = lists.map(l =>
          `<option value="${esc(l.entity_id)}" ${l.entity_id === s.todo_entity_id ? 'selected' : ''}>${esc(l.name)}</option>`
        ).join('') + (hasCurrent ? '' : `<option value="${esc(s.todo_entity_id)}" selected>${esc(s.todo_entity_id)}</option>`);
      }
    }
  } catch (e) {
    toast(t('error'), 'error');
  }
}

async function saveSettings() {
  const payload = {
    household_name: document.getElementById('set-household').value.trim(),
    language: document.getElementById('set-language').value,
    todo_entity_id: document.getElementById('set-todo').value,
    auto_sync_todo: document.getElementById('set-autosync').checked,
    expose_sensors: document.getElementById('set-sensors').checked,
  };
  try {
    const s = await api.saveSettings(payload);
    State.settings = s;
    setAppLang(s.language);
    updateHeader();
    toast(t('settings_saved'), 'success');
  } catch (e) {
    toast(t('error'), 'error');
  }
}

/* ════════ Language / header ════════ */
function toggleLang() { setAppLang(State.lang === 'nl' ? 'en' : 'nl'); }
function setAppLang(lang) {
  State.lang = lang;
  window.setLang(lang);
  document.documentElement.lang = lang;
  document.getElementById('lang-btn').textContent = lang === 'nl' ? 'EN' : 'NL';
  updateHeader();
  // Re-render the active section so dynamic content re-translates
  if (State.section === 'stock') { renderChips(); renderStock(); }
  if (State.section === 'shopping') loadShopping();
  if (State.section === 'settings') loadSettings();
}
function updateHeader() {
  const name = (State.settings && State.settings.household_name) || '';
  document.getElementById('header-name').textContent = name || t('app_title');
  document.getElementById('header-sub').textContent = name ? t('app_title') : '';
}

/* ════════ Init ════════ */
async function init() {
  // language: localStorage → settings → config → nl
  let lang = localStorage.getItem('hs_lang');
  await initServerTime();
  tickClock();
  setInterval(tickClock, 10000);
  try {
    const s = await api.getSettings();
    State.settings = s;
    if (!lang) lang = s.language || 'nl';
  } catch (e) { /* standalone before DB ready */ }
  setAppLang(lang || 'nl');
  updateHeader();
  await loadStock();
}

document.addEventListener('DOMContentLoaded', init);

/* small helper */
function emptyState(icon, text, sub, extra = '') {
  return `<div class="empty-state">
    <div class="empty-state-icon">${icon}</div>
    <div class="empty-state-text">${esc(text)}</div>
    ${sub ? `<div class="empty-state-sub">${esc(sub)}</div>` : ''}
    ${extra}
  </div>`;
}
