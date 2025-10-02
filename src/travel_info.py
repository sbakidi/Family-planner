import os
import requests

GOOGLE_MAPS_ENDPOINT = "https://maps.googleapis.com/maps/api/directions/json"


def get_route_info(origin: str, destination: str, api_key: str | None = None) -> dict:
    """Return travel duration in minutes and a traffic warning."""
    api_key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"duration_minutes": None, "traffic_warning": False}

    params = {
        "origin": origin,
        "destination": destination,
        "departure_time": "now",
        "key": api_key,
    }

    try:
        resp = requests.get(GOOGLE_MAPS_ENDPOINT, params=params, timeout=5)
        data = resp.json()
        leg = data["routes"][0]["legs"][0]
        duration = leg.get("duration", {}).get("value")
        duration_in_traffic = leg.get("duration_in_traffic", {}).get("value", duration)
        mins = duration // 60 if duration else None
        mins_traffic = duration_in_traffic // 60 if duration_in_traffic else mins
        traffic_warning = False
        if mins and mins_traffic and mins_traffic - mins > 10:
            traffic_warning = True
        return {
            "duration_minutes": mins_traffic,
            "traffic_warning": traffic_warning,
        }
    except Exception as e:
        print(f"Error fetching route info: {e}")
        return {"duration_minutes": None, "traffic_warning": False}
