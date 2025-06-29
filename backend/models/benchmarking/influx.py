import pandas as pd

from config import influx_client, INFLUXDB_ORG

BUCKET = "WeatherForecast"

def query_benchmark_scores(time_range: str):
    query = f'''from(bucket: "WeatherForecast") 
        |> range(start: -{time_range})
        |> filter(fn: (r) => r["_measurement"] == "error_score")
        |> filter(fn: (r) => r["_field"] == "error")
        |> keep(columns: ["_time", "_model", "feature", "_value", "forecast_horizon"])
        '''
    query_api = influx_client.query_api()
    tables = query_api.query(query=query, org=INFLUXDB_ORG)

    data = []
    for table in tables:
        for record in table.records:
            data.append(record.values)

    df = pd.DataFrame(data)    
    return df