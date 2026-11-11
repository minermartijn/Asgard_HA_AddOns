/**
 * ASGARD NotifyHub - Frontend Application Logic (v0.1.5)
 */

(function () {
  'use strict';

  // --- Centralized API URL Resolver for Home Assistant Ingress & Direct Access ---
  function getApiUrl(endpoint) {
    if (!endpoint) return '';
    const clean = String(endpoint).replace(/^\/+/, '');
    if (window.__INGRESS_BASE__) {
      return `${window.__INGRESS_BASE__.replace(/\/+$/, '')}/${clean}`;
    }
    const ingressMatch = window.location.pathname.match(/^(\/api\/hassio_ingress\/[^\/]+)/);
    if (ingressMatch) {
      return `${ingressMatch[1]}/${clean}`;
    }
    let dir = window.location.pathname || '/';
    if (dir.endsWith('/index.html')) {
      dir = dir.slice(0, -10);
    }
    if (!dir.endsWith('/')) {
      dir += '/';
    }
    return `${dir}${clean}`;
  }

  // --- Strict Client-Side Action Allowlist Helper ---
  const BLOCKED_NOTIFY_SERVICES = new Set(['send_message']);
  const ALLOWED_PERSISTENT_SERVICES = new Set(['create']);

  function isAllowedAction(domain, service) {
    const d = String(domain || '').trim().toLowerCase();
    const s = String(service || '').trim().toLowerCase();
    if (!s || !/^[a-z0-9_]+$/.test(s)) return false;
    if (d === 'notify') return !BLOCKED_NOTIFY_SERVICES.has(s);
    if (d === 'persistent_notification') return ALLOWED_PERSISTENT_SERVICES.has(s);
    return false;
  }

  // --- Delivery Status Metadata ---
  const STATUS_META = {
    submitted: {
      label: 'Submitted to HA',
      previewLabel: 'Will Submit to HA',
      badgeClass: 'status-ok',
      rowClass: 'outcome-submitted',
      category: 'submitted',
      defaultDetail: 'Submitted to Home Assistant action (physical device delivery depends on integration)',
    },
    blocked_quiet_hours: {
      label: 'Silenced · Quiet Hours',
      previewLabel: 'Silenced · Quiet Hours',
      badgeClass: 'status-warning',
      rowClass: 'outcome-warning',
      category: 'suppressed',
      defaultDetail: 'Suppressed by active quiet hours policy',
    },
    suppressed_duplicate: {
      label: 'Suppressed · Duplicate',
      previewLabel: 'Suppressed · Duplicate',
      badgeClass: 'status-warning',
      rowClass: 'outcome-warning',
      category: 'suppressed',
      defaultDetail: 'Suppressed as duplicate within deduplication window',
    },
    blocked_priority: {
      label: 'Blocked · Min Priority',
      previewLabel: 'Blocked · Min Priority',
      badgeClass: 'status-warning',
      rowClass: 'outcome-warning',
      category: 'suppressed',
      defaultDetail: 'Blocked because message priority is below route minimum priority',
    },
    route_disabled: {
      label: 'Skipped · Route Disabled',
      previewLabel: 'Skipped · Route Disabled',
      badgeClass: 'status-secondary',
      rowClass: 'outcome-warning',
      category: 'suppressed',
      defaultDetail: 'Route is disabled in NotifyHub',
    },
    recipient_disabled: {
      label: 'Skipped · Recipient Disabled',
      previewLabel: 'Skipped · Recipient Disabled',
      badgeClass: 'status-secondary',
      rowClass: 'outcome-warning',
      category: 'suppressed',
      defaultDetail: 'Recipient is disabled in NotifyHub',
    },
    invalid_route: {
      label: 'Blocked · Unsupported Route',
      previewLabel: 'Blocked · Unsupported Route',
      badgeClass: 'status-danger',
      rowClass: 'outcome-danger',
      category: 'failed',
      defaultDetail: 'Route targets an unsupported or disallowed Home Assistant action',
    },
    failed: {
      label: 'Failed · HA Rejected',
      previewLabel: 'Failed',
      badgeClass: 'status-danger',
      rowClass: 'outcome-danger',
      category: 'failed',
      defaultDetail: 'Home Assistant rejected the notification action call',
    },
  };

  function getStatusMeta(status) {
    const key = String(status || '').toLowerCase();
    if (STATUS_META[key]) return STATUS_META[key];
    if (key === 'silenced') return STATUS_META.blocked_quiet_hours;
    if (key === 'skipped_dedup') return STATUS_META.suppressed_duplicate;
    return {
      label: status || 'Unknown',
      previewLabel: status || 'Unknown',
      badgeClass: 'status-unknown',
      rowClass: 'outcome-warning',
      category: 'suppressed',
      defaultDetail: String(status || ''),
    };
  }

  // --- Aggregate Dispatch Outcome Honestly ---
  function summarizeDispatch(records) {
    const list = Array.isArray(records) ? records : [];
    const counts = {
      submitted: 0,
      blocked_quiet_hours: 0,
      suppressed_duplicate: 0,
      blocked_priority: 0,
      route_disabled: 0,
      recipient_disabled: 0,
      invalid_route: 0,
      failed: 0,
    };

    list.forEach((r) => {
      const k = String(r.status || '').toLowerCase();
      if (Object.prototype.hasOwnProperty.call(counts, k)) {
        counts[k] += 1;
      } else if (k === 'silenced') {
        counts.blocked_quiet_hours += 1;
      } else if (k === 'skipped_dedup') {
        counts.suppressed_duplicate += 1;
      } else {
        counts.failed += 1;
      }
    });

    const total = list.length;
    const submitted = counts.submitted;
    const failedTotal = counts.failed + counts.invalid_route;
    const suppressedTotal =
      counts.blocked_quiet_hours +
      counts.suppressed_duplicate +
      counts.blocked_priority +
      counts.route_disabled +
      counts.recipient_disabled;

    const parts = [];
    if (counts.submitted > 0) parts.push(`${counts.submitted} submitted to Home Assistant`);
    if (counts.blocked_quiet_hours > 0) parts.push(`${counts.blocked_quiet_hours} silenced by quiet hours`);
    if (counts.suppressed_duplicate > 0) parts.push(`${counts.suppressed_duplicate} suppressed as duplicate`);
    if (counts.blocked_priority > 0) parts.push(`${counts.blocked_priority} blocked by minimum priority`);
    if (counts.route_disabled > 0) parts.push(`${counts.route_disabled} skipped (route disabled)`);
    if (counts.recipient_disabled > 0) parts.push(`${counts.recipient_disabled} skipped (recipient disabled)`);
    if (counts.invalid_route > 0) parts.push(`${counts.invalid_route} blocked (unsupported route)`);
    if (counts.failed > 0) parts.push(`${counts.failed} failed Home Assistant action`);

    const breakdown = parts.join(', ');

    if (total === 0) {
      return {
        outcome: 'no_routes',
        bannerType: 'warning',
        bannerText: 'Not sent: no routes matched the selected target.',
        badgeText: 'No Routes Matched',
        badgeClass: 'panel-tag status-warning',
        summaryBarText: '0 routes evaluated. Add or enable a route for this target.',
        submitted,
        suppressedTotal,
        failedTotal,
        total,
        counts,
      };
    }

    if (submitted === total) {
      return {
        outcome: 'submitted',
        bannerType: 'success',
        bannerText: `Submitted to Home Assistant: ${submitted} of ${total} route(s) accepted by Home Assistant (device delivery is handled by the HA integration).`,
        badgeText: `Submitted (${submitted}/${total})`,
        badgeClass: 'panel-tag status-ok',
        summaryBarText: `All ${submitted} route(s) submitted to Home Assistant.`,
        submitted,
        suppressedTotal,
        failedTotal,
        total,
        counts,
      };
    }

    if (submitted > 0) {
      return {
        outcome: 'partial',
        bannerType: 'warning',
        bannerText: `Partial outcome (${submitted} of ${total} submitted to Home Assistant): ${breakdown}.`,
        badgeText: `Partial (${submitted}/${total} submitted)`,
        badgeClass: 'panel-tag status-warning',
        summaryBarText: `Mixed results: ${breakdown}.`,
        submitted,
        suppressedTotal,
        failedTotal,
        total,
        counts,
      };
    }

    if (failedTotal > 0 && suppressedTotal === 0) {
      return {
        outcome: 'failed',
        bannerType: 'error',
        bannerText: `Submission failed (0 submitted to Home Assistant): ${breakdown}.`,
        badgeText: `Failed (${failedTotal})`,
        badgeClass: 'panel-tag status-danger',
        summaryBarText: `0 submitted to Home Assistant — ${breakdown}.`,
        submitted,
        suppressedTotal,
        failedTotal,
        total,
        counts,
      };
    }

    if (failedTotal > 0 && suppressedTotal > 0) {
      return {
        outcome: 'failed_and_suppressed',
        bannerType: 'warning',
        bannerText: `Not submitted (0 of ${total} submitted to Home Assistant): ${breakdown}.`,
        badgeText: '0 Submitted · Mixed Errors/Policy',
        badgeClass: 'panel-tag status-warning',
        summaryBarText: `0 submitted to Home Assistant — ${breakdown}.`,
        submitted,
        suppressedTotal,
        failedTotal,
        total,
        counts,
      };
    }

    return {
      outcome: 'suppressed',
      bannerType: 'warning',
      bannerText: `Notification not sent (0 submitted to Home Assistant): ${breakdown}.`,
      badgeText: `Suppressed (${suppressedTotal})`,
      badgeClass: 'panel-tag status-warning',
      summaryBarText: `0 submitted to Home Assistant — ${breakdown}.`,
      submitted,
      suppressedTotal,
      failedTotal,
      total,
      counts,
    };
  }

  // --- State ---
  const state = {
    services: [],
    recipients: [],
    groups: [],
    policies: [],
    history: [],
    summary: null,
    defaultTimezone: 'Europe/Amsterdam',
    targetMode: 'recipient',
  };

  // --- DOM Elements ---
  const el = {
    haStatusBadge: document.getElementById('ha-status-badge'),
    btnRefreshServices: document.getElementById('btn-refresh-services'),
    statusBanner: document.getElementById('status-banner'),
    tabs: document.querySelectorAll('.tab-btn'),
    tabPanes: document.querySelectorAll('.tab-pane'),

    // Dashboard Overview
    cardHaBadge: document.getElementById('card-ha-badge'),
    statHaConn: document.getElementById('stat-ha-conn'),
    statServicesCount: document.getElementById('stat-services-count'),
    statSubmissions: document.getElementById('stat-submissions'),
    statQuiet: document.getElementById('stat-quiet'),
    statRecipients: document.getElementById('stat-recipients'),
    statRoutesHint: document.getElementById('stat-routes-hint'),
    tagDiscoveredCount: document.getElementById('tag-discovered-count'),
    dashboardServicesList: document.getElementById('dashboard-services-list'),

    // Composer
    composerForm: document.getElementById('composer-form'),
    compTargetModes: document.getElementById('comp-target-modes'),
    compModeRadios: document.querySelectorAll('input[name="comp-target-mode"]'),
    compModeLabels: document.querySelectorAll('.segment-option[data-target-mode]'),
    compGroupRecipientWrap: document.getElementById('comp-group-recipient-wrap'),
    compRecipientId: document.getElementById('comp-recipient-id'),
    compGroupSelectWrap: document.getElementById('comp-group-select-wrap'),
    compGroupId: document.getElementById('comp-group-id'),
    compEveryoneWrap: document.getElementById('comp-everyone-wrap'),
    compEveryoneDesc: document.getElementById('comp-everyone-desc'),
    compTargetSummary: document.getElementById('comp-target-summary'),
    compPriority: document.getElementById('comp-priority'),
    compTitle: document.getElementById('comp-title'),
    compMessage: document.getElementById('comp-message'),
    btnPreviewSend: document.getElementById('btn-preview-send'),
    previewSummaryBar: document.getElementById('preview-summary-bar'),
    previewResultsContainer: document.getElementById('preview-results-container'),
    previewBadge: document.getElementById('preview-badge'),

    // Recipients
    recipientsContainer: document.getElementById('recipients-container'),
    btnAddRecipient: document.getElementById('btn-add-recipient'),

    // Groups
    groupsContainer: document.getElementById('groups-container'),
    btnAddGroup: document.getElementById('btn-add-group'),

    // Policies
    policiesContainer: document.getElementById('policies-container'),
    btnAddPolicy: document.getElementById('btn-add-policy'),

    // History
    historyTable: document.getElementById('history-table'),
    historyTbody: document.getElementById('history-tbody'),
    historyCards: document.getElementById('history-cards'),
    btnRefreshHistory: document.getElementById('btn-refresh-history'),
    btnPurgeHistory: document.getElementById('btn-purge-history'),

    // Modal
    appModal: document.getElementById('app-modal'),
    modalTitle: document.getElementById('modal-title'),
    modalBody: document.getElementById('modal-body'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
  };

  // --- Helper: Format Dates safely ---
  function formatDate(isoStr) {
    if (!isoStr) return '–';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return String(isoStr);
      return new Intl.DateTimeFormat(undefined, {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }).format(d);
    } catch {
      return String(isoStr);
    }
  }

  // --- Helper: Escape HTML ---
  function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
  }

  // --- Notification Banner ---
  let bannerTimer = null;
  function showBanner(message, type = 'error', durationMs = 7000) {
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

  // --- API Client ---
  async function apiGet(endpoint) {
    const url = getApiUrl(endpoint);
    try {
      const res = await fetch(url, { credentials: 'same-origin' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      return res.json();
    } catch (netErr) {
      console.warn(`API GET failed for ${url}:`, netErr);
      throw netErr;
    }
  }

  async function apiPost(endpoint, body) {
    const url = getApiUrl(endpoint);
    try {
      const res = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      return res.json();
    } catch (netErr) {
      console.warn(`API POST failed for ${url}:`, netErr);
      throw netErr;
    }
  }

  async function apiDelete(endpoint) {
    const url = getApiUrl(endpoint);
    try {
      const res = await fetch(url, { method: 'DELETE', credentials: 'same-origin' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      return res.json();
    } catch (netErr) {
      console.warn(`API DELETE failed for ${url}:`, netErr);
      throw netErr;
    }
  }

  // --- Tab Navigation ---
  function initTabs() {
    el.tabs.forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');
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
        const activePane = document.getElementById(targetTab);
        if (activePane) {
          activePane.classList.add('active');
          activePane.hidden = false;
        }

        if (targetTab === 'tab-history') {
          loadHistory();
        }
      });
    });
  }

  // --- Modal Helpers ---
  function openModal(title, contentHtml) {
    el.modalTitle.textContent = title;
    el.modalBody.innerHTML = contentHtml;
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
      if (e.target.closest('.modal-content')) {
        return;
      }
      if (e.target === el.appModal) {
        closeModal();
      }
    });

    el.appModal.addEventListener('close', () => {
      el.modalBody.innerHTML = '';
    });
  }

  // --- Clean Friendly Service Name & Optional Description ---
  function formatDiscoveredService(svc) {
    const full = svc.full_name || `${svc.ha_domain}.${svc.ha_service}`;
    let friendly = String(svc.display_name || full).trim();
    let extraDesc = svc.description ? String(svc.description).trim() : '';

    // Clean verbose boilerplate HA strings like "Send a notification via mobile_app_..."
    const viaMatch = friendly.match(/^Send a notification (?:via|with)\s+([a-zA-Z0-9_.-]+)$/i);
    if (viaMatch) {
      friendly = viaMatch[1].replace(/^mobile_app_/, 'Mobile App: ');
    }
    // Strip trailing "(notify.xyz)" if already shown in the technical code pill
    friendly = friendly.replace(/\s*\(notify\.[a-z0-9_]+\)\s*$/i, '').trim() || full;

    const isEntity = svc.target_type === 'entity';
    const typeLabel =
      svc.ha_domain === 'persistent_notification'
        ? 'HA UI Banner'
        : isEntity
          ? 'Notify Entity'
          : 'Notify Service';
    const typeBadgeClass = isEntity ? 'status-info' : 'status-secondary';

    // Show expandable details only when there is a meaningful description beyond "Notification entity: ..."
    const hasLongDesc =
      extraDesc &&
      !extraDesc.toLowerCase().startsWith('notification entity:') &&
      extraDesc.toLowerCase() !== friendly.toLowerCase();

    return {
      full,
      friendly,
      typeLabel,
      typeBadgeClass,
      isEntity,
      hasLongDesc,
      extraDesc,
      preferredAlt: svc.preferred_alternative || null,
    };
  }

  // --- Render Overview ---
  function renderOverview() {
    if (!state.summary) return;
    const s = state.summary;

    if (s.default_timezone) {
      state.defaultTimezone = s.default_timezone;
    }

    let haStatus = 'Checking…';
    let haClass = 'status-unknown';

    if (s.demo_mode) {
      haStatus = 'Demo Mode';
      haClass = 'status-ok';
    } else if (s.ha_connected) {
      haStatus = 'Connected';
      haClass = 'status-ok';
    } else {
      haStatus = s.ha_error ? `Disconnected (${s.ha_error})` : 'Offline / Token Missing';
      haClass = 'status-danger';
    }

    if (el.haStatusBadge) {
      el.haStatusBadge.textContent = haStatus;
      el.haStatusBadge.className = `status-badge ${haClass}`;
    }
    if (el.cardHaBadge) {
      el.cardHaBadge.textContent = s.ha_connected ? (s.demo_mode ? 'DEMO' : 'OK') : 'FAIL';
      el.cardHaBadge.className = `status-badge ${haClass}`;
    }
    if (el.statHaConn) el.statHaConn.textContent = haStatus;
    const allowedServices = state.services.filter((svc) => isAllowedAction(svc.ha_domain, svc.ha_service));
    const svcCount = allowedServices.length;
    if (el.statServicesCount) el.statServicesCount.textContent = `${svcCount} notify actions discovered`;
    if (el.statSubmissions) el.statSubmissions.textContent = String(s.submissions_24h ?? 0);
    const quietCount = s.blocked_quiet_hours_24h ?? s.quiet_silenced_24h ?? 0;
    if (el.statQuiet) el.statQuiet.textContent = String(quietCount);
    if (el.statRecipients) el.statRecipients.textContent = String(s.recipients_count ?? 0);
    if (el.statRoutesHint) el.statRoutesHint.textContent = `${s.routes_count ?? 0} active routes mapped`;
    if (el.tagDiscoveredCount) el.tagDiscoveredCount.textContent = `${svcCount} discovered`;

    if (el.dashboardServicesList) {
      if (allowedServices.length === 0) {
        const msg = s.ha_error || 'No Home Assistant notify services detected or connection pending.';
        el.dashboardServicesList.innerHTML = `<p class="hint">${escapeHtml(msg)}</p>`;
      } else {
        el.dashboardServicesList.innerHTML = allowedServices
          .map((svc) => {
            const info = formatDiscoveredService(svc);
            return `
              <div class="service-chip">
                <div class="service-chip-top">
                  <span class="chip-name">${escapeHtml(info.friendly)}</span>
                  <div class="chip-badges">
                    <span class="status-badge ${info.typeBadgeClass}">${escapeHtml(info.typeLabel)}</span>
                  </div>
                </div>
                <code class="chip-code">${escapeHtml(info.full)}</code>
                ${
                  info.preferredAlt
                    ? `<div class="service-alt-hint">Companion action <code>${escapeHtml(info.preferredAlt)}</code> is also available (recommended for Wear OS / mobile push).</div>`
                    : ''
                }
                ${
                  info.hasLongDesc
                    ? `<details class="service-desc-toggle"><summary>Description</summary><p>${escapeHtml(info.extraDesc)}</p></details>`
                    : `<span class="chip-desc">${escapeHtml(info.isEntity ? 'Invoked via notify.send_message' : 'Direct Home Assistant notify action')}</span>`
                }
              </div>
            `;
          })
          .join('');
      }
    }
  }

  // --- Composer Target Mode & Confirmation ---
  function setComposerTargetMode(mode) {
    const validMode = ['recipient', 'group', 'all'].includes(mode) ? mode : 'recipient';
    state.targetMode = validMode;

    el.compModeLabels.forEach((lbl) => {
      const m = lbl.getAttribute('data-target-mode');
      lbl.classList.toggle('active', m === validMode);
    });
    el.compModeRadios.forEach((radio) => {
      radio.checked = radio.value === validMode;
    });

    if (el.compGroupRecipientWrap && el.compRecipientId) {
      const showRec = validMode === 'recipient';
      el.compGroupRecipientWrap.hidden = !showRec;
      el.compRecipientId.disabled = !showRec;
    }

    if (el.compGroupSelectWrap && el.compGroupId) {
      const showGrp = validMode === 'group';
      el.compGroupSelectWrap.hidden = !showGrp;
      el.compGroupId.disabled = !showGrp;
    }

    if (el.compEveryoneWrap) {
      el.compEveryoneWrap.hidden = validMode !== 'all';
    }

    updateComposerTargetConfirmation();
  }

  function updateComposerTargetConfirmation() {
    if (!el.compTargetSummary) return;
    const mode = state.targetMode;

    if (mode === 'recipient') {
      const recId = el.compRecipientId ? el.compRecipientId.value : '';
      const rec = state.recipients.find((r) => r.id === recId) || state.recipients[0];
      if (!rec) {
        el.compTargetSummary.textContent = 'Sending to: No recipient configured';
        return;
      }
      const totalRoutes = (rec.routes || []).length;
      const activeRoutes = (rec.routes || []).filter((rt) => rt.enabled).length;
      const routeWord = activeRoutes === 1 ? 'route' : 'routes';
      const statusSuffix = !rec.enabled
        ? ' (recipient disabled)'
        : totalRoutes !== activeRoutes
          ? ` (${totalRoutes - activeRoutes} disabled)`
          : '';
      el.compTargetSummary.textContent = `Sending to: ${rec.name} — ${activeRoutes} ${routeWord}${statusSuffix}`;
      return;
    }

    if (mode === 'group') {
      const grpId = el.compGroupId ? el.compGroupId.value : '';
      const grp = state.groups.find((g) => g.id === grpId) || state.groups[0];
      if (!grp) {
        el.compTargetSummary.textContent = 'Sending to: No group configured';
        return;
      }
      const count = (grp.recipient_ids || []).length;
      const recWord = count === 1 ? 'recipient' : 'recipients';
      el.compTargetSummary.textContent = `Sending to: ${grp.name} — ${count} ${recWord}`;
      return;
    }

    // Everyone (broadcast to all enabled recipients)
    const enabledRecs = state.recipients.filter((r) => r.enabled);
    const activeRoutes = enabledRecs.reduce(
      (sum, r) => sum + (r.routes || []).filter((rt) => rt.enabled).length,
      0
    );
    const recWord = enabledRecs.length === 1 ? 'recipient' : 'recipients';
    const routeWord = activeRoutes === 1 ? 'route' : 'routes';
    if (el.compEveryoneDesc) {
      const names = enabledRecs.map((r) => r.name).join(', ');
      el.compEveryoneDesc.textContent = enabledRecs.length
        ? `Includes all ${enabledRecs.length} enabled ${recWord} (${names}) across ${activeRoutes} active ${routeWord}. Disabled recipients are excluded.`
        : 'No enabled recipients are currently configured.';
    }
    el.compTargetSummary.textContent = `Sending to: Everyone — all ${enabledRecs.length} enabled ${recWord} (${activeRoutes} active ${routeWord})`;
  }

  function renderComposerSelects() {
    if (el.compRecipientId) {
      const prevRec = el.compRecipientId.value;
      el.compRecipientId.innerHTML = state.recipients
        .map((r) => {
          const activeCount = (r.routes || []).filter((rt) => rt.enabled).length;
          const labelSuffix = r.enabled ? `${activeCount} route${activeCount === 1 ? '' : 's'}` : 'disabled';
          return `<option value="${escapeHtml(r.id)}">${escapeHtml(r.name)} (${labelSuffix})</option>`;
        })
        .join('');
      if (prevRec && state.recipients.some((r) => r.id === prevRec)) {
        el.compRecipientId.value = prevRec;
      }
    }

    if (el.compGroupId) {
      const prevGrp = el.compGroupId.value;
      el.compGroupId.innerHTML = state.groups
        .map((g) => {
          const count = (g.recipient_ids || []).length;
          return `<option value="${escapeHtml(g.id)}">${escapeHtml(g.name)} (${count} member${count === 1 ? '' : 's'})</option>`;
        })
        .join('');
      if (prevGrp && state.groups.some((g) => g.id === prevGrp)) {
        el.compGroupId.value = prevGrp;
      }
    }

    updateComposerTargetConfirmation();
  }

  function initComposer() {
    el.compModeRadios.forEach((radio) => {
      radio.addEventListener('change', () => {
        if (radio.checked) {
          setComposerTargetMode(radio.value);
        }
      });
    });

    el.compModeLabels.forEach((lbl) => {
      lbl.addEventListener('click', () => {
        const mode = lbl.getAttribute('data-target-mode');
        setComposerTargetMode(mode);
      });
    });

    if (el.compRecipientId) {
      el.compRecipientId.addEventListener('change', updateComposerTargetConfirmation);
    }
    if (el.compGroupId) {
      el.compGroupId.addEventListener('change', updateComposerTargetConfirmation);
    }

    setComposerTargetMode(state.targetMode);

    // Preview click handler
    if (el.btnPreviewSend) {
      el.btnPreviewSend.addEventListener('click', async () => {
        try {
          const payload = getComposerPayload();
          if (!payload.message) {
            payload.message = '(Dry-run preview message)';
          }
          const res = await apiPost('api/send/preview', payload);
          renderPreviewResults(res);
        } catch (err) {
          showBanner(`Preview error: ${err.message}`, 'error');
        }
      });
    }

    // Submit handler
    if (el.composerForm) {
      el.composerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const payload = getComposerPayload();
          if (!payload.message.trim()) {
            showBanner('Please enter a notification message body.', 'warning');
            return;
          }
          const res = await apiPost('api/send', payload);
          const records = res.records || [];
          const summary = summarizeDispatch(records);

          showBanner(summary.bannerText, summary.bannerType, 8000);
          if (summary.submitted > 0) {
            el.compMessage.value = '';
          }
          await refreshAllData();
          renderPreviewFromRecords(records, summary);
        } catch (err) {
          showBanner(`Dispatch error: ${err.message}`, 'error');
        }
      });
    }
  }

  function getComposerPayload() {
    const targetType = state.targetMode || 'recipient';
    let targetId = null;
    if (targetType === 'recipient') {
      targetId = el.compRecipientId ? el.compRecipientId.value : null;
    } else if (targetType === 'group') {
      targetId = el.compGroupId ? el.compGroupId.value : null;
    }

    return {
      target_type: targetType,
      target_id: targetId,
      recipient_id: targetType === 'recipient' ? targetId : null,
      group_id: targetType === 'group' ? targetId : null,
      priority: el.compPriority ? el.compPriority.value : 'normal',
      title: el.compTitle && el.compTitle.value.trim() ? el.compTitle.value.trim() : null,
      message: el.compMessage ? el.compMessage.value.trim() : '',
    };
  }

  function renderPreviewResults(preview) {
    if (!el.previewResultsContainer) return;
    const items = (preview && preview.items) || [];
    const summary = summarizeDispatch(items);

    el.previewBadge.textContent = `Dry-Run · ${summary.submitted}/${summary.total} Will Submit`;
    el.previewBadge.className = 'panel-tag status-info';

    if (el.previewSummaryBar) {
      el.previewSummaryBar.hidden = false;
      el.previewSummaryBar.textContent =
        items.length === 0
          ? 'Dry-run result: 0 routes matched the target selection.'
          : `Dry-run simulation: ${summary.submitted} will submit to Home Assistant, ${summary.suppressedTotal} suppressed/blocked by policy, ${summary.failedTotal} invalid route(s).`;
    }

    if (items.length === 0) {
      el.previewResultsContainer.innerHTML =
        '<p class="hint">No routes match the target criteria or the target has no routes configured.</p>';
      return;
    }

    el.previewResultsContainer.innerHTML = items
      .map((item) => {
        const meta = getStatusMeta(item.status);
        return `
          <div class="preview-item ${meta.rowClass}" data-status="${escapeHtml(item.status)}">
            <div class="preview-item-head">
              <span class="preview-target"><strong>${escapeHtml(item.recipient_name)}</strong> &rarr; <code>${escapeHtml(item.service_target || item.ha_service)}</code></span>
              <span class="status-badge ${meta.badgeClass}">${escapeHtml(meta.previewLabel)}</span>
            </div>
            <p class="preview-reason">${escapeHtml(item.reason || meta.defaultDetail)}</p>
          </div>
        `;
      })
      .join('');
  }

  function renderPreviewFromRecords(records, precomputedSummary) {
    if (!el.previewResultsContainer) return;
    const list = Array.isArray(records) ? records : [];
    const summary = precomputedSummary || summarizeDispatch(list);

    el.previewBadge.textContent = summary.badgeText;
    el.previewBadge.className = summary.badgeClass;

    if (el.previewSummaryBar) {
      el.previewSummaryBar.hidden = false;
      el.previewSummaryBar.textContent = summary.summaryBarText;
    }

    if (list.length === 0) {
      el.previewResultsContainer.innerHTML = '<p class="hint">No routes matched the selected target.</p>';
      return;
    }

    el.previewResultsContainer.innerHTML = list
      .map((r) => {
        const meta = getStatusMeta(r.status);
        const actionName = r.ha_domain ? `${r.ha_domain}.${r.ha_service}` : r.ha_service;
        return `
          <div class="preview-item ${meta.rowClass}" data-status="${escapeHtml(r.status)}">
            <div class="preview-item-head">
              <span class="preview-target"><strong>${escapeHtml(r.recipient_name || r.recipient_id)}</strong> &rarr; <code>${escapeHtml(actionName)}</code></span>
              <span class="status-badge ${meta.badgeClass}">${escapeHtml(meta.label)}</span>
            </div>
            <p class="preview-reason">${escapeHtml(r.details || meta.defaultDetail)}</p>
          </div>
        `;
      })
      .join('');
  }

  // --- Timezone Preset Helper inside Modals ---
  const TZ_PRESETS = ['Europe/Amsterdam', 'UTC', 'Europe/Brussels', 'Europe/Berlin', 'Europe/London'];

  function renderTzPresetsHtml(inputId, currentTz) {
    return `
      <div class="tz-presets" data-tz-for="${escapeHtml(inputId)}">
        ${TZ_PRESETS.map(
          (tz) =>
            `<button type="button" class="tz-preset-btn ${tz === currentTz ? 'active' : ''}" data-tz-val="${escapeHtml(tz)}">${escapeHtml(tz)}</button>`
        ).join('')}
      </div>
    `;
  }

  function bindTzPresets(inputId) {
    const input = document.getElementById(inputId);
    const wrap = document.querySelector(`.tz-presets[data-tz-for="${inputId}"]`);
    if (!input || !wrap) return;
    const buttons = wrap.querySelectorAll('.tz-preset-btn');
    const syncActive = () => {
      const val = input.value.trim();
      buttons.forEach((b) => {
        b.classList.toggle('active', b.getAttribute('data-tz-val') === val);
      });
    };
    buttons.forEach((btn) => {
      btn.addEventListener('click', () => {
        input.value = btn.getAttribute('data-tz-val');
        syncActive();
      });
    });
    input.addEventListener('input', syncActive);
  }

  // --- Render Recipients & Routes ---
  function renderRecipients() {
    if (!el.recipientsContainer) return;

    if (state.recipients.length === 0) {
      el.recipientsContainer.innerHTML =
        '<p class="hint">No recipients configured yet. Click "+ New Recipient" above.</p>';
      return;
    }

    el.recipientsContainer.innerHTML = state.recipients
      .map(
        (rec) => `
      <article class="recipient-card">
        <div class="card-head">
          <div>
            <h3>${escapeHtml(rec.name)}</h3>
            <span class="recipient-tz">Timezone: <code>${escapeHtml(rec.timezone)}</code></span>
          </div>
          <div class="card-head-actions">
            <span class="status-badge ${rec.enabled ? 'status-ok' : 'status-danger'}">
              ${rec.enabled ? 'Enabled' : 'Disabled'}
            </span>
            <button class="btn btn-sm btn-secondary" type="button" onclick="window.asgardHub.editRecipient('${escapeHtml(rec.id)}')">Edit</button>
            <button class="btn btn-sm btn-danger" type="button" aria-label="Delete recipient ${escapeHtml(rec.name)}" onclick="window.asgardHub.deleteRecipient('${escapeHtml(rec.id)}')">&times;</button>
          </div>
        </div>

        <div class="routes-section">
          <div class="routes-header">
            <h4>Mapped Routes (${(rec.routes || []).length})</h4>
            <button class="btn btn-sm btn-primary" type="button" onclick="window.asgardHub.addRouteModal('${escapeHtml(rec.id)}')">+ Route</button>
          </div>
          ${
            rec.routes && rec.routes.length > 0
              ? `
            <div class="routes-list">
              ${rec.routes
                .map((rt) => {
                  const allowed = isAllowedAction(rt.ha_domain, rt.ha_service);
                  return `
                <div class="route-item">
                  <div class="route-info">
                    <div class="route-title-row">
                      <strong>${escapeHtml(rt.name)}</strong>
                      <span>&rarr;</span>
                      <code>${escapeHtml(rt.ha_domain)}.${escapeHtml(rt.ha_service)}</code>
                    </div>
                    <div class="route-meta">
                      <span class="status-badge status-secondary">Min: ${escapeHtml(rt.priority_min)}</span>
                      <span class="status-badge ${rt.enabled ? 'status-ok' : 'status-secondary'}">${rt.enabled ? 'Enabled' : 'Disabled'}</span>
                      ${!allowed ? '<span class="status-badge status-danger">Unsupported Action</span>' : ''}
                    </div>
                  </div>
                  <div class="route-actions">
                    <button class="btn btn-sm btn-secondary" type="button" onclick="window.asgardHub.testRoute('${escapeHtml(rt.id)}')">Ping Test</button>
                    <button class="btn btn-sm btn-secondary" type="button" onclick="window.asgardHub.editRouteModal('${escapeHtml(rec.id)}', '${escapeHtml(rt.id)}')">Edit</button>
                    <button class="btn btn-sm btn-danger" type="button" aria-label="Delete route ${escapeHtml(rt.name)}" onclick="window.asgardHub.deleteRoute('${escapeHtml(rt.id)}')">&times;</button>
                  </div>
                </div>
              `;
                })
                .join('')}
            </div>
          `
              : '<p class="hint">No notification routes mapped yet.</p>'
          }
        </div>
      </article>
    `
      )
      .join('');
  }

  // --- Render Groups ---
  function renderGroups() {
    if (!el.groupsContainer) return;

    if (state.groups.length === 0) {
      el.groupsContainer.innerHTML =
        '<p class="hint">No recipient groups configured. Click "+ New Group" above.</p>';
      return;
    }

    el.groupsContainer.innerHTML = state.groups
      .map((g) => {
        const members = (g.recipient_ids || []).map((rid) => {
          const r = state.recipients.find((x) => x.id === rid);
          return { id: rid, name: r ? r.name : `${rid} (deleted)`, missing: !r };
        });

        return `
        <article class="recipient-card">
          <div class="card-head">
            <div>
              <h3>${escapeHtml(g.name)}</h3>
              <p class="hint">${escapeHtml(g.description || 'No description')}</p>
            </div>
            <div class="card-head-actions">
              <button class="btn btn-sm btn-secondary" type="button" onclick="window.asgardHub.editGroup('${escapeHtml(g.id)}')">Edit</button>
              <button class="btn btn-sm btn-danger" type="button" aria-label="Delete group ${escapeHtml(g.name)}" onclick="window.asgardHub.deleteGroup('${escapeHtml(g.id)}')">&times;</button>
            </div>
          </div>
          <div class="group-members">
            <h4>Group Members (${members.length})</h4>
            <div class="chips-wrap">
              ${
                members.length > 0
                  ? members
                      .map(
                        (m) =>
                          `<span class="chip ${m.missing ? 'status-danger' : ''}">${escapeHtml(m.name)}</span>`
                      )
                      .join('')
                  : '<span class="hint">No members assigned.</span>'
              }
            </div>
          </div>
        </article>
      `;
      })
      .join('');
  }

  // --- Render Policies ---
  const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  function resolvePolicyTarget(p) {
    if (p.target_type === 'recipient') {
      const r = state.recipients.find((x) => x.id === p.target_id);
      if (r) {
        return { label: `Recipient: ${r.name}`, orphaned: false, missingDetail: null };
      }
      return {
        label: 'Orphaned Policy · Deleted Recipient',
        orphaned: true,
        missingDetail: `Target recipient (${p.target_id}) was deleted. Click Edit to reassign this policy to an active recipient or group, or delete it.`,
      };
    }
    if (p.target_type === 'group') {
      const g = state.groups.find((x) => x.id === p.target_id);
      if (g) {
        return { label: `Group: ${g.name}`, orphaned: false, missingDetail: null };
      }
      return {
        label: 'Orphaned Policy · Deleted Group',
        orphaned: true,
        missingDetail: `Target group (${p.target_id}) was deleted. Click Edit to reassign this policy to an active group or recipient, or delete it.`,
      };
    }
    return { label: 'Household Global Policy', orphaned: false, missingDetail: null };
  }

  function renderPolicies() {
    if (!el.policiesContainer) return;

    if (state.policies.length === 0) {
      el.policiesContainer.innerHTML =
        '<p class="hint">No quiet hours policies configured. Click "+ New Policy" above.</p>';
      return;
    }

    el.policiesContainer.innerHTML = state.policies
      .map((p) => {
        const target = resolvePolicyTarget(p);
        const isOrphaned = Boolean(p.orphaned || target.orphaned);
        const activeDays = (p.day_mask || []).map((d) => DAY_NAMES[d] ?? d).join(', ');

        return `
        <article class="recipient-card ${isOrphaned ? 'card-orphaned' : ''}" data-policy-id="${escapeHtml(p.id)}">
          <div class="card-head">
            <div>
              <h3>${escapeHtml(target.label)}</h3>
              <span class="recipient-tz">Timezone: <code>${escapeHtml(p.timezone)}</code></span>
            </div>
            <div class="card-head-actions">
              ${isOrphaned ? '<span class="status-badge status-danger">Orphaned Target</span>' : ''}
              <span class="status-badge ${p.enabled ? 'status-ok' : 'status-secondary'}">
                ${p.enabled ? 'Enabled' : 'Disabled'}
              </span>
              <button class="btn btn-sm btn-secondary" type="button" onclick="window.asgardHub.editPolicyModal('${escapeHtml(p.id)}')">Edit</button>
              <button class="btn btn-sm btn-danger" type="button" aria-label="Delete policy" onclick="window.asgardHub.deletePolicy('${escapeHtml(p.id)}')">&times;</button>
            </div>
          </div>

          ${isOrphaned && target.missingDetail ? `<div class="orphan-warning" role="alert">${escapeHtml(target.missingDetail)}</div>` : ''}

          <div class="policy-details">
            <p><strong>Quiet Hours Window:</strong> <code>${escapeHtml(p.quiet_start)} &rarr; ${escapeHtml(p.quiet_end)}</code></p>
            <p><strong>Active Days:</strong> <span>${escapeHtml(activeDays || 'None')}</span></p>
            <p><strong>Urgent Override:</strong> ${
              p.urgent_override
                ? '<span class="status-badge status-ok">Permitted (Urgent Bypasses Quiet Hours)</span>'
                : '<span class="status-badge status-warning">Silenced Even If Urgent</span>'
            }</p>
          </div>
        </article>
      `;
      })
      .join('');
  }

  // --- Render Audit History (Desktop Table + Mobile Stacked Cards) ---
  async function loadHistory() {
    try {
      const data = await apiGet('api/history?limit=100');
      state.history = data.history || [];
      renderHistory();
    } catch (err) {
      showBanner(`History load error: ${err.message}`, 'error');
    }
  }

  function renderHistory() {
    if (!el.historyTbody) return;

    if (state.history.length === 0) {
      el.historyTbody.innerHTML = '<tr><td colspan="6" class="hint">No delivery logs recorded yet.</td></tr>';
      if (el.historyCards) {
        el.historyCards.innerHTML = '<p class="hint">No delivery logs recorded yet.</p>';
      }
      return;
    }

    el.historyTbody.innerHTML = state.history
      .map((h) => {
        const meta = getStatusMeta(h.status);
        const action = h.ha_domain ? `${h.ha_domain}.${h.ha_service}` : h.ha_service;
        return `
        <tr>
          <td>${escapeHtml(formatDate(h.created_utc || h.created_at))}</td>
          <td><span class="status-badge status-secondary">${escapeHtml(h.priority)}</span></td>
          <td>${escapeHtml(h.recipient_name || h.recipient_id || '–')}</td>
          <td><code>${escapeHtml(action)}</code></td>
          <td><span class="status-badge ${meta.badgeClass}">${escapeHtml(meta.label)}</span></td>
          <td class="history-detail">${escapeHtml(h.details || meta.defaultDetail)}</td>
        </tr>
      `;
      })
      .join('');

    if (el.historyCards) {
      el.historyCards.innerHTML = state.history
        .map((h) => {
          const meta = getStatusMeta(h.status);
          const action = h.ha_domain ? `${h.ha_domain}.${h.ha_service}` : h.ha_service;
          return `
          <article class="history-card" data-status="${escapeHtml(h.status)}">
            <div class="history-card-head">
              <span class="history-card-time">${escapeHtml(formatDate(h.created_utc || h.created_at))}</span>
              <span class="status-badge ${meta.badgeClass}">${escapeHtml(meta.label)}</span>
            </div>
            <div class="history-card-row">
              <strong>${escapeHtml(h.recipient_name || h.recipient_id || '–')}</strong>
              <span class="status-badge status-secondary">${escapeHtml(h.priority)}</span>
            </div>
            <div class="history-card-row">
              <span>Action:</span>
              <code>${escapeHtml(action)}</code>
            </div>
            <p class="history-card-reason">${escapeHtml(h.details || meta.defaultDetail)}</p>
          </article>
        `;
        })
        .join('');
    }
  }

  // --- Build Service Options HTML for Route Modal ---
  function buildRouteServiceOptionsHtml(selectedValue) {
    const allowed = state.services.filter((s) => isAllowedAction(s.ha_domain, s.ha_service));
    const options = [];
    const seen = new Set();

    allowed.forEach((s) => {
      const full = `${s.ha_domain}.${s.ha_service}`;
      seen.add(full);
      const info = formatDiscoveredService(s);
      const tag = info.isEntity ? ' [Entity]' : ' [Service]';
      const sel = full === selectedValue ? 'selected' : '';
      options.push(
        `<option value="${escapeHtml(full)}" ${sel}>${escapeHtml(info.friendly)} (${escapeHtml(full)})${tag}</option>`
      );
    });

    if (selectedValue && !seen.has(selectedValue)) {
      const [d, s] = selectedValue.split('.', 2);
      if (isAllowedAction(d, s)) {
        options.unshift(
          `<option value="${escapeHtml(selectedValue)}" selected>${escapeHtml(selectedValue)} (Saved Route)</option>`
        );
      }
    }

    if (options.length === 0) {
      options.push('<option value="persistent_notification.create">persistent_notification.create [HA UI Banner]</option>');
    }
    return options.join('');
  }

  // --- Build Policy Form Modal (Create & Edit) ---
  function openPolicyModal(existingPolicy) {
    const isEdit = Boolean(existingPolicy);
    const defaultTz = isEdit
      ? existingPolicy.timezone || 'UTC'
      : state.defaultTimezone || 'Europe/Amsterdam';
    const currentStart = isEdit ? existingPolicy.quiet_start : '22:00';
    const currentEnd = isEdit ? existingPolicy.quiet_end : '07:00';
    const currentMask = isEdit && Array.isArray(existingPolicy.day_mask) ? existingPolicy.day_mask : [0, 1, 2, 3, 4, 5, 6];
    const currentUrgent = isEdit ? Boolean(existingPolicy.urgent_override) : true;
    const currentEnabled = isEdit ? Boolean(existingPolicy.enabled) : true;
    const currentSelection = isEdit
      ? existingPolicy.target_type === 'global'
        ? 'global:household_global'
        : `${existingPolicy.target_type}:${existingPolicy.target_id}`
      : state.recipients[0]
        ? `recipient:${state.recipients[0].id}`
        : state.groups[0]
          ? `group:${state.groups[0].id}`
          : 'global:household_global';

    const recOptions = state.recipients
      .map((r) => {
        const val = `recipient:${r.id}`;
        const sel = currentSelection === val || (isEdit && existingPolicy.target_id === r.id) ? 'selected' : '';
        return `<option value="${escapeHtml(val)}" ${sel}>Recipient: ${escapeHtml(r.name)}</option>`;
      })
      .join('');
    const grpOptions = state.groups
      .map((g) => {
        const val = `group:${g.id}`;
        const sel = currentSelection === val || (isEdit && existingPolicy.target_id === g.id) ? 'selected' : '';
        return `<option value="${escapeHtml(val)}" ${sel}>Group: ${escapeHtml(g.name)}</option>`;
      })
      .join('');
    const globalSelected = currentSelection === 'global:household_global' ? 'selected' : '';

    const html = `
      <form id="modal-policy-form" class="form-grid">
        <div class="form-group">
          <label for="pol-target">Target Scope *</label>
          <select id="pol-target" required>
            ${recOptions ? `<optgroup label="Recipients">${recOptions}</optgroup>` : ''}
            ${grpOptions ? `<optgroup label="Groups">${grpOptions}</optgroup>` : ''}
            <optgroup label="Global">
              <option value="global:household_global" ${globalSelected}>Household Global Policy</option>
            </optgroup>
          </select>
        </div>
        <div class="form-group">
          <label for="pol-tz">Policy Timezone (IANA) *</label>
          <input type="text" id="pol-tz" list="iana-timezones-list" value="${escapeHtml(defaultTz)}" required placeholder="e.g. Europe/Amsterdam or UTC" />
          ${renderTzPresetsHtml('pol-tz', defaultTz)}
        </div>
        <div class="form-group">
          <label for="pol-start">Quiet Start Time (HH:MM, 24h) *</label>
          <input type="time" id="pol-start" value="${escapeHtml(currentStart)}" required />
        </div>
        <div class="form-group">
          <label for="pol-end">Quiet End Time (HH:MM, 24h) *</label>
          <input type="time" id="pol-end" value="${escapeHtml(currentEnd)}" required />
        </div>
        <div class="form-group">
          <label>Active Days *</label>
          <div class="checkboxes-wrap">
            ${DAY_NAMES.map(
              (d, idx) => `
              <label class="checkbox-inline">
                <input type="checkbox" name="pol-day" value="${idx}" ${currentMask.includes(idx) ? 'checked' : ''} /> ${d}
              </label>
            `
            ).join('')}
          </div>
        </div>
        <div class="form-group">
          <label class="checkbox-inline"><input type="checkbox" id="pol-urgent-override" ${currentUrgent ? 'checked' : ''} /> Urgent messages override quiet hours</label>
        </div>
        <div class="form-group">
          <label class="checkbox-inline"><input type="checkbox" id="pol-enabled" ${currentEnabled ? 'checked' : ''} /> Policy Enabled</label>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">${isEdit ? 'Update Policy' : 'Save Policy'}</button>
        </div>
      </form>
    `;

    openModal(isEdit ? 'Edit Quiet Hours Policy' : 'Create Quiet Hours Policy', html);
    bindTzPresets('pol-tz');

    document.getElementById('modal-policy-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const rawTarget = document.getElementById('pol-target').value;
        let targetType = 'recipient';
        let targetId = rawTarget;
        if (rawTarget.includes(':')) {
          const parts = rawTarget.split(':', 2);
          targetType = parts[0];
          targetId = parts[1];
        } else if (state.groups.some((g) => g.id === rawTarget)) {
          targetType = 'group';
        } else if (rawTarget === 'household_global') {
          targetType = 'global';
        }

        if (targetType === 'recipient' && !state.recipients.some((r) => r.id === targetId)) {
          showBanner('Selected recipient no longer exists. Please choose an existing target.', 'error');
          return;
        }
        if (targetType === 'group' && !state.groups.some((g) => g.id === targetId)) {
          showBanner('Selected group no longer exists. Please choose an existing target.', 'error');
          return;
        }

        const tz = document.getElementById('pol-tz').value.trim() || defaultTz;
        const quietStart = document.getElementById('pol-start').value;
        const quietEnd = document.getElementById('pol-end').value;
        const days = Array.from(document.querySelectorAll('input[name="pol-day"]:checked')).map((c) =>
          parseInt(c.value, 10)
        );
        if (days.length === 0) {
          showBanner('Select at least one active weekday for the quiet hours policy.', 'warning');
          return;
        }
        const urgentOverride = document.getElementById('pol-urgent-override').checked;
        const enabled = document.getElementById('pol-enabled').checked;

        const body = {
          target_id: targetId,
          target_type: targetType,
          quiet_start: quietStart,
          quiet_end: quietEnd,
          day_mask: days,
          timezone: tz,
          urgent_override: urgentOverride,
          enabled,
        };
        if (isEdit) {
          body.id = existingPolicy.id;
        }

        await apiPost('api/policies', body);
        closeModal();
        await refreshAllData();
        showBanner(isEdit ? 'Policy updated successfully.' : 'Policy created successfully.', 'success', 4000);
      } catch (err) {
        showBanner(`Policy error: ${err.message}`, 'error');
      }
    });
  }

  // --- Global Actions & Modals Exposed to window.asgardHub ---
  window.asgardHub = {
    addRecipientModal: () => {
      const defaultTz = state.defaultTimezone || 'Europe/Amsterdam';
      const html = `
        <form id="modal-rec-form" class="form-grid">
          <div class="form-group">
            <label for="rec-name">Recipient Name *</label>
            <input type="text" id="rec-name" required placeholder="e.g. Martijn" />
          </div>
          <div class="form-group">
            <label for="rec-tz">Timezone (IANA) *</label>
            <input type="text" id="rec-tz" list="iana-timezones-list" value="${escapeHtml(defaultTz)}" required placeholder="e.g. Europe/Amsterdam or UTC" />
            ${renderTzPresetsHtml('rec-tz', defaultTz)}
          </div>
          <div class="form-group">
            <label class="checkbox-inline"><input type="checkbox" id="rec-enabled" checked /> Enabled</label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">Save Recipient</button>
          </div>
        </form>
      `;
      openModal('Add Recipient', html);
      bindTzPresets('rec-tz');
      document.getElementById('modal-rec-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const name = document.getElementById('rec-name').value.trim();
          const tz = document.getElementById('rec-tz').value.trim() || defaultTz;
          const enabled = document.getElementById('rec-enabled').checked;
          await apiPost('api/recipients', { name, timezone: tz, enabled });
          closeModal();
          await refreshAllData();
          showBanner('Recipient created successfully.', 'success', 4000);
        } catch (err) {
          showBanner(`Error: ${err.message}`, 'error');
        }
      });
    },

    editRecipient: (recId) => {
      const rec = state.recipients.find((r) => r.id === recId);
      if (!rec) return;

      const html = `
        <form id="modal-rec-form" class="form-grid">
          <div class="form-group">
            <label for="rec-name">Recipient Name *</label>
            <input type="text" id="rec-name" required value="${escapeHtml(rec.name)}" />
          </div>
          <div class="form-group">
            <label for="rec-tz">Timezone (IANA) *</label>
            <input type="text" id="rec-tz" list="iana-timezones-list" value="${escapeHtml(rec.timezone)}" required />
            ${renderTzPresetsHtml('rec-tz', rec.timezone)}
          </div>
          <div class="form-group">
            <label class="checkbox-inline"><input type="checkbox" id="rec-enabled" ${rec.enabled ? 'checked' : ''} /> Enabled</label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">Update Recipient</button>
          </div>
        </form>
      `;
      openModal('Edit Recipient', html);
      bindTzPresets('rec-tz');
      document.getElementById('modal-rec-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const name = document.getElementById('rec-name').value.trim();
          const tz = document.getElementById('rec-tz').value.trim() || rec.timezone;
          const enabled = document.getElementById('rec-enabled').checked;
          await apiPost('api/recipients', { id: recId, name, timezone: tz, enabled });
          closeModal();
          await refreshAllData();
          showBanner('Recipient updated successfully.', 'success', 4000);
        } catch (err) {
          showBanner(`Error: ${err.message}`, 'error');
        }
      });
    },

    deleteRecipient: async (recId) => {
      if (!confirm('Are you sure you want to delete this recipient and all their routes?')) return;
      try {
        await apiDelete(`api/recipients/${recId}`);
        await refreshAllData();
        showBanner('Recipient deleted.', 'success', 4000);
      } catch (err) {
        showBanner(`Delete error: ${err.message}`, 'error');
      }
    },

    addRouteModal: (recId) => {
      window.asgardHub.editRouteModal(recId, null);
    },

    editRouteModal: (recId, routeId) => {
      const rec = state.recipients.find((r) => r.id === recId);
      const existing =
        rec && routeId ? (rec.routes || []).find((rt) => rt.id === routeId) : null;
      const currentFull = existing ? `${existing.ha_domain}.${existing.ha_service}` : '';
      const svcOptions = buildRouteServiceOptionsHtml(currentFull);
      const currentMinPri = existing ? existing.priority_min : 'normal';
      const currentEnabled = existing ? Boolean(existing.enabled) : true;

      const html = `
        <form id="modal-route-form" class="form-grid">
          <div class="form-group">
            <label for="route-name">Route Label *</label>
            <input type="text" id="route-name" required value="${escapeHtml(existing ? existing.name : '')}" placeholder="e.g. Pixel Phone or HA Notification" />
          </div>
          <div class="form-group">
            <label for="route-service">HA Delivery Action *</label>
            <select id="route-service">
              ${svcOptions}
            </select>
          </div>
          <div class="form-group">
            <label for="route-min-priority">Minimum Priority to Dispatch</label>
            <select id="route-min-priority">
              <option value="informational" ${currentMinPri === 'informational' ? 'selected' : ''}>Informational (All messages)</option>
              <option value="normal" ${currentMinPri === 'normal' ? 'selected' : ''}>Normal</option>
              <option value="urgent" ${currentMinPri === 'urgent' ? 'selected' : ''}>Urgent Only</option>
            </select>
          </div>
          <div class="form-group">
            <label class="checkbox-inline"><input type="checkbox" id="route-enabled" ${currentEnabled ? 'checked' : ''} /> Route Enabled</label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">${existing ? 'Update Route' : 'Save Route'}</button>
          </div>
        </form>
      `;
      openModal(`${existing ? 'Edit' : 'Add'} Route for ${rec ? rec.name : 'Recipient'}`, html);
      document.getElementById('modal-route-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const name = document.getElementById('route-name').value.trim();
          const selectedSvc = document.getElementById('route-service').value;
          const [haDomain, haService] = selectedSvc.includes('.')
            ? selectedSvc.split('.', 2)
            : ['notify', selectedSvc];
          const minPri = document.getElementById('route-min-priority').value;
          const enabled = document.getElementById('route-enabled').checked;

          const body = {
            recipient_id: recId,
            name,
            ha_domain: haDomain,
            ha_service: haService,
            priority_min: minPri,
            enabled,
          };
          if (existing) {
            body.id = existing.id;
          }

          await apiPost('api/routes', body);
          closeModal();
          await refreshAllData();
          showBanner(existing ? 'Route updated successfully.' : 'Route saved successfully.', 'success', 4000);
        } catch (err) {
          showBanner(`Route save error: ${err.message}`, 'error');
        }
      });
    },

    deleteRoute: async (routeId) => {
      if (!confirm('Are you sure you want to delete this route?')) return;
      try {
        await apiDelete(`api/routes/${routeId}`);
        await refreshAllData();
        showBanner('Route deleted.', 'success', 4000);
      } catch (err) {
        showBanner(`Delete error: ${err.message}`, 'error');
      }
    },

    testRoute: async (routeId) => {
      try {
        showBanner('Testing route submission to Home Assistant…', 'info', 3000);
        const res = await apiPost(`api/routes/${routeId}/test`, {});
        if (res.success) {
          showBanner(
            `Route test submitted to Home Assistant (${res.ha_service}). Device delivery depends on the HA integration.`,
            'success',
            6000
          );
        } else {
          showBanner(`Route test FAILED (${res.ha_service}): ${res.error || 'Unknown error'}`, 'error', 9000);
        }
      } catch (err) {
        showBanner(`Test error: ${err.message}`, 'error');
      }
    },

    addGroupModal: () => {
      const recCheckboxes = state.recipients
        .map(
          (r) => `
        <label class="checkbox-inline">
          <input type="checkbox" name="grp-rec" value="${escapeHtml(r.id)}" /> ${escapeHtml(r.name)}
        </label>
      `
        )
        .join('');

      const html = `
        <form id="modal-grp-form" class="form-grid">
          <div class="form-group">
            <label for="grp-name">Group Name *</label>
            <input type="text" id="grp-name" required placeholder="e.g. All Adults" />
          </div>
          <div class="form-group">
            <label for="grp-desc">Description</label>
            <input type="text" id="grp-desc" placeholder="e.g. Household notification group" />
          </div>
          <div class="form-group">
            <label>Member Recipients</label>
            <div class="checkboxes-wrap">
              ${recCheckboxes || '<p class="hint">No recipients created yet.</p>'}
            </div>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">Save Group</button>
          </div>
        </form>
      `;
      openModal('Create Recipient Group', html);
      document.getElementById('modal-grp-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const name = document.getElementById('grp-name').value.trim();
          const desc = document.getElementById('grp-desc').value.trim();
          const checked = Array.from(document.querySelectorAll('input[name="grp-rec"]:checked')).map(
            (c) => c.value
          );

          await apiPost('api/groups', {
            name,
            description: desc,
            recipient_ids: checked,
          });
          closeModal();
          await refreshAllData();
          showBanner('Group created successfully.', 'success', 4000);
        } catch (err) {
          showBanner(`Group error: ${err.message}`, 'error');
        }
      });
    },

    editGroup: (groupId) => {
      const grp = state.groups.find((g) => g.id === groupId);
      if (!grp) return;

      const recCheckboxes = state.recipients
        .map((r) => {
          const isMember = (grp.recipient_ids || []).includes(r.id);
          return `
          <label class="checkbox-inline">
            <input type="checkbox" name="grp-rec" value="${escapeHtml(r.id)}" ${isMember ? 'checked' : ''} /> ${escapeHtml(r.name)}
          </label>
        `;
        })
        .join('');

      const html = `
        <form id="modal-grp-form" class="form-grid">
          <div class="form-group">
            <label for="grp-name">Group Name *</label>
            <input type="text" id="grp-name" required value="${escapeHtml(grp.name)}" />
          </div>
          <div class="form-group">
            <label for="grp-desc">Description</label>
            <input type="text" id="grp-desc" value="${escapeHtml(grp.description || '')}" />
          </div>
          <div class="form-group">
            <label>Member Recipients</label>
            <div class="checkboxes-wrap">
              ${recCheckboxes}
            </div>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">Update Group</button>
          </div>
        </form>
      `;
      openModal('Edit Recipient Group', html);
      document.getElementById('modal-grp-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const name = document.getElementById('grp-name').value.trim();
          const desc = document.getElementById('grp-desc').value.trim();
          const checked = Array.from(document.querySelectorAll('input[name="grp-rec"]:checked')).map(
            (c) => c.value
          );

          await apiPost('api/groups', {
            id: groupId,
            name,
            description: desc,
            recipient_ids: checked,
          });
          closeModal();
          await refreshAllData();
          showBanner('Group updated successfully.', 'success', 4000);
        } catch (err) {
          showBanner(`Group error: ${err.message}`, 'error');
        }
      });
    },

    deleteGroup: async (groupId) => {
      if (!confirm('Are you sure you want to delete this group?')) return;
      try {
        await apiDelete(`api/groups/${groupId}`);
        await refreshAllData();
        showBanner('Group deleted.', 'success', 4000);
      } catch (err) {
        showBanner(`Group delete error: ${err.message}`, 'error');
      }
    },

    addPolicyModal: () => {
      openPolicyModal(null);
    },

    editPolicyModal: (policyId) => {
      const pol = state.policies.find((p) => p.id === policyId);
      if (!pol) return;
      openPolicyModal(pol);
    },

    deletePolicy: async (policyId) => {
      if (!confirm('Are you sure you want to delete this quiet hours policy?')) return;
      try {
        await apiDelete(`api/policies/${policyId}`);
        await refreshAllData();
        showBanner('Policy deleted.', 'success', 4000);
      } catch (err) {
        showBanner(`Policy delete error: ${err.message}`, 'error');
      }
    },
  };

  // --- Attach Header / Global Listeners ---
  if (el.btnRefreshServices) {
    el.btnRefreshServices.addEventListener('click', async () => {
      try {
        showBanner('Syncing services from Home Assistant…', 'info', 2000);
        const data = await apiGet('api/services?refresh=true');
        state.services = data.services || [];
        await refreshAllData();
        showBanner('Services synchronized.', 'success', 3000);
      } catch (err) {
        showBanner(`Sync error: ${err.message}`, 'error');
      }
    });
  }

  if (el.btnAddRecipient) el.btnAddRecipient.addEventListener('click', window.asgardHub.addRecipientModal);
  if (el.btnAddGroup) el.btnAddGroup.addEventListener('click', window.asgardHub.addGroupModal);
  if (el.btnAddPolicy) el.btnAddPolicy.addEventListener('click', window.asgardHub.addPolicyModal);
  if (el.btnRefreshHistory) el.btnRefreshHistory.addEventListener('click', loadHistory);

  if (el.btnPurgeHistory) {
    el.btnPurgeHistory.addEventListener('click', async () => {
      if (!confirm('Purge delivery audit history older than 30 days?')) return;
      try {
        const res = await apiPost('api/history/purge?days=30', {});
        showBanner(`Purged ${res.count} records.`, 'success', 4000);
        await loadHistory();
      } catch (err) {
        showBanner(`Purge error: ${err.message}`, 'error');
      }
    });
  }

  // --- Main Refresh Function ---
  async function refreshAllData() {
    try {
      const [sum, svcs, recs, grps, pols] = await Promise.all([
        apiGet('api/summary'),
        apiGet('api/services'),
        apiGet('api/recipients'),
        apiGet('api/groups'),
        apiGet('api/policies'),
      ]);

      state.summary = sum;
      state.services = svcs.services || [];
      state.recipients = recs.recipients || [];
      state.groups = grps.groups || [];
      state.policies = pols.policies || [];

      renderOverview();
      renderComposerSelects();
      renderRecipients();
      renderGroups();
      renderPolicies();
    } catch (err) {
      showBanner(`Failed to load data: ${err.message}`, 'error');
    }
  }

  // --- Initialization ---
  async function init() {
    initTabs();
    initComposer();
    await refreshAllData();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
