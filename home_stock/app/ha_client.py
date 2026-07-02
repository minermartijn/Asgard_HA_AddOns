"""
Minimal synchronous Home Assistant Core API client.

Runs inside a Home Assistant add-on, where `SUPERVISOR_TOKEN` is injected
automatically and the Core API is reachable at http://supervisor/core/api
(authorized by `homeassistant_api: true` in config.yaml).

Uses only the standard library (urllib) so no extra dependency is required.
Degrades gracefully when not running inside HA (token unset) so the UI still
works in standalone/local-dev mode.
"""
import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


class HAClient:
    def __init__(self):
        self.token = os.getenv("SUPERVISOR_TOKEN") or ""
        self.base = os.getenv("HA_API_URL", "http://supervisor/core/api").rstrip("/")

    @property
    def available(self) -> bool:
        return bool(self.token)

    def _request(self, method: str, path: str, payload=None, params: str = ""):
        if not self.token:
            raise RuntimeError("SUPERVISOR_TOKEN not set — not running inside Home Assistant")
        url = f"{self.base}{path}{params}"
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode()
            return json.loads(body) if body else {}

    def set_state(self, entity_id: str, state, attributes: dict = None):
        return self._request(
            "POST", f"/states/{entity_id}",
            {"state": str(state), "attributes": attributes or {}},
        )

    def call_service(self, domain: str, service: str, data: dict = None):
        return self._request("POST", f"/services/{domain}/{service}", data or {})

    def get_states(self):
        return self._request("GET", "/states")

    def get_todo_entities(self):
        states = self.get_states()
        return [
            {
                "entity_id": s["entity_id"],
                "name": s.get("attributes", {}).get("friendly_name", s["entity_id"]),
            }
            for s in states
            if isinstance(s, dict) and s.get("entity_id", "").startswith("todo.")
        ]

    def get_todo_items(self, entity_id: str):
        """Return the list of item summaries currently on a to-do entity.

        Uses the todo.get_items service with a response. Returns None if the
        call is unsupported so callers can fall back to add-without-dedupe.
        """
        try:
            resp = self._request(
                "POST", "/services/todo/get_items",
                {"entity_id": entity_id}, params="?return_response",
            )
            service_response = resp.get("service_response", {}) if isinstance(resp, dict) else {}
            entity = service_response.get(entity_id, {})
            return [i.get("summary") for i in entity.get("items", []) if i.get("summary")]
        except Exception as e:  # noqa: BLE001
            logger.warning("todo.get_items failed (%s); skipping dedupe", e)
            return None


ha = HAClient()
