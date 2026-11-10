# Security policy

These apps integrate with Home Assistant. The MCP servers expose administrative operations, including configuration, app management, backup operations, and device control. Treat access to either MCP server as **high privilege**.

## Reporting a vulnerability

Please **do not open a public issue containing exploit details, API keys, long-lived access tokens, private configuration, or unredacted logs**.

If GitHub's private vulnerability reporting option is enabled for this repository, use **Security → Report a vulnerability** to contact the maintainer privately. If it is not enabled, contact the maintainer via their GitHub profile to arrange a private reporting channel before sending sensitive details.

Useful information to include: the affected app and version, a concise impact description, reproduction steps using dummy credentials, and a proposed mitigation if known. No response or fix deadline is guaranteed.

## Safe deployment guidance

- **Use a trusted network by default.** Do not expose ports 8010 or 8015 directly to the public internet. If remote access is necessary, use TLS and an appropriately configured access gateway or VPN, with additional authentication and network restrictions where possible.
- **Prefer API keys in headers** (such as `Authorization: Bearer` or `X-API-Key`) when the client supports them.
- **Treat URL-based keys as sensitive.** The MCP servers also accept keys in query parameters or URL paths for compatibility, but these can be recorded in reverse-proxy/access logs, browser history, monitoring systems, and copied configuration. Redact them from logs and support requests, and rotate any exposed key.
- **Protect Home Assistant credentials.** Store the long-lived Home Assistant token and MCP API keys in the app configuration or an appropriate secrets store; never commit them to Git.
- **Apply least privilege.** The Full MCP server enables powerful tools by default. Disable tools you don't require, especially destructive operations and configuration writes. Be aware that Lifeboat can still administer apps and backups.
- **Review AI actions.** Where practical, require human confirmation for destructive actions such as deleting backups, removing integrations, changing configurations, and restoring backups.
- **Update carefully.** Keep verified backups and maintain an independent recovery route before changing or restarting the primary MCP server.

These precautions reduce risk but do not replace a security audit. The existence of this policy is not a claim that the apps have undergone independent penetration testing.
