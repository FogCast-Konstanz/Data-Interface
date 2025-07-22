import logging
from datetime import datetime

import pytz
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from actual.DWD import DWD
from actual.PegelOnline import PegelOnline
from actual.OpenMeteo import OpenMeteo
from auth import require_api_key
from weather_forecast.influx import get_models, get_forecasts, get_current_forecast, get_archive_water_level, get_monthly_averaged_water_level, get_yearly_averaged_water_level
from weather_station.raspi_station import save_station_data_to_influxdb, get_station_data_from_influxdb
from models.benchmarking.influx import query_benchmark_scores
import re

app = Flask(__name__)
CORS(app)


dwd = DWD()
pegel_online = PegelOnline()


@app.route("/models")
def models():
    try:
        models = get_models()
        return jsonify(models)
    except Exception as e:
        logging.exception(
            "Error occurred while querying InfluxDB for tag values:", exc_info=e)
        return jsonify({"error": str(e)}), 500


@app.route('/forecasts', methods=['GET'])
def forecasts():
    forecast_datetime = request.args.get('datetime')
    model_id = request.args.get('model_id')

    if not forecast_datetime or not model_id:
        return jsonify({"error": "datetime and model_id are required parameters"}), 400

    try:
        forecast_datetime = datetime.strptime(
            forecast_datetime, '%Y-%m-%dT%H:%M:%SZ')
        forecast_datetime = forecast_datetime.replace(tzinfo=pytz.utc)

    except ValueError:
        return jsonify({"error": "datetime must be in the format YYYY-MM-DDTHH:MM:SSZ"}), 400

    try:
        df = get_forecasts(model_id, forecast_datetime)
        return jsonify(df.to_dict(orient='records'))

    except KeyError as e:
        logging.exception(
            "Error occurred while querying InfluxDB for forecasts:", exc_info=e)
        return jsonify({"error": f"KeyError: {str(e)}"}), 400

    except Exception as e:
        logging.exception(
            "Error occurred while querying InfluxDB for forecasts:", exc_info=e)
        return jsonify({"error": str(e)}), 500


@app.route('/current-forecast', methods=['GET'])
def current_forecast():
    model_id = request.args.get('model_id')

    if not model_id:
        return jsonify({"error": "model_id is a required parameter"}), 400

    try:
        df = get_current_forecast(model_id)
        return jsonify(df.to_dict(orient='records'))

    except KeyError as e:
        logging.exception(
            "Error occurred while querying InfluxDB for forecasts:", exc_info=e)
        return jsonify({"error": f"KeyError: {str(e)}"}), 400

    except Exception as e:
        logging.exception(
            "Error occurred while querying InfluxDB for forecasts:", exc_info=e)
        return jsonify({"error": str(e)}), 500


@app.route('/actual/live-data', methods=['GET'])
def actual_live_data():
    try:
        dwd_measurements = dwd.get_real_time_data()
        # current default station is Konstanz Rhein
        pegel_online_measurements = pegel_online.get_water_level_measurements(
            PegelOnline.Period.last_24_hours, PegelOnline.Station.KONSTANZ_RHEIN)
        pegel_online_measurements = sorted(
            pegel_online_measurements, key=lambda x: x.date, reverse=True)[0]
        result = [entry.to_json() for entry in dwd_measurements +
                  [pegel_online_measurements]]
        return jsonify(result)
    except Exception as e:
        logging.exception(
            "Error occurred while fetching actual data:", exc_info=e)
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


@app.route('/actual/archive', methods=['GET'])
def actual_weather_archive():
    date = request.args.get('date')
    model_id = request.args.get('model_id')
    if date and model_id:
        try:
            open_meteo = OpenMeteo()
            data = open_meteo.get_measurements(
                "icon_seamless", datetime.strptime(date, '%Y-%m-%d %H:%M:%S'))
            return jsonify(data.to_dict(orient='records'))
        except Exception as e:
            logging.exception(
                "Error occurred while retrieving data from OpenMeteo archive endpoint:", exc_info=e)
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "date and model_id are required parameters"}), 400


