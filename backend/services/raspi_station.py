from datetime import datetime
import influxdb_client
import influxdb_client.client
import influxdb_client.client.write_api
from influxdb_client import Point
import pandas as pd
from config import influx_client, INFLUXDB_ORG

BUCKET = "WeatherData"


def save_station_data_to_influxdb(data):
    """
    Save station data to InfluxDB.
    """
    # Check data format
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")

    required_fields = ["timestamp", "temperature",
                       "water_temperature", "humidity"]
    if not all(field in data for field in required_fields):
        raise ValueError(
            f"Data must contain the following fields: {', '.join(required_fields)}")

    # Check types
    if isinstance(data["timestamp"], str):
        try:
            data["timestamp"] = datetime.strptime(
                data["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            raise ValueError(
                "Timestamp must be in the format YYYY-MM-DDTHH:MM:SSZ")
    else:
        raise ValueError(
            "Timestamp must be a string in the format YYYY-MM-DDTHH:MM:SSZ")

    if not isinstance(data["temperature"], (int, float)):
        raise ValueError("Temperature must be an integer or float")
    if not isinstance(data["water_temperature"], (int, float)):
        raise ValueError("Water temperature must be an integer or float")
    if not isinstance(data["humidity"], (int, float)):
        raise ValueError("Humidity must be an integer or float")

    write_api = influx_client.write_api(
        write_options=influxdb_client.client.write_api.SYNCHRONOUS)

    # Create a point
    point = Point("weather_station") \
        .field("temperature", float(data["temperature"])) \
        .field("water_temperature", float(data["water_temperature"])) \
        .field("humidity", float(data["humidity"])) \
        .time(data["timestamp"].isoformat())

    # Write the point to InfluxDB
    write_api.write(bucket=BUCKET, org=INFLUXDB_ORG, record=point)
    write_api.close()


def get_station_data_from_influxdb(start: datetime, stop: datetime):
    """
    Retrieve station data from InfluxDB within a specified time range.
    """

    if start >= stop:
        raise ValueError("Start time must be before stop time")

    query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: {start.strftime('%Y-%m-%dT%H:%M:%SZ')}, stop: {stop.strftime('%Y-%m-%dT%H:%M:%SZ')})
      |> filter(fn: (r) => r["_measurement"] == "weather_station")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
      |> drop(columns: ["_start", "_stop", "_measurement"])
      |> rename(columns: {{_time: "time"}})
    '''

    query_api = influx_client.query_api()
    result = query_api.query(query=query, org=INFLUXDB_ORG)

    data = []
    for table in result:
        for record in table.records:
            data.append(
                record.values
            )

    df = pd.DataFrame(data)
    df = df.drop(columns=["result", "table"])
    return df.to_dict(orient='records')
