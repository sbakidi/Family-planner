import os
from datetime import date
from typing import Optional, Dict, Any

import requests


class HealthDevice:
    """Simple client for wearable device APIs."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"HealthDevice API request failed: {e}")
            return None

    def fetch_steps(self, start: date, end: date):
        params = {"start": start.isoformat(), "end": end.isoformat()}
        return self._get("steps", params)

    def fetch_sleep(self, start: date, end: date):
        params = {"start": start.isoformat(), "end": end.isoformat()}
        return self._get("sleep", params)


def summarize_health(steps_data: Any, sleep_data: Any) -> Dict[str, Any]:
    """Return basic totals from fetched data."""
    summary = {"total_steps": 0, "total_sleep_hours": 0}
    if steps_data and isinstance(steps_data, list):
        summary["total_steps"] = sum(d.get("steps", 0) for d in steps_data)
    if sleep_data and isinstance(sleep_data, list):
        summary["total_sleep_hours"] = sum(d.get("hours", 0) for d in sleep_data)
    return summary


def device_from_env() -> Optional[HealthDevice]:
    """Create HealthDevice from environment variables if available."""
    base = os.environ.get("HEALTH_API_URL")
    token = os.environ.get("HEALTH_API_TOKEN")
    if not base or not token:
        return None
    return HealthDevice(base, token)
