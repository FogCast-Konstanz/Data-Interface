# Fogcast Data Interface

## Overview
The Fogcast Data Interface repository provides the backend service for processing weather and water level data. It includes modules for fetching the current weather from DWD, OpenMeteo and PegelOnline, as well as for fetching weather forecasts based on forecasts from OpenMeteo. It also contains modules that collect and process weather data from the during the project installed weather station in Konstanz.

## Repository Structure
- **backend/**: Contains the main application logic, including authentication, configuration, and API endpoints.
- **app.py**: The entry point for the backend application. Here all the routes are defined and the application is initialized.
- **actual/**: Includes modules for fetching data from external sources like DWD, OpenMeteo, and PegelOnline.
- **migrations/**: Scripts for migrating water level data.
- **models/benchmarking**: Modules for querying benchmarking results stored in the database.
- **weather_forecast/**: Contains modules for fetching weather forecasts stored in the database.
- **weather_station/**: Modules for collecting and processing weather data from the installed weather station in Konstanz.
- **tests/**: Jupyter notebooks for testing data retrieval.

## Key Features
- Backend services for data management and API integration.
- Modules for fetching and processing weather and water level data.
- Fog prediction analysis using machine learning models.
- Migration scripts for water level data.

## Requirements
Refer to `requirements.txt` for dependencies.

## Usage
1. Set up the environment using Docker (`compose.yaml`).
2. Run the backend services (`backend/app.py`).
3. Use the analysis notebooks for fog prediction (`fog-model/meteostat.ipynb`).