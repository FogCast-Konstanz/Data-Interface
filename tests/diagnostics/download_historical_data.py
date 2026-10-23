#!/usr/bin/env python3
"""Download historical weather-station data as JSON and CSV."""
import csv
import json
import os
from pathlib import Path
import requests

api = os.getenv("PRODUCTION_API", "https://fogcast.in.htwg-konstanz.de/api").rstrip("/")
start = os.getenv("HISTORY_START", "2025-05-01T00:00:00Z")
stop = os.getenv("HISTORY_STOP", "2025-10-01T00:00:00Z")
data = requests.get(
    f"{api}/weatherstation", params={"start": start, "stop": stop},
    timeout=60,
).json()
Path("raspi_weatherstation_export.json").write_text(
    json.dumps(data, indent=2), encoding="utf-8"
)
fields = sorted({key for row in data for key in row})
with Path("raspi_weatherstation_export.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(data)
print(f"{len(data)} Datenpunkte exportiert.")
