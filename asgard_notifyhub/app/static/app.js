/**
 * ASGARD NotifyHub - Frontend Application Logic
 */

(function () {
  'use strict';

  // --- State ---
  const state = {
    services: [],
    recipients: [],
    groups: [],
    policies: [],
    history: [],
    summary: null,
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
    compTargetType: document.getElementById('comp-target-type'),
    compGroupRecipientWrap: document.getElementById('comp-group-recipient-wrap'),
    compRecipientId: document.getElementById('comp-recipient-id'),
    compGroupSelectWrap: document.getElementById('comp-group-select-wrap'),
    compGroupId: document.getElementById('comp-group-id'),
    compPriority: document.getElementById('comp-priority'),
    compTitle: document.getElementById('comp-title'),
    compMessage: document.getElementById('comp-message'),
    btnPreviewSend: document.getElementById('btn-preview-send'),
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
  function showBanner(message, type = 'error', durationMs = 6000) {
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

  function hideBanner() {
    if (el.statusBanner) el.statusBanner.hidden = true;
  }

  // --- API Client ---
  async function apiGet(endpoint) {
    const res = await fetch(endpoint);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  async function apiPost(endpoint, body) {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  async function apiDelete(endpoint) {
    const res = await fetch(endpoint, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
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

        // Lazy loads when switching tabs
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
    el.appModal.close();
    el.modalBody.innerHTML = '';
  }

  if (el.modalCloseBtn) {
    el.modalCloseBtn.addEventListener('click', closeModal);
  }

  // Close when clicking outside dialog content
  if (el.appModal) {
    el.appModal.addEventListener('click', (e) => {
      const rect = el.appModal.getBoundingClientRect();
      const isInDialog = (
        rect.top <= e.clientY &&
        e.clientY <= rect.top + rect.height &&
        rect.left <= e.clientX &&
        e.clientX <= rect.left + rect.width
      );
      if (!isInDialog) {
        closeModal();
      }
    });
  }

  // --- Render Overview ---
  function renderOverview() {
    if (!state.summary) return;
    const s = state.summary;

    const haStatus = s.ha_connected ? (s.demo_mode ? 'Demo Mode' : 'Connected') : 'Offline / Token Missing';
    const haClass = s.ha_connected ? 'status-ok' : 'status-danger';

    if (el.haStatusBadge) {
      el.haStatusBadge.textContent = haStatus;
      el.haStatusBadge.className = `status-badge ${haClass}`;
    }
    if (el.cardHaBadge) {
      el.cardHaBadge.textContent = s.ha_connected ? 'OK' : 'FAIL';
      el.cardHaBadge.className = `status-badge ${haClass}`;
    }
    if (el.statHaConn) el.statHaConn.textContent = haStatus;
    if (el.statServicesCount) el.statServicesCount.textContent = `${s.services_discovered} notify actions discovered`;
    if (el.statSubmissions) el.statSubmissions.textContent = String(s.submissions_24h);
    if (el.statQuiet) el.statQuiet.textContent = String(s.quiet_silenced_24h);
    if (el.statRecipients) el.statRecipients.textContent = String(s.recipients_count);
    if (el.statRoutesHint) el.statRoutesHint.textContent = `${s.routes_count} active routes mapped`;
    if (el.tagDiscoveredCount) el.tagDiscoveredCount.textContent = `${state.services.length} discovered`;

    // Render discovered services
    if (el.dashboardServicesList) {
      if (state.services.length === 0) {
        el.dashboardServicesList.innerHTML = '<p class="hint">No Home Assistant notify services detected or connection pending.</p>';
      } else {
        el.dashboardServicesList.innerHTML = state.services.map((svc) => `
          <div class="service-chip">
            <span class="chip-name">${escapeHtml(svc.full_name || svc.service)}</span>
            <span class="chip-desc">${escapeHtml(svc.description || 'Notify Service')}</span>
          </div>
        `).join('');
      }
    }
  }

  // --- Render Composer Selects ---
  function renderComposerSelects() {
    if (el.compRecipientId) {
      el.compRecipientId.innerHTML = state.recipients.map((r) => `
        <option value="${escapeHtml(r.id)}">${escapeHtml(r.name)} (${r.routes ? r.routes.length : 0} routes)</option>
      `).join('');
    }

    if (el.compGroupId) {
      el.compGroupId.innerHTML = state.groups.map((g) => `
        <option value="${escapeHtml(g.id)}">${escapeHtml(g.name)} (${g.recipient_ids ? g.recipient_ids.length : 0} members)</option>
      `).join('');
    }
  }

  function initComposer() {
    if (!el.compTargetType) return;

    el.compTargetType.addEventListener('change', () => {
      const type = el.compTargetType.value;
      if (type === 'recipient') {
        el.compGroupRecipientWrap.hidden = false;
        el.compGroupSelectWrap.hidden = true;
      } else if (type === 'group') {
        el.compGroupRecipientWrap.hidden = true;
        el.compGroupSelectWrap.hidden = false;
      } else {
        el.compGroupRecipientWrap.hidden = true;
        el.compGroupSelectWrap.hidden = true;
      }
    });

    // Preview click handler
    if (el.btnPreviewSend) {
      el.btnPreviewSend.addEventListener('click', async () => {
        try {
          const payload = getComposerPayload();
          const res = await apiPost('/api/send/preview', payload);
          renderPreviewResults(res);
        } catch (err) {
          showBanner(`Preview error: ${err.message}`);
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
            showBanner('Please enter a notification message body.');
            return;
          }
          const res = await apiPost('/api/send', payload);
          showBanner(`Dispatched: ${res.records.length} routing submission(s) processed.`, 'success', 5000);
          el.compMessage.value = '';
          await refreshAllData();
          renderPreviewFromRecords(res.records);
        } catch (err) {
          showBanner(`Dispatch error: ${err.message}`);
        }
      });
    }
  }

  function getComposerPayload() {
    const targetType = el.compTargetType.value;
    let targetId = null;
    if (targetType === 'recipient') {
      targetId = el.compRecipientId.value;
    } else if (targetType === 'group') {
      targetId = el.compGroupId.value;
    }

    return {
      target_type: targetType,
      target_id: targetId,
      priority: el.compPriority.value,
      title: el.compTitle.value.trim() || null,
      message: el.compMessage.value.trim(),
    };
  }

  function renderPreviewResults(preview) {
    if (!el.previewResultsContainer) return;
    el.previewBadge.textContent = 'Dry-Run Preview';
    el.previewBadge.className = 'panel-tag';

    if (!preview.items || preview.items.length === 0) {
      el.previewResultsContainer.innerHTML = '<p class="hint">No routes match the target criteria or all routes are disabled.</p>';
      return;
    }

    el.previewResultsContainer.innerHTML = preview.items.map((item) => {
      let badgeClass = 'status-ok';
      let statusText = 'Will Submit';
      if (!item.will_send) {
        if (item.quiet_hours_active) {
          badgeClass = 'status-warning';
          statusText = 'Silenced (Quiet Hours)';
        } else if (item.dedup_hit) {
          badgeClass = 'status-warning';
          statusText = 'Skipped (Duplicate)';
        } else {
          badgeClass = 'status-danger';
          statusText = 'Skipped';
        }
      }

      return `
        <div class="preview-item">
          <div class="preview-item-head">
            <strong>${escapeHtml(item.recipient_name)}</strong> &rarr; <code>${escapeHtml(item.service_target)}</code>
            <span class="status-badge ${badgeClass}">${statusText}</span>
          </div>
          <p class="preview-reason">${escapeHtml(item.reason || 'Normal dispatch')}</p>
        </div>
      `;
    }).join('');
  }

  function renderPreviewFromRecords(records) {
    if (!el.previewResultsContainer) return;
    el.previewBadge.textContent = 'Dispatch Executed';
    el.previewBadge.className = 'panel-tag status-ok';

    if (!records || records.length === 0) {
      el.previewResultsContainer.innerHTML = '<p class="hint">No actions taken.</p>';
      return;
    }

    el.previewResultsContainer.innerHTML = records.map((r) => {
      let badgeClass = 'status-ok';
      if (r.status === 'silenced') badgeClass = 'status-warning';
      else if (r.status === 'skipped_dedup') badgeClass = 'status-warning';
      else if (r.status === 'failed') badgeClass = 'status-danger';

      return `
        <div class="preview-item">
          <div class="preview-item-head">
            <strong>${escapeHtml(r.recipient_name || r.recipient_id)}</strong> &rarr; <code>${escapeHtml(r.ha_domain)}.${escapeHtml(r.ha_service)}</code>
            <span class="status-badge ${badgeClass}">${escapeHtml(r.status)}</span>
          </div>
          <p class="preview-reason">${escapeHtml(r.error_detail || (r.status === 'submitted' ? 'Submitted to Home Assistant action' : r.status))}</p>
        </div>
      `;
    }).join('');
  }

  // --- Render Recipients & Routes ---
  function renderRecipients() {
    if (!el.recipientsContainer) return;

    if (state.recipients.length === 0) {
      el.recipientsContainer.innerHTML = '<p class="hint">No recipients configured yet. Click "+ New Recipient" above.</p>';
      return;
    }

    el.recipientsContainer.innerHTML = state.recipients.map((rec) => `
      <article class="recipient-card">
        <div class="card-head">
          <div>
            <h3>${escapeHtml(rec.name)}</h3>
            <span class="recipient-tz">Timezone: ${escapeHtml(rec.timezone)}</span>
          </div>
          <div class="card-head-actions">
            <span class="status-badge ${rec.enabled ? 'status-ok' : 'status-danger'}">
              ${rec.enabled ? 'Enabled' : 'Disabled'}
            </span>
            <button class="btn btn-sm btn-secondary" onclick="window.asgardHub.editRecipient('${escapeHtml(rec.id)}')">Edit</button>
            <button class="btn btn-sm btn-danger" onclick="window.asgardHub.deleteRecipient('${escapeHtml(rec.id)}')">&times;</button>
          </div>
        </div>

        <div class="routes-section">
          <div class="routes-header">
            <h4>Mapped Routes (${(rec.routes || []).length})</h4>
            <button class="btn btn-sm btn-primary" onclick="window.asgardHub.addRouteModal('${escapeHtml(rec.id)}')">+ Route</button>
          </div>
          ${(rec.routes && rec.routes.length > 0) ? `
            <div class="routes-list">
              ${rec.routes.map((rt) => `
                <div class="route-item">
                  <div class="route-info">
                    <strong>${escapeHtml(rt.name)}</strong> &rarr; <code>${escapeHtml(rt.ha_domain)}.${escapeHtml(rt.ha_service)}</code>
                    <span class="route-meta">Min Priority: <em>${escapeHtml(rt.priority_min)}</em> ${rt.enabled ? '' : '(Disabled)'}</span>
                  </div>
                  <div class="route-actions">
                    <button class="btn btn-sm btn-secondary" onclick="window.asgardHub.testRoute('${escapeHtml(rt.id)}')">Ping Test</button>
                    <button class="btn btn-sm btn-danger" onclick="window.asgardHub.deleteRoute('${escapeHtml(rt.id)}')">&times;</button>
                  </div>
                </div>
              `).join('')}
            </div>
          ` : '<p class="hint">No notification routes mapped yet.</p>'}
        </div>
      </article>
    `).join('');
  }

  // --- Render Groups ---
  function renderGroups() {
    if (!el.groupsContainer) return;

    if (state.groups.length === 0) {
      el.groupsContainer.innerHTML = '<p class="hint">No recipient groups configured. Click "+ New Group" above.</p>';
      return;
    }

    el.groupsContainer.innerHTML = state.groups.map((g) => {
      const memberNames = (g.recipient_ids || []).map((rid) => {
        const r = state.recipients.find((x) => x.id === rid);
        return r ? r.name : rid;
      });

      return `
        <article class="recipient-card">
          <div class="card-head">
            <div>
              <h3>${escapeHtml(g.name)}</h3>
              <p class="hint">${escapeHtml(g.description || 'No description')}</p>
            </div>
            <div class="card-head-actions">
              <button class="btn btn-sm btn-secondary" onclick="window.asgardHub.editGroup('${escapeHtml(g.id)}')">Edit</button>
              <button class="btn btn-sm btn-danger" onclick="window.asgardHub.deleteGroup('${escapeHtml(g.id)}')">&times;</button>
            </div>
          </div>
          <div class="group-members">
            <h4>Group Members (${memberNames.length})</h4>
            <div class="chips-wrap">
              ${memberNames.map((name) => `<span class="chip">${escapeHtml(name)}</span>`).join('')}
            </div>
          </div>
        </article>
      `;
    }).join('');
  }

  // --- Render Policies ---
  const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  function renderPolicies() {
    if (!el.policiesContainer) return;

    if (state.policies.length === 0) {
      el.policiesContainer.innerHTML = '<p class="hint">No quiet hours policies configured. Click "+ New Policy" above.</p>';
      return;
    }

    el.policiesContainer.innerHTML = state.policies.map((p) => {
      let targetLabel = p.target_id;
      if (p.target_type === 'recipient') {
        const r = state.recipients.find((x) => x.id === p.target_id);
        targetLabel = r ? `Recipient: ${r.name}` : `Recipient: ${p.target_id}`;
      } else if (p.target_type === 'group') {
        const g = state.groups.find((x) => x.id === p.target_id);
        targetLabel = g ? `Group: ${g.name}` : `Group: ${p.target_id}`;
      } else {
        targetLabel = 'Household Broad Policy';
      }

      const activeDays = (p.day_mask || []).map((d) => DAY_NAMES[d] || d).join(', ');

      return `
        <article class="recipient-card">
          <div class="card-head">
            <div>
              <h3>${escapeHtml(targetLabel)}</h3>
              <span class="recipient-tz">Timezone: ${escapeHtml(p.timezone)}</span>
            </div>
            <div class="card-head-actions">
              <span class="status-badge ${p.enabled ? 'status-ok' : 'status-danger'}">
                ${p.enabled ? 'Enabled' : 'Disabled'}
              </span>
              <button class="btn btn-sm btn-danger" onclick="window.asgardHub.deletePolicy('${escapeHtml(p.id)}')">&times;</button>
            </div>
          </div>

          <div class="policy-details">
            <p><strong>Quiet Hours Window:</strong> <code>${escapeHtml(p.quiet_start)} &rarr; ${escapeHtml(p.quiet_end)}</code></p>
            <p><strong>Active Days:</strong> ${escapeHtml(activeDays)}</p>
            <p><strong>Urgent Override:</strong> ${p.urgent_override ? '<span class="status-badge status-ok">Permitted (Urgent Bypasses Quiet Hours)</span>' : '<span class="status-badge status-warning">Silenced Even If Urgent</span>'}</p>
          </div>
        </article>
      `;
    }).join('');
  }

  // --- Render Audit History ---
  async function loadHistory() {
    try {
      const data = await apiGet('/api/history?limit=100');
      state.history = data.history || [];
      renderHistory();
    } catch (err) {
      showBanner(`History load error: ${err.message}`);
    }
  }

  function renderHistory() {
    if (!el.historyTbody) return;

    if (state.history.length === 0) {
      el.historyTbody.innerHTML = '<tr><td colspan="6" class="hint">No delivery logs recorded yet.</td></tr>';
      return;
    }

    el.historyTbody.innerHTML = state.history.map((h) => {
      let badgeClass = 'status-ok';
      if (h.status === 'silenced') badgeClass = 'status-warning';
      else if (h.status === 'skipped_dedup') badgeClass = 'status-warning';
      else if (h.status === 'failed') badgeClass = 'status-danger';

      return `
        <tr>
          <td>${escapeHtml(formatDate(h.created_at))}</td>
          <td><span class="status-badge status-secondary">${escapeHtml(h.priority)}</span></td>
          <td>${escapeHtml(h.recipient_name || h.recipient_id || '–')}</td>
          <td><code>${escapeHtml(h.ha_domain)}.${escapeHtml(h.ha_service)}</code></td>
          <td><span class="status-badge ${badgeClass}">${escapeHtml(h.status)}</span></td>
          <td class="history-detail">${escapeHtml(h.error_detail || (h.status === 'submitted' ? 'Submitted to HA action' : '–'))}</td>
        </tr>
      `;
    }).join('');
  }

  // --- Global Actions & Modals Exposed to window.asgardHub ---
  window.asgardHub = {
    // Recipient Modals
    addRecipientModal: () => {
      const html = `
        <form id="modal-rec-form" class="form-grid">
          <div class="form-group">
            <label for="rec-name">Recipient Name *</label>
            <input type="text" id="rec-name" required placeholder="e.g. Martijn" />
          </div>
          <div class="form-group">
            <label for="rec-tz">Timezone</label>
            <input type="text" id="rec-tz" value="UTC" placeholder="e.g. Europe/Amsterdam or UTC" />
          </div>
          <div class="form-group">
            <label><input type="checkbox" id="rec-enabled" checked /> Enabled</label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">Save Recipient</button>
          </div>
        </form>
      `;
      openModal('Add Recipient', html);
      document.getElementById('modal-rec-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const name = document.getElementById('rec-name').value.trim();
          const tz = document.getElementById('rec-tz').value.trim() || 'UTC';
          const enabled = document.getElementById('rec-enabled').checked;
          await apiPost('/api/recipients', { name, timezone: tz, enabled });
          closeModal();
          await refreshAllData();
          showBanner('Recipient created successfully.', 'success', 4000);
        } catch (err) {
          showBanner(`Error: ${err.message}`);
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
            <label for="rec-tz">Timezone</label>
            <input type="text" id="rec-tz" value="${escapeHtml(rec.timezone)}" />
          </div>
          <div class="form-group">
            <label><input type="checkbox" id="rec-enabled" ${rec.enabled ? 'checked' : ''} /> Enabled</label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">Update Recipient</button>
          </div>
        </form>
      `;
      openModal('Edit Recipient', html);
      document.getElementById('modal-rec-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const name = document.getElementById('rec-name').value.trim();
          const tz = document.getElementById('rec-tz').value.trim() || 'UTC';
          const enabled = document.getElementById('rec-enabled').checked;
          await apiPost('/api/recipients', { id: recId, name, timezone: tz, enabled });
          closeModal();
          await refreshAllData();
          showBanner('Recipient updated successfully.', 'success', 4000);
        } catch (err) {
          showBanner(`Error: ${err.message}`);
        }
      });
    },

    deleteRecipient: async (recId) => {
      if (!confirm('Are you sure you want to delete this recipient and all their routes?')) return;
      try {
        await apiDelete(`/api/recipients/${recId}`);
        await refreshAllData();
        showBanner('Recipient deleted.', 'success', 4000);
      } catch (err) {
        showBanner(`Delete error: ${err.message}`);
      }
    },

    // Route Modals
    addRouteModal: (recId) => {
      const rec = state.recipients.find((r) => r.id === recId);
      const svcOptions = state.services.map((s) => {
        const full = `${s.domain}.${s.service}`;
        return `<option value="${escapeHtml(full)}">${escapeHtml(full)} (${escapeHtml(s.description || 'Notify')})</option>`;
      }).join('');

      const html = `
        <form id="modal-route-form" class="form-grid">
          <div class="form-group">
            <label for="route-name">Route Label *</label>
            <input type="text" id="route-name" required placeholder="e.g. Pixel Phone or HA Notification" />
          </div>
          <div class="form-group">
            <label for="route-service">HA Service Action *</label>
            <select id="route-service">
              ${svcOptions || '<option value="persistent_notification.create">persistent_notification.create</option>'}
            </select>
          </div>
          <div class="form-group">
            <label for="route-min-priority">Minimum Priority to Dispatch</label>
            <select id="route-min-priority">
              <option value="informational">Informational (All messages)</option>
              <option value="normal" selected>Normal</option>
              <option value="urgent">Urgent Only</option>
            </select>
          </div>
          <div class="form-group">
            <label><input type="checkbox" id="route-enabled" checked /> Route Enabled</label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">Save Route</button>
          </div>
        </form>
      `;
      openModal(`Add Route for ${rec ? rec.name : 'Recipient'}`, html);
      document.getElementById('modal-route-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const name = document.getElementById('route-name').value.trim();
          const selectedSvc = document.getElementById('route-service').value;
          const [haDomain, haService] = selectedSvc.includes('.') ? selectedSvc.split('.', 2) : ['notify', selectedSvc];
          const minPri = document.getElementById('route-min-priority').value;
          const enabled = document.getElementById('route-enabled').checked;

          await apiPost('/api/routes', {
            recipient_id: recId,
            name,
            ha_domain: haDomain,
            ha_service: haService,
            priority_min: minPri,
            enabled,
          });
          closeModal();
          await refreshAllData();
          showBanner('Route saved successfully.', 'success', 4000);
        } catch (err) {
          showBanner(`Route save error: ${err.message}`);
        }
      });
    },

    deleteRoute: async (routeId) => {
      if (!confirm('Are you sure you want to delete this route?')) return;
      try {
        await apiDelete(`/api/routes/${routeId}`);
        await refreshAllData();
        showBanner('Route deleted.', 'success', 4000);
      } catch (err) {
        showBanner(`Delete error: ${err.message}`);
      }
    },

    testRoute: async (routeId) => {
      try {
        showBanner('Testing route dispatch to Home Assistant…', 'info', 3000);
        const res = await apiPost(`/api/routes/${routeId}/test`, {});
        if (res.success) {
          showBanner(`Route test SUCCESS: submitted to ${res.ha_service}`, 'success', 5000);
        } else {
          showBanner(`Route test FAILED: ${res.error || 'Unknown error'}`);
        }
      } catch (err) {
        showBanner(`Test error: ${err.message}`);
      }
    },

    // Group Modals
    addGroupModal: () => {
      const recCheckboxes = state.recipients.map((r) => `
        <label class="checkbox-inline">
          <input type="checkbox" name="grp-rec" value="${escapeHtml(r.id)}" /> ${escapeHtml(r.name)}
        </label>
      `).join('');

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
          const checked = Array.from(document.querySelectorAll('input[name="grp-rec"]:checked')).map((c) => c.value);

          await apiPost('/api/groups', {
            name,
            description: desc,
            recipient_ids: checked,
          });
          closeModal();
          await refreshAllData();
          showBanner('Group created successfully.', 'success', 4000);
        } catch (err) {
          showBanner(`Group error: ${err.message}`);
        }
      });
    },

    editGroup: (groupId) => {
      const grp = state.groups.find((g) => g.id === groupId);
      if (!grp) return;

      const recCheckboxes = state.recipients.map((r) => {
        const isMember = (grp.recipient_ids || []).includes(r.id);
        return `
          <label class="checkbox-inline">
            <input type="checkbox" name="grp-rec" value="${escapeHtml(r.id)}" ${isMember ? 'checked' : ''} /> ${escapeHtml(r.name)}
          </label>
        `;
      }).join('');

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
          const checked = Array.from(document.querySelectorAll('input[name="grp-rec"]:checked')).map((c) => c.value);

          await apiPost('/api/groups', {
            id: groupId,
            name,
            description: desc,
            recipient_ids: checked,
          });
          closeModal();
          await refreshAllData();
          showBanner('Group updated successfully.', 'success', 4000);
        } catch (err) {
          showBanner(`Group error: ${err.message}`);
        }
      });
    },

    deleteGroup: async (groupId) => {
      if (!confirm('Are you sure you want to delete this group?')) return;
      try {
        await apiDelete(`/api/groups/${groupId}`);
        await refreshAllData();
        showBanner('Group deleted.', 'success', 4000);
      } catch (err) {
        showBanner(`Group delete error: ${err.message}`);
      }
    },

    // Policy Modals
    addPolicyModal: () => {
      const recOptions = state.recipients.map((r) => `<option value="${escapeHtml(r.id)}">Recipient: ${escapeHtml(r.name)}</option>`).join('');
      const grpOptions = state.groups.map((g) => `<option value="${escapeHtml(g.id)}">Group: ${escapeHtml(g.name)}</option>`).join('');

      const html = `
        <form id="modal-policy-form" class="form-grid">
          <div class="form-group">
            <label for="pol-target">Target Scope</label>
            <select id="pol-target">
              <optgroup label="Recipients">
                ${recOptions}
              </optgroup>
              <optgroup label="Groups">
                ${grpOptions}
              </optgroup>
              <optgroup label="Global">
                <option value="household_global">Household Global Policy</option>
              </optgroup>
            </select>
          </div>
          <div class="form-group">
            <label for="pol-start">Quiet Start Time (HH:MM)</label>
            <input type="time" id="pol-start" value="22:00" required />
          </div>
          <div class="form-group">
            <label for="pol-end">Quiet End Time (HH:MM)</label>
            <input type="time" id="pol-end" value="07:00" required />
          </div>
          <div class="form-group">
            <label>Active Days</label>
            <div class="checkboxes-wrap">
              ${DAY_NAMES.map((d, idx) => `
                <label class="checkbox-inline"><input type="checkbox" name="pol-day" value="${idx}" checked /> ${d}</label>
              `).join('')}
            </div>
          </div>
          <div class="form-group">
            <label><input type="checkbox" id="pol-urgent-override" checked /> Urgent messages override quiet hours</label>
          </div>
          <div class="form-group">
            <label><input type="checkbox" id="pol-enabled" checked /> Policy Enabled</label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">Save Policy</button>
          </div>
        </form>
      `;
      openModal('Create Quiet Hours Policy', html);
      document.getElementById('modal-policy-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const targetId = document.getElementById('pol-target').value;
          let targetType = 'recipient';
          if (state.groups.some((g) => g.id === targetId)) targetType = 'group';
          else if (targetId === 'household_global') targetType = 'global';

          const quietStart = document.getElementById('pol-start').value;
          const quietEnd = document.getElementById('pol-end').value;
          const days = Array.from(document.querySelectorAll('input[name="pol-day"]:checked')).map((c) => parseInt(c.value, 10));
          const urgentOverride = document.getElementById('pol-urgent-override').checked;
          const enabled = document.getElementById('pol-enabled').checked;

          await apiPost('/api/policies', {
            target_id: targetId,
            target_type: targetType,
            quiet_start: quietStart,
            quiet_end: quietEnd,
            day_mask: days,
            urgent_override: urgentOverride,
            enabled,
          });
          closeModal();
          await refreshAllData();
          showBanner('Policy created successfully.', 'success', 4000);
        } catch (err) {
          showBanner(`Policy error: ${err.message}`);
        }
      });
    },

    deletePolicy: async (policyId) => {
      if (!confirm('Are you sure you want to delete this quiet hours policy?')) return;
      try {
        await apiDelete(`/api/policies/${policyId}`);
        await refreshAllData();
        showBanner('Policy deleted.', 'success', 4000);
      } catch (err) {
        showBanner(`Policy delete error: ${err.message}`);
      }
    },
  };

  // --- Attach Header / Global Listeners ---
  if (el.btnRefreshServices) {
    el.btnRefreshServices.addEventListener('click', async () => {
      try {
        showBanner('Syncing services from Home Assistant…', 'info', 2000);
        const data = await apiGet('/api/services?refresh=true');
        state.services = data.services || [];
        await refreshAllData();
        showBanner('Services synchronized.', 'success', 3000);
      } catch (err) {
        showBanner(`Sync error: ${err.message}`);
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
        const res = await apiPost('/api/history/purge?days=30', {});
        showBanner(`Purged ${res.count} records.`, 'success', 4000);
        await loadHistory();
      } catch (err) {
        showBanner(`Purge error: ${err.message}`);
      }
    });
  }

  // --- Main Refresh Function ---
  async function refreshAllData() {
    try {
      const [sum, svcs, recs, grps, pols] = await Promise.all([
        apiGet('/api/summary'),
        apiGet('/api/services'),
        apiGet('/api/recipients'),
        apiGet('/api/groups'),
        apiGet('/api/policies'),
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
      showBanner(`Failed to load data: ${err.message}`);
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
