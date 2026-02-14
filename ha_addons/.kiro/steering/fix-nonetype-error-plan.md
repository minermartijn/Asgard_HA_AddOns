# Plan: Fix TypeError: 'NoneType' object is not callable

## Problem Analysis

### Current Behavior
```python
async def handle_messages_with_key(request: Request):
    if not verify_path_api_key(request, api_key):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    # This returns None, but Starlette expects a Response object
    await sse.handle_post_message(request.scope, request.receive, request._send)
    # Implicit return None here
```

### Why It Fails
1. `sse.handle_post_message()` signature: `-> None` (returns nothing)
2. It sends the response directly through `request._send` (ASGI send callable)
3. Starlette's routing expects handlers to return a Response object
4. When we return `None`, Starlette tries to call it as `await response(scope, receive, send)`
5. This causes: `TypeError: 'NoneType' object is not callable`

### Why It Still Works
- The response is already sent via `request._send` before the error occurs
- The error happens AFTER the client receives the 202 Accepted response
- It's purely a Starlette routing layer complaint

## Previous Failed Attempt

**What was tried**: Wrapping in a Response object or returning a JSONResponse
```python
await sse.handle_post_message(request.scope, request.receive, request._send)
return JSONResponse({"status": "ok"}, status_code=202)
```

**Why it failed**: 
- `sse.handle_post_message()` already sent the response via `request._send`
- Trying to send another response causes "Response already started" error
- Can't send two responses to the same request

## The Correct Solution

### Option 1: Use Raw ASGI Handler (RECOMMENDED)

Instead of using Starlette's Route, use a raw ASGI app that doesn't expect a return value.

```python
def create_messages_handler_with_path_key(sse: SseServerTransport, api_key: str):
    """Create raw ASGI handler for messages."""
    
    async def handle_messages_asgi(scope, receive, send):
        """Raw ASGI handler - no return value expected"""
        # Parse path params manually
        path_params = scope.get("path_params", {})
        path_key = path_params.get("api_key", "")
        
        if path_key != api_key:
            # Send 401 response manually
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"error": "Unauthorized"}',
            })
            return
        
        # Handle the message - sends response directly
        await sse.handle_post_message(scope, receive, send)
        # No return needed - we're a raw ASGI app
    
    return handle_messages_asgi
```

Then in server.py, mount it differently:
```python
from starlette.routing import Mount

app = Starlette(
    routes=[
        Route("/sse", handle_sse, methods=["GET"]),
        Route("/sse/{api_key}", handle_sse_with_key, methods=["GET"]),
        Mount("/messages", app=handle_messages),  # Raw ASGI app
        Mount("/messages/{api_key}", app=handle_messages_with_key),  # Raw ASGI app
    ]
)
```

**Problem with Option 1**: Mount doesn't support path parameters like `{api_key}`

### Option 2: Custom Middleware Wrapper (BETTER)

Create a middleware that converts the None return into a proper response:

```python
from starlette.responses import Response

def asgi_handler_wrapper(handler):
    """Wrap an ASGI handler that returns None to work with Starlette routing."""
    
    async def wrapped(request: Request):
        # Call the handler (which sends response via request._send)
        await handler(request)
        
        # Return a dummy response that won't be sent
        # (response already sent by handler)
        return Response(status_code=200)
    
    return wrapped
```

**Problem with Option 2**: Still tries to send a second response, causes errors

### Option 3: Use Starlette's Mount with Custom Router (COMPLEX)

Create a custom router that handles the ASGI app directly without expecting returns.

**Problem**: Too complex, requires deep Starlette internals knowledge

### Option 4: Suppress the Error with Exception Handler (HACKY)

Add a custom exception handler that catches and ignores the TypeError:

```python
from starlette.exceptions import HTTPException

async def suppress_nonetype_error(request, exc):
    """Suppress the NoneType callable error - response already sent."""
    if isinstance(exc, TypeError) and "'NoneType' object is not callable" in str(exc):
        # Response was already sent, just return empty response
        return Response(status_code=200)
    # Re-raise other errors
    raise exc

app.add_exception_handler(TypeError, suppress_nonetype_error)
```

