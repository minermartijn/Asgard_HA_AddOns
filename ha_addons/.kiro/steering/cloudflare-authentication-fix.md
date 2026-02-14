---
inclusion: always
---

# Cloudflare Authentication Fix - Critical Solution

## The Core Problem

When deploying an MCP SSE server behind Cloudflare (tunnels, proxies, or CDN), authentication breaks because:

1. **Cloudflare strips authentication headers** - `Authorization` and custom headers like `X-API-Key` are not forwarded by default
2. **MCP clients don't preserve query parameters** - When Kiro connects to `/sse?api_key=xxx`, it successfully authenticates, but then constructs `/messages` requests WITHOUT the `?api_key=xxx` parameter
3. **Result**: All message requests fail with 401 Unauthorized

## The Failed Attempts

### ❌ Attempt 1: Query Parameters
```python
# Tried adding api_key to query params
sse = SseServerTransport("/messages")
# Client config: url: "https://domain.com/sse?api_key=xxx"
```
**Why it failed**: Query params are not preserved when MCP client constructs `/messages` URL

### ❌ Attempt 2: Authorization Headers
```json
{
  "headers": {
    "Authorization": "Bearer API_KEY"
  }
}
```
**Why it failed**: Cloudflare strips these headers before forwarding to backend

### ❌ Attempt 3: X-API-Key Headers
```json
{
  "headers": {
    "X-API-Key": "API_KEY"
  }
}
```
**Why it failed**: Cloudflare also strips custom headers

### ❌ Attempt 4: Session-Based Authentication
```python
# Store authenticated sessions
authenticated_sessions = set()
# Add session_id to set on /sse connection
# Check session_id on /messages
```
**Why it failed**: Session ID comes in `/messages` request, not `/sse` request, so we never captured it

### ❌ Attempt 5: Trust Cloudflare Headers
```python
# Check for CF-Connecting-IP and CF-Ray headers
if cf_ip and cf_ray:
    return True  # Trust all Cloudflare requests
```
**Why it failed**: SECURITY ISSUE - Anyone with the public URL could access the server

## ✅ The Working Solution

**Embed the API key directly in the messages endpoint path:**

```python
# In src/server.py, when creating SSE transport
sse = SseServerTransport(f"/messages/{api_key}")
```

### Why This Works

1. The SSE transport tells the MCP client: "Send messages to `/messages/{api_key}`"
2. The API key is now part of the URL path, not a header or query parameter
3. Cloudflare forwards URL paths unchanged
4. The server extracts the API key from `request.path_params`
5. Authentication succeeds!

### Implementation

```python
# Create SSE transport with API key in path
sse = SseServerTransport(f"/messages/{api_key}")

# Create handler that extracts API key from path
async def handle_messages_with_key(request: Request):
    path_key = request.path_params.get("api_key", "")
    if path_key != api_key:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    await sse.handle_post_message(request.scope, request.receive, request._send)

# Register the route with path parameter
Route("/messages/{api_key}", handle_messages_with_key, methods=["POST"])
```

## Key Insights

1. **URL paths survive proxies** - Unlike headers and query params, URL paths are always preserved
2. **SSE transport controls the messages endpoint** - The endpoint specified in `SseServerTransport()` is what the client uses
3. **Path parameters are secure** - As long as the API key is strong, embedding it in the path is secure over HTTPS
4. **MCP clients follow instructions** - When the server says "use `/messages/{key}`", the client does exactly that

## Verification

Check logs for these patterns:

### ✅ Success Pattern
```
INFO: 192.168.1.10:12345 - "GET /sse?api_key=xxx HTTP/1.1" 200 OK
INFO: 192.168.1.10:12346 - "POST /messages/xxx?session_id=yyy HTTP/1.1" 202 Accepted
```

### ❌ Failure Pattern
```
INFO: 192.168.1.10:12345 - "GET /sse?api_key=xxx HTTP/1.1" 200 OK
WARNING: Unauthorized message attempt from 192.168.1.10, session: yyy
INFO: 192.168.1.10:12346 - "POST /messages?session_id=yyy HTTP/1.1" 401 Unauthorized
```

Notice the difference: Success has `/messages/xxx` (API key in path), failure has `/messages` (no API key).

## When to Use This Pattern

Use this solution when:
- ✅ Deploying MCP SSE servers behind Cloudflare
- ✅ Using any reverse proxy that strips headers
- ✅ Need to support MCP clients that don't preserve query params
- ✅ Want a simple, reliable authentication method

Don't use this pattern when:
- ❌ You have direct network access (use headers instead)
- ❌ You need to rotate keys frequently (path-based keys are harder to rotate)
- ❌ You're implementing OAuth2 or other complex auth flows

## Security Notes

1. **Always use HTTPS** - API keys in URL paths are visible in logs and browser history
2. **Use strong API keys** - Generate with `secrets.token_urlsafe(32)` or similar
3. **Rotate keys if exposed** - If logs are leaked, rotate the API key immediately
4. **Consider Cloudflare Access** - For additional security, add Cloudflare Access authentication on top

## Testing After Changes

If you modify authentication code, test this sequence:

1. Restart the add-on
2. Reconnect the MCP client
3. Check logs for `/messages/{api_key}` pattern (not `/messages`)
4. Run a tool (like `list_addons`)
5. Verify 202 Accepted response (not 401 Unauthorized)

## Related Files

- `src/server.py` - Lines ~165 (SSE transport creation) and ~220-235 (message handler)
- `.kiro/settings/mcp.json` - Client configuration
- `config.yaml` - Add-on configuration with API key option
