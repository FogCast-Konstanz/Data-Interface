import os
import influxdb_client

INFLUXDB_ORG = "FogCast"
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_URL = os.getenv("INFLUXDB_URL")

if not INFLUXDB_TOKEN:
    raise ValueError("INFLUXDB_TOKEN environment variable is not set")
if not INFLUXDB_URL:
    raise ValueError("INFLUXDB_URL environment variable is not set")

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable is not set")

influx_client = influxdb_client.InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG,
    timeout=120_000,
    verify_ssl=False,
    http_client_kwargs={"timeout": 300}
)
