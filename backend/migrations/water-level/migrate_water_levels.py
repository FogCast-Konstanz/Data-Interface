"""
This script migrates water level data from a CSV file to an InfluxDB database.
"""

from datetime import datetime
import os
import influxdb_client
import pandas as pd
import pytz
from datetime import datetime
import pytz

from dotenv import load_dotenv
import itertools
import time

load_dotenv("./.env")

INFLUXDB_BUCKET = "WeatherForecast"
INFLUXDB_ORG = "FogCast"
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_URL = os.getenv("INFLUXDB_URL")

client = influxdb_client.InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)

df_rhein = pd.read_csv("backend/migrations/water-level/see_rhein_pegel.csv", sep=",")
df_bodensee = pd.read_csv("backend/migrations/water-level/bodensee_pegel.csv", sep=",")

def to_RFC3339(date:str) -> str:
    naive_dt = datetime.strptime(date, "%Y-%m-%d %H:%M")
    berlin_tz = pytz.timezone("Europe/Berlin")
    localized_dt = berlin_tz.localize(naive_dt)
    utc_dt = localized_dt.astimezone(pytz.UTC)
    rfc3339_utc = utc_dt.isoformat().replace("+00:00", "Z")
    return rfc3339_utc

# get data in a format that can be dirctly written to influxdb
def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    df["RFC3339"] = df["Datum / Uhrzeit"].apply(to_RFC3339)
    df = df.drop(columns=["Gewässer", "Parameter", "Datum / Uhrzeit", "Produkt", "Zeitbezug"])
    df = df.rename(columns={
        "Messstellennummer": "station_id",
        "Stationsname": "station_name",
        "Wert": "value",
        "Einheit": "unit",
        "RFC3339": "date"
    })    
    df["value"] = pd.to_numeric(df["value"], errors="coerce")  
    return df
    
df_bodensee_normalized = normalize_data(df_bodensee.copy())
df_rhein_normalized = normalize_data(df_rhein.copy())

print("normalized bodensee", df_bodensee_normalized.head(5), df_bodensee_normalized.columns)
print("\nnormalized rhein", df_bodensee_normalized.head(5), df_bodensee_normalized.columns)

print("\normalized bodensee shape", df_bodensee_normalized.shape)
print("normalized rhein shape", df_rhein_normalized.shape)

# start with writing data to influxdb
write_api = client.write_api(write_options=influxdb_client.client.write_api.SYNCHRONOUS)

# convert dataframe to influxdb points; use bacthes to speed up
def write_data_to_influxdb(df: pd.DataFrame, batch_size: int = 5000):
    total_rows = len(df)
    batch = []
    progress_bar = itertools.cycle(["|", "/", "-", "\\"])

    for index, row in df.iterrows():
        point = influxdb_client.Point("water_level") \
            .field("value", row["value"]) \
            .tag("unit", row["unit"]) \
            .tag("station_id", row["station_id"]) \
            .tag("station_name", row["station_name"]) \
            .time(datetime.strptime(row["date"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC))
        batch.append(point)

        if len(batch) == batch_size:
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=batch)
            batch = []

        if index % 1000 == 0 or index == total_rows - 1:
            print(f"\rWriting {index + 1}/{total_rows} {next(progress_bar)}", end="")

    if batch:
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=batch)

    print("\nMigration completed.")
    
write_data_to_influxdb(df_bodensee_normalized)
write_data_to_influxdb(df_rhein_normalized)

# Close the client
client.close()

