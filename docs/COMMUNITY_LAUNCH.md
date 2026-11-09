# Community introduction draft (not posted)

This is a draft for a Home Assistant community forum discussion or relevant developer community. Confirm the software works on the claimed versions, observe each community's self-promotion rules, and add a real demo link before publishing.

## Suggested title

Two independent MCP add-ons for Home Assistant: full management + a recovery Lifeboat

## Suggested post

I've been building a collection of Home Assistant add-ons as an independent hobbyist developer. Two of them focus on connecting MCP-compatible AI assistants to Home Assistant:

**HA Full MCP Server** provides tools for querying and managing entities, automations, integrations, add-ons, backups and diagnostics.

**HA Addon MCP Server (Lifeboat)** runs as a separate add-on. Its purpose is to keep a way back into the Supervisor when the primary MCP add-on is stopped or an update fails, assuming Home Assistant and the Lifeboat add-on are still working.

The idea came from a practical problem: an AI assistant that updates its own communication server can lose the connection it needs to troubleshoot a failed update.

Both projects are available in my public add-on repository:
https://github.com/minermartijn/Asgard_HA_AddOns

The MCP servers expose sensitive administrative actions, so please read the security guidance before connecting them, and don't expose their ports directly to the internet.

I'd particularly appreciate feedback on the Lifeboat recovery design, documentation, and what would make these useful to other Home Assistant users. Bug reports and contributions are welcome.

**Demo:** [Insert link to a verified, sanitized demo when available.]

I'm maintaining this in my free time, so I can't promise immediate support or claim compatibility with configurations I haven't tested.
