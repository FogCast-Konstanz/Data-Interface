# Fogcast Data Interface

## Overview
The Fogcast Data Interface repository provides the backend service for processing weather and water level data. It includes modules for fetching the current weather from DWD, OpenMeteo and PegelOnline, as well as for fetching weather forecasts based on forecasts from OpenMeteo. It also contains modules that collect and process weather data from the during the project installed weather station in Konstanz.

## Repository Structure

### Root Level
- **backend/**: Contains the main application logic, including authentication, configuration, and API endpoints
- **fog-model/**: Jupyter notebooks for fog prediction analysis using Meteostat and XGBoost
- **tests/**: Jupyter notebooks for testing data retrieval
- **compose.yaml**: Docker Compose configuration for containerized deployment
- **README.md**: Project documentation

### Backend Structure
- **app.py**: Main Flask application entry point with route registration and Swagger documentation
- **config.py**: Configuration settings for database connections and external services
- **requirements.txt**: Python dependencies for the backend service
- **wsgi.py**: WSGI entry point for production deployment
- **Dockerfile**: Docker container configuration

### Backend Modules
- **routes/**: Modularized API route definitions
  - `models_routes.py`: Endpoints for weather forecast models
  - `forecasts_routes.py`: Weather forecast data endpoints
  - `actual_routes.py`: Real-time and historical weather/water data endpoints
  - `weatherstation_routes.py`: Local weather station data endpoints
- **services/**: Business logic and data processing services
  - `influx.py`: InfluxDB query services for time-series data
  - `fog.py`: Fog prediction algorithms and weather code analysis
  - `auth.py`: Authentication and authorization services
  - `raspi_station.py`: Raspberry Pi weather station data processing
- **services/actual/**: External data source integrations
  - `DWD.py`: German Weather Service (DWD) API integration
  - `OpenMeteo.py`: OpenMeteo weather API integration
  - `PegelOnline.py`: German water level service integration
- **services/benchmarking/**: Data analysis and benchmarking
  - `influx.py`: Model performance metrics from InfluxDB
- **migrations/**: Database migration scripts
  - `migrate_water_levels.py`: Script for migrating historical water level data


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

## Endpoints

### Models
- **GET /models**
  - **Description**: Get available forecast models
  - **Parameters**: None
  - **Returns**: Array of available model names (strings)
  - **Data Sources**: OpenMeteo (via InfluxDB)

### Forecasts
- **GET /forecasts**
  - **Description**: Get weather forecasts for a specific model and datetime
  - **Parameters**: 
    - `datetime` (required): Forecast datetime in format YYYY-MM-DDTHH:MM:SSZ
    - `model_id` (required): ID of the forecast model
  - **Returns**: Array of forecast data objects including weather parameters and fog predictions
  - **Data Sources**: OpenMeteo (via InfluxDB)

- **GET /current-forecast**
  - **Description**: Get the current forecast for a specific model
  - **Parameters**: 
    - `model_id` (required): ID of the forecast model
  - **Returns**: Array of current forecast data objects
  - **Data Sources**: OpenMeteo (via InfluxDB)

### Actual Data
- **GET /actual/live-data**
  - **Description**: Get current live weather and water level data
  - **Parameters**: None
  - **Returns**: Array of current weather measurements and water level data
  - **Data Sources**: DWD (weather), PegelOnline (water levels)

- **GET /actual/temperature-history**
  - **Description**: Get historical temperature data from DWD
  - **Parameters**: 
    - `start` (required): Start datetime in format YYYY-MM-DD HH:MM:SS
    - `stop` (required): Stop datetime in format YYYY-MM-DD HH:MM:SS
    - `frequency` (required): Data frequency (daily, hourly, 10-minutes)
  - **Returns**: Array of historical temperature measurements
  - **Data Sources**: DWD

- **GET /actual/archive**
  - **Description**: Get archived weather data from OpenMeteo using the icon_seamless model
  - **Parameters**: 
    - `date` (required): Date in format YYYY-MM-DD HH:MM:SS
    - `model_id` (required): Model ID (e.g., icon_seamless)
  - **Returns**: Array of archived weather data objects
  - **Data Sources**: OpenMeteo

- **GET /actual/fog-count-history**
  - **Description**: Get historical fog count data from DWD
  - **Parameters**: 
    - `start` (required): Start datetime in format YYYY-MM-DD HH:MM:SS
    - `stop` (required): Stop datetime in format YYYY-MM-DD HH:MM:SS
    - `frequency` (required): Data frequency (monthly, yearly)
  - **Returns**: Array of historical fog count data
  - **Data Sources**: DWD

- **GET /actual/water-level**
  - **Description**: Get current water level measurements for the last 31 days
  - **Parameters**: 
    - `station_id` (required): Station ID (1 for Konstanz Bodensee, 2 for Konstanz Rhein)
  - **Returns**: Array of water level measurements
  - **Data Sources**: PegelOnline

### Archive Data
- **GET /archive/water-level**
  - **Description**: Get archived water level data with optional aggregation
  - **Parameters**: 
    - `start` (required): Start datetime in format YYYY-MM-DDTHH:MM:SS
    - `stop` (required): Stop datetime in format YYYY-MM-DDTHH:MM:SS
    - `station_id` (required): Station ID (1 for Konstanz Bodensee, 2 for Konstanz Rhein)
    - `period` (optional): Aggregation period (y=yearly, m=monthly, w=weekly, d=daily)
  - **Returns**: Array of water level data objects with optional time aggregation
  - **Data Sources**: PegelOnline (via InfluxDB)

### Weather Station
- **POST /weatherstation**
  - **Description**: Submit weather station data (requires API key authentication)
  - **Parameters**: JSON body with weather station data
  - **Returns**: Success message
  - **Data Sources**: Raspberry Pi weather station

- **GET /weatherstation**
  - **Description**: Get weather station data for a time range
  - **Parameters**: 
    - `start` (required): Start datetime in format YYYY-MM-DDTHH:MM:SSZ
    - `stop` (required): Stop datetime in format YYYY-MM-DDTHH:MM:SSZ
  - **Returns**: Array of weather station data objects
  - **Data Sources**: InfluxDB (weather station data)

### Model Benchmarking
- **GET /models/benchmarking**
  - **Description**: Get model benchmarking scores
  - **Parameters**: 
    - `time_range` (required): Time range for benchmarking (1d, 4d, 7d, 15d, 30d)
  - **Returns**: Array of benchmarking score objects for different models
  - **Data Sources**: InfluxDB

### Utility Endpoints
- **GET /dwd-proxy**
  - **Description**: Proxy requests to DWD (German Weather Service)
  - **Parameters**: 
    - `url` (required): URL to proxy to DWD
    - `accept` (header, required): Content type (must be application/json)
  - **Returns**: Proxied data from DWD
  - **Data Sources**: DWD (proxied)

- **GET /health-check**
  - **Description**: Health check endpoint
  - **Parameters**: None
  - **Returns**: "success" string
  - **Data Sources**: None


### Data Sources Summary
- **DWD**: German Weather Service for real-time and historical weather data
- **OpenMeteo**: Weather archive and forecast data
- **PegelOnline**: German water level monitoring service
- **InfluxDB**: Time-series database for storing processed weather, forecast, and benchmarking data
- **Raspberry Pi Weather Station**: Local weather station installed in Konstanz

