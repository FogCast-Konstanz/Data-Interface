from datetime import datetime
from flask import Blueprint, jsonify, request
import pytz
import logging

from services.raspi_station import save_station_data_to_influxdb, get_station_data_from_influxdb
from services.raspi_backup import write_raspi_backup
from services.auth import require_api_key
from config import influx_client, INFLUXDB_ORG

weatherstation_bp = Blueprint('weatherstation', __name__)


@weatherstation_bp.route('/weatherstation', methods=['POST'])
@require_api_key
def post_station_data():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        write_raspi_backup(data)
        save_station_data_to_influxdb(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except (OSError, RuntimeError) as e:
        logging.exception("Could not write Raspberry-Pi backup")
        return jsonify({"error": "Raspberry-Pi backup is unavailable"}), 503
    return jsonify({"message": "Data received successfully"}), 200


@weatherstation_bp.route('/weatherstation', methods=['GET'])
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


@weatherstation_bp.route('/weatherstation/ceilometer', methods=['GET'])
def get_ceilometer_data():
    start = request.args.get('start')
    stop = request.args.get('stop')

    if not start or not stop:
        return jsonify({"error": "start and stop are required parameters"}), 400

    try:
        start_dt = datetime.strptime(start, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
        stop_dt = datetime.strptime(stop, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
    except ValueError:
        return jsonify({"error": "start and stop must be in the format YYYY-MM-DDTHH:MM:SSZ"}), 400

    if start_dt >= stop_dt:
        return jsonify({"error": "start must be before stop"}), 400

    try:
        query_api = influx_client.query_api()
        query = f'''
        from(bucket: "WeatherData")
          |> range(start: {start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}, stop: {stop_dt.strftime('%Y-%m-%dT%H:%M:%SZ')})
          |> filter(fn: (r) => r["_measurement"] == "ceilometer")
          |> sort(columns: ["_time"])
        '''
        result = query_api.query(query=query, org=INFLUXDB_ORG)

        data = []
        for table in result:
            for record in table.records:
                data.append({"time": record.values.get("_time"), "value": record.values.get("_value")})

        return jsonify(data)
    except Exception as e:
        logging.exception("Error occurred while retrieving ceilometer data from InfluxDB:", exc_info=e)
        return jsonify({"error": str(e)}), 500


@weatherstation_bp.route('/weatherstation/uv', methods=['GET'])
def get_uv_data():
    start = request.args.get('start')
    stop = request.args.get('stop')

    if not start or not stop:
        return jsonify({"error": "start and stop are required parameters"}), 400

    try:
        start_dt = datetime.strptime(start, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
        stop_dt = datetime.strptime(stop, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
    except ValueError:
        return jsonify({"error": "start and stop must be in the format YYYY-MM-DDTHH:MM:SSZ"}), 400

    if start_dt >= stop_dt:
        return jsonify({"error": "start must be before stop"}), 400

    try:
        query_api = influx_client.query_api()
        query = f'''
        from(bucket: "WeatherData")
          |> range(start: {start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}, stop: {stop_dt.strftime('%Y-%m-%dT%H:%M:%SZ')})
          |> filter(fn: (r) => r["_measurement"] == "uv")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"])
        '''
        result = query_api.query(query=query, org=INFLUXDB_ORG)
        data = []
        for table in result:
            for record in table.records:
                row = dict(record.values)
                row["time"] = row.pop("_time", None)
                for key in ("result", "table", "_start", "_stop", "_measurement"):
                    row.pop(key, None)
                data.append(row)
        return jsonify(data)
    except Exception as e:
        logging.exception("Error occurred while retrieving UV data from InfluxDB:", exc_info=e)
        return jsonify({"error": str(e)}), 500


@weatherstation_bp.route('/weatherstation/fallback', methods=['GET'])
def get_fallback_data():
    """
    Retrieve fallback forecast data for periods when Raspberry Pi had no data.
    These are DWD-based predictions generated by the Fallback System.
    """
    start = request.args.get('start')
    stop = request.args.get('stop')

    if not start or not stop:
        return jsonify({"error": "start and stop are required parameters"}), 400

    try:
        start = datetime.strptime(start, '%Y-%m-%dT%H:%M:%SZ')
        start = start.replace(tzinfo=pytz.utc)
    except ValueError:
        return jsonify({"error": "start must be in the format YYYY-MM-DDTHH:MM:SSZ"}), 400

    try:
        stop = datetime.strptime(stop, '%Y-%m-%dT%H:%M:%SZ')
        stop = stop.replace(tzinfo=pytz.utc)
    except ValueError:
        return jsonify({"error": "stop must be in the format YYYY-MM-DDTHH:MM:SSZ"}), 400

    try:
        # Get all station data and filter for fallback entries
        from influxdb_client import InfluxDBClient
        from config import influx_client, INFLUXDB_ORG

        query_api = influx_client.query_api()

        # Flux query to get only fallback data (is_fallback=true)
        query = f'''
        from(bucket: "WeatherData")
          |> range(start: {start.isoformat()}, stop: {stop.isoformat()})
          |> filter(fn: (r) => r["_measurement"] == "weather_station")
          |> filter(fn: (r) => r["is_fallback"] == "true")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"])
          |> drop(columns: ["_start", "_stop", "_measurement"])
          |> rename(columns: {{_time: "timestamp"}})
        '''

        result = query_api.query(query=query, org=INFLUXDB_ORG)

        data = []
        for table in result:
            for record in table.records:
                row = {"timestamp": record.values.get("_time")}
                for key, value in record.values.items():
                    if key not in ["_measurement", "_start", "_stop", "result", "table", "_time"]:
                        row[key] = value
                data.append(row)

        return jsonify(data)
    except Exception as e:
        logging.exception(
            "Error occurred while retrieving fallback data from InfluxDB:", exc_info=e)
        return jsonify({"error": str(e)}), 500
