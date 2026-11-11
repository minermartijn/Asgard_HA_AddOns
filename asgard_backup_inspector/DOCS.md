# ASGARD Backup Inspector — Documentation

## Options

| Option | Default | Description |
| --- | --- | --- |
| `stale_threshold_hours` | `48` | If the newest listed backup is older than this, the status is **Stale**. Range 1–2160 hours. |
| `demo_mode` | `false` | Show synthetic example data instead of reading from the Supervisor. The UI then shows a "Demo mode" banner. Useful for previews and screenshots. |

The Supervisor's own "days until stale" backup setting is also shown for reference, but the App's verdict uses `stale_threshold_hours`.

## Statuses

| Status | Meaning |
| --- | --- |
| Recent backup listed | The newest backup with a readable date is within the threshold. |
| Stale | The newest backup is older than the threshold. |
| No backups found | The Supervisor answered and listed zero backups. This is never shown as healthy. |
| Unknown | No usable data: the Supervisor could not be read, or no backup has a readable date. |

## How data is read

- The App calls only `GET http://supervisor/backups/info` with its own Supervisor token.
- Results are cached for 5 minutes. **Refresh** re-reads the metadata (at most once every 10 seconds). Refresh never creates a backup.
- If a check fails after an earlier success, the last good data stays visible and is marked as coming from the last successful check.
- Timestamps are stored in UTC and shown in your browser's time zone, with the zone name included.
- Successful snapshot measurements are recorded in `/data/history.json` (bounded to 500 entries with 1h dedup) to provide authentic storage trends over time without modifying backup archives.

## What metadata is shown

Visible to Home Assistant administrators via Ingress: backup ID, name, creation date, type (full/partial), size, password-protected flag, compression flag and storage location names. Backup contents (included apps/folders), passwords and file paths are not shown. Backup names are not written to the App log.

## Troubleshooting

| Message | Likely cause | What to do |
| --- | --- | --- |
| "not allowed to read backup information (403)" | The Supervisor did not grant access to `/backups/info`. | Make sure the App is up to date and reinstall/restart it so the manifest permissions apply. Please report it with your Supervisor version. |
| "rejected the App token (401)" | Token problem. | Restart the App. |
| "did not answer in time" / "could not be reached" | Supervisor busy, starting or restarting. | Wait and press Refresh. |
| "No Supervisor token is available" | Running outside Home Assistant. | Use `demo_mode`, or run it as a Home Assistant App. |

## Development

```bash
cd asgard_backup_inspector
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python3 -m pytest -q tests
node --test tests/test_frontend.js
```

All test fixtures are synthetic. Never add real backup files or real Supervisor responses to the repository.
