/* ASGARD Backup Inspector — vanilla JS, served under Home Assistant Ingress.
 * Every request uses a RELATIVE URL ("api/..."), never "/api/...", so it
 * resolves under whatever /api/hassio_ingress/<token>/ prefix HA assigns. */
'use strict';

const $ = (id) => document.getElementById(id);

const FRESHNESS_LABEL = {
  fresh: 'Recent backup listed',
  stale: 'Stale',
  no_backups: 'No backups found',
  unknown: 'Unknown',
};

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return 'Unknown';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = bytes;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) { value /= 1024; i += 1; }
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatAge(seconds) {
  if (seconds === null || seconds === undefined) return 'Unknown';
  const h = seconds / 3600;
  if (h < 1) return `${Math.max(1, Math.round(seconds / 60))} min ago`;
  if (h < 48) return `${Math.round(h)} h ago`;
  return `${Math.round(h / 24)} days ago`;
}

function formatDate(iso) {
  if (!iso) return 'Unknown';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'Unknown';
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short', timeZoneName: 'short' });
}

function setText(id, text) { $(id).textContent = text; }

async function getJSON(path, options) {
  const res = await fetch(path, { credentials: 'same-origin', ...options });
  let body = null;
  try { body = await res.json(); } catch (_) { /* non-JSON */ }
  return { ok: res.ok, status: res.status, body };
}

function renderSummary(s) {
  $('demo-banner').hidden = !s.demo_mode;

  const freshEl = $('freshness');
  freshEl.textContent = FRESHNESS_LABEL[s.freshness] || 'Unknown';
  freshEl.className = `value status-${s.freshness}`;
  setText('freshness-hint', `Threshold: ${s.stale_threshold_hours} h`);

  setText('count', String(s.total_count));
  setText('newest', formatAge(s.newest_backup_age_seconds));
  setText('newest-date', s.newest_backup_utc ? formatDate(s.newest_backup_utc) : '');
  setText('storage', formatBytes(s.known_size_total_bytes));
  setText('storage-hint', s.unknown_size_count ? `${s.unknown_size_count} backup(s) with unknown size not included` : '');

  const err = $('error-banner');
  if (s.error_message) {
    err.textContent = s.showing_cached_data
      ? `${s.error_message} Showing data from the last successful check.`
      : s.error_message;
    err.hidden = false;
  } else {
    err.hidden = true;
  }

  const warn = $('warnings');
  warn.replaceChildren();
  (s.warnings || []).forEach((w) => {
    const p = document.createElement('p');
    p.textContent = w;
    warn.appendChild(p);
  });
  warn.hidden = !(s.warnings && s.warnings.length);

  setText('last-checked', s.last_checked_utc ? `Last checked: ${formatDate(s.last_checked_utc)}` : 'Not checked yet');
  $('cards').setAttribute('aria-busy', 'false');
}

function renderBackups(page, summary) {
  const rows = $('backup-rows');
  rows.replaceChildren();
  const hasData = page.items.length > 0;
  $('backup-table').hidden = !hasData;
  $('empty').hidden = hasData || summary.freshness !== 'no_backups';
  const now = Date.now();
  page.items.forEach((b) => {
    const tr = document.createElement('tr');
    const created = b.created_utc ? new Date(b.created_utc) : null;
    const age = created ? Math.max(0, (now - created.getTime()) / 1000) : null;
    const cells = [
      formatDate(b.created_utc),
      formatAge(age),
      b.name || 'Unnamed',
      b.backup_type || 'Unknown',
      formatBytes(b.size_bytes),
      b.protected === null ? 'Unknown' : (b.protected ? 'Yes' : 'No'),
      b.locations.length ? b.locations.join(', ') : (b.location || 'Unknown'),
    ];
    cells.forEach((text) => {
      const td = document.createElement('td');
      td.textContent = text; // textContent: never interpret backup names as HTML
      tr.appendChild(td);
    });
    rows.appendChild(tr);
  });
}

async function load() {
  const s = await getJSON('api/summary');
  if (!s.ok || !s.body) {
    $('error-banner').textContent = `Could not load the dashboard (HTTP ${s.status}).`;
    $('error-banner').hidden = false;
    return;
  }
  renderSummary(s.body);
  const b = await getJSON('api/backups?limit=200');
  if (b.ok && b.body) renderBackups(b.body, s.body);
}

async function refresh() {
  const btn = $('refresh');
  btn.disabled = true;
  try {
    const r = await getJSON('api/refresh', { method: 'POST' });
    if (r.status === 429) {
      btn.textContent = `Wait ${r.body?.retry_after_seconds ?? ''}s`;
      setTimeout(() => { btn.textContent = 'Refresh'; }, 2000);
    }
    await load();
  } finally {
    btn.disabled = false;
  }
}

$('refresh').addEventListener('click', refresh);
load();
