# Security Documentation

## Overview

This document outlines the security measures implemented in the Home Assistant MCP Server and provides guidance for secure deployment.

## Security Features

### 1. Authentication

**API Key Authentication**
- All endpoints require API key authentication
- API keys are generated using `secrets.token_urlsafe(32)` providing 256 bits of entropy
- Supports multiple authentication methods:
  - Path parameter: `/messages/{api_key}` (recommended for Cloudflare)
  - Query parameter: `?api_key=xxx`
  - Authorization header: `Bearer {api_key}`
  - X-API-Key header: `{api_key}`

**Timing Attack Protection**
- API key comparisons use `secrets.compare_digest()` for constant-time comparison
- Prevents timing attacks that could leak key information

**No Unauthenticated Endpoints**
- All HTTP endpoints require valid API key
- No health check or status endpoints exposed without authentication
- MCP resources are only accessible after authentication

### 2. Transport Security

**HTTPS Enforcement**
- Server should always be deployed behind HTTPS proxy (Cloudflare, nginx, etc.)
- API keys transmitted over HTTPS are encrypted in transit
- Never expose the server directly on HTTP in production

**Cloudflare Compatibility**
- Path-based authentication survives proxy forwarding
- API key embedded in URL path is preserved through Cloudflare

### 3. Token Management

**Supervisor Token**
- Automatically provided by Home Assistant
- Used for Supervisor API access (addon management)
- Never exposed in logs or responses

**Home Assistant Core Token**
- Optional long-lived access token
- Used for Core API access (entities, services)
- Stored securely in addon configuration
- Only boolean flag logged (not actual token)

**API Key Storage**
- Stored in addon configuration (encrypted by Home Assistant)
- Only logged once during initial generation
- User must save and configure in MCP client

### 4. Input Validation

**Parameter Validation**
- All tool handlers validate required parameters
- Type checking on configuration options
- Empty string checks on addon_slug parameters
- JSON structure validation for configuration objects

**Error Handling**
- Specific error messages for different failure modes
- No sensitive information in error responses
- Proper HTTP status codes (401, 403, 404, 400)

### 5. Logging Security

**Safe Logging Practices**
- API keys only logged during initial generation (necessary for user setup)
- Tokens logged as boolean flags only (SET/NOT SET)
- Authentication failures logged with IP address for monitoring
- No sensitive data in normal operation logs

### 6. CORS Configuration

**Current Configuration**
```python
allow_origins=["*"]
allow_credentials=True
allow_methods=["*"]
allow_headers=["*"]
```

**Security Considerations**
- Permissive CORS is acceptable because all endpoints require API key
- API key provides strong authentication (256-bit entropy)
- Server typically behind Cloudflare or similar proxy
- HTTPS enforced in production

**Hardening (Optional)**
For stricter security, configure specific origins:
```python
allow_origins=[
    "https://your-domain.com",
    "https://kiro.app",
]
```

## Security Best Practices

### Deployment

1. **Always Use HTTPS**
   - Deploy behind Cloudflare, nginx, or similar HTTPS proxy
   - Never expose port 8015 directly to the internet
   - Use Cloudflare tunnel or VPN for remote access

2. **Strong API Keys**
   - Use generated API keys (256-bit entropy)
   - Never use weak or predictable keys
   - Rotate keys if compromised

3. **Network Isolation**
   - Run server in Home Assistant addon (isolated container)
   - Use `host_network: true` for Supervisor API access
   - Firewall rules to restrict access

4. **Access Control**
   - Limit API key distribution
   - One key per client/user
   - Revoke keys when no longer needed

### Monitoring

1. **Log Monitoring**
   - Monitor for unauthorized access attempts
   - Check for unusual patterns in logs
   - Alert on repeated 401 errors

2. **Audit Trail**
   - All tool executions logged
   - Authentication attempts logged with IP
   - Failed authentications logged with details

### Key Rotation

To rotate API keys:
1. Generate new key: `python generate_api_key.py`
2. Update addon configuration with new key
3. Restart addon
4. Update all MCP clients with new key
5. Old key immediately invalidated

## Threat Model

### Protected Against

✅ **Timing Attacks**
- Constant-time comparison prevents key guessing

✅ **Brute Force Attacks**
- 256-bit key space (2^256 combinations)
- Computationally infeasible to brute force

✅ **Man-in-the-Middle (MITM)**
- HTTPS encryption protects API key in transit
- Cloudflare provides TLS termination

✅ **Unauthorized Access**
- All endpoints require authentication
- No bypass routes or backdoors

✅ **Token Leakage**
- Tokens not exposed in logs (except initial generation)
- Tokens not included in error messages

### Potential Risks

⚠️ **API Key Exposure**
- If API key is leaked, attacker has full access
- Mitigation: Use HTTPS, secure key storage, key rotation

⚠️ **Log File Access**
- Generated API key visible in initial logs
- Mitigation: Secure log file access, rotate key after setup

⚠️ **No Rate Limiting**
- No built-in rate limiting on authentication attempts
- Mitigation: Strong key makes brute force infeasible, use Cloudflare rate limiting

⚠️ **Permissive CORS**
- Allows requests from any origin
- Mitigation: API key required, HTTPS enforced, can restrict origins if needed

## Security Checklist

Before deploying to production:

- [ ] HTTPS proxy configured (Cloudflare, nginx, etc.)
- [ ] Strong API key generated and saved securely
- [ ] API key configured in addon settings
- [ ] API key configured in MCP clients
- [ ] Firewall rules configured (if applicable)
- [ ] Log monitoring enabled
- [ ] Backup of configuration created
- [ ] Access limited to authorized users only
- [ ] Initial API key from logs rotated (optional)

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Contact the maintainer privately
3. Provide detailed description of the vulnerability
4. Include steps to reproduce (if applicable)
5. Allow time for fix before public disclosure

## Security Updates

- Version 0.6.0: Added constant-time API key comparison
- Version 0.6.0: Documented CORS security considerations
- Version 0.6.0: Implemented comprehensive authentication

## References

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [Python secrets module](https://docs.python.org/3/library/secrets.html)
- [Starlette Security](https://www.starlette.io/middleware/#corsmiddleware)
- [Home Assistant Security](https://www.home-assistant.io/docs/configuration/securing/)