@app.route('/archive/water-level', methods=['GET'])
def archive_water_level():
    try:
        # Validate and parse 'start' parameter
        start = request.args.get('start')
        if not start:
            return jsonify({"error": "start is a required parameter"}), 400
        start = datetime.strptime(
            start, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=pytz.utc)

        # Validate and parse 'stop' parameter
        stop = request.args.get('stop')
        if not stop:
            return jsonify({"error": "stop is a required parameter"}), 400
        stop = datetime.strptime(
            stop, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=pytz.utc)

        # Validate and parse 'station_id' parameter
        station_id = request.args.get('station_id')
        if not station_id or not station_id.isdigit():
            return jsonify({"error": "station_id must be an integer"}), 400
        station_id = int(station_id)
        if station_id == 1:
            station_id = PegelOnline.Station.KONSTANZ_BODENSEE_N.value
        elif station_id == 2:
            station_id = PegelOnline.Station.KONSTANZ_RHEIN_N.value
        else:
            return jsonify({"error": "station_id must be either 1 (Konstanz Bodensee) or 2 (Konstanz Rhein)"}), 400

        # Validate and parse 'period' parameter
        period = request.args.get('period')
        if period:
            if period == "m":
                df = get_monthly_averaged_water_level(station_id, start, stop)
            elif period == "y":
                df = get_yearly_averaged_water_level(station_id, start, stop)
            else:
                return jsonify({"error": "period must be either 'm' (monthly) or 'y' (yearly)"}), 400
        else:
            df = get_archive_water_level(station_id, start, stop)

        # Return the data as JSON
        return jsonify(df.to_dict(orient='records'))

    except ValueError as e:
        return jsonify({"error": f"Invalid date format: {str(e)}"}), 400
    except Exception as e:
        logging.exception(
            "Error occurred while fetching archive water level data:", exc_info=e)
        return jsonify({"error": str(e)}), 500


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


@app.route('/actual/water-level', methods=['GET'])
def actual_water_level():
    station_id = request.args.get('station_id')
    if station_id:
        if not station_id.isdigit():
            return jsonify({"error": "station_id must be an integer"}), 400
        station_id = int(station_id)
        if station_id == 1:
            station_id = PegelOnline.Station.KONSTANZ_BODENSEE
        elif station_id == 2:
            station_id = PegelOnline.Station.KONSTANZ_RHEIN
        else:
            return jsonify({"error": "station_id must be either 1 (Konstanz Bodensee) or 2 (Konstanz Rhein)"}), 400
        try:
            data = pegel_online.get_water_level_measurements(
                PegelOnline.Period.last_31_days, station_id)
            return jsonify([entry.to_json() for entry in data])
        except BaseException as e:
            logging.exception(
                "Error occurred while fetching water level measurements for the last 30 days:", exc_info=e)
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


@app.route('/weatherstation', methods=['POST'])
@require_api_key
def post_station_data():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        save_station_data_to_influxdb(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"message": "Data received successfully"}), 200


@app.route('/weatherstation', methods=['GET'])
def get_station_data():
    start = request.args.get('start')
    stop = request.args.get('stop')

    if not start or not stop:
        return jsonify({"error": "start and stop are required parameters"}), 400

    try:
        start = datetime.strptime(start, '%Y-%m-%dT%H:%M:%SZ')
        start = start.replace(tzinfo=pytz.utc)
    except ValueError:
        return jsonify({"error": "start must be in the format format YYYY-MM-DDTHH:MM:SSZ"}), 400

    try:
        stop = datetime.strptime(stop, '%Y-%m-%dT%H:%M:%SZ')
        stop = stop.replace(tzinfo=pytz.utc)
    except ValueError:
        return jsonify({"error": "stop must be in the format format YYYY-MM-DDTHH:MM:SSZ"}), 400

    try:
        data = get_station_data_from_influxdb(start, stop)
        return jsonify(data)
    except Exception as e:
        logging.exception(
            "Error occurred while retrieving station data from InfluxDB:", exc_info=e)
        return jsonify({"error": str(e)}), 500


@app.route('/models/benchmarking', methods=['GET'])
def get_model_benchmarking():
    time_range = request.args.get('time_range')
    if time_range in ["1d", "4d", "7d", "15d", "30d"]:
        try:
            return jsonify(query_benchmark_scores(time_range).to_dict(orient='records'))
        except BaseException as e:
            logging.exception(
                f"Error occurred while fetching model benchmarking scores for timerange={time_range}:", exc_info=e)
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "time_range must be one of the following: 1d, 4d, 7d, 15d, 30d"}), 400


@app.route('/health-check', methods=['GET'])
def health_check():
    return "success"


if __name__ == '__main__':
    app.run(debug=True)
