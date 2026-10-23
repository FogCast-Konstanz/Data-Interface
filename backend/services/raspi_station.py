from datetime import datetime
import influxdb_client
import influxdb_client.client
import influxdb_client.client.write_api
from influxdb_client import Point
import pandas as pd
from config import influx_client, INFLUXDB_ORG

BUCKET = "WeatherData"
UV_MEASUREMENT = "uv"


def _get_numeric_value(data: dict, *keys):
    for key in keys:
        if key in data and data[key] is not None:
            value = data[key]
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    pass
    return None


def save_station_data_to_influxdb(data):
    """
    Save station data to InfluxDB.
    """
    # Check data format
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")

    required_fields = ["timestamp", "temperature", "humidity"]
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

    temperature = _get_numeric_value(data, "temperature")
    water_temperature = _get_numeric_value(data, "water_temperature", "watertemp", "water_temp")
    humidity = _get_numeric_value(data, "humidity")
    ceilometer = _get_numeric_value(data, "ceilometer", "cloud_base", "cloudheight", "cloud_height")
    uv_index = _get_numeric_value(data, "uv_index", "uv", "uvi")
    uv_irradiance = _get_numeric_value(
        data, "uv_irradiance", "uv_radiation", "uv_power_density"
    )

    if temperature is None:
        raise ValueError("Temperature must be an integer or float")
    if humidity is None:
        raise ValueError("Humidity must be an integer or float")

    write_api = influx_client.write_api(
        write_options=influxdb_client.client.write_api.SYNCHRONOUS)

    # Create a point
    point = Point("weather_station") \
        .field("temperature", float(temperature)) \
        .field("humidity", float(humidity)) \
        .time(data["timestamp"].isoformat())

    if water_temperature is not None:
        point.field("water_temperature", float(water_temperature))
    if ceilometer is not None:
        point.field("ceilometer", float(ceilometer))
    if uv_index is not None:
        point.field("uv_index", float(uv_index))
    if uv_irradiance is not None:
        point.field("uv_irradiance", float(uv_irradiance))

    # Write the point to InfluxDB
    write_api.write(bucket=BUCKET, org=INFLUXDB_ORG, record=point)
    if uv_index is not None or uv_irradiance is not None:
        uv_point = Point(UV_MEASUREMENT).time(data["timestamp"].isoformat())
        if uv_index is not None:
            uv_point.field("uv_index", float(uv_index))
        if uv_irradiance is not None:
            uv_point.field("uv_irradiance", float(uv_irradiance))
        write_api.write(bucket=BUCKET, org=INFLUXDB_ORG, record=uv_point)
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

    # Only drop columns if they exist and DataFrame is not empty
    if not df.empty:
        columns_to_drop = [col for col in ["result", "table"] if col in df.columns]
        if columns_to_drop:
            df = df.drop(columns=columns_to_drop)

    return df.to_dict(orient='records')