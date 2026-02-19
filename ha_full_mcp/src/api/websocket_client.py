"""WebSocket client for Home Assistant API."""
import asyncio
import logging
import json
from typing import Any, Optional
import aiohttp

logger = logging.getLogger(__name__)


class WebSocketClient:
    """WebSocket client for Home Assistant API operations."""
    
    def __init__(self, ha_url: str, access_token: str):
        """Initialize WebSocket client.
        
        Args:
            ha_url: Home Assistant URL (e.g., http://homeassistant:8123)
            access_token: Long-lived access token
        """
        self.ha_url = ha_url.replace('http://', 'ws://').replace('https://', 'wss://')
        self.ws_url = f"{self.ha_url}/api/websocket"
        self.access_token = access_token
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._message_id = 1
        self._pending_requests: dict[int, asyncio.Future] = {}
        self._receive_task: Optional[asyncio.Task] = None
        self._authenticated = False
    
    async def connect(self) -> None:
        """Establish WebSocket connection and authenticate."""
        if self._ws and not self._ws.closed:
            return
        
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        try:
            logger.info(f"Connecting to WebSocket: {self.ws_url}")
            self._ws = await self._session.ws_connect(self.ws_url)
            
            # Wait for auth_required message
            msg = await self._ws.receive_json()
            if msg.get('type') != 'auth_required':
                raise ConnectionError(f"Expected auth_required, got: {msg.get('type')}")
            
            # Send authentication
            await self._ws.send_json({
                'type': 'auth',
                'access_token': self.access_token
            })
            
            # Wait for auth response
            auth_msg = await self._ws.receive_json()
            if auth_msg.get('type') == 'auth_ok':
                self._authenticated = True
                logger.info("WebSocket authenticated successfully")
                
                # Start receiving messages
                self._receive_task = asyncio.create_task(self._receive_messages())
            else:
                raise ConnectionError(f"Authentication failed: {auth_msg.get('message', 'Unknown error')}")
        
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            await self.close()
            raise
    
    async def _receive_messages(self) -> None:
        """Receive and process WebSocket messages."""
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    msg_id = data.get('id')
                    
                    if msg_id and msg_id in self._pending_requests:
                        future = self._pending_requests.pop(msg_id)
                        if data.get('success', True):
                            future.set_result(data.get('result'))
                        else:
                            error = data.get('error', {})
                            future.set_exception(
                                Exception(f"WebSocket error: {error.get('message', 'Unknown error')}")
                            )
                
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self._ws.exception()}")
                    break
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
    
    async def send_command(self, command_type: str, **kwargs) -> Any:
        """Send a command and wait for response.
        
        Args:
            command_type: Command type (e.g., 'lovelace/dashboards/list')
            **kwargs: Additional command parameters
        
        Returns:
            Command result
        """
        if not self._authenticated:
            await self.connect()
        
        msg_id = self._message_id
        self._message_id += 1
        
        message = {
            'id': msg_id,
            'type': command_type,
            **kwargs
        }
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[msg_id] = future
        
        try:
            await self._ws.send_json(message)
            logger.debug(f"Sent WebSocket command: {command_type} (id={msg_id})")
            
            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        
        except asyncio.TimeoutError:
            self._pending_requests.pop(msg_id, None)
            raise TimeoutError(f"WebSocket command timed out: {command_type}")
        except Exception as e:
            self._pending_requests.pop(msg_id, None)
            raise
    
    async def close(self) -> None:
        """Close WebSocket connection and cleanup."""
        self._authenticated = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None
        
        if self._ws and not self._ws.closed:
            await self._ws.close()
            self._ws = None
        
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        
        # Cancel all pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()
        
        logger.info("WebSocket connection closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
