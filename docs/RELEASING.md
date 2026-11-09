# Releasing an add-on

Each add-on in this repository has its own version in its folder's `config.yaml`. Do **not** assign one version to the entire repository.

| Add-on | Folder | GitHub release tag |
| --- | --- | --- |
| Full MCP | `ha_full_mcp` | `ha-full-mcp-v1.11.1` |
| Lifeboat | `ha_addons` | `ha-lifeboat-v1.4.0` |
| Baby Tracker | `baby_tracker` | `baby-tracker-v1.0.5` |
| Home Stock | `home_stock` | `home-stock-v1.0.0` |

**Published initial releases (2026-11-09):** `ha-full-mcp-v1.11.1` and `ha-lifeboat-v1.4.0`. The Baby Tracker and Home Stock tags remain proposals until verified and published.

## Checklist before publishing

1. Confirm the current add-on behavior and the README claims on a test Home Assistant installation.
2. Run the repository's quality workflow; inspect failures before releasing.
3. Check `config.yaml`, any internal version constants, README, and CHANGELOG for consistency.
4. Review security implications of new or changed MCP tools. Do not paste tokens or unredacted logs into release notes.
5. Publish a tag only from a reviewed commit on `main`. Use a unique namespaced tag because the four add-ons have independent versions.
6. In GitHub **Releases > Draft a new release**, choose the matching tag, title it with the add-on name and version, and use the add-on CHANGELOG as the source of release notes.
7. Test an update from the previous installed version on a non-critical Home Assistant environment. Verify the Lifeboat recovery route for Full MCP changes.
8. If publishing fails, do not retag a different commit under the same published version without documenting the correction.

Publication is managed by the manual [Publish an add-on release workflow](../.github/workflows/publish-release.yml). Publishing releases does not deploy add-ons to Home Assistant.

## Suggested next step

Initial GitHub Releases are published for both MCP add-ons. Baby Tracker and Home Stock still need independent installation and behavior verification before their first tagged releases. Future releases should be driven by genuine version changes, not GitHub activity.
