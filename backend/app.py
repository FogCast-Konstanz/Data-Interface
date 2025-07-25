import logging

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from services.benchmarking.influx import get_latest_benchmark
from routes.models_routes import models_bp
from routes.forecasts_routes import forecasts_bp
from routes.weatherstation_routes import weatherstation_bp
from routes.actual_routes import actual_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(models_bp)
app.register_blueprint(forecasts_bp)
app.register_blueprint(weatherstation_bp)
app.register_blueprint(actual_bp)


@app.route('/dwd-proxy', methods=['GET'])
def dwd_proxy():
    if request.headers.get('accept') != 'application/json':
        return jsonify({"error": "only application/json content type is supported"}), 400
    params = request.args
    url = params.get('url')
    if not url:
        return jsonify({"error": "url parameter is required"}), 400
    other_params = {k: v for k, v in params.items() if k != 'url'}
    response = requests.get(url, params=other_params)
    return response.json()


@app.route('/models/benchmarking', methods=['GET'])
def get_model_benchmarking():
    try:
        return jsonify(get_latest_benchmark().to_dict(orient='records'))
    except BaseException as e:
        logging.exception(
            f"Error occurred while fetching model benchmarking scores:", exc_info=e)
        return jsonify({"error": str(e)}), 500


@app.route('/health-check', methods=['GET'])
def health_check():
    return "success"


if __name__ == '__main__':
    app.run(debug=True, port=8000)
