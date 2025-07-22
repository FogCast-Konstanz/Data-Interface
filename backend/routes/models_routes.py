from flask import Blueprint, jsonify
from services.influx import get_models
import logging

models_bp = Blueprint('models', __name__)


@models_bp.route("/models")
def models():
    try:
        models = get_models()
        return jsonify(models)
    except Exception as e:
        logging.exception(
            "Error occurred while querying InfluxDB for tag values:", exc_info=e)
        return jsonify({"error": str(e)}), 500
