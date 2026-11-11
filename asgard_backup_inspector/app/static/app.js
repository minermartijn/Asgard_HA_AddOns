/* ASGARD Backup Inspector — Vanilla JS Client for Home Assistant Ingress
 * Fully relative pathing, robust error isolation, zero external dependencies.
 */
'use strict';

// Element selector helper
const $ = (id) => document.getElementById(id);

const FRESHNESS_CONFIG = {
  fresh: {
    label: 'Recent backup listed',
    badgeClass: 'status-fresh',
    desc: 'The most recent backup is within your freshness threshold.'
  },
  stale: {
    label: 'Backup stale',
    badgeClass: 'status-stale',
    desc: 'The most recent backup is older than your configured threshold.'
  },
  no_backups: {
    label: 'No backups found',
    badgeClass: 'status-no_backups',
    desc: 'The Supervisor reports zero backups stored in configured locations.'
  },
  unknown: {
    label: 'Status unknown',
    badgeClass: 'status-unknown',
    desc: 'Backup freshness cannot be verified due to missing dates or unconfigured API.'
  },
  unavailable: {
    label: 'Supervisor unavailable',
    badgeClass: 'status-unavailable',
    desc: 'Could not communicate with Home Assistant Supervisor.'
  },
  forbidden: {
    label: 'Permission denied',
    badgeClass: 'status-unavailable',
    desc: 'App lacks required permissions to read Supervisor backup info (403).'
  },
  partial: {
    label: 'Partial metadata',
    badgeClass: 'status-partial',
    desc: 'Backup records retrieved, but some entries could not be parsed.'
  }
};

// Safe date formatter with fallback
let dateTimeFormatter = null;
try {
  dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short'
  });
} catch (_) {
  try {
    dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (_) {
    dateTimeFormatter = null;
  }
}

function formatDate(iso) {
  if (!iso) return 'Unknown';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return 'Unknown';
    if (dateTimeFormatter) {
      return dateTimeFormatter.format(d);
    }
    return d.toLocaleString();
  } catch (err) {
    console.warn('formatDate error for', iso, err);
    return 'Unknown';
  }
}

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return 'Unknown';
  if (typeof bytes !== 'number' || Number.isNaN(bytes) || bytes < 0) return 'Unknown';
  if (bytes === 0) return '0 B';
  try {
    const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
    let val = bytes;
    let i = 0;
    while (val >= 1024 && i < units.length - 1) {
      val /= 1024;
      i += 1;
    }
    return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
  } catch (_) {
    return 'Unknown';
  }
}

function formatAge(seconds) {
  if (seconds === null || seconds === undefined || typeof seconds !== 'number' || Number.isNaN(seconds)) {
    return 'Unknown';
  }
  try {
    if (seconds < 60) return 'Just now';
    const h = seconds / 3600;
    if (h < 1) return `${Math.max(1, Math.round(seconds / 60))} min ago`;
    if (h < 48) return `${Math.round(h)} h ago`;
    return `${Math.round(h / 24)} days ago`;
  } catch (_) {
    return 'Unknown';
  }
}

function safeSetText(id, text) {
  try {
    const el = $(id);
    if (el) el.textContent = text !== undefined && text !== null ? String(text) : '–';
  } catch (err) {
    console.warn(`safeSetText error for ${id}:`, err);
  }
}

async function getJSON(path, options = {}) {
  try {
    const res = await fetch(path, { credentials: 'same-origin', ...options });
    let body = null;
    try {
      body = await res.json();
    } catch (_) {
      /* non-JSON payload */
    }
    return { ok: res.ok, status: res.status, body };
  } catch (netErr) {
    console.warn(`Fetch error for ${path}:`, netErr);
    return { ok: false, status: 0, body: null, error: netErr };
  }
}

// State
let allBackups = [];
let currentSummary = null;
let currentPage = 1;
let pageSize = 25;
let currentSort = 'date-desc';
let filterType = 'all';
let filterLocation = 'all';
let filterProtection = 'all';
let searchKeyword = '';

