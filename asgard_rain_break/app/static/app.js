/**
 * ASGARD RainBreak — Frontend Application (Home Assistant Ingress-safe)
 */
(function () {
  'use strict';

  const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const ACTIVITY_ICONS = {
    walk: '🚶 Walk',
    bike: '🚲 Bike Ride',
    run: '🏃 Run',
    break: '☕ Outdoor Break',
  };

  const CITY_PRESETS = [
    { name: 'Amsterdam (NL)', lat: 52.3676, lon: 4.9041 },
    { name: 'Utrecht (NL)', lat: 52.0907, lon: 5.1214 },
    { name: 'Rotterdam (NL)', lat: 51.9244, lon: 4.4777 },
    { name: 'Eindhoven (NL)', lat: 51.4416, lon: 5.4697 },
    { name: 'Groningen (NL)', lat: 53.2194, lon: 6.5665 },
    { name: 'Antwerp (BE)', lat: 51.2194, lon: 4.4025 },
    { name: 'Brussels (BE)', lat: 50.8503, lon: 4.3517 },
  ];

  // --- Centralized Ingress-Safe API URL Resolver ---
  function getApiUrl(endpoint) {
    const clean = String(endpoint || '').replace(/^\/+/, '');
    const baseEl = document.querySelector('base');
    if (baseEl && baseEl.href) {
      const baseHref = baseEl.href.endsWith('/') ? baseEl.href : `${baseEl.href}/`;
      return new URL(clean, baseHref).toString();
    }
    let pathname = window.location.pathname || '/';
    if (!pathname.endsWith('/')) {
      pathname = `${pathname}/`;
    }
    const baseOriginPath = `${window.location.origin}${pathname}`;
    return new URL(clean, baseOriginPath).toString();
  }

  function escapeHtml(val) {
    if (val === null || val === undefined) return '';
    const d = document.createElement('div');
    d.textContent = String(val);
    return d.innerHTML;
  }

  function formatDays(days) {
    if (!Array.isArray(days) || days.length === 0) return 'No days';
    if (days.length === 7) return 'Every day';
    const sorted = [...days].sort((a, b) => a - b);
    if (sorted.join(',') === '0,1,2,3,4') return 'Mon–Fri (Workdays)';
    if (sorted.join(',') === '5,6') return 'Sat–Sun (Weekend)';
    return sorted.map((d) => DAY_NAMES[d] || d).join(', ');
  }

  function formatTimestamp(isoStr) {
    if (!isoStr) return '-';
    try {
      const dt = new Date(isoStr);
      return dt.toLocaleString([], {
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return String(isoStr);
    }
  }

  // --- Application State ---
  const state = {
    overview: null,
    config: null,
    discovered: { persons: [], zones: [], notify_actions: [] },
    locations: [],
    users: [],
    breaks: [],
    forecasts: [],
    evaluations: [],
    recentAlerts: [],
    selectedForecastLocationId: null,
  };

  // --- DOM References ---
  const el = {
    haStatusBadge: document.getElementById('ha-status-badge'),
    btnSyncHa: document.getElementById('btn-sync-ha'),
    btnRefreshNow: document.getElementById('btn-refresh-now'),
    statusBanner: document.getElementById('status-banner'),
    tabs: document.querySelectorAll('.tab-btn'),
    tabPanes: document.querySelectorAll('.tab-pane'),

    // Dashboard
    statUsersBadge: document.getElementById('stat-users-badge'),
    statUsersValue: document.getElementById('stat-users-value'),
    statUsersHint: document.getElementById('stat-users-hint'),
    statRadarBadge: document.getElementById('stat-radar-badge'),
    statRadarValue: document.getElementById('stat-radar-value'),
    statRadarHint: document.getElementById('stat-radar-hint'),
    statBreaksBadge: document.getElementById('stat-breaks-badge'),
    statBreaksValue: document.getElementById('stat-breaks-value'),
    statBreaksHint: document.getElementById('stat-breaks-hint'),
    statChannelsBadge: document.getElementById('stat-channels-badge'),
    statChannelsValue: document.getElementById('stat-channels-value'),
    statChannelsHint: document.getElementById('stat-channels-hint'),
    dashBreakEvaluations: document.getElementById('dashboard-break-evaluations'),
    forecastLocationPills: document.getElementById('forecast-location-pills'),
    forecastSummaryBar: document.getElementById('forecast-summary-bar'),
    forecastTimelineContainer: document.getElementById('forecast-timeline-container'),
    btnDashAddBreak: document.getElementById('btn-dash-add-break'),
    btnEvaluateAll: document.getElementById('btn-evaluate-all'),

    // Breaks
    breaksList: document.getElementById('breaks-list'),
    btnPresetCommute: document.getElementById('btn-preset-commute'),
    btnPresetWorkday: document.getElementById('btn-preset-workday'),
    btnAddBreak: document.getElementById('btn-add-break'),

    // Users
    usersList: document.getElementById('users-list'),
    btnUsersSyncHa: document.getElementById('btn-users-sync-ha'),
    btnAddUser: document.getElementById('btn-add-user'),

    // Locations
    locationsList: document.getElementById('locations-list'),
    discoveredHaEntities: document.getElementById('discovered-ha-entities'),
    btnAddLocation: document.getElementById('btn-add-location'),

    // Settings & Audit
    configForm: document.getElementById('config-form'),
    cfgWeatherProvider: document.getElementById('cfg-weather-provider'),
    cfgRainThreshold: document.getElementById('cfg-rain-threshold'),
    cfgHeavyThreshold: document.getElementById('cfg-heavy-threshold'),
    cfgTimezone: document.getElementById('cfg-timezone'),
    cfgDedupMinutes: document.getElementById('cfg-dedup-minutes'),
    cfgPushoverToken: document.getElementById('cfg-pushover-token'),
    cfgBgMonitoring: document.getElementById('cfg-bg-monitoring'),
    simButtons: document.querySelectorAll('.sim-btn'),
    quickTestForm: document.getElementById('quick-test-form'),
    testUserId: document.getElementById('test-user-id'),
    testUrgency: document.getElementById('test-urgency'),
    testCustomMsg: document.getElementById('test-custom-msg'),
    btnClearHistory: document.getElementById('btn-clear-history'),
    historyTbody: document.getElementById('history-tbody'),
    historyCards: document.getElementById('history-cards'),

    // Modal
    appModal: document.getElementById('app-modal'),
    modalTitle: document.getElementById('modal-title'),
    modalBody: document.getElementById('modal-body'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
  };

  // --- Banner Helper ---
  let bannerTimer = null;
  function showBanner(message, type = 'info', durationMs = 7000) {
    if (!el.statusBanner) return;
    el.statusBanner.className = `banner banner-${type}`;
    el.statusBanner.textContent = message;
    el.statusBanner.hidden = false;
    if (bannerTimer) clearTimeout(bannerTimer);
    if (durationMs > 0) {
      bannerTimer = setTimeout(() => {
        el.statusBanner.hidden = true;
      }, durationMs);
    }
  }

  // --- API Helpers ---
  async function apiGet(endpoint) {
    const url = getApiUrl(endpoint);
    const res = await fetch(url, { credentials: 'same-origin' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  async function apiPost(endpoint, body) {
    const url = getApiUrl(endpoint);
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  async function apiDelete(endpoint) {
    const url = getApiUrl(endpoint);
    const res = await fetch(url, { method: 'DELETE', credentials: 'same-origin' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  // --- Modal Helpers (Protected against native <select> option clicks closing backdrop) ---
  function openModal(title, html) {
    el.modalTitle.textContent = title;
    el.modalBody.innerHTML = html;
    el.appModal.showModal();
  }

  function closeModal() {
    if (el.appModal && el.appModal.open) {
      el.appModal.close();
    }
    if (el.modalBody) {
      el.modalBody.innerHTML = '';
    }
  }

  if (el.modalCloseBtn) {
    el.modalCloseBtn.addEventListener('click', closeModal);
  }
  if (el.appModal) {
    el.appModal.addEventListener('click', (e) => {
      if (e.target.closest('.modal-content')) return;
      if (e.target === el.appModal) closeModal();
    });
  }

  // --- Tab Navigation ---
  function initTabs() {
    el.tabs.forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = btn.getAttribute('data-tab');
        el.tabs.forEach((t) => {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
        });
        el.tabPanes.forEach((p) => {
          p.classList.remove('active');
          p.hidden = true;
        });
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
        const pane = document.getElementById(target);
        if (pane) {
          pane.classList.add('active');
          pane.hidden = false;
        }
      });
    });
  }

  // --- Render Functions ---
  function renderHeaderAndStats() {
    if (state.overview && state.overview.ha_connected) {
      el.haStatusBadge.className = 'status-pill status-ok';
      el.haStatusBadge.textContent = state.overview.demo_mode ? 'DEMO RADAR' : 'HA CONNECTED';
    } else {
      el.haStatusBadge.className = 'status-pill status-warn';
      el.haStatusBadge.textContent = 'STANDALONE';
    }

    const totalUsers = state.users.length;
    const activeUsers = state.users.filter((u) => u.enabled);
    el.statUsersBadge.textContent = `${activeUsers.length} Active`;
    el.statUsersBadge.className = `badge ${activeUsers.length > 0 ? 'badge-success' : 'badge-warning'}`;
    el.statUsersValue.textContent = `${activeUsers.length} / ${totalUsers} Users`;
    el.statUsersHint.textContent =
      activeUsers.length > 0
        ? `Active: ${activeUsers.map((u) => u.name).join(', ')}`
        : 'Enable a user profile to start alerts';

    // Radar summary
    const wetForecasts = state.forecasts.filter((f) => f.is_currently_raining || f.next_rain_in_minutes !== null);
    if (wetForecasts.length > 0) {
      const f0 = wetForecasts[0];
      el.statRadarBadge.className = 'badge badge-warning';
      el.statRadarBadge.textContent = f0.is_currently_raining ? 'Raining Now' : `Rain in ${f0.next_rain_in_minutes}m`;
      el.statRadarValue.textContent = `${f0.peak_mm_h_next_2h.toFixed(1)} mm/h peak`;
      el.statRadarHint.textContent = `${f0.location_name}: ${f0.summary_text}`;
    } else {
      el.statRadarBadge.className = 'badge badge-success';
      el.statRadarBadge.textContent = 'All Dry';
      el.statRadarValue.textContent = '0.0 mm/h';
      el.statRadarHint.textContent = `Clear across ${state.forecasts.length} watched location(s)`;
    }

    // Breaks summary
    const shiftBreaks = state.evaluations.filter(
      (e) => e.status === 'shift_earlier_dry' || e.status === 'shift_later_dry' || e.status === 'shift_cleaner_slot'
    );
    el.statBreaksBadge.textContent = `${state.breaks.filter((b) => b.enabled).length} Active`;
    if (shiftBreaks.length > 0) {
      el.statBreaksBadge.className = 'badge badge-warning';
      el.statBreaksValue.textContent = `${shiftBreaks.length} Shift Advised`;
      el.statBreaksHint.textContent = `${shiftBreaks[0].break_name}: ${shiftBreaks[0].headline}`;
    } else {
      el.statBreaksBadge.className = 'badge badge-success';
      el.statBreaksValue.textContent = 'On Schedule';
      el.statBreaksHint.textContent = `${state.evaluations.length} break window(s) evaluated`;
    }

    // Channels summary
    let haCount = 0;
    let poCount = 0;
    activeUsers.forEach((u) => {
      if (u.ha_notify_enabled) haCount += (u.ha_notify_targets || []).length;
      if (u.pushover_enabled && u.pushover_user_key) poCount += 1;
    });
    el.statChannelsValue.textContent = `${haCount + poCount} Active Route(s)`;
    el.statChannelsHint.textContent = `${haCount} HA Notify · ${poCount} Pushover`;
  }

  function renderBreakEvaluations() {
    if (!el.dashBreakEvaluations) return;
    if (state.evaluations.length === 0) {
      el.dashBreakEvaluations.innerHTML = `
        <div class="empty-state">
          No break windows configured yet. Click <strong>+ Add Break Window</strong> or load the 10:00 / 12:30 / 15:00 Workday Preset.
        </div>`;
      return;
    }

    el.dashBreakEvaluations.innerHTML = state.evaluations
      .map((ev) => {
        const isPaused = ev.status === 'paused_wrong_location';
        const isDry = ev.status === 'dry_on_schedule';
        const isShift =
          ev.status === 'shift_earlier_dry' ||
          ev.status === 'shift_later_dry' ||
          ev.status === 'dry_but_rain_soon_after' ||
          ev.status === 'shift_cleaner_slot';
        const cardClass = isPaused ? 'eval-paused' : isDry ? 'eval-dry' : isShift ? 'eval-shift' : 'eval-rain';
        const badgeClass = isPaused ? 'badge-muted' : isDry ? 'badge-success' : isShift ? 'badge-warning' : 'badge-danger';
        const statusLabel = {
          dry_on_schedule: 'Dry on Schedule',
          dry_but_rain_soon_after: 'Go On Time (Rain After)',
          shift_earlier_dry: 'Go Earlier · Dry Slot',
          shift_later_dry: 'Go Later · Dry Slot',
          shift_cleaner_slot: 'Shift · Lighter Rain',
          heavy_rain_no_window: 'Continuous Rain',
          paused_wrong_location: 'Paused · Not At Location',
        }[ev.status] || ev.status;

        const urgBadge =
          ev.effective_urgency === 'urgent'
            ? `<span class="badge badge-danger">URGENT</span>`
            : `<span class="badge badge-info">NEUTRAL</span>`;

        // Select key slots around planned & recommended (-30, -15, 0, +15, +30)
        const keySlots = (ev.all_candidates || []).filter(
          (c) =>
            c.shift_minutes % 15 === 0 ||
            c.start_time === ev.recommended_slot.start_time ||
            c.shift_minutes === 0
        );

        const stripHtml = keySlots
          .map((c) => {
            const isBest = c.start_time === ev.recommended_slot.start_time && !isDry;
            const isPlanned = c.shift_minutes === 0;
            const cls = isBest ? 'slot-best' : !c.is_dry ? 'slot-wet' : isPlanned ? 'slot-planned' : '';
            const tag = isBest ? '★ Best ' : isPlanned ? 'Planned ' : '';
            return `<span class="slot-chip ${cls}" title="${c.start_time}–${c.end_time}: max ${c.max_mm_h} mm/h">
              ${tag}${escapeHtml(c.start_time)} (${c.max_mm_h.toFixed(1)} mm/h)
            </span>`;
          })
          .join('');

        return `
          <article class="eval-card ${cardClass}">
            <div class="eval-head">
              <div>
                <div class="eval-title">${escapeHtml(ev.break_name)}</div>
                <div class="eval-sub">
                  👤 ${escapeHtml(ev.user_name)} &middot; 📍 ${escapeHtml(ev.location_name)} &middot; 🕒 Planned ${escapeHtml(ev.planned_start)}–${escapeHtml(ev.planned_end)} (${ev.duration_minutes}m)
                </div>
              </div>
              <div class="item-tags">
                <span class="badge ${badgeClass}">${escapeHtml(statusLabel)}</span>
                ${urgBadge}
              </div>
            </div>
            <div class="eval-headline">💡 ${escapeHtml(ev.headline)}</div>
            <div class="eval-advice">${escapeHtml(ev.advice_text)}</div>
            <div class="slot-strip">${stripHtml}</div>
            <div class="eval-footer">
              <span class="eval-sub">${escapeHtml(ev.schedule_reason)}</span>
              <div class="item-tags">
                <button type="button" class="btn btn-sm btn-secondary" onclick="window.rainBreakApp.editBreakModal('${escapeHtml(ev.break_id)}')">
                  Edit Break
                </button>
                <button type="button" class="btn btn-sm btn-primary" onclick="window.rainBreakApp.sendBreakAdviceNow('${escapeHtml(ev.break_id)}')">
                  &#128232; Send Advice Now
                </button>
              </div>
            </div>
          </article>
        `;
      })
      .join('');
  }

  function renderForecastTimeline() {
    if (!el.forecastLocationPills || !el.forecastTimelineContainer) return;
    if (state.forecasts.length === 0) {
      el.forecastLocationPills.innerHTML = '';
      el.forecastTimelineContainer.innerHTML = `<div class="empty-state">No locations available.</div>`;
      return;
    }

    if (
      !state.selectedForecastLocationId ||
      !state.forecasts.some((f) => f.location_id === state.selectedForecastLocationId)
    ) {
      const liveFc = state.forecasts.find((f) => f.location_id.startsWith('live_'));
      state.selectedForecastLocationId = liveFc ? liveFc.location_id : state.forecasts[0].location_id;
    }

    // Always sort live user locations first so they appear at the top/front of pills
    const sortedForecasts = [...state.forecasts].sort((a, b) => {
      const aLive = a.location_id.startsWith('live_') ? 1 : 0;
      const bLive = b.location_id.startsWith('live_') ? 1 : 0;
      return bLive - aLive;
    });

    el.forecastLocationPills.innerHTML = sortedForecasts
      .map((f) => {
        const isLive = f.location_id.startsWith('live_');
        const active = f.location_id === state.selectedForecastLocationId ? 'active' : '';
        const liveClass = isLive ? 'loc-pill-live' : '';
        const pulse = isLive ? '<span class="pulse-dot"></span>' : '';
        const icon = isLive ? '📍 ' : '🗺️ ';
        return `<button type="button" class="loc-pill ${liveClass} ${active}" data-loc-id="${escapeHtml(f.location_id)}" title="${escapeHtml(f.location_name)}">
          ${pulse}${icon}${escapeHtml(f.location_name)}
        </button>`;
      })
      .join('');

    el.forecastLocationPills.querySelectorAll('.loc-pill').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.selectedForecastLocationId = btn.getAttribute('data-loc-id');
        renderForecastTimeline();
      });
    });

    const activeFc =
      state.forecasts.find((f) => f.location_id === state.selectedForecastLocationId) || state.forecasts[0];

    el.forecastSummaryBar.innerHTML = `
      <div>
        <strong>${escapeHtml(activeFc.location_name)}</strong>
        <span class="eval-sub">(${activeFc.latitude.toFixed(4)}, ${activeFc.longitude.toFixed(4)} &middot; Source: ${escapeHtml(activeFc.source_used)})</span>
        — ${escapeHtml(activeFc.summary_text)}
      </div>
      <span class="badge ${activeFc.is_currently_raining ? 'badge-danger' : activeFc.next_rain_in_minutes !== null ? 'badge-warning' : 'badge-success'}">
        Peak 2h: ${activeFc.peak_mm_h_next_2h.toFixed(1)} mm/h
      </span>
    `;

    // Display next 24 points (2 hours of 5-min radar) or window around upcoming breaks
    const nearPoints = (activeFc.points || []).filter((p) => p.minutes_from_now >= -5 && p.minutes_from_now <= 120);
    const displayPts = nearPoints.length >= 8 ? nearPoints.slice(0, 25) : (activeFc.points || []).slice(0, 25);

    if (displayPts.length === 0) {
      el.forecastTimelineContainer.innerHTML = `<div class="empty-state">No timeline points returned.</div>`;
      return;
    }

    const maxScale = Math.max(3.0, ...displayPts.map((p) => p.mm_per_hour));
    const barsHtml = displayPts
      .map((p) => {
        const pct = p.mm_per_hour <= 0 ? 6 : Math.min(100, Math.max(12, Math.round((p.mm_per_hour / maxScale) * 100)));
        const fillClass = p.mm_per_hour >= 1.5 ? 'bar-heavy' : p.mm_per_hour >= 0.15 ? '' : 'bar-dry';
        return `
          <div class="rain-bar-col" title="${p.time_label}: ${p.mm_per_hour.toFixed(2)} mm/h (${p.probability_pct}% prob)">
            <span class="rain-bar-val">${p.mm_per_hour > 0 ? p.mm_per_hour.toFixed(1) : '0'}</span>
            <div class="rain-bar-track">
              <div class="rain-bar-fill ${fillClass}" style="height: ${pct}%"></div>
            </div>
            <span class="rain-bar-time">${escapeHtml(p.time_label)}</span>
          </div>
        `;
      })
      .join('');

    el.forecastTimelineContainer.innerHTML = `<div class="rain-bars">${barsHtml}</div>`;
  }

  function renderBreaksTab() {
    if (!el.breaksList) return;
    if (state.breaks.length === 0) {
      el.breaksList.innerHTML = `<div class="empty-state">No break windows configured. Click <strong>Load Workday Preset</strong> or <strong>+ Add Break Window</strong>.</div>`;
      return;
    }

    const userMap = Object.fromEntries(state.users.map((u) => [u.id, u.name]));
    const locMap = Object.fromEntries(state.locations.map((l) => [l.id, l.name]));

    el.breaksList.innerHTML = state.breaks
      .map((b) => {
        const uName = userMap[b.user_id] || b.user_id;
        const locLabel = b.location_override_id
          ? locMap[b.location_override_id] || b.location_override_id
          : "User's Active Location Mode";
        const actLabel = ACTIVITY_ICONS[b.activity_type] || '🚶 Walk';
        return `
          <article class="item-card ${b.enabled ? '' : 'card-disabled'}">
            <div class="item-card-head">
              <div>
                <div class="item-title">${escapeHtml(b.name)}</div>
                <div class="eval-sub">${actLabel} &middot; 👤 ${escapeHtml(uName)}</div>
              </div>
              <span class="badge ${b.enabled ? 'badge-success' : 'badge-warning'}">${b.enabled ? 'Enabled' : 'Paused'}</span>
            </div>
            <div class="item-meta">
              <div><strong>Planned Time:</strong> ${escapeHtml(b.start_time)} (${b.duration_minutes} min duration)</div>
              <div><strong>Look-Around Flex:</strong> -${b.flex_before_minutes} min earlier / +${b.flex_after_minutes} min later</div>
              <div><strong>Lead Alert:</strong> ${b.lead_alert_minutes} min before window &middot; <strong>Days:</strong> ${escapeHtml(formatDays(b.active_days))}</div>
              <div><strong>Location:</strong> ${escapeHtml(locLabel)} &middot; <strong>Urgency:</strong> ${escapeHtml(b.urgency_override.toUpperCase())}</div>
            </div>
            <div class="item-actions">
              <button type="button" class="btn btn-sm btn-secondary" onclick="window.rainBreakApp.editBreakModal('${escapeHtml(b.id)}')">Edit</button>
              <button type="button" class="btn btn-sm btn-primary" onclick="window.rainBreakApp.sendBreakAdviceNow('${escapeHtml(b.id)}')">Test Advice</button>
              <button type="button" class="btn btn-sm btn-danger" onclick="window.rainBreakApp.deleteBreak('${escapeHtml(b.id)}')">Delete</button>
            </div>
          </article>
        `;
      })
      .join('');
  }

  function renderUsersTab() {
    if (!el.usersList) return;
    if (state.users.length === 0) {
      el.usersList.innerHTML = `<div class="empty-state">No users configured.</div>`;
      return;
    }

    const locMap = Object.fromEntries(state.locations.map((l) => [l.id, l.name]));

    el.usersList.innerHTML = state.users
      .map((u) => {
        const locDesc =
          u.location_mode === 'live_person'
            ? `📍 Auto Live HA Person (${u.ha_person_entity || 'unlinked'})`
            : u.location_mode === 'fixed_location'
              ? `🏢 Fixed Location (${locMap[u.fixed_location_id] || u.fixed_location_id || 'Default'})`
              : `🗺️ Multi-Location (${(u.watched_location_ids || []).map((id) => locMap[id] || id).join(', ')})`;

        const schedDesc =
          u.schedule_mode === 'urgent_window_else_neutral'
            ? `🔔 Urgent ${u.window_start}–${u.window_end}, Neutral outside (${formatDays(u.active_days)})`
            : u.schedule_mode === 'active_window_only'
              ? `🕒 Only between ${u.window_start}–${u.window_end} (${u.default_urgency.toUpperCase()})`
              : `🌐 Always 24/7 (${u.default_urgency.toUpperCase()})`;

        const haRoutes = u.ha_notify_enabled ? (u.ha_notify_targets || []).join(', ') || 'None selected' : 'Disabled';
        const poStatus = u.pushover_enabled
          ? u.pushover_user_key
            ? `Enabled (User ${u.pushover_user_key.slice(0, 5)}… · Priority ${u.pushover_urgent_priority})`
            : 'Enabled (Missing User Key)'
          : 'Disabled';

        return `
          <article class="item-card ${u.enabled ? '' : 'card-disabled'}">
            <div class="item-card-head">
              <div>
                <div class="item-title">👤 ${escapeHtml(u.name)}</div>
                <div class="eval-sub">${u.ha_person_entity ? `<span class="code-pill">${escapeHtml(u.ha_person_entity)}</span>` : 'Standalone Profile'}</div>
              </div>
              <div class="item-tags">
                <span class="badge ${u.enabled ? 'badge-success' : 'badge-warning'}">
                  ${u.enabled ? 'ACTIVE' : 'PAUSED'}
                </span>
              </div>
            </div>
            <div class="item-meta">
              <div><strong>Location Mode:</strong> ${escapeHtml(locDesc)}</div>
              <div><strong>Schedule &amp; Urgency:</strong> ${escapeHtml(schedDesc)}</div>
              <div><strong>HA Notify:</strong> ${escapeHtml(haRoutes)}</div>
              <div><strong>Pushover API:</strong> ${escapeHtml(poStatus)}</div>
              <div><strong>Continuous Rain Radar Alert:</strong> ${u.continuous_rain_alerts ? `Yes (${u.rain_lead_minutes}m lead time)` : 'Off (Break Windows only)'}</div>
            </div>
            <div class="item-actions">
              <button type="button" class="btn btn-sm ${u.enabled ? 'btn-secondary' : 'btn-primary'}" onclick="window.rainBreakApp.toggleUser('${escapeHtml(u.id)}', ${!u.enabled})">
                ${u.enabled ? 'Pause User' : 'Activate User'}
              </button>
              <button type="button" class="btn btn-sm btn-secondary" onclick="window.rainBreakApp.editUserModal('${escapeHtml(u.id)}')">
                Configure
              </button>
              <button type="button" class="btn btn-sm btn-secondary" onclick="window.rainBreakApp.testUserAlert('${escapeHtml(u.id)}', 'urgent')">
                Test Urgent
              </button>
              <button type="button" class="btn btn-sm btn-secondary" onclick="window.rainBreakApp.testUserAlert('${escapeHtml(u.id)}', 'neutral')">
                Test Neutral
              </button>
              <button type="button" class="btn btn-sm btn-danger" onclick="window.rainBreakApp.deleteUser('${escapeHtml(u.id)}')">
                Delete
              </button>
            </div>
          </article>
        `;
      })
      .join('');

    // Also populate test-user-id select in Settings tab
    if (el.testUserId) {
      el.testUserId.innerHTML = state.users
        .map((u) => `<option value="${escapeHtml(u.id)}">${escapeHtml(u.name)} (${u.enabled ? 'Active' : 'Paused'})</option>`)
        .join('');
    }
  }

  function renderLocationsTab() {
    if (!el.locationsList) return;
    if (state.locations.length === 0) {
      el.locationsList.innerHTML = `<div class="empty-state">No saved locations yet.</div>`;
    } else {
      el.locationsList.innerHTML = state.locations
        .map(
          (loc) => `
          <article class="item-card">
            <div class="item-card-head">
              <div>
                <div class="item-title">🗺️ ${escapeHtml(loc.name)}</div>
                <div class="eval-sub">
                  ${loc.ha_zone_entity ? `<span class="code-pill">${escapeHtml(loc.ha_zone_entity)}</span>` : 'Custom Coordinates'}
                </div>
              </div>
              <span class="badge ${loc.enabled ? 'badge-success' : 'badge-warning'}">${loc.enabled ? 'Enabled' : 'Disabled'}</span>
            </div>
            <div class="item-meta">
              <div><strong>Coordinates:</strong> ${loc.latitude.toFixed(4)}, ${loc.longitude.toFixed(4)}</div>
              <div><strong>Coverage:</strong> ${loc.latitude >= 49.0 && loc.latitude <= 54.5 && loc.longitude >= 2.5 && loc.longitude <= 7.6 ? 'Buienradar 5-min + Open-Meteo' : 'Open-Meteo Worldwide'}</div>
            </div>
            <div class="item-actions">
              <button type="button" class="btn btn-sm btn-secondary" onclick="window.rainBreakApp.editLocationModal('${escapeHtml(loc.id)}')">Edit</button>
              <button type="button" class="btn btn-sm btn-danger" onclick="window.rainBreakApp.deleteLocation('${escapeHtml(loc.id)}')">Delete</button>
            </div>
          </article>
        `
        )
        .join('');
    }

    if (el.discoveredHaEntities) {
      const persons = state.discovered.persons || [];
      const zones = state.discovered.zones || [];
      if (persons.length === 0 && zones.length === 0) {
        el.discoveredHaEntities.innerHTML = `<div class="empty-state">No Home Assistant persons or zones discovered yet.</div>`;
        return;
      }

      const pCards = persons.map(
        (p) => `
        <article class="item-card">
          <div class="item-card-head">
            <div>
              <div class="item-title">👤 ${escapeHtml(p.name)}</div>
              <span class="code-pill">${escapeHtml(p.entity_id)}</span>
            </div>
            <span class="badge badge-info">State: ${escapeHtml(p.state)}</span>
          </div>
          <div class="item-meta">
            <div><strong>Live GPS:</strong> ${p.latitude !== null && p.longitude !== null ? `${p.latitude.toFixed(4)}, ${p.longitude.toFixed(4)}` : 'No GPS coordinates'}</div>
            <div><strong>Tracker Source:</strong> ${escapeHtml(p.source || 'N/A')}</div>
          </div>
          ${p.latitude !== null && p.longitude !== null ? `
          <div class="item-actions">
            <button type="button" class="btn btn-sm btn-secondary" onclick="window.rainBreakApp.importHaEntity('${escapeHtml(p.name)} Live GPS', ${p.latitude}, ${p.longitude}, '${escapeHtml(p.entity_id)}')">
              + Save Current GPS as Location
            </button>
          </div>` : ''}
        </article>
      `
      );

      const zCards = zones.map(
        (z) => `
        <article class="item-card">
          <div class="item-card-head">
            <div>
              <div class="item-title">📍 Zone: ${escapeHtml(z.name)}</div>
              <span class="code-pill">${escapeHtml(z.entity_id)}</span>
            </div>
            <span class="badge badge-success">HA Zone</span>
          </div>
          <div class="item-meta">
            <div><strong>Coordinates:</strong> ${z.latitude.toFixed(4)}, ${z.longitude.toFixed(4)} (${z.radius_m}m radius)</div>
          </div>
          <div class="item-actions">
            <button type="button" class="btn btn-sm btn-primary" title="Import this Home Assistant zone into saved locations" onclick="window.rainBreakApp.importHaEntity('${escapeHtml(z.name)}', ${z.latitude}, ${z.longitude}, '${escapeHtml(z.entity_id)}')">
              + Add as Saved Location
            </button>
            <button type="button" class="btn btn-sm btn-secondary" title="Save and assign as Work location" onclick="window.rainBreakApp.importHaEntity('${escapeHtml(z.name)}', ${z.latitude}, ${z.longitude}, '${escapeHtml(z.entity_id)}', 'work')">
              🏢 Set as Work
            </button>
            <button type="button" class="btn btn-sm btn-secondary" title="Save and assign as Home location" onclick="window.rainBreakApp.importHaEntity('${escapeHtml(z.name)}', ${z.latitude}, ${z.longitude}, '${escapeHtml(z.entity_id)}', 'home')">
              🏠 Set as Home
            </button>
          </div>
        </article>
      `
      );

      el.discoveredHaEntities.innerHTML = [...pCards, ...zCards].join('');
    }
  }

  function renderSettingsAndHistory() {
    if (state.config) {
      el.cfgWeatherProvider.value = state.config.weather_provider || 'auto';
      el.cfgRainThreshold.value = state.config.rain_threshold_mm ?? 0.15;
      el.cfgHeavyThreshold.value = state.config.heavy_rain_threshold_mm ?? 2.0;
      el.cfgTimezone.value = state.config.default_timezone || 'Europe/Amsterdam';
      el.cfgDedupMinutes.value = state.config.dedup_cooldown_minutes ?? 30;
      el.cfgPushoverToken.value = state.config.pushover_app_token || '';
      el.cfgBgMonitoring.checked = Boolean(state.config.background_monitoring_enabled);
    }

    const alerts = state.recentAlerts || [];
    if (alerts.length === 0) {
      el.historyTbody.innerHTML = `<tr><td colspan="7" class="empty-cell">No alerts logged yet.</td></tr>`;
      el.historyCards.innerHTML = `<div class="empty-state">No alerts logged yet.</div>`;
      return;
    }

    el.historyTbody.innerHTML = alerts
      .map((r) => {
        const stBadge =
          r.status === 'submitted' ? 'badge-success' : r.status === 'failed' ? 'badge-danger' : 'badge-warning';
        const urgBadge = r.urgency === 'urgent' ? 'badge-danger' : 'badge-info';
        return `
          <tr>
            <td>${escapeHtml(formatTimestamp(r.timestamp))}</td>
            <td><strong>${escapeHtml(r.user_name)}</strong></td>
            <td>${escapeHtml(r.break_name ? `${r.break_name} (${r.location_name})` : r.location_name)}</td>
            <td><span class="badge ${urgBadge}">${escapeHtml(r.urgency)}</span></td>
            <td><span class="code-pill">${escapeHtml(r.channel)}: ${escapeHtml(r.target)}</span></td>
            <td><span class="badge ${stBadge}">${escapeHtml(r.status)}</span></td>
            <td>${escapeHtml(r.detail)}</td>
          </tr>
        `;
      })
      .join('');

    el.historyCards.innerHTML = alerts
      .map((r) => {
        const stBadge =
          r.status === 'submitted' ? 'badge-success' : r.status === 'failed' ? 'badge-danger' : 'badge-warning';
        const urgBadge = r.urgency === 'urgent' ? 'badge-danger' : 'badge-info';
        return `
          <div class="history-card">
            <div class="item-card-head">
              <strong>${escapeHtml(r.user_name)} &middot; ${escapeHtml(r.break_name || r.location_name)}</strong>
              <span class="badge ${stBadge}">${escapeHtml(r.status)}</span>
            </div>
            <div class="item-tags">
              <span class="badge ${urgBadge}">${escapeHtml(r.urgency)}</span>
              <span class="code-pill">${escapeHtml(r.channel)}: ${escapeHtml(r.target)}</span>
              <span class="eval-sub">${escapeHtml(formatTimestamp(r.timestamp))}</span>
            </div>
            <div class="eval-sub">${escapeHtml(r.detail)}</div>
          </div>
        `;
      })
      .join('');
  }

  // --- Refresh Full Overview ---
  async function refreshAll(forceRefresh = false) {
    try {
      const data = await apiGet(`api/overview${forceRefresh ? '?refresh=true' : ''}`);
      state.overview = data;
      state.config = data.config;
      state.discovered = data.discovered || { persons: [], zones: [], notify_actions: [] };
      state.locations = data.locations || [];
      state.users = data.users || [];
      state.breaks = data.breaks || [];
      state.forecasts = data.forecasts || [];
      state.evaluations = data.break_evaluations || [];
      state.recentAlerts = data.recent_alerts || [];

      renderHeaderAndStats();
      renderBreakEvaluations();
      renderForecastTimeline();
      renderBreaksTab();
      renderUsersTab();
      renderLocationsTab();
      renderSettingsAndHistory();
    } catch (err) {
      showBanner(`Failed to load RainBreak state: ${err.message}`, 'error');
    }
  }

  // --- Modals: Break Window Create/Edit ---
  function openBreakModal(existingBreak) {
    const isEdit = Boolean(existingBreak);
    const b = existingBreak || {
      id: '',
      user_id: state.users[0] ? state.users[0].id : 'usr_primary',
      name: 'Morning Break Walk (10:00)',
      activity_type: 'walk',
      start_time: '10:00',
      duration_minutes: 15,
      flex_before_minutes: 30,
      flex_after_minutes: 30,
      lead_alert_minutes: 25,
      active_days: [0, 1, 2, 3, 4],
      location_override_id: '',
      location_req_mode: 'any_location',
      required_location_id: '',
      destination_location_id: '',
      urgency_override: 'auto',
      notify_when_dry: false,
      enabled: true,
    };

    const userOpts = state.users
      .map(
        (u) =>
          `<option value="${escapeHtml(u.id)}" ${u.id === b.user_id ? 'selected' : ''}>${escapeHtml(u.name)} (${u.enabled ? 'Active' : 'Paused'})</option>`
      )
      .join('');

    const locOpts = [
      `<option value="" ${!b.location_override_id ? 'selected' : ''}>Follow User's Active Location Mode (Auto Live / Preset)</option>`,
      ...state.locations.map(
        (l) =>
          `<option value="${escapeHtml(l.id)}" ${l.id === b.location_override_id ? 'selected' : ''}>Override: ${escapeHtml(l.name)}</option>`
      ),
    ].join('');

    const html = `
      <form id="modal-break-form" class="form-grid">
        <div class="form-row-2">
          <div class="form-group">
            <label for="brk-name">Break / Activity Name *</label>
            <input type="text" id="brk-name" value="${escapeHtml(b.name)}" required placeholder="e.g. Morning Walk (10:00)" />
          </div>
          <div class="form-group">
            <label for="brk-activity">Activity Type</label>
            <select id="brk-activity">
              <option value="walk" ${b.activity_type === 'walk' ? 'selected' : ''}>🚶 Walk</option>
              <option value="bike" ${b.activity_type === 'bike' ? 'selected' : ''}>🚲 Bike Ride / Exercise</option>
              <option value="bike_commute" ${b.activity_type === 'bike_commute' ? 'selected' : ''}>🚲 Bike Commute (to/from work)</option>
              <option value="run" ${b.activity_type === 'run' ? 'selected' : ''}>🏃 Run</option>
              <option value="dog_walk" ${b.activity_type === 'dog_walk' ? 'selected' : ''}>🐕 Dog Walk</option>
              <option value="commute" ${b.activity_type === 'commute' ? 'selected' : ''}>🚗 Commute / Transit</option>
              <option value="break" ${b.activity_type === 'break' ? 'selected' : ''}>☕ Outdoor Break</option>
            </select>
          </div>
        </div>

        <div class="form-row-2">
          <div class="form-group">
            <label for="brk-user">Assigned User *</label>
            <select id="brk-user">${userOpts}</select>
          </div>
          <div class="form-group">
            <label for="brk-location">Forecast Location Scope</label>
            <select id="brk-location">${locOpts}</select>
          </div>
        </div>

        <div class="form-row-2">
          <div class="form-group">
            <label for="brk-loc-req-mode">Location Geofence Condition</label>
            <select id="brk-loc-req-mode">
              <option value="any_location" ${(!b.location_req_mode || b.location_req_mode === 'any_location') ? 'selected' : ''}>Active Anywhere (No Geofence)</option>
              <option value="only_at_location" ${b.location_req_mode === 'only_at_location' ? 'selected' : ''}>Only Active When AT Location (e.g. At Work)</option>
              <option value="only_away_from_location" ${b.location_req_mode === 'only_away_from_location' ? 'selected' : ''}>Only Active When AWAY from Location (e.g. Away from Home)</option>
            </select>
          </div>
          <div class="form-group" id="brk-req-loc-group" ${(!b.location_req_mode || b.location_req_mode === 'any_location') ? 'style="display:none;"' : ''}>
            <label for="brk-req-loc">Geofence Reference Location</label>
            <select id="brk-req-loc">
              <option value="">-- Select Saved Location --</option>
              ${state.locations.map((l) => `<option value="${escapeHtml(l.id)}" ${l.id === b.required_location_id ? 'selected' : ''}>${escapeHtml(l.name)}</option>`).join('')}
            </select>
          </div>
        </div>

        <div class="form-row-2">
          <div class="form-group">
            <label for="brk-start">Planned Start Time (24h) *</label>
            <input type="time" id="brk-start" value="${escapeHtml(b.start_time)}" required />
          </div>
          <div class="form-group">
            <label for="brk-duration">Break Duration (minutes) *</label>
            <select id="brk-duration">
              ${[10, 15, 20, 30, 45, 60, 90]
                .map((m) => `<option value="${m}" ${Number(b.duration_minutes) === m ? 'selected' : ''}>${m} minutes</option>`)
                .join('')}
            </select>
          </div>
        </div>

        <div class="form-row-2">
          <div class="form-group">
            <label for="brk-flex-before">Can Leave Earlier By (min)</label>
            <input type="number" id="brk-flex-before" min="0" max="120" step="5" value="${b.flex_before_minutes}" required />
            <span class="field-help">Checks dry slots before your break (e.g. 15–30 min earlier)</span>
          </div>
          <div class="form-group">
            <label for="brk-flex-after">Can Shift Later By (min)</label>
            <input type="number" id="brk-flex-after" min="0" max="120" step="5" value="${b.flex_after_minutes}" required />
            <span class="field-help">Checks dry slots after your planned break</span>
          </div>
        </div>

        <div class="form-row-2">
          <div class="form-group">
            <label for="brk-lead">Alert Lead Time (min before window)</label>
            <input type="number" id="brk-lead" min="5" max="120" step="5" value="${b.lead_alert_minutes}" required />
          </div>
          <div class="form-group">
            <label for="brk-urgency">Urgency Level</label>
            <select id="brk-urgency">
              <option value="auto" ${b.urgency_override === 'auto' ? 'selected' : ''}>Follow User Schedule Rule (Auto)</option>
              <option value="urgent" ${b.urgency_override === 'urgent' ? 'selected' : ''}>Always Urgent (High Priority)</option>
              <option value="neutral" ${b.urgency_override === 'neutral' ? 'selected' : ''}>Always Neutral (Standard Priority)</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label>Active Days</label>
          <div class="checkboxes-wrap">
            ${DAY_NAMES.map(
              (d, idx) => `
              <label class="checkbox-inline">
                <input type="checkbox" name="brk-day" value="${idx}" ${(b.active_days || []).includes(idx) ? 'checked' : ''} /> ${d}
              </label>
            `
            ).join('')}
          </div>
        </div>

        <div class="form-group">
          <label class="checkbox-inline">
            <input type="checkbox" id="brk-notify-dry" ${b.notify_when_dry ? 'checked' : ''} />
            Also send confirmation alert when planned break is completely dry
          </label>
          <label class="checkbox-inline">
            <input type="checkbox" id="brk-enabled" ${b.enabled ? 'checked' : ''} />
            Break Window Enabled
          </label>
        </div>

        <div class="form-actions">
          <button type="button" class="btn btn-secondary" onclick="document.getElementById('app-modal').close()">Cancel</button>
          <button type="submit" class="btn btn-primary">${isEdit ? 'Update Break Window' : 'Create Break Window'}</button>
        </div>
      </form>
    `;

    openModal(isEdit ? 'Edit Break Window' : 'Add Break Window', html);

    const reqModeSel = document.getElementById('brk-loc-req-mode');
    const reqGroup = document.getElementById('brk-req-loc-group');
    if (reqModeSel && reqGroup) {
      reqModeSel.addEventListener('change', () => {
        reqGroup.style.display = reqModeSel.value === 'any_location' ? 'none' : 'block';
      });
    }

    document.getElementById('modal-break-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const days = Array.from(document.querySelectorAll('input[name="brk-day"]:checked')).map((c) => Number(c.value));
        const payload = {
          id: b.id || '',
          user_id: document.getElementById('brk-user').value,
          name: document.getElementById('brk-name').value.trim(),
          activity_type: document.getElementById('brk-activity').value,
          start_time: document.getElementById('brk-start').value,
          duration_minutes: Number(document.getElementById('brk-duration').value),
          flex_before_minutes: Number(document.getElementById('brk-flex-before').value),
          flex_after_minutes: Number(document.getElementById('brk-flex-after').value),
          lead_alert_minutes: Number(document.getElementById('brk-lead').value),
          active_days: days,
          location_override_id: document.getElementById('brk-location').value || null,
          location_req_mode: document.getElementById('brk-loc-req-mode').value,
          required_location_id: document.getElementById('brk-req-loc') ? (document.getElementById('brk-req-loc').value || null) : null,
          destination_location_id: b.destination_location_id || null,
          urgency_override: document.getElementById('brk-urgency').value,
          notify_when_dry: document.getElementById('brk-notify-dry').checked,
          enabled: document.getElementById('brk-enabled').checked,
        };
        await apiPost('api/breaks', payload);
        closeModal();
        await refreshAll(true);
        showBanner('Break window saved and evaluated.', 'success');
      } catch (err) {
        showBanner(`Failed to save break window: ${err.message}`, 'error');
      }
    });
  }

  // --- Modal: User Profile Create/Edit ---
  function openUserModal(existingUser) {
    const isEdit = Boolean(existingUser);
    const u = existingUser || {
      id: '',
      name: '',
      enabled: true,
      ha_person_entity: state.discovered.persons[0] ? state.discovered.persons[0].entity_id : '',
      location_mode: 'live_person',
      fixed_location_id: state.locations[0] ? state.locations[0].id : 'loc_home',
      fallback_location_id: state.locations[0] ? state.locations[0].id : 'loc_home',
      watched_location_ids: state.locations.map((l) => l.id),
      schedule_mode: 'urgent_window_else_neutral',
      window_start: '07:30',
      window_end: '17:30',
      active_days: [0, 1, 2, 3, 4],
      default_urgency: 'urgent',
      timezone: (state.config && state.config.default_timezone) || 'Europe/Amsterdam',
      continuous_rain_alerts: true,
      rain_lead_minutes: 20,
      ha_notify_enabled: true,
      ha_notify_targets: [],
      pushover_enabled: false,
      pushover_user_key: '',
      pushover_app_token: '',
      pushover_device: '',
      pushover_urgent_priority: 1,
      pushover_sound: 'pushover',
    };

    const personOpts = [
      `<option value="">-- None / Standalone Profile --</option>`,
      ...(state.discovered.persons || []).map(
        (p) =>
          `<option value="${escapeHtml(p.entity_id)}" ${p.entity_id === u.ha_person_entity ? 'selected' : ''}>${escapeHtml(p.name)} (${escapeHtml(p.entity_id)} · ${escapeHtml(p.state)})</option>`
      ),
    ].join('');

    const locOpts = state.locations
      .map(
        (l) =>
          `<option value="${escapeHtml(l.id)}" ${l.id === u.fixed_location_id ? 'selected' : ''}>${escapeHtml(l.name)}</option>`
      )
      .join('');

    const fbOpts = state.locations
      .map(
        (l) =>
          `<option value="${escapeHtml(l.id)}" ${l.id === u.fallback_location_id ? 'selected' : ''}>${escapeHtml(l.name)}</option>`
      )
      .join('');

    const watchedChecks = state.locations
      .map(
        (l) => `
        <label class="checkbox-inline">
          <input type="checkbox" name="usr-watched-loc" value="${escapeHtml(l.id)}" ${(u.watched_location_ids || []).includes(l.id) ? 'checked' : ''} />
          ${escapeHtml(l.name)}
        </label>
      `
      )
      .join('');

    const notifyChecks = (state.discovered.notify_actions || [])
      .map(
        (a) => `
        <label class="checkbox-inline" title="${escapeHtml(a.description)}">
          <input type="checkbox" name="usr-ha-target" value="${escapeHtml(a.action)}" ${(u.ha_notify_targets || []).includes(a.action) ? 'checked' : ''} />
          ${escapeHtml(a.name)} (<span class="code-pill">${escapeHtml(a.action)}</span>)
        </label>
      `
      )
      .join('');

    const html = `
      <form id="modal-user-form" class="form-grid">
        <div class="form-row-2">
          <div class="form-group">
            <label for="usr-name">User Display Name *</label>
            <input type="text" id="usr-name" value="${escapeHtml(u.name)}" required placeholder="e.g. Martijn" />
          </div>
          <div class="form-group">
            <label for="usr-person">Linked Home Assistant Person</label>
            <select id="usr-person">${personOpts}</select>
          </div>
        </div>

        <div class="form-group">
          <label class="checkbox-inline">
            <input type="checkbox" id="usr-enabled" ${u.enabled ? 'checked' : ''} />
            <strong>Enable rain &amp; break monitoring for this user</strong>
          </label>
        </div>

        <hr class="divider" />

        <div class="form-group">
          <label for="usr-loc-mode">1. Location Tracking Mode</label>
          <select id="usr-loc-mode">
            <option value="live_person" ${u.location_mode === 'live_person' ? 'selected' : ''}>📍 Auto: Use Live HA Person GPS Location (with Fallback)</option>
            <option value="fixed_location" ${u.location_mode === 'fixed_location' ? 'selected' : ''}>🏢 Single Preset Location (e.g. Work or Home)</option>
            <option value="multi_location" ${u.location_mode === 'multi_location' ? 'selected' : ''}>🗺️ Multi-Location Watch (Monitor Multiple Presets)</option>
          </select>
        </div>

        <div class="form-row-2">
          <div class="form-group">
            <label for="usr-fixed-loc">Selected Preset Location</label>
            <select id="usr-fixed-loc">${locOpts}</select>
          </div>
          <div class="form-group">
            <label for="usr-fb-loc">Fallback Location (if Live GPS unavailable)</label>
            <select id="usr-fb-loc">${fbOpts}</select>
          </div>
        </div>

        <div class="form-group">
          <label>Watched Locations (for Multi-Location Mode)</label>
          <div class="checkboxes-wrap">${watchedChecks}</div>
        </div>

        <hr class="divider" />

        <div class="form-group">
          <label for="usr-sched-mode">2. Time Schedule &amp; Urgency Policy</label>
          <select id="usr-sched-mode">
            <option value="urgent_window_else_neutral" ${u.schedule_mode === 'urgent_window_else_neutral' ? 'selected' : ''}>🔔 Urgent Between Times, Neutral Outside (Recommended for Workdays)</option>
            <option value="active_window_only" ${u.schedule_mode === 'active_window_only' ? 'selected' : ''}>🕒 Only Between Times (Silent Outside Window)</option>
            <option value="always" ${u.schedule_mode === 'always' ? 'selected' : ''}>🌐 Always Active (24/7 with Default Urgency)</option>
          </select>
        </div>

        <div class="form-row-2">
          <div class="form-group">
            <label for="usr-win-start">Window Start (24h)</label>
            <input type="time" id="usr-win-start" value="${escapeHtml(u.window_start)}" required />
          </div>
          <div class="form-group">
            <label for="usr-win-end">Window End (24h)</label>
            <input type="time" id="usr-win-end" value="${escapeHtml(u.window_end)}" required />
          </div>
        </div>

        <div class="form-row-2">
          <div class="form-group">
            <label for="usr-def-urgency">Default Urgency</label>
            <select id="usr-def-urgency">
              <option value="urgent" ${u.default_urgency === 'urgent' ? 'selected' : ''}>Urgent (High Priority)</option>
              <option value="neutral" ${u.default_urgency === 'neutral' ? 'selected' : ''}>Neutral (Standard Priority)</option>
            </select>
          </div>
          <div class="form-group">
            <label for="usr-tz">User Timezone</label>
            <input type="text" id="usr-tz" list="iana-timezones-list" value="${escapeHtml(u.timezone || 'Europe/Amsterdam')}" required />
          </div>
        </div>

        <div class="form-group">
          <label>Active Days for Time Window</label>
          <div class="checkboxes-wrap">
            ${DAY_NAMES.map(
              (d, idx) => `
              <label class="checkbox-inline">
                <input type="checkbox" name="usr-day" value="${idx}" ${(u.active_days || []).includes(idx) ? 'checked' : ''} /> ${d}
              </label>
            `
            ).join('')}
          </div>
        </div>

        <hr class="divider" />

        <div class="form-group">
          <label class="checkbox-inline">
            <input type="checkbox" id="usr-ha-enabled" ${u.ha_notify_enabled ? 'checked' : ''} />
            <strong>3A. Enable Home Assistant Notify Channel</strong>
          </label>
          <div class="checkboxes-wrap">${notifyChecks || '<span class="field-help">No HA notify actions discovered yet.</span>'}</div>
        </div>

        <hr class="divider" />

        <div class="form-group">
          <label class="checkbox-inline">
            <input type="checkbox" id="usr-po-enabled" ${u.pushover_enabled ? 'checked' : ''} />
            <strong>3B. Enable Pushover Notification Channel (App API + User Key)</strong>
          </label>
        </div>

        <div class="form-row-2">
          <div class="form-group">
            <label for="usr-po-user">Pushover User / Group Key</label>
            <input type="text" id="usr-po-user" value="${escapeHtml(u.pushover_user_key || '')}" placeholder="e.g. uQiRzpo4DXghDmr9QzzfQu27cmVRsG" autocomplete="off" />
          </div>
          <div class="form-group">
            <label for="usr-po-token">Pushover App API Token (Optional override)</label>
            <input type="password" id="usr-po-token" value="${escapeHtml(u.pushover_app_token || '')}" placeholder="Leave blank to use Global App Token" autocomplete="off" />
          </div>
        </div>

        <div class="form-row-2">
          <div class="form-group">
            <label for="usr-po-prio">Pushover Priority When Urgent</label>
            <select id="usr-po-prio">
              <option value="1" ${Number(u.pushover_urgent_priority) === 1 ? 'selected' : ''}>High Priority (1 — Bypasses Quiet Hours)</option>
              <option value="2" ${Number(u.pushover_urgent_priority) === 2 ? 'selected' : ''}>Emergency Priority (2 — Repeats Until Acknowledged)</option>
              <option value="0" ${Number(u.pushover_urgent_priority) === 0 ? 'selected' : ''}>Normal Priority (0)</option>
            </select>
          </div>
          <div class="form-group">
            <label for="usr-po-sound">Pushover Sound</label>
            <select id="usr-po-sound">
              ${['pushover', 'bike', 'siren', 'climber', 'cosmic', 'intermission', 'magic', 'none']
                .map((s) => `<option value="${s}" ${u.pushover_sound === s ? 'selected' : ''}>${s}</option>`)
                .join('')}
            </select>
          </div>
        </div>

        <div class="form-row-2">
          <div class="form-group">
            <label class="checkbox-inline">
              <input type="checkbox" id="usr-cont-rain" ${u.continuous_rain_alerts ? 'checked' : ''} />
              Also alert on imminent rain outside scheduled breaks
            </label>
          </div>
          <div class="form-group">
            <label for="usr-rain-lead">Imminent Rain Lead Time (min)</label>
            <input type="number" id="usr-rain-lead" min="5" max="120" value="${u.rain_lead_minutes ?? 20}" />
          </div>
        </div>

        <div class="form-actions">
          <button type="button" class="btn btn-secondary" onclick="document.getElementById('app-modal').close()">Cancel</button>
          <button type="submit" class="btn btn-primary">${isEdit ? 'Save User Profile' : 'Create User Profile'}</button>
        </div>
      </form>
    `;

    openModal(isEdit ? `Configure User: ${u.name}` : 'Add User Profile', html);

    document.getElementById('modal-user-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const watched = Array.from(document.querySelectorAll('input[name="usr-watched-loc"]:checked')).map((c) => c.value);
        const haTargets = Array.from(document.querySelectorAll('input[name="usr-ha-target"]:checked')).map((c) => c.value);
        const days = Array.from(document.querySelectorAll('input[name="usr-day"]:checked')).map((c) => Number(c.value));

        const payload = {
          id: u.id || '',
          name: document.getElementById('usr-name').value.trim(),
          enabled: document.getElementById('usr-enabled').checked,
          ha_person_entity: document.getElementById('usr-person').value || null,
          location_mode: document.getElementById('usr-loc-mode').value,
          fixed_location_id: document.getElementById('usr-fixed-loc').value || null,
          fallback_location_id: document.getElementById('usr-fb-loc').value || null,
          watched_location_ids: watched,
          schedule_mode: document.getElementById('usr-sched-mode').value,
          window_start: document.getElementById('usr-win-start').value,
          window_end: document.getElementById('usr-win-end').value,
          active_days: days,
          default_urgency: document.getElementById('usr-def-urgency').value,
          timezone: document.getElementById('usr-tz').value.trim() || 'Europe/Amsterdam',
          continuous_rain_alerts: document.getElementById('usr-cont-rain').checked,
          rain_lead_minutes: Number(document.getElementById('usr-rain-lead').value || 20),
          ha_notify_enabled: document.getElementById('usr-ha-enabled').checked,
          ha_notify_targets: haTargets,
          pushover_enabled: document.getElementById('usr-po-enabled').checked,
          pushover_user_key: document.getElementById('usr-po-user').value.trim(),
          pushover_app_token: document.getElementById('usr-po-token').value.trim(),
          pushover_device: u.pushover_device || '',
          pushover_urgent_priority: Number(document.getElementById('usr-po-prio').value),
          pushover_sound: document.getElementById('usr-po-sound').value,
        };

        await apiPost('api/users', payload);
        closeModal();
        await refreshAll(true);
        showBanner(`User profile "${payload.name}" saved.`, 'success');
      } catch (err) {
        showBanner(`Failed to save user: ${err.message}`, 'error');
      }
    });
  }

  // --- Modal: Location Create/Edit ---
  function openLocationModal(existingLoc) {
    const isEdit = Boolean(existingLoc);
    const loc = existingLoc || {
      id: '',
      name: '',
      latitude: 52.0907,
      longitude: 5.1214,
      ha_zone_entity: '',
      enabled: true,
    };

    const presetButtons = CITY_PRESETS.map(
      (c) =>
        `<button type="button" class="btn btn-sm btn-secondary city-preset-btn" data-name="${escapeHtml(c.name)}" data-lat="${c.lat}" data-lon="${c.lon}">${escapeHtml(c.name)}</button>`
    ).join('');

    const html = `
      <form id="modal-loc-form" class="form-grid">
        <div class="form-group">
          <label for="loc-import-ha">⚡ 1-Click Import from Home Assistant</label>
          <select id="loc-import-ha">
            <option value="">-- Choose Discovered HA Zone or Person to Auto-Fill --</option>
            ${(state.discovered.zones || []).map((z) => `<option value="zone" data-name="${escapeHtml(z.name)}" data-lat="${z.latitude}" data-lon="${z.longitude}" data-entity="${escapeHtml(z.entity_id)}">📍 Zone: ${escapeHtml(z.name)} (${z.latitude.toFixed(4)}, ${z.longitude.toFixed(4)})</option>`).join('')}
            ${(state.discovered.persons || []).filter((p) => p.latitude !== null && p.longitude !== null).map((p) => `<option value="person" data-name="${escapeHtml(p.name)} Live GPS" data-lat="${p.latitude}" data-lon="${p.longitude}" data-entity="${escapeHtml(p.entity_id)}">👤 Person: ${escapeHtml(p.name)} (${p.latitude.toFixed(4)}, ${p.longitude.toFixed(4)})</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label>Quick City Presets</label>
          <div class="checkboxes-wrap">${presetButtons}</div>
        </div>
        <input type="hidden" id="loc-ha-entity" value="${escapeHtml(loc.ha_zone_entity || '')}" />
        <div class="form-group">
          <label for="loc-name">Location Name *</label>
          <input type="text" id="loc-name" value="${escapeHtml(loc.name)}" required placeholder="e.g. Work / Office" />
        </div>
        <div class="form-row-2">
          <div class="form-group">
            <label for="loc-lat">Latitude *</label>
            <input type="number" id="loc-lat" step="0.0001" min="-90" max="90" value="${loc.latitude}" required />
          </div>
          <div class="form-group">
            <label for="loc-lon">Longitude *</label>
            <input type="number" id="loc-lon" step="0.0001" min="-180" max="180" value="${loc.longitude}" required />
          </div>
        </div>
        <div class="form-group">
          <label class="checkbox-inline">
            <input type="checkbox" id="loc-enabled" ${loc.enabled ? 'checked' : ''} />
            Enable radar monitoring for this location
          </label>
        </div>
        <div class="form-actions">
          <button type="button" class="btn btn-secondary" onclick="document.getElementById('app-modal').close()">Cancel</button>
          <button type="submit" class="btn btn-primary">${isEdit ? 'Update Location' : 'Save Location'}</button>
        </div>
      </form>
    `;

    openModal(isEdit ? 'Edit Saved Location' : 'Add Saved Location', html);

    const haImportSel = document.getElementById('loc-import-ha');
    if (haImportSel) {
      haImportSel.addEventListener('change', () => {
        const opt = haImportSel.selectedOptions[0];
        if (opt && opt.getAttribute('data-name')) {
          document.getElementById('loc-name').value = opt.getAttribute('data-name');
          document.getElementById('loc-lat').value = opt.getAttribute('data-lat');
          document.getElementById('loc-lon').value = opt.getAttribute('data-lon');
          document.getElementById('loc-ha-entity').value = opt.getAttribute('data-entity') || '';
        }
      });
    }

    document.querySelectorAll('.city-preset-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const nameInput = document.getElementById('loc-name');
        if (!nameInput.value.trim()) {
          nameInput.value = btn.getAttribute('data-name');
        }
        document.getElementById('loc-lat').value = btn.getAttribute('data-lat');
        document.getElementById('loc-lon').value = btn.getAttribute('data-lon');
      });
    });

    document.getElementById('modal-loc-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const payload = {
          id: loc.id || '',
          name: document.getElementById('loc-name').value.trim(),
          latitude: Number(document.getElementById('loc-lat').value),
          longitude: Number(document.getElementById('loc-lon').value),
          ha_zone_entity: document.getElementById('loc-ha-entity').value.trim() || loc.ha_zone_entity || null,
          enabled: document.getElementById('loc-enabled').checked,
        };
        await apiPost('api/locations', payload);
        closeModal();
        await refreshAll(true);
        showBanner(`Location "${payload.name}" saved.`, 'success');
      } catch (err) {
        showBanner(`Location error: ${err.message}`, 'error');
      }
    });
  }

  // --- Global Public Handlers ---
  window.rainBreakApp = {
    editBreakModal: (breakId) => {
      const b = state.breaks.find((x) => x.id === breakId);
      if (b) openBreakModal(b);
    },
    deleteBreak: async (breakId) => {
      if (!confirm('Delete this break window?')) return;
      try {
        await apiDelete(`api/breaks/${breakId}`);
        await refreshAll(true);
        showBanner('Break window deleted.', 'info');
      } catch (err) {
        showBanner(`Delete failed: ${err.message}`, 'error');
      }
    },
    sendBreakAdviceNow: async (breakId) => {
      try {
        const res = await apiPost('api/evaluate/run', {
          break_id: breakId,
          send_notifications: true,
          ignore_dedup: true,
        });
        const recs = res.records || [];
        const submitted = recs.filter((r) => r.status === 'submitted').length;
        const failed = recs.filter((r) => r.status === 'failed').length;
        await refreshAll(false);
        if (submitted > 0 && failed === 0) {
          showBanner(`Submitted break advice to ${submitted} channel(s).`, 'success');
        } else if (submitted > 0 && failed > 0) {
          showBanner(`Partial dispatch: ${submitted} submitted, ${failed} failed.`, 'warning');
        } else {
          const detail = recs[0] ? recs[0].detail : 'No active channels configured.';
          showBanner(`Alert not sent: ${detail}`, 'warning');
        }
      } catch (err) {
        showBanner(`Failed to send break advice: ${err.message}`, 'error');
      }
    },
    toggleUser: async (userId, enabled) => {
      try {
        await apiPost(`api/users/${userId}/toggle`, { enabled });
        await refreshAll(false);
        showBanner(`User monitoring ${enabled ? 'activated' : 'paused'}.`, 'success');
      } catch (err) {
        showBanner(`Toggle error: ${err.message}`, 'error');
      }
    },
    editUserModal: (userId) => {
      const u = state.users.find((x) => x.id === userId);
      if (u) openUserModal(u);
    },
    deleteUser: async (userId) => {
      if (!confirm('Delete this user profile?')) return;
      try {
        await apiDelete(`api/users/${userId}`);
        await refreshAll(true);
        showBanner('User profile deleted.', 'info');
      } catch (err) {
        showBanner(`Delete error: ${err.message}`, 'error');
      }
    },
    testUserAlert: async (userId, urgency) => {
      try {
        const res = await apiPost('api/test-notification', { user_id: userId, urgency });
        await refreshAll(false);
        const s = res.summary || {};
        if (s.submitted > 0 && s.failed === 0) {
          showBanner(`Test (${urgency.toUpperCase()}) submitted to ${s.submitted} channel(s).`, 'success');
        } else if (s.submitted > 0) {
          showBanner(`Partial test result: ${s.submitted} submitted, ${s.failed} failed.`, 'warning');
        } else {
          const reason = (res.records && res.records[0] && res.records[0].detail) || 'Check channel settings.';
          showBanner(`Test notification failed/skipped: ${reason}`, 'error');
        }
      } catch (err) {
        showBanner(`Test error: ${err.message}`, 'error');
      }
    },
    editLocationModal: (locId) => {
      const l = state.locations.find((x) => x.id === locId);
      if (l) openLocationModal(l);
    },
    deleteLocation: async (locId) => {
      if (!confirm('Delete this saved location?')) return;
      try {
        await apiDelete(`api/locations/${locId}`);
        await refreshAll(true);
        showBanner('Location deleted.', 'info');
      } catch (err) {
        showBanner(`Delete error: ${err.message}`, 'error');
      }
    },
    importHaEntity: async (name, lat, lon, entityId, role) => {
      try {
        const primaryUser = state.users.find((u) => u.enabled) || state.users[0];
        await apiPost('api/locations/import-ha', {
          name,
          latitude: Number(lat),
          longitude: Number(lon),
          ha_zone_entity: entityId || null,
          role: role || null,
          user_id: primaryUser ? primaryUser.id : null,
        });
        await refreshAll(true);
        showBanner(`Imported "${name}" from Home Assistant${role ? ` and configured as ${role}` : ''}!`, 'success');
      } catch (err) {
        showBanner(`Import error: ${err.message}`, 'error');
      }
    },
  };

  // --- Wire Event Listeners ---
  if (el.btnSyncHa) {
    el.btnSyncHa.addEventListener('click', async () => {
      try {
        const res = await apiPost('api/ha/sync', {});
        await refreshAll(true);
        showBanner(
          `Synced Home Assistant (${res.persons_count} persons, ${res.zones_count} zones, ${res.notify_actions_count} notify actions).`,
          'success'
        );
      } catch (err) {
        showBanner(`Sync error: ${err.message}`, 'error');
      }
    });
  }

  if (el.btnUsersSyncHa) {
    el.btnUsersSyncHa.addEventListener('click', () => el.btnSyncHa.click());
  }

  if (el.btnRefreshNow) {
    el.btnRefreshNow.addEventListener('click', async () => {
      await refreshAll(true);
      showBanner('Precipitation radar and break evaluations refreshed.', 'info', 3500);
    });
  }

  if (el.btnAddBreak) el.btnAddBreak.addEventListener('click', () => openBreakModal(null));
  if (el.btnDashAddBreak) el.btnDashAddBreak.addEventListener('click', () => openBreakModal(null));
  if (el.btnAddUser) el.btnAddUser.addEventListener('click', () => openUserModal(null));
  if (el.btnAddLocation) el.btnAddLocation.addEventListener('click', () => openLocationModal(null));

  if (el.btnPresetCommute) {
    el.btnPresetCommute.addEventListener('click', async () => {
      try {
        const primaryUser = state.users.find((u) => u.enabled) || state.users[0];
        if (!primaryUser) {
          showBanner('Please create a user profile first.', 'warning');
          return;
        }
        await apiPost('api/breaks/preset', {
          user_id: primaryUser.id,
          preset: 'commute_and_workday',
        });
        await refreshAll(true);
        showBanner(`Loaded Commute & Workday Routine (08:00 Commute, 10:00 Walk, 12:30 Lunch, 15:00 Break, 17:00 Commute) for ${primaryUser.name}.`, 'success');
      } catch (err) {
        showBanner(`Preset error: ${err.message}`, 'error');
      }
    });
  }

  if (el.btnPresetWorkday) {
    el.btnPresetWorkday.addEventListener('click', async () => {
      try {
        const primaryUser = state.users.find((u) => u.enabled) || state.users[0];
        if (!primaryUser) {
          showBanner('Please create a user profile first.', 'warning');
          return;
        }
        await apiPost('api/breaks/preset', {
          user_id: primaryUser.id,
          preset: 'workday_3_breaks',
        });
        await refreshAll(true);
        showBanner(`Loaded 10:00 (15m), 12:30 (30m), and 15:00 (15m) workday breaks for ${primaryUser.name}.`, 'success');
      } catch (err) {
        showBanner(`Preset error: ${err.message}`, 'error');
      }
    });
  }

  if (el.btnEvaluateAll) {
    el.btnEvaluateAll.addEventListener('click', async () => {
      try {
        const res = await apiPost('api/evaluate/run', {
          send_notifications: true,
          ignore_dedup: true,
        });
        const recs = res.records || [];
        const submitted = recs.filter((r) => r.status === 'submitted').length;
        await refreshAll(false);
        showBanner(
          `Evaluated ${res.evaluations.length} break window(s) — ${submitted} notification(s) dispatched.`,
          submitted > 0 ? 'success' : 'info'
        );
      } catch (err) {
        showBanner(`Evaluation error: ${err.message}`, 'error');
      }
    });
  }

  if (el.configForm) {
    el.configForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const payload = {
          default_timezone: el.cfgTimezone.value.trim() || 'Europe/Amsterdam',
          weather_provider: el.cfgWeatherProvider.value,
          rain_threshold_mm: Number(el.cfgRainThreshold.value),
          heavy_rain_threshold_mm: Number(el.cfgHeavyThreshold.value),
          pushover_app_token: el.cfgPushoverToken.value.trim(),
          background_monitoring_enabled: el.cfgBgMonitoring.checked,
          dedup_cooldown_minutes: Number(el.cfgDedupMinutes.value),
        };
        await apiPost('api/config', payload);
        await refreshAll(true);
        showBanner('Global settings saved.', 'success');
      } catch (err) {
        showBanner(`Settings error: ${err.message}`, 'error');
      }
    });
  }

  el.simButtons.forEach((btn) => {
    btn.addEventListener('click', async () => {
      const scenario = btn.getAttribute('data-scenario');
      try {
        await apiPost('api/demo/scenario', { scenario });
        await refreshAll(true);
        showBanner(`Simulated radar scenario "${scenario}" applied — inspect the Radar & Break Advisor tab!`, 'info');
      } catch (err) {
        showBanner(`Simulator error: ${err.message}`, 'error');
      }
    });
  });

  if (el.quickTestForm) {
    el.quickTestForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const uid = el.testUserId.value;
      const urg = el.testUrgency.value;
      const customMsg = el.testCustomMsg.value.trim() || null;
      try {
        const res = await apiPost('api/test-notification', {
          user_id: uid,
          urgency: urg,
          custom_message: customMsg,
        });
        await refreshAll(false);
        const s = res.summary || {};
        if (s.submitted > 0 && s.failed === 0) {
          showBanner(`Dispatched ${urg.toUpperCase()} test alert (${s.submitted} channel(s) submitted).`, 'success');
        } else if (s.submitted > 0) {
          showBanner(`Partial outcome: ${s.submitted} submitted, ${s.failed} failed.`, 'warning');
        } else {
          const detail = (res.records && res.records[0] && res.records[0].detail) || 'No channels configured.';
          showBanner(`Test alert not sent: ${detail}`, 'error');
        }
      } catch (err) {
        showBanner(`Test dispatch error: ${err.message}`, 'error');
      }
    });
  }

  if (el.btnClearHistory) {
    el.btnClearHistory.addEventListener('click', async () => {
      if (!confirm('Clear alert delivery history?')) return;
      await apiDelete('api/history');
      await refreshAll(false);
      showBanner('Alert history cleared.', 'info');
    });
  }

  // --- Boot ---
  initTabs();
  refreshAll(false);
})();
