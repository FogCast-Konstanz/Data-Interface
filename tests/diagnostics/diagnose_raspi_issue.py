#!/usr/bin/env python3
"""Check production API availability and the age of its latest measurement."""
from datetime import datetime, timedelta, timezone
import os
import requests

api = os.getenv("PRODUCTION_API", "https://fogcast.in.htwg-konstanz.de/api").rstrip("/")
response = requests.get(f"{api}/health-check", timeout=15)
response.raise_for_status()
print("Produktionsserver:", response.text)
stop = datetime.now(timezone.utc)
start = stop - timedelta(days=365)
data = requests.get(
    f"{api}/weatherstation",
    params={"start": start.isoformat(), "stop": stop.isoformat()},
    timeout=30,
).json()
timestamps = [
    datetime.fromisoformat(item["time"].replace("Z", "+00:00"))
    for item in data if isinstance(item, dict) and item.get("time")
]
if timestamps:
    latest = max(timestamps)
    print("Letzte Produktionsmessung:", latest.isoformat())
else:
    print("Keine Produktionsmessung gefunden.")
