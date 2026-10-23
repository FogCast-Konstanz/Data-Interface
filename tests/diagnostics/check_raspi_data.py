#!/usr/bin/env python3
"""Check recent Raspberry-Pi measurements in InfluxDB."""
from datetime import datetime, timedelta, timezone
import os
import sys

try:
    from influxdb_client import InfluxDBClient
except ImportError:
    print("Installiere zuerst influxdb-client.", file=sys.stderr)
    raise SystemExit(1)

url = os.getenv("INFLUXDB_URL")
token = os.getenv("INFLUXDB_TOKEN")
org = os.getenv("INFLUXDB_ORG", "FogCast")
if not url or not token:
    raise SystemExit("INFLUXDB_URL und INFLUXDB_TOKEN müssen gesetzt sein.")

query = '''
from(bucket: "WeatherData")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_measurement"] == "weather_station")
  |> last()
'''
with InfluxDBClient(url=url, token=token, org=org, verify_ssl=False) as client:
    records = [record for table in client.query_api().query(query) for record in table.records]
    if not records:
        print("Keine Wetterstationsdaten in den letzten sieben Tagen gefunden.")
        raise SystemExit(1)
    latest = max(record.get_time() for record in records)
    age = datetime.now(timezone.utc) - latest.astimezone(timezone.utc)
    print(f"Letzte Messung: {latest.isoformat()} ({age})")
