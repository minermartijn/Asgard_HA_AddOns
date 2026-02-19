"""Diagnostic API - combines core and advanced diagnostic methods."""
from .diagnostic_api_core import DiagnosticCoreAPI
from .diagnostic_api_advanced import DiagnosticAdvancedAPI


class DiagnosticAPI(DiagnosticCoreAPI, DiagnosticAdvancedAPI):
    """
    Complete diagnostic API combining core and advanced methods.
    
    Core methods (DiagnosticCoreAPI):
    - get_system_health: System resources and health
    - get_error_log_summary: Error analysis
    - list_unavailable_entities: Broken entities
    - get_recorder_stats: Database statistics
    - check_network_connectivity: Network status
    
    Advanced methods (DiagnosticAdvancedAPI):
    - list_custom_components: Custom integrations
    - get_startup_time_breakdown: Component load times
    - validate_all_automations: Automation validation
    - list_deprecated_features: Deprecation warnings
    - get_integration_diagnostics: Integration health
    """
    pass
