"""Home Assistant API Client - Modular implementation with mixins."""
from .base_client import BaseClient
from .addon_api import AddonAPI
from .system_api import SystemAPI
from .backup_api import BackupAPI
from .integration_api import IntegrationAPI
from .entity_api import EntityAPI
from .dashboard_api import DashboardAPI
from .automation_api import AutomationAPI
from .diagnostic_api import DiagnosticAPI


class HomeAssistantClient(BaseClient, AddonAPI, SystemAPI, BackupAPI, IntegrationAPI, EntityAPI, DashboardAPI, AutomationAPI, DiagnosticAPI):
    """
    Complete Home Assistant API client combining all API modules.
    
    This client uses multiple inheritance (mixin pattern) to organize
    API methods into logical groups:
    - BaseClient: Authentication and request handling
    - AddonAPI: Addon management (list, install, configure, etc.)
    - SystemAPI: System operations (logs, config files, restart)
    - BackupAPI: Backup management (create, restore, delete)
    - IntegrationAPI: Integration management
    - EntityAPI: Entity and service management
    - DashboardAPI: Dashboard management (create, update, delete)
    - AutomationAPI: Automation management (create, update, trigger)
    - DiagnosticAPI: System diagnostics and health monitoring
    """
    pass


__all__ = ['HomeAssistantClient']
