from datetime import datetime
import pandas as pd
import pytz

from weather_forecast.fog import add_fog_based_on_weather_code
from influx_config import client, INFLUXDB_ORG

BUCKET = "WeatherForecast"

influx_api = client.query_api()

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

def get_forecasts(model_id:str, forecast_datetime:datetime):
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

    query_api = client.query_api()
    tables = query_api.query(query=query, org=INFLUXDB_ORG)

    # Parse query results into a DataFrame
    data = []
    for table in tables:
        for record in table.records:
            data.append(record.values)

    df = pd.DataFrame(data)
    df["forecast_date"] = pd.to_datetime(df["forecast_date"])
    df = add_fog_based_on_weather_code(df)

    return df

def get_current_forecast(model_id:str):
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

    query_api = client.query_api()
    tables = query_api.query(query=query, org=INFLUXDB_ORG)

    # Parse query results into a DataFrame
    data = []
    for table in tables:
        for record in table.records:
            data.append(record.values)

    df = pd.DataFrame(data)
    df["forecast_date"] = pd.to_datetime(df["forecast_date"])
    df = add_fog_based_on_weather_code(df)

    # Filter rows where forecast_date is greater than or equal to now
    utc_now = datetime.now(pytz.utc)
    df = df[df["forecast_date"] >= utc_now]
    return df


def get_archive_water_level(station_id:int, start:datetime, stop:datetime):
    query = f'''
        from(bucket: "{BUCKET}")
            |> range(start: {start.strftime('%Y-%m-%dT%H:%M:%SZ')}, stop: {stop.strftime('%Y-%m-%dT%H:%M:%SZ')})
            |> filter(fn: (r) => r["_measurement"] == "water_level")
            |> filter(fn: (r) => r["_field"] == "value")
            |> filter(fn: (r) => r["station_id"] == "{station_id}")
            |> drop(columns: ["_measurement", "_field", "table", "_start", "_stop", "station_id"])  
    '''
    query_api = client.query_api()
    tables = query_api.query(query=query, org=INFLUXDB_ORG)

    # Parse query results into a DataFrame
    data = []
    for table in tables:
        for record in table.records:
            data.append(record.values)

    df = pd.DataFrame(data)
    df = df.drop(columns=["result", "table"])
    df = df.rename(columns={"_time": "date", "_value": "value"})
    return df