"""Dashboard management API methods using WebSocket."""
import logging
from typing import Any
from .websocket_client import WebSocketClient

logger = logging.getLogger(__name__)


class DashboardAPI:
    """Mixin for dashboard management API methods."""
    
    def _get_ws_client(self) -> WebSocketClient:
        """Get or create WebSocket client."""
        if not hasattr(self, '_ws_client') or self._ws_client is None:
            self._ws_client = WebSocketClient(self.ha_url, self.ha_token)
        return self._ws_client
    
    async def list_dashboards(self) -> list[dict[str, Any]]:
        """List all Lovelace dashboards using WebSocket.
        
        Returns:
            List of dashboard configurations
        """
        try:
            ws_client = self._get_ws_client()
            result = await ws_client.send_command('lovelace/dashboards/list')
            
            logger.info(f"Listed {len(result) if result else 0} dashboards")
            return result if isinstance(result, list) else []
        
        except Exception as e:
            logger.error(f"Failed to list dashboards: {e}")
            # Fallback: return empty list
            return []
    
    async def get_dashboard_config(self, dashboard_id: str = None) -> dict[str, Any]:
        """Get dashboard configuration using WebSocket.
        
        Args:
            dashboard_id: Dashboard ID (None or 'lovelace' for default dashboard)
        
        Returns:
            Dashboard configuration
        """
        try:
            ws_client = self._get_ws_client()
            
            # Use url_path for specific dashboard, None for default
            if dashboard_id and dashboard_id != "lovelace":
                result = await ws_client.send_command(
                    'lovelace/config',
                    url_path=dashboard_id
                )
            else:
                result = await ws_client.send_command('lovelace/config')
            
            logger.info(f"Retrieved dashboard config: {dashboard_id or 'default'}")
            return result if isinstance(result, dict) else {}
        
        except Exception as e:
            logger.error(f"Failed to get dashboard config: {e}")
            return {}
    
    async def create_dashboard(self, dashboard_id: str, title: str, 
                              icon: str = "mdi:view-dashboard", 
                              show_in_sidebar: bool = True,
                              require_admin: bool = False) -> dict[str, Any]:
        """Create a new dashboard using WebSocket.
        
        Args:
            dashboard_id: Unique dashboard ID (URL path)
            title: Dashboard title
            icon: Dashboard icon (default: mdi:view-dashboard)
            show_in_sidebar: Show in sidebar (default: True)
            require_admin: Require admin access (default: False)
        
        Returns:
            Created dashboard info
        """
        try:
            ws_client = self._get_ws_client()
            
            result = await ws_client.send_command(
                'lovelace/dashboards/create',
                url_path=dashboard_id,
                title=title,
                icon=icon,
                show_in_sidebar=show_in_sidebar,
                require_admin=require_admin
            )
            
            logger.info(f"Created dashboard: {dashboard_id}")
            return result if isinstance(result, dict) else {}
        
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            raise
    
    async def update_dashboard_config(self, dashboard_id: str, config: dict[str, Any]) -> dict[str, Any]:
        """Update dashboard configuration using WebSocket.
        
        Args:
            dashboard_id: Dashboard ID (None or 'lovelace' for default)
            config: Dashboard configuration (views, etc.)
        
        Returns:
            Result of the operation
        """
        try:
            ws_client = self._get_ws_client()
            
            # Use url_path for specific dashboard
            if dashboard_id and dashboard_id != "lovelace":
                result = await ws_client.send_command(
                    'lovelace/config/save',
                    config=config,
                    url_path=dashboard_id
                )
            else:
                result = await ws_client.send_command(
                    'lovelace/config/save',
                    config=config
                )
            
            logger.info(f"Updated dashboard config: {dashboard_id or 'default'}")
            return result if isinstance(result, dict) else {}
        
        except Exception as e:
            logger.error(f"Failed to update dashboard config: {e}")
            raise
    
    async def update_dashboard_metadata(self, dashboard_id: str, 
                                       title: str = None,
                                       icon: str = None,
                                       show_in_sidebar: bool = None,
                                       require_admin: bool = None) -> dict[str, Any]:
        """Update dashboard metadata using WebSocket.
        
        Args:
            dashboard_id: Dashboard ID
            title: New title (optional)
            icon: New icon (optional)
            show_in_sidebar: Show in sidebar (optional)
            require_admin: Require admin (optional)
        
        Returns:
            Updated dashboard info
        """
        try:
            ws_client = self._get_ws_client()
            
            updates = {'url_path': dashboard_id}
            if title is not None:
                updates['title'] = title
            if icon is not None:
                updates['icon'] = icon
            if show_in_sidebar is not None:
                updates['show_in_sidebar'] = show_in_sidebar
            if require_admin is not None:
                updates['require_admin'] = require_admin
            
            result = await ws_client.send_command(
                'lovelace/dashboards/update',
                **updates
            )
            
            logger.info(f"Updated dashboard metadata: {dashboard_id}")
            return result if isinstance(result, dict) else {}
        
        except Exception as e:
            logger.error(f"Failed to update dashboard metadata: {e}")
            raise
    
    async def delete_dashboard(self, dashboard_id: str) -> dict[str, Any]:
        """Delete a dashboard using WebSocket.
        
        Args:
            dashboard_id: Dashboard ID to delete
        
        Returns:
            Result of the operation
        """
        try:
            ws_client = self._get_ws_client()
            
            result = await ws_client.send_command(
                'lovelace/dashboards/delete',
                url_path=dashboard_id
            )
            
            logger.info(f"Deleted dashboard: {dashboard_id}")
            return result if isinstance(result, dict) else {}
        
        except Exception as e:
            logger.error(f"Failed to delete dashboard: {e}")
            raise
    
    async def close_websocket(self) -> None:
        """Close WebSocket connection if open."""
        if hasattr(self, '_ws_client') and self._ws_client:
            await self._ws_client.close()
            self._ws_client = None
