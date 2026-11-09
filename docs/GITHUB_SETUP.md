# GitHub profile and repository settings checklist

Some GitHub settings cannot be changed by this connector. Use the following exact values and actions after merging the documentation PR.

## Public profile README

GitHub shows a README on your profile only when you create a **public repository named exactly `minermartijn`** under the `minermartijn` account and place `README.md` at its root.

1. Create `minermartijn/minermartijn` as a public repository.
2. Copy the contents of [PROFILE_README.md](PROFILE_README.md) into that repository's root `README.md`.
3. On your profile, pin `Asgard_HA_AddOns`, `MyMonitor` and `MyCurl` (or replace a pin if another repo is more actively maintained). Verify all names and links first.

## Repository About panel

Proposed description:

> Home Assistant add-ons with MCP servers for AI-assisted control and independent recovery, plus household utilities.

Suggested topics (choose those accurately describing the project):

`home-assistant`, `home-assistant-addon`, `mcp-server`, `model-context-protocol`, `python`, `ai-agents`, `automation`, `smart-home`

Update these under the repository About panel using its gear icon. No claim is made that these settings have been changed.

## Security settings

- Enable private vulnerability reporting if available under Settings → Security (consult GitHub's current UI).
- Enable Dependabot alerts and secret scanning where available; verify feature eligibility and current settings.
- Consider branch protection/rulesets requiring CI after the checks are confirmed reliable. As a solo maintainer, allow an explicit owner bypass if needed, rather than forcing unreviewable deadlocks.
- Never turn on required checks until the tests actually pass.

## Releases

See [RELEASING.md](RELEASING.md); do not publish initial GitHub Releases until each published add-on version has been verified on a test installation.
