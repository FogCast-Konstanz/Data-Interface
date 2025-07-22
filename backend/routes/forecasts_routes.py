from flask import Blueprint, jsonify, request
from datetime import datetime
import pytz
from services.influx import get_forecasts, get_current_forecast
import logging

forecasts_bp = Blueprint('forecasts', __name__)


@forecasts_bp.route('/forecasts', methods=['GET'])
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


@forecasts_bp.route('/current-forecast', methods=['GET'])
def current_forecast():
    model_id = request.args.get('model_id')

    if not model_id:
        return jsonify({"error": "model_id is a required parameter"}), 400

    try:
        df = get_current_forecast(model_id)
        return jsonify(df.to_dict(orient='records'))

    except ValueError as e:
        logging.error(e)
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        logging.exception(
            "Error occurred while querying InfluxDB for forecasts:", exc_info=e)
        return jsonify({"error": str(e)}), 500
