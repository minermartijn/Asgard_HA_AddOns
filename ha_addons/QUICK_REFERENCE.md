# Quick Reference - API Key Authentication

## Generate API Key

```bash
python3 generate_api_key.py
```

## Add-on Configuration

```yaml
ha_token: "your_ha_token"
api_key: "your_generated_api_key"
```

## Kiro MCP Configuration

```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://YOUR_HA_IP:8015/sse",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

## Alternative Header Format

You can also use `X-API-Key` header:

```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://YOUR_HA_IP:8015/sse",
      "headers": {
        "X-API-Key": "YOUR_API_KEY"
      }
    }
  }
}
```

## Testing with curl

```bash
# Test SSE endpoint
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://YOUR_HA_IP:8015/sse

# Or with X-API-Key
curl -H "X-API-Key: YOUR_API_KEY" \
  http://YOUR_HA_IP:8015/sse
```

## What Happens Without API Key

If you don't configure an API key in the add-on:
1. A random key is generated on startup
2. The key is displayed in the add-on logs
3. You must copy this key to your Kiro configuration
4. The key will change every time the add-on restarts

**Recommendation:** Always configure a permanent API key in the add-on settings.
