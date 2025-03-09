import logging
import os
from datetime import datetime

import influxdb_client
import pandas as pd
import pytz
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from actual.DWD import DWD
from actual.PegelOnline import PegelOnline

app = Flask(__name__)
CORS(app)

INFLUXDB_BUCKET = "WeatherForecast"
INFLUXDB_ORG = "FogCast"
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_URL = os.getenv("INFLUXDB_URL")

client = influxdb_client.InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)

influx_api = client.query_api()

dwd = DWD()
pegel_online = PegelOnline()

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
    try:
        tag_values = query_tag_values("model")
        return jsonify(tag_values)
    except Exception as e:
        logging.exception("Error occurred while querying InfluxDB for tag values:", exc_info=e)
        return jsonify({"error": str(e)}), 500


@app.route('/forecasts', methods=['GET'])
def forecasts():
    forecast_datetime = request.args.get('datetime')
    model_id = request.args.get('model_id')

    if not forecast_datetime or not model_id:
        return jsonify({"error": "datetime and model_id are required parameters"}), 400

    try:
        forecast_datetime = datetime.strptime(forecast_datetime, '%Y-%m-%dT%H:%M:%SZ')
        forecast_datetime = forecast_datetime.replace(tzinfo=pytz.utc)

    except ValueError:
        return jsonify({"error": "datetime must be in the format YYYY-MM-DDTHH:MM:SSZ"}), 400

    try:
        query = f'''
        import "date"
        from(bucket: "{INFLUXDB_BUCKET}")
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
        return jsonify(df.to_dict(orient='records'))

    except Exception as e:
        logging.exception("Error occurred while querying InfluxDB for forecasts:", exc_info=e)
        return jsonify({"error": str(e)}), 500


@app.route('/actual/live-data', methods=['GET'])
def actual_live_data():
    try:
        dwd_measurements = dwd.get_real_time_data()
        pegel_online_measurements = pegel_online.get_water_level_measurements(PegelOnline.Period.last_24_hours)
        pegel_online_measurements = sorted(pegel_online_measurements, key=lambda x: x.date, reverse=True)[0]
        result = [entry.to_json() for entry in dwd_measurements + [pegel_online_measurements]]
        return jsonify(result)
    except Exception as e:
        logging.exception("Error occurred while fetching actual data:", exc_info=e)
        return jsonify({"error": str(e)}), 500


@app.route('/actual/temperature-history', methods=['GET'])
def actual_temperature_history():
    start = request.args.get('start')
    stop = request.args.get('stop')
    frequency = request.args.get('frequency')

    if start and stop and frequency:
        try:
            start = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
            start = start.replace(tzinfo=pytz.utc)
        except ValueError:
            return jsonify({"error": "start must be in the format YYYY-MM-DD HH:MM:SS"}), 400

        try:
            stop = datetime.strptime(stop, '%Y-%m-%d %H:%M:%S')
            stop = stop.replace(tzinfo=pytz.utc)
        except ValueError:
            return jsonify({"error": "stop must be in the format YYYY-MM-DD HH:MM:SS"}), 400

        if frequency == 'daily':
            frequency = DWD.Frequency.daily
        elif frequency == 'hourly':
            frequency = DWD.Frequency.hourly
        elif frequency == '10-minutes':
            frequency = DWD.Frequency.ten_minutes
        else:
            return jsonify({"error": "frequency must be daily, hourly or 10-minutes"}), 400
        return jsonify([x.to_json() for x in dwd.get_temperature(start, stop, frequency)])
    else:
        return jsonify({"error": "start, stop and frequency are required parameters"}), 400


@app.route('/actual/fog-count-history', methods=['GET'])
def actual_fog_count_history():
    start = request.args.get('start')
    stop = request.args.get('stop')
    frequency = request.args.get('frequency')

    if start and stop and frequency:
        try:
            start = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
            start = start.replace(tzinfo=pytz.utc)
        except ValueError:
            return jsonify({"error": "start must be in the format YYYY-MM-DD HH:MM:SS"}), 400

        try:
            stop = datetime.strptime(stop, '%Y-%m-%d %H:%M:%S')
            stop = stop.replace(tzinfo=pytz.utc)
        except ValueError:
            return jsonify({"error": "stop must be in the format YYYY-MM-DD HH:MM:SS"}), 400

        if frequency == 'monthly':
            frequency = DWD.Frequency.monthly
        elif frequency == 'yearly':
            frequency = DWD.Frequency.yearly
        else:
            return jsonify({"error": "frequency must be either monthly or yearly"}), 400
        return jsonify([x.to_json() for x in dwd.get_fog_count(start, stop, frequency)])
    else:
        return jsonify({"error": "start, stop and frequency are required parameters"}), 400


@app.route('/actual/water-level-history', methods=['GET'])
def actual_water_level_history():
    try:
        data = pegel_online.get_water_level_measurements(PegelOnline.Period.last_31_days)
        return jsonify([entry.to_json() for entry in data])
    except BaseException as e:
        logging.exception("Error occurred while fetching water level measurements for the last 30 days:", exc_info=e)
        return jsonify({"error": str(e)}), 500

@app.route('/dwd-proxy', methods=['GET'])
def dwd_proxy():
    if request.headers.get('accept') != 'application/json':
        return jsonify({"error": "only application/json content type is supported"}), 400
    params = request.args
    url = params.get('url')
    other_params = {k: v for k, v in params.items() if k != 'url'}
    response = requests.get(url, params=other_params)
    return response.json()


@app.route('/backend-health-check')
def health_check():
    return "success"


if __name__ == '__main__':
    app.run(debug=True)