function renderSummary(s) {
  currentSummary = s;

  // Demo Banner
  try {
    const demoEl = $('demo-banner');
    if (demoEl) demoEl.hidden = !s.demo_mode;
  } catch (_) {}

  // Health Card
  try {
    const cfg = FRESHNESS_CONFIG[s.freshness] || FRESHNESS_CONFIG[s.api_status] || FRESHNESS_CONFIG.unknown;
    safeSetText('freshness', cfg.label);
    const badge = $('freshness-badge');
    if (badge) {
      badge.textContent = s.freshness ? s.freshness.toUpperCase() : 'UNKNOWN';
      badge.className = `status-badge ${cfg.badgeClass}`;
    }
    safeSetText('freshness-hint', cfg.desc + (s.stale_threshold_hours ? ` Threshold: ${s.stale_threshold_hours}h.` : ''));
  } catch (err) {
    console.error('Error rendering health card:', err);
  }

  // Count Card
  try {
    safeSetText('count', String(s.total_count ?? 0));
    const fullCount = s.full_backup_count ?? 0;
    const partialCount = s.partial_backup_count ?? 0;
    safeSetText('count-breakdown', `${fullCount} full · ${partialCount} partial`);
  } catch (err) {
    console.error('Error rendering count card:', err);
  }

  // Newest Backup Card
  try {
    safeSetText('newest', formatAge(s.newest_backup_age_seconds));
    safeSetText('newest-date', s.newest_backup_utc ? formatDate(s.newest_backup_utc) : 'No date reported');
  } catch (err) {
    console.error('Error rendering newest backup card:', err);
  }

  // Storage Card
  try {
    safeSetText('storage', formatBytes(s.known_size_total_bytes));
    if (s.unknown_size_count && s.unknown_size_count > 0) {
      safeSetText('storage-hint', `${s.unknown_size_count} backup(s) with unknown size not included`);
    } else {
      safeSetText('storage-hint', 'All backup sizes reported');
    }
  } catch (err) {
    console.error('Error rendering storage card:', err);
  }

  // Error Banner & Cached Banner
  try {
    const errBanner = $('error-banner');
    const cachedBanner = $('cached-banner');
    if (s.error_message) {
      if (errBanner) {
        errBanner.textContent = s.error_message;
        errBanner.hidden = false;
      }
    } else if (errBanner) {
      errBanner.hidden = true;
    }

    if (cachedBanner) {
      if (s.showing_cached_data) {
        cachedBanner.textContent = `Showing cached data from previous successful check (${s.last_success_utc ? formatDate(s.last_success_utc) : 'prior check'}).`;
        cachedBanner.hidden = false;
      } else {
        cachedBanner.hidden = true;
      }
    }
  } catch (_) {}

  // Warnings
  try {
    const warnEl = $('warnings');
    if (warnEl) {
      warnEl.replaceChildren();
      if (s.warnings && s.warnings.length > 0) {
        s.warnings.forEach((w) => {
          const p = document.createElement('p');
          p.textContent = w;
          warnEl.appendChild(p);
        });
        warnEl.hidden = false;
      } else {
        warnEl.hidden = true;
      }
    }
  } catch (_) {}

  // Diagnostics Panel Values
  try {
    safeSetText('diag-api', s.api_status ? s.api_status.toUpperCase() : 'UNKNOWN');
    safeSetText('diag-threshold', `${s.stale_threshold_hours || 48} hours`);
    safeSetText('diag-supervisor-stale', s.supervisor_days_until_stale ? `${s.supervisor_days_until_stale} days` : 'Not configured');
    safeSetText('diag-last-success', s.last_success_utc ? formatDate(s.last_success_utc) : 'Never');
  } catch (_) {}

  // Last Checked
  try {
    safeSetText('last-checked', s.last_checked_utc ? `Last checked: ${formatDate(s.last_checked_utc)}` : 'Not checked yet');
    const cardsEl = $('cards');
    if (cardsEl) cardsEl.setAttribute('aria-busy', 'false');
  } catch (_) {}
}

