# Contributing to Asgard Home Assistant Add-ons

Thanks for helping improve these projects. This repository is maintained by an independent developer and welcomes reproducible issues, documentation fixes, tests, and focused pull requests.

## Before you contribute

- Check existing issues and the latest add-on changelog. Keep changes scoped to one add-on where possible.
- For security vulnerabilities, **do not open a public issue**. Follow [SECURITY.md](SECURITY.md).
- Never post real API keys, Home Assistant long-lived tokens, passwords, private addresses, or unredacted logs.

## Repository layout

| Directory | Project |
| --- | --- |
| `ha_full_mcp/` | Full Home Assistant MCP server |
| `ha_addons/` | Independent Lifeboat MCP server |
| `baby_tracker/` | Baby Tracker |
| `home_stock/` | Home Stock |

## Development workflow

1. Fork the repository and branch from `main`.
2. Read [the maintainer guide](docs/MAINTAINING.md) plus the appropriate README and changelog.
3. For Python code, create a virtual environment and install the affected add-on's `requirements.txt`.
4. Run `python -m compileall -q baby_tracker home_stock ha_addons/src ha_full_mcp/src` from the repository root.
5. For MCP changes, run `python -m unittest discover -s ha_full_mcp/tests -p 'test_*.py' -v` and/or `python -m unittest discover -s ha_addons/tests -p 'test_*.py' -v`. The tests require the relevant add-on dependencies and `httpx-sse`; some Lifeboat tests start local HTTP servers.
6. For changes that depend on Home Assistant Supervisor, validate on a test installation as well. Unit tests do not replace an integration test.
7. Update `config.yaml`, source version constants, README, and CHANGELOG together when releasing an add-on.
8. Open a PR describing the changed add-on, risk, tests actually run, and any manual validation.

Do not claim a test passed unless you ran it. If a check fails, include the failure.

## Commit attribution

Commits should use the contributor's real identity and preserve legitimate human contributions. See the [maintainer guide](docs/MAINTAINING.md) for commit and release conventions.

## Releases

Each add-on is versioned separately; see [Releasing](docs/RELEASING.md). Do not assume all add-ons share one release version.

## License

This repository's root MIT license covers original code owned by the maintainer. Contributions are submitted under that license unless otherwise agreed. Third-party dependencies and assets retain their own licenses.
