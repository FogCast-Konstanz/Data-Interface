from typing import Optional
from datetime import datetime
import pandas as pd
import pytz

from services.fog import add_fog
from config import influx_client, INFLUXDB_ORG

BUCKET = "WeatherForecast"
WEATHER_BUCKET = "WeatherData"
CEILOMETER_MEASUREMENT = "ceilometer"
UV_MEASUREMENT = "uv"

influx_api = influx_client.query_api()


def _query_tag_values(tag_key: str):
    query = f'''
        import "influxdata/influxdb/schema"
        schema.measurementTagValues(
            bucket: "WeatherForecast",
            measurement: "forecast",
            tag: "{tag_key}",
        )
        '''
    result = influx_api.query(query)
    tag_keys = []
    for table in result:
        for record in table.records:
            tag_keys.append(record.values["_value"])
    return tag_keys


def get_models():
    models = _query_tag_values("model")
    return models


def get_forecasts(model_id: str, forecast_datetime: datetime):
    query = f'''
        import "date"
        from(bucket: "{BUCKET}")
        |> range(start: date.sub(from:{forecast_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')}, d:14d), stop: {forecast_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')})
        |> filter(fn: (r) => r["_measurement"] == "forecast")
        |> filter(fn: (r) => r["forecast_date"] == "{forecast_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        |> filter(fn: (r) => r["model"] == "{model_id}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"])
    '''

    query_api = influx_client.query_api()
    tables = query_api.query(query=query, org=INFLUXDB_ORG)

    # Parse query results into a DataFrame
    data = []
    for table in tables:
        for record in table.records:
            data.append(record.values)

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    if df.empty:
        # Return empty DataFrame with expected structure
        return df

    df["forecast_date"] = pd.to_datetime(df["forecast_date"])
    df = add_fog(df)

    return df


def get_current_forecast(model_id: str):
    query = f'''
        import "date"
        from(bucket: "{BUCKET}")
        |> range(start: -2h)
        |> filter(fn: (r) => r["_measurement"] == "forecast")
        |> filter(fn: (r) => r["model"] == "{model_id}")
        |> last()
        |> pivot(rowKey:["forecast_date"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["forecast_date"])
        |> drop(columns: ["_start", "_stop", "_time", "_measurement"])
    '''

    query_api = influx_client.query_api()
    tables = query_api.query(query=query, org=INFLUXDB_ORG)

    # Parse query results into a DataFrame
    data = []
    for table in tables:
        for record in table.records:
            data.append(record.values)

    if len(data) == 0:
        raise ValueError("No data for requested forecast date")

    df = pd.DataFrame(data)
    df["forecast_date"] = pd.to_datetime(df["forecast_date"])
    df = add_fog(df)

    # Filter rows where forecast_date is greater than or equal to now
    utc_now = datetime.now(pytz.utc)
    df = df[df["forecast_date"] >= utc_now]
    return df


def _query_water_level(station_id: int, start: datetime, stop: datetime, aggregate_window: Optional[str] = None):
    base_query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: {start.strftime('%Y-%m-%dT%H:%M:%SZ')}, stop: {stop.strftime('%Y-%m-%dT%H:%M:%SZ')})
      |> filter(fn: (r) => r["_measurement"] == "water_level")
      |> filter(fn: (r) => r["_field"] == "value")
      |> filter(fn: (r) => r["station_id"] == "{station_id}")
  '''
    if aggregate_window:
        base_query += f'''
      |> aggregateWindow(every: {aggregate_window}, fn: mean, createEmpty: false)
    '''
    base_query += '''
    |> drop(columns: ["_measurement", "_field", "table", "_start", "_stop", "station_id"])
  '''

    query_api = influx_client.query_api()
    tables = query_api.query(query=base_query, org=INFLUXDB_ORG)

    # Parse query results into a DataFrame
    data = []
    for table in tables:
        for record in table.records:
            data.append(record.values)

    df = pd.DataFrame(data)

    if not df.empty:
        columns_to_drop = [col for col in ["result", "table"] if col in df.columns]
        if columns_to_drop:
            df = df.drop(columns=columns_to_drop)
        df = df.rename(columns={"_time": "date", "_value": "value"})

    return df


def get_archive_water_level(station_id: int, start: datetime, stop: datetime):
    df = _query_water_level(station_id, start, stop)
    return df


def get_daily_averaged_water_level(station_id: int, start: datetime, stop: datetime):
    df = _query_water_level(station_id, start, stop, aggregate_window="1d")
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.to_period("D").dt.to_timestamp()
    return df


def get_weekly_averaged_water_level(station_id: int, start: datetime, stop: datetime):
    df = _query_water_level(station_id, start, stop, aggregate_window="1w")
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.to_period("W").dt.to_timestamp()
    return df


def get_monthly_averaged_water_level(station_id: int, start: datetime, stop: datetime):
    df = _query_water_level(station_id, start, stop, aggregate_window="1mo")
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()
    return df


def get_yearly_averaged_water_level(station_id: int, start: datetime, stop: datetime):
    df = _query_water_level(station_id, start, stop, aggregate_window="1y")
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.to_period("Y").dt.to_timestamp()
    return df


def get_ceilometer_history(start: datetime, stop: datetime):
    query = f'''
    from(bucket: "{WEATHER_BUCKET}")
      |> range(start: {start.strftime('%Y-%m-%dT%H:%M:%SZ')}, stop: {stop.strftime('%Y-%m-%dT%H:%M:%SZ')})
      |> filter(fn: (r) => r["_measurement"] == "{CEILOMETER_MEASUREMENT}")
      |> sort(columns: ["_time"])
      |> rename(columns: {{_time: "date", _value: "value"}})
    '''

    query_api = influx_client.query_api()
    tables = query_api.query(query=query, org=INFLUXDB_ORG)

    data = []
    for table in tables:
        for record in table.records:
            data.append(record.values)

    df = pd.DataFrame(data)
    if not df.empty:
        columns_to_drop = [col for col in ["result", "table", "_measurement", "_field", "_start", "_stop"] if col in df.columns]
        if columns_to_drop:
            df = df.drop(columns=columns_to_drop)
    return df


def get_uv_history(start: datetime, stop: datetime):
    query = f'''
    from(bucket: "{WEATHER_BUCKET}")
      |> range(start: {start.strftime('%Y-%m-%dT%H:%M:%SZ')}, stop: {stop.strftime('%Y-%m-%dT%H:%M:%SZ')})
      |> filter(fn: (r) => r["_measurement"] == "{UV_MEASUREMENT}")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
      |> rename(columns: {{_time: "date"}})
    '''

    tables = influx_api.query(query)
    data = [record.values for table in tables for record in table.records]
    df = pd.DataFrame(data)
    if not df.empty:
        columns_to_drop = [
            col for col in ["result", "table", "_measurement", "_start", "_stop"]
            if col in df.columns
        ]
        if columns_to_drop:
            df = df.drop(columns=columns_to_drop)
    return df
