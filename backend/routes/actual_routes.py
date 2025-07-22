import logging
from datetime import datetime

import pytz
from flask import Blueprint, jsonify, request

from services.actual.DWD import DWD
from services.actual.PegelOnline import PegelOnline
from services.actual.OpenMeteo import OpenMeteo
from services.influx import get_archive_water_level, get_monthly_averaged_water_level, get_yearly_averaged_water_level

actual_bp = Blueprint('actual', __name__)

dwd = DWD()
pegel_online = PegelOnline()


@actual_bp.route('/actual/live-data', methods=['GET'])
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


@actual_bp.route('/actual/temperature-history', methods=['GET'])
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


@actual_bp.route('/actual/archive', methods=['GET'])
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


@actual_bp.route('/archive/water-level', methods=['GET'])
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


@actual_bp.route('/actual/fog-count-history', methods=['GET'])
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


@actual_bp.route('/actual/water-level', methods=['GET'])
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
