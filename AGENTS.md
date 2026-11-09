# Repository agent instructions

This repository contains four Home Assistant add-ons: `ha_full_mcp`, `ha_addons` (Lifeboat), `baby_tracker`, and `home_stock`.

Read `GEMINI.md` and `CLAUDE.md` for repository-specific development, documentation, versioning, and release instructions. Ensure all software changes follow the project security guidance in `SECURITY.md`.

## Commit identity and attribution

- Follow the repository owner's configured Git author and committer identity; do not spoof identities.
- Do not add AI assistants, programming tools, or orchestration systems (Claude, Paperclip, Codex, Gemini, etc.) as Git co-authors.
- Never append `Co-Authored-By` trailers for AI agents or tool-specific session URLs/identifiers to commit messages.
- Preserve legitimate human contributor attribution where applicable.
- Do not rewrite existing commit history without explicit authorization.

## Change safety

- Do not modify Home Assistant add-on configuration, startup commands, credentials, authentication, scopes, or ports as a side effect of documentation changes.
- When changing an add-on, keep its `config.yaml`, version constants, changelog, and README synchronized.
- Before claiming tests pass, run the relevant suite and report the actual outcome.
