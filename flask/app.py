import os
import sys
from datetime import datetime

from flask import Flask, jsonify, request
import influxdb_client
import pandas as pd
app = Flask(__name__)

INFLUXDB_BUCKET = "WeatherForecast"
INFLUXDB_ORG = "FogCast"
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_URL = os.getenv("INFLUXDB_URL")

client = influxdb_client.InfluxDBClient(
    url= INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)

influx_api = client.query_api()
app = Flask(__name__)

def query_tag_values(tag_key: str):
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

@app.route("/models")
def models():
    tag_values = query_tag_values("model")
    return jsonify(tag_values)


@app.route('/forecasts', methods=['GET'])
def forecasts():
    forecast_datetime = request.args.get('datetime')
    model_id = request.args.get('model_id')

    if not forecast_datetime or not model_id:
        return jsonify({"error": "datetime and model_id are required parameters"}), 400

    try:
        forecast_datetime = datetime.strptime(forecast_datetime, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        return jsonify({"error": "datetime must be in the format YYYY-MM-DDTHH:MM:SSZ"}), 400

    try:
        query = f'''
        import "date"
        from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: date.sub(from:{forecast_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')}, d:8d), stop: {forecast_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')})
        |> filter(fn: (r) => r["_measurement"] == "forecast")
        |> filter(fn: (r) => r["forecast_date"] == "{forecast_datetime.strftime('%Y-%m-%d %H:%M:%S+00:00')}")
        |> filter(fn: (r) => r["model"] == "{model_id}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        query_api = client.query_api()
        tables = query_api.query(query=query, org=INFLUXDB_ORG)

        # Parse query results into a DataFrame
        data = []
        for table in tables:
            for record in table.records:
                data.append(record.values)

        df = pd.DataFrame(data)
        return jsonify(df.to_dict(orient='records'))

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/flask-health-check')
def flask_health_check():
	return "success"

if __name__ == '__main__':
    app.run(debug=True)