function renderVisualizations(backups, summary) {
  if (!backups || !Array.isArray(backups)) return;

  // 1. Storage Breakdown by Type
  try {
    let fullBytes = 0;
    let partialBytes = 0;
    const locationsMap = {};

    backups.forEach((b) => {
      const sz = typeof b.size_bytes === 'number' && b.size_bytes > 0 ? b.size_bytes : 0;
      if (b.backup_type === 'full') {
        fullBytes += sz;
      } else if (b.backup_type === 'partial') {
        partialBytes += sz;
      }
      const locs = b.locations && b.locations.length ? b.locations : [b.location || '.local'];
      locs.forEach((loc) => {
        const lName = loc || '.local';
        locationsMap[lName] = (locationsMap[lName] || 0) + 1;
      });
    });

    const totalTypeBytes = fullBytes + partialBytes;
    const fullPct = totalTypeBytes > 0 ? Math.round((fullBytes / totalTypeBytes) * 100) : 50;
    const partialPct = 100 - fullPct;

    const barFull = $('bar-full');
    const barPartial = $('bar-partial');
    if (barFull) {
      barFull.style.width = `${fullPct}%`;
      barFull.title = `Full: ${formatBytes(fullBytes)} (${fullPct}%)`;
    }
    if (barPartial) {
      barPartial.style.width = `${partialPct}%`;
      barPartial.title = `Partial: ${formatBytes(partialBytes)} (${partialPct}%)`;
    }
    safeSetText('full-storage-label', `Full: ${formatBytes(fullBytes)}`);
    safeSetText('partial-storage-label', `Partial: ${formatBytes(partialBytes)}`);

    // Storage Locations badges
    const locsContainer = $('storage-locations');
    if (locsContainer) {
      locsContainer.replaceChildren();
      Object.entries(locationsMap).forEach(([loc, count]) => {
        const span = document.createElement('span');
        span.className = 'loc-badge';
        span.textContent = `${loc} (${count})`;
        locsContainer.appendChild(span);
      });
    }

    // Populate Location Filter Dropdown if needed
    const filterLocEl = $('filter-location');
    if (filterLocEl && filterLocEl.options.length <= 1) {
      Object.keys(locationsMap).sort().forEach((loc) => {
        const opt = document.createElement('option');
        opt.value = loc;
        opt.textContent = `Location: ${loc}`;
        filterLocEl.appendChild(opt);
      });
    }
  } catch (err) {
    console.error('Error rendering storage visualization:', err);
  }

  // 2. Timeline Visualization
  try {
    const track = $('timeline-track');
    if (track) {
      track.replaceChildren();
      // Take up to 10 most recent backups
      const recent = backups.slice(0, 10);
      if (recent.length === 0) {
        const p = document.createElement('p');
        p.className = 'hint';
        p.textContent = 'No backups listed.';
        track.appendChild(p);
      } else {
        recent.forEach((b) => {
          const item = document.createElement('div');
          const isFull = b.backup_type === 'full';
          item.className = `timeline-item ${isFull ? 'timeline-full' : 'timeline-partial'}`;

          const ageSpan = document.createElement('span');
          ageSpan.className = 'timeline-age';
          const created = b.created_utc ? new Date(b.created_utc) : null;
          const ageSec = created ? Math.max(0, (Date.now() - created.getTime()) / 1000) : null;
          ageSpan.textContent = formatAge(ageSec);

          const nameSpan = document.createElement('span');
          nameSpan.className = 'timeline-name';
          nameSpan.textContent = b.name || b.id || 'Backup';
          nameSpan.title = b.name || b.id;

          const sizeSpan = document.createElement('span');
          sizeSpan.className = 'hint';
          sizeSpan.textContent = `${isFull ? 'Full' : 'Partial'} · ${formatBytes(b.size_bytes)}`;

          item.appendChild(ageSpan);
          item.appendChild(nameSpan);
          item.appendChild(sizeSpan);
          track.appendChild(item);
        });
      }
    }
  } catch (err) {
    console.error('Error rendering timeline:', err);
  }
}

