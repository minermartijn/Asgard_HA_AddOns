---
inclusion: always
---

# Home Assistant Addon Development Rules

## CRITICAL: config.yaml Configuration

### ❌ NEVER Add the `image` Field to config.yaml

**WRONG - DO NOT DO THIS:**
```yaml
name: Home Assistant KIRO MCP Server ADDON
version: "1.1.0"
slug: ha_mcp_server_addon_kiro
image: local/amd64-addon-ha_mcp_server_addon_kiro  # ❌ NEVER ADD THIS
```

**CORRECT - Always use this format:**
```yaml
name: Home Assistant KIRO MCP Server ADDON
version: "1.1.0"
slug: ha_mcp_server_addon_kiro
description: Model Context Protocol server for Home Assistant with full API access
# NO image field - let Home Assistant build from Dockerfile
```

### Why This Matters

When you add an `image` field to `config.yaml`:
- Home Assistant treats it as a pre-built image to pull from a registry
- Version changes trigger "Update" instead of "Rebuild"
- Update attempts fail with 401/404 errors (image doesn't exist in registry)
- The addon cannot be updated or rebuilt properly

When you OMIT the `image` field:
- Home Assistant builds the image locally using `Dockerfile` and `build.json`
- Version changes trigger proper "Rebuild" option
- Rebuilds work correctly from source code
- This is the correct approach for local addon development

## Local Addon Build Configuration

### Required Files

1. **config.yaml** - Addon manifest (NO image field)
2. **build.json** - Build configuration with base images
3. **Dockerfile** - Container build instructions
4. **run.sh** - Startup script

### Correct build.json Format

```json
{
  "build_from": {
    "aarch64": "ghcr.io/home-assistant/aarch64-base:3.19",
    "amd64": "ghcr.io/home-assistant/amd64-base:3.19",
    "armhf": "ghcr.io/home-assistant/armhf-base:3.19",
    "armv7": "ghcr.io/home-assistant/armv7-base:3.19",
    "i386": "ghcr.io/home-assistant/i386-base:3.19"
  }
}
```

This tells Home Assistant which base images to use for building, not which pre-built image to pull.

## Version Updates for Local Addons

### Correct Process

1. Update version in `config.yaml`:
   ```yaml
   version: "1.1.0"
   ```

2. Update `CHANGELOG.md` with changes

3. User rebuilds addon through Home Assistant UI:
   - Settings → Add-ons → [Addon Name]
   - Click "Rebuild" button
   - Wait for build to complete

4. Test the new version

### What NOT to Do

- ❌ Don't add `image` field to config.yaml
- ❌ Don't try to use `update_addon` API for local addons
- ❌ Don't expect "Update" button to work (it will fail)

## Addon Slug Naming

### Local Addon Slug

When Home Assistant installs a local addon, it prefixes the slug with `local_`:
- **config.yaml slug**: `ha_mcp_server_addon_kiro`
- **Actual installed slug**: `local_ha_mcp_server_addon_kiro`

Always use the `local_` prefixed slug when calling MCP tools:
```python
mcp_home_assistant_get_addon_info(addon_slug="local_ha_mcp_server_addon_kiro")
```

## Common Errors and Solutions

### Error: "Failed to fetch manifest - 401"

**Cause**: `image` field in config.yaml makes Home Assistant try to pull from Docker Hub

**Solution**: Remove the `image` field from config.yaml

### Error: "pull access denied - 404"

**Cause**: Same as above - trying to pull non-existent image

**Solution**: Remove the `image` field from config.yaml

### Error: "Addon is not rebuildable"

**Cause**: Addon configuration issue or API limitation

**Solution**: Use Home Assistant UI to rebuild instead of API

## Best Practices

1. **Never add `image` field** to config.yaml for local addons
2. **Always use build.json** to specify base images
3. **Test rebuilds** after version changes
4. **Document version changes** in CHANGELOG.md
5. **Use UI for rebuilds** - more reliable than API

## Summary

**Golden Rule**: For local addon development, NEVER add the `image` field to config.yaml. Let Home Assistant build from source using Dockerfile and build.json.
