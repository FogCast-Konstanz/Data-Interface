import pandas as pd

from config import influx_client, INFLUXDB_ORG

BUCKET = "WeatherForecast"

def get_latest_benchmark():
    query_api = influx_client.query_api()

    # Step 1: Fetch ALL rows in the last day
    raw_query = f'''
    from(bucket: "benchmark_score")
    |> range(start: -1d)
    |> filter(fn: (r) => r["_measurement"] == "forecast_error")
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> keep(columns: ["model", "cloud_cover", "dew_point_2m", "precipitation", 
                        "relative_humidity_2m", "surface_pressure", "temperature_2m", 
                        "lead_time", "forecast_date", "wind_speed_10m"])
    '''

    df_all = query_api.query_data_frame(raw_query)

    if isinstance(df_all, list):
        df_all = pd.concat(df_all)
    df_all = df_all.reset_index(drop=True)

    # Get the latest timestamp
    latest_forecast_datetime = df_all["forecast_date"].max()

    # Filter only rows with that latest timestamp
    df_latest = df_all[df_all["forecast_date"] == latest_forecast_datetime]

    return df_latest
