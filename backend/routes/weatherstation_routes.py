from datetime import datetime
from flask import Blueprint, jsonify, request
import pytz
import logging

from services.raspi_station import save_station_data_to_influxdb, get_station_data_from_influxdb
from services.auth import require_api_key

weatherstation_bp = Blueprint('weatherstation', __name__)


@weatherstation_bp.route('/weatherstation', methods=['POST'])
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