function renderHistory(entries) {
  try {
    const countTag = $('history-points-count');
    const emptyMsg = $('history-empty');
    const chartWrap = $('history-chart');
    const svg = $('history-svg');

    if (!entries || !Array.isArray(entries) || entries.length === 0) {
      if (countTag) countTag.textContent = '0 recorded';
      if (emptyMsg) emptyMsg.hidden = false;
      if (chartWrap) chartWrap.hidden = true;
      return;
    }

    if (countTag) countTag.textContent = `${entries.length} recorded`;

    if (entries.length < 2) {
      if (emptyMsg) {
        emptyMsg.textContent = `1 measurement recorded (${formatDate(entries[0].recorded_utc)}). Trend line will appear as subsequent checks occur.`;
        emptyMsg.hidden = false;
      }
      if (chartWrap) chartWrap.hidden = true;
      return;
    }

    if (emptyMsg) emptyMsg.hidden = true;
    if (chartWrap) chartWrap.hidden = false;

    // Draw clean SVG sparkline
    if (svg) {
      svg.replaceChildren();
      const width = 600;
      const height = 120;
      const padX = 20;
      const padY = 20;

      const maxVal = Math.max(...entries.map((e) => e.known_size_bytes || 0), 1024 * 1024);
      const minVal = Math.min(...entries.map((e) => e.known_size_bytes || 0), 0);
      const valRange = maxVal - minVal || 1;

      const points = entries.map((e, idx) => {
        const x = padX + (idx / (entries.length - 1)) * (width - padX * 2);
        const y = height - padY - (( (e.known_size_bytes || 0) - minVal) / valRange) * (height - padY * 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(' ');

      // Polyline
      const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
      polyline.setAttribute('points', points);
      polyline.setAttribute('fill', 'none');
      polyline.setAttribute('stroke', '#3b82f6');
      polyline.setAttribute('stroke-width', '3');
      polyline.setAttribute('stroke-linecap', 'round');
      polyline.setAttribute('stroke-linejoin', 'round');
      svg.appendChild(polyline);

      // Dots on last and first
      [0, entries.length - 1].forEach((idx) => {
        const e = entries[idx];
        const x = padX + (idx / (entries.length - 1)) * (width - padX * 2);
        const y = height - padY - (( (e.known_size_bytes || 0) - minVal) / valRange) * (height - padY * 2);
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', x.toFixed(1));
        circle.setAttribute('cy', y.toFixed(1));
        circle.setAttribute('r', '4');
        circle.setAttribute('fill', '#d4a843');
        svg.appendChild(circle);
      });
    }
  } catch (err) {
    console.error('Error rendering history chart:', err);
  }
}

function getFilteredAndSortedBackups() {
  let list = allBackups.slice();

  // Keyword filter
  if (searchKeyword) {
    const q = searchKeyword.toLowerCase();
    list = list.filter((b) => {
      const name = (b.name || '').toLowerCase();
      const id = (b.id || '').toLowerCase();
      const loc = (b.location || '').toLowerCase();
      const locs = (b.locations || []).join(' ').toLowerCase();
      return name.includes(q) || id.includes(q) || loc.includes(q) || locs.includes(q);
    });
  }

  // Type filter
  if (filterType !== 'all') {
    list = list.filter((b) => b.backup_type === filterType);
  }

  // Location filter
  if (filterLocation !== 'all') {
    list = list.filter((b) => {
      if (b.locations && b.locations.length) {
        return b.locations.includes(filterLocation);
      }
      return (b.location || '.local') === filterLocation;
    });
  }

  // Protection filter
  if (filterProtection === 'protected') {
    list = list.filter((b) => b.protected === true);
  } else if (filterProtection === 'unprotected') {
    list = list.filter((b) => b.protected === false);
  }

  // Sort
  list.sort((a, b) => {
    if (currentSort === 'date-desc') {
      const da = a.created_utc ? new Date(a.created_utc).getTime() : 0;
      const db = b.created_utc ? new Date(b.created_utc).getTime() : 0;
      return db - da;
    }
    if (currentSort === 'date-asc') {
      const da = a.created_utc ? new Date(a.created_utc).getTime() : 0;
      const db = b.created_utc ? new Date(b.created_utc).getTime() : 0;
      return da - db;
    }
    if (currentSort === 'size-desc') {
      const sa = typeof a.size_bytes === 'number' ? a.size_bytes : -1;
      const sb = typeof b.size_bytes === 'number' ? b.size_bytes : -1;
      return sb - sa;
    }
    if (currentSort === 'size-asc') {
      const sa = typeof a.size_bytes === 'number' ? a.size_bytes : Infinity;
      const sb = typeof b.size_bytes === 'number' ? b.size_bytes : Infinity;
      return sa - sb;
    }
    if (currentSort === 'name-asc') {
      const na = (a.name || a.id || '').toLowerCase();
      const nb = (b.name || b.id || '').toLowerCase();
      return na.localeCompare(nb);
    }
    return 0;
  });

  return list;
}

function renderTable() {
  try {
    const filtered = getFilteredAndSortedBackups();
    const rowsEl = $('backup-rows');
    const tableEl = $('backup-table');
    const emptyEl = $('empty');
    const noResultsEl = $('no-filter-results');
    const paginationBar = $('pagination-bar');
    const pageInfo = $('page-info');
    const prevBtn = $('btn-prev-page');
    const nextBtn = $('btn-next-page');

    if (!rowsEl || !tableEl) return;

    rowsEl.replaceChildren();

    // Check zero state
    if (allBackups.length === 0) {
      tableEl.hidden = true;
      if (emptyEl) emptyEl.hidden = false;
      if (noResultsEl) noResultsEl.hidden = true;
      if (paginationBar) paginationBar.hidden = true;
      return;
    }

    if (emptyEl) emptyEl.hidden = true;

    if (filtered.length === 0) {
      tableEl.hidden = true;
      if (noResultsEl) noResultsEl.hidden = false;
      if (paginationBar) paginationBar.hidden = true;
      return;
    }

    if (noResultsEl) noResultsEl.hidden = true;
    tableEl.hidden = false;

    // Pagination calculations
    const totalFiltered = filtered.length;
    const effectivePageSize = pageSize === 'all' ? totalFiltered : Number(pageSize);
    const maxPage = Math.max(1, Math.ceil(totalFiltered / effectivePageSize));

    if (currentPage > maxPage) currentPage = maxPage;
    if (currentPage < 1) currentPage = 1;

    const startIdx = (currentPage - 1) * effectivePageSize;
    const endIdx = Math.min(startIdx + effectivePageSize, totalFiltered);
    const pageItems = filtered.slice(startIdx, endIdx);

    // Update Pagination Controls
    if (paginationBar) {
      paginationBar.hidden = false;
      if (pageInfo) {
        pageInfo.textContent = `Showing ${startIdx + 1}–${endIdx} of ${totalFiltered} backup${totalFiltered === 1 ? '' : 's'}`;
      }
      if (prevBtn) prevBtn.disabled = currentPage <= 1;
      if (nextBtn) nextBtn.disabled = currentPage >= maxPage;
    }

    const now = Date.now();

    pageItems.forEach((b) => {
      const tr = document.createElement('tr');

      // 1. Lock column
      const tdLock = document.createElement('td');
      tdLock.className = 'th-protect';
      if (b.protected === true) {
        tdLock.innerHTML = '<span class="lock-icon lock-yes" title="Password protected">&#128274;</span>';
      } else if (b.protected === false) {
        tdLock.innerHTML = '<span class="lock-icon lock-no" title="Unprotected">&#128275;</span>';
      } else {
        tdLock.innerHTML = '<span class="hint" title="Protection unknown">?</span>';
      }
      tr.appendChild(tdLock);

      // 2. Created date
      const tdDate = document.createElement('td');
      tdDate.textContent = formatDate(b.created_utc);
      tr.appendChild(tdDate);

      // 3. Age
      const tdAge = document.createElement('td');
      const created = b.created_utc ? new Date(b.created_utc) : null;
      const ageSec = created ? Math.max(0, (now - created.getTime()) / 1000) : null;
      tdAge.textContent = formatAge(ageSec);
      tr.appendChild(tdAge);

      // 4. Name & ID
      const tdName = document.createElement('td');
      const nameDiv = document.createElement('div');
      nameDiv.className = 'backup-title';
      nameDiv.textContent = b.name || 'Unnamed Backup';
      const idDiv = document.createElement('div');
      idDiv.className = 'backup-id';
      idDiv.textContent = b.id;
      tdName.appendChild(nameDiv);
      tdName.appendChild(idDiv);
      tr.appendChild(tdName);

      // 5. Type
      const tdType = document.createElement('td');
      const typeSpan = document.createElement('span');
      const isFull = b.backup_type === 'full';
      typeSpan.className = `type-badge ${isFull ? 'type-full' : 'type-partial'}`;
      typeSpan.textContent = b.backup_type || 'Unknown';
      tdType.appendChild(typeSpan);
      tr.appendChild(tdType);

      // 6. Size
      const tdSize = document.createElement('td');
      if (typeof b.size_bytes === 'number') {
        tdSize.textContent = formatBytes(b.size_bytes);
      } else {
        const unkSpan = document.createElement('span');
        unkSpan.className = 'hint';
        unkSpan.textContent = 'Unknown';
        tdSize.appendChild(unkSpan);
      }
      tr.appendChild(tdSize);

      // 7. Locations
      const tdLoc = document.createElement('td');
      const locList = b.locations && b.locations.length ? b.locations : [b.location || '.local'];
      locList.forEach((l) => {
        const lSpan = document.createElement('span');
        lSpan.className = 'loc-badge';
        lSpan.textContent = l || '.local';
        tdLoc.appendChild(lSpan);
      });
      tr.appendChild(tdLoc);

      rowsEl.appendChild(tr);
    });
  } catch (err) {
    console.error('Error rendering backup table:', err);
  }
}

async function load() {
  try {
    // 1. Fetch summary
    const s = await getJSON('api/summary');
    if (!s.ok || !s.body) {
      const errBanner = $('error-banner');
      if (errBanner) {
        errBanner.textContent = `Could not load backup summary (HTTP ${s.status}). Check Supervisor connection.`;
        errBanner.hidden = false;
      }
      return;
    }

    renderSummary(s.body);

    // 2. Fetch all backups for client-side search/sort/filter
    const b = await getJSON('api/backups?limit=1000');
    if (b.ok && b.body && Array.isArray(b.body.items)) {
      allBackups = b.body.items;
      renderVisualizations(allBackups, s.body);
      renderTable();
    } else {
      console.warn('Could not load backups list or format invalid:', b);
    }

    // 3. Fetch history trends
    const h = await getJSON('api/history');
    if (h.ok && h.body && Array.isArray(h.body.entries)) {
      renderHistory(h.body.entries);
    }
  } catch (err) {
    console.error('Unhandled load() exception:', err);
    const errBanner = $('error-banner');
    if (errBanner) {
      errBanner.textContent = `Unexpected error loading dashboard: ${err && err.message ? err.message : String(err)}`;
      errBanner.hidden = false;
    }
  }
}

async function refresh() {
  const btn = $('refresh');
  if (!btn) return;

  btn.disabled = true;
  const originalText = 'Refresh';

  try {
    const r = await getJSON('api/refresh', { method: 'POST' });
    if (r.status === 429) {
      const wait = r.body && r.body.retry_after_seconds ? r.body.retry_after_seconds : 10;
      let remaining = wait;
      safeSetText('cached-banner', `Rate limit active: Please wait ${remaining}s before refreshing again.`);
      $('cached-banner').hidden = false;
      const interval = setInterval(() => {
        remaining -= 1;
        if (remaining > 0) {
          btn.textContent = `Wait ${remaining}s`;
        } else {
          clearInterval(interval);
          btn.textContent = originalText;
          btn.disabled = false;
          $('cached-banner').hidden = true;
        }
      }, 1000);
      return;
    }
    await load();
  } catch (err) {
    console.error('Refresh failed:', err);
  } finally {
    if (!btn.textContent.startsWith('Wait')) {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }
}

// Bind UI Events
document.addEventListener('DOMContentLoaded', () => {
  // Refresh button
  const refreshBtn = $('refresh');
  if (refreshBtn) refreshBtn.addEventListener('click', refresh);

  // Diagnostics toggle
  const diagBtn = $('toggle-diagnostics');
  const closeDiagBtn = $('close-diagnostics');
  const diagPanel = $('diagnostics-panel');
  if (diagBtn && diagPanel) {
    diagBtn.addEventListener('click', () => {
      diagPanel.hidden = !diagPanel.hidden;
    });
  }
  if (closeDiagBtn && diagPanel) {
    closeDiagBtn.addEventListener('click', () => {
      diagPanel.hidden = true;
    });
  }

  // Search input
  const searchInput = $('table-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchKeyword = e.target.value.trim();
      currentPage = 1;
      renderTable();
    });
  }

  // Filter Type
  const filterTypeEl = $('filter-type');
  if (filterTypeEl) {
    filterTypeEl.addEventListener('change', (e) => {
      filterType = e.target.value;
      currentPage = 1;
      renderTable();
    });
  }

  // Filter Location
  const filterLocEl = $('filter-location');
  if (filterLocEl) {
    filterLocEl.addEventListener('change', (e) => {
      filterLocation = e.target.value;
      currentPage = 1;
      renderTable();
    });
  }

  // Filter Protection
  const filterProtEl = $('filter-protection');
  if (filterProtEl) {
    filterProtEl.addEventListener('change', (e) => {
      filterProtection = e.target.value;
      currentPage = 1;
      renderTable();
    });
  }

  // Sort select
  const sortSelect = $('sort-order');
  if (sortSelect) {
    sortSelect.addEventListener('change', (e) => {
      currentSort = e.target.value;
      renderTable();
    });
  }

  // Table header sorting clicks
  document.querySelectorAll('th.sortable').forEach((th) => {
    th.addEventListener('click', () => {
      const field = th.dataset.sort;
      if (field === 'date') {
        currentSort = currentSort === 'date-desc' ? 'date-asc' : 'date-desc';
      } else if (field === 'size') {
        currentSort = currentSort === 'size-desc' ? 'size-asc' : 'size-desc';
      } else if (field === 'name') {
        currentSort = currentSort === 'name-asc' ? 'name-desc' : 'name-asc';
      } else if (field === 'type') {
        currentSort = currentSort === 'type-asc' ? 'type-desc' : 'type-asc';
      }
      if (sortSelect) sortSelect.value = currentSort;
      renderTable();
    });
  });

  // Page size select
  const pageSizeEl = $('page-size');
  if (pageSizeEl) {
    pageSizeEl.addEventListener('change', (e) => {
      pageSize = e.target.value;
      currentPage = 1;
      renderTable();
    });
  }

  // Pagination Prev / Next
  const prevBtn = $('btn-prev-page');
  const nextBtn = $('btn-next-page');
  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage -= 1;
        renderTable();
      }
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      currentPage += 1;
      renderTable();
    });
  }

  // Kick off initial load
  load();
});