**Problem**: Catches ALL TypeErrors, might hide real bugs

## THE ACTUAL SOLUTION: Return Empty Response Object

The key insight: We need to return a Response object, but NOT send it.

```python
from starlette.responses import Response

async def handle_messages_with_key(request: Request):
    """Handle POST messages with API key in path"""
    if not verify_path_api_key(request, api_key):
        logger.warning(f"Unauthorized message attempt from {request.client.host}")
        return JSONResponse(
            {"error": "Unauthorized - Invalid or missing API key"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Handle the message - this sends response directly via request._send
    await sse.handle_post_message(request.scope, request.receive, request._send)
    
    # Return a Response object to satisfy Starlette
    # But use a special flag to prevent it from being sent
    # Actually, we can't do this - Starlette will try to send it
    
    # WAIT - let's check if there's a way to tell Starlette response was already sent
    return None  # This is the problem
```

## THE REAL SOLUTION: Don't Use Starlette Routes for These Endpoints

After deep analysis, the issue is architectural:
- `sse.handle_post_message()` is designed to be called from raw ASGI
- Starlette Routes expect handlers to return Response objects
- These two patterns are incompatible

**Solution**: Use Starlette's lower-level routing that supports raw ASGI apps:

```python
from starlette.routing import Route, Mount
from starlette.applications import Starlette

# For SSE endpoints, use Route (they return responses properly)
# For message endpoints, we need raw ASGI

def create_raw_messages_handler(sse: SseServerTransport, api_key: str):
    """Create raw ASGI app for message handling."""
    
    async def asgi_app(scope, receive, send):
        """Raw ASGI app - handles messages directly."""
        # Check if this is the path with API key
        path = scope.get("path", "")
        
        # Extract API key from path if present
        # Path will be like "/messages/APIKEY" or "/messages"
        path_parts = path.strip("/").split("/")
        
        if len(path_parts) >= 2:
            # Has API key in path
            path_key = path_parts[1]
        else:
            # Check query params or headers
            # Parse query string manually
            query_string = scope.get("query_string", b"").decode()
            # ... parse for api_key
            path_key = None
        
        if path_key != api_key:
            # Send 401
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"error": "Unauthorized"}',
            })
            return
        
        # Handle message
        await sse.handle_post_message(scope, receive, send)
    
    return asgi_app
```

**Problem**: This is getting too complex and error-prone

## FINAL SOLUTION: Accept the Cosmetic Error OR Use Response Subclass

After all this analysis, there are only 2 viable options:

### Option A: Keep Current Code (RECOMMENDED)
- Accept the cosmetic error in logs
- Document it clearly (already done)
- Functionality is perfect
- No risk of breaking anything

### Option B: Create Custom Response Class
```python
class AlreadySentResponse(Response):
    """Response that indicates content was already sent via ASGI."""
    
    async def __call__(self, scope, receive, send):
        """Don't send anything - response already sent."""
        pass  # Do nothing

async def handle_messages_with_key(request: Request):
    if not verify_path_api_key(request, api_key):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    await sse.handle_post_message(request.scope, request.receive, request._send)
    
    # Return special response that does nothing when called
    return AlreadySentResponse()
```

## Recommendation

**Use Option B** - Create the `AlreadySentResponse` class. This:
- ✅ Fixes the cosmetic error
- ✅ Doesn't break functionality
- ✅ Is clean and maintainable
- ✅ Clearly documents intent
- ✅ No risk of double-sending responses

## Implementation Steps

1. Create `AlreadySentResponse` class in `routes.py`
2. Update both message handlers to return `AlreadySentResponse()`
3. Test thoroughly to ensure no breakage
4. Update steering docs to remove "known issue" note

## Testing Checklist

After implementing:
- [ ] SSE connection works
- [ ] Messages are received and processed
- [ ] Tools execute successfully
- [ ] No TypeError in logs
- [ ] No "Response already started" errors
- [ ] Authentication still works correctly
- [ ] Both `/messages` and `/messages/{api_key}` routes work
