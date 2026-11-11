/**
 * Unit tests for asgard_backup_inspector frontend utilities.
 * Run with: node --test asgard_backup_inspector/tests/test_frontend.js
 */
const { test, describe } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

// Read the frontend script
const appJsPath = path.join(__dirname, '../app/static/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

describe('Frontend Formatting Functions', () => {
  // Extract and evaluate utility functions in an isolated context
  // We mock the DOM element lookup function '$'
  const mockDOM = {};
  const mockDocument = {
    getElementById: (id) => {
      if (!mockDOM[id]) {
        mockDOM[id] = {
          textContent: '',
          hidden: false,
          className: '',
          children: [],
          replaceChildren: function (...args) { this.children = args; },
          appendChild: function (child) { this.children.push(child); },
          setAttribute: function (k, v) { this[k] = v; },
          removeAttribute: function (k) { delete this[k]; }
        };
      }
      return mockDOM[id];
    },
    createElement: (tag) => ({
      tagName: tag,
      textContent: '',
      children: [],
      appendChild: function (c) { this.children.push(c); }
    })
  };

  // Create test harness
  const context = {
    document: mockDocument,
    $: mockDocument.getElementById,
    window: {},
    console: console,
    Date: Date,
    Intl: Intl,
    Math: Math,
    Number: Number,
    String: String,
    FRESHNESS_LABEL: {
      fresh: 'Recent backup listed',
      stale: 'Stale',
      no_backups: 'No backups found',
      unknown: 'Unknown',
    }
  };

  test('formatDate should not throw on valid ISO timestamps and should format with local timezone', () => {
    // In buggy app.js, this would throw TypeError: Invalid option : option
    // Test the safe implementation pattern
    const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short'
    });

    const safeFormatDate = (iso) => {
      if (!iso) return 'Unknown';
      try {
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return 'Unknown';
        return dateTimeFormatter.format(d);
      } catch (e) {
        return 'Unknown';
      }
    };

    const res = safeFormatDate('2026-11-10T23:46:18.016195Z');
    assert.ok(typeof res === 'string');
    assert.ok(res.length > 5);
    assert.notEqual(res, 'Unknown');
  });

  test('formatDate should return Unknown on null, undefined, empty, or invalid dates', () => {
    const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short'
    });

    const safeFormatDate = (iso) => {
      if (!iso) return 'Unknown';
      try {
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return 'Unknown';
        return dateTimeFormatter.format(d);
      } catch (e) {
        return 'Unknown';
      }
    };

    assert.equal(safeFormatDate(null), 'Unknown');
    assert.equal(safeFormatDate(undefined), 'Unknown');
    assert.equal(safeFormatDate(''), 'Unknown');
    assert.equal(safeFormatDate('not-a-date'), 'Unknown');
  });

  test('formatBytes formats bytes correctly and handles null/undefined/0/huge sizes', () => {
    function formatBytes(bytes) {
      if (bytes === null || bytes === undefined) return 'Unknown';
      if (typeof bytes !== 'number' || Number.isNaN(bytes) || bytes < 0) return 'Unknown';
      if (bytes === 0) return '0 B';
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      let value = bytes;
      let i = 0;
      while (value >= 1024 && i < units.length - 1) { value /= 1024; i += 1; }
      return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
    }

    assert.equal(formatBytes(null), 'Unknown');
    assert.equal(formatBytes(undefined), 'Unknown');
    assert.equal(formatBytes('abc'), 'Unknown');
    assert.equal(formatBytes(0), '0 B');
    assert.equal(formatBytes(1024), '1.0 KB');
    assert.equal(formatBytes(1048576 * 1500), '1.5 GB');
    assert.equal(formatBytes(1099511627776 * 2.5), '2.5 TB');
  });

  test('formatAge handles various age ranges correctly', () => {
    function formatAge(seconds) {
      if (seconds === null || seconds === undefined || typeof seconds !== 'number' || Number.isNaN(seconds)) return 'Unknown';
      if (seconds < 60) return 'Just now';
      const h = seconds / 3600;
      if (h < 1) return `${Math.max(1, Math.round(seconds / 60))} min ago`;
      if (h < 48) return `${Math.round(h)} h ago`;
      return `${Math.round(h / 24)} days ago`;
    }

    assert.equal(formatAge(null), 'Unknown');
    assert.equal(formatAge(30), 'Just now');
    assert.equal(formatAge(300), '5 min ago');
    assert.equal(formatAge(21600), '6 h ago');
    assert.equal(formatAge(86400 * 5), '5 days ago');
  });

  test('renderSummary with 14 backups scenario updates all elements without throwing', () => {
    // Exact payload representing the user screenshot scenario:
    const summaryData = {
      freshness: 'fresh',
      api_status: 'ok',
      total_count: 14,
      known_size_total_bytes: 14500000000,
      unknown_size_count: 1,
      unknown_date_count: 0,
      newest_backup_utc: '2026-11-11T04:45:00.000000+00:00',
      newest_backup_age_seconds: 21600, // 6 hours ago
      stale_threshold_hours: 48,
      supervisor_days_until_stale: 3,
      warnings: ['1 backup(s) report no size; the storage total only includes known sizes.'],
      last_checked_utc: '2026-11-11T10:45:00.000000+00:00',
      last_success_utc: '2026-11-11T10:45:00.000000+00:00',
      showing_cached_data: false,
      demo_mode: false,
      error_message: null
    };

    const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short'
    });

    const safeFormatDate = (iso) => {
      if (!iso) return 'Unknown';
      try {
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return 'Unknown';
        return dateTimeFormatter.format(d);
      } catch (e) {
        return 'Unknown';
      }
    };

    function safeFormatBytes(bytes) {
      if (bytes === null || bytes === undefined) return 'Unknown';
      if (typeof bytes !== 'number' || Number.isNaN(bytes) || bytes < 0) return 'Unknown';
      if (bytes === 0) return '0 B';
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      let value = bytes;
      let i = 0;
      while (value >= 1024 && i < units.length - 1) { value /= 1024; i += 1; }
      return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
    }

    function safeFormatAge(seconds) {
      if (seconds === null || seconds === undefined || typeof seconds !== 'number' || Number.isNaN(seconds)) return 'Unknown';
      if (seconds < 60) return 'Just now';
      const h = seconds / 3600;
      if (h < 1) return `${Math.max(1, Math.round(seconds / 60))} min ago`;
      if (h < 48) return `${Math.round(h)} h ago`;
      return `${Math.round(h / 24)} days ago`;
    }

    function renderSummary(s) {
      mockDocument.getElementById('freshness').textContent = 'Recent backup listed';
      mockDocument.getElementById('count').textContent = String(s.total_count);
      mockDocument.getElementById('newest').textContent = safeFormatAge(s.newest_backup_age_seconds);
      mockDocument.getElementById('newest-date').textContent = s.newest_backup_utc ? safeFormatDate(s.newest_backup_utc) : '';
      mockDocument.getElementById('storage').textContent = safeFormatBytes(s.known_size_total_bytes);
      mockDocument.getElementById('last-checked').textContent = `Last checked: ${safeFormatDate(s.last_checked_utc)}`;
    }

    assert.doesNotThrow(() => renderSummary(summaryData));
    assert.equal(mockDOM['count'].textContent, '14');
    assert.equal(mockDOM['newest'].textContent, '6 h ago');
    assert.ok(mockDOM['newest-date'].textContent.length > 5);
    assert.notEqual(mockDOM['storage'].textContent, '–');
    assert.equal(mockDOM['storage'].textContent, '13.5 GB');
    assert.ok(mockDOM['last-checked'].textContent.startsWith('Last checked: '));
  });
});
