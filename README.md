# Fogcast Data Interface

## Overview

The Fogcast Data Interface is the Flask backend for weather, water-level,
weather-station and model-benchmarking data. It integrates DWD, Open-Meteo,
PegelOnline, the Raspberry Pi weather station and InfluxDB.

## Repository Structure

### Root Level

- **backend/**: Main application logic, authentication, configuration and API endpoints
- **fog-model/**: Notebooks for fog-prediction analysis
- **tests/**: Tests, diagnostics and example data requests
- **compose.yaml**: Docker Compose configuration for the backend
- **docker-compose.influxdb.yaml**: Optional local InfluxDB configuration
- **README.md**: Project documentation

### Backend Structure

- **app.py**: Flask application entry point
- **config.py**: Database and service configuration
- **requirements.txt**: Python dependencies
- **Dockerfile**: Container configuration
- **routes/**: API route definitions
- **services/**: Business logic and data processing
- **services/actual/**: DWD, Open-Meteo and PegelOnline integrations
- **migrations/**: Database migration scripts

## Key Features

- Backend services for weather and water-level data
- Integration of external weather and water-level APIs
- Raspberry Pi weather-station data ingestion
- Fog-prediction analysis and model benchmarking
- Ceilometer and UV sensor data interfaces
- Optional CSV backup for direct Raspberry Pi measurements

## Requirements

Refer to `backend/requirements.txt` for the Python dependencies.

## Usage

1. Create a local environment file:

   ```bash
   cp .env.example .env
   ```

2. Start the backend with Docker:

   ```bash
   docker compose up -d
   ```

Production credentials must not be committed to the repository.

## Data Flow

```text
Raspberry Pi
    -> HTTPS POST /api/weatherstation
    -> Flask backend
    -> InfluxDB
```

The Raspberry Pi does not connect directly to InfluxDB. It only requires the
backend URL and a valid API key.

## Endpoints

### Models

- **GET /models**: Get available forecast models
- **GET /models/benchmarking**: Get model benchmarking scores

### Forecasts

- **GET /forecasts**: Get forecasts for a model and datetime
- **GET /current-forecast**: Get the current forecast for a model
- **GET /archive/water-level**: Get archived water-level data

### Actual Data

- **GET /actual/live-data**: Get current weather and water-level data
- **GET /actual/temperature-history**: Get historical DWD temperature data
- **GET /actual/fog-count-history**: Get historical DWD fog data
- **GET /actual/water-level**: Get current water-level data
- **GET /actual/ceilometer-history**: Get historical ceilometer data
- **GET /actual/uv-history**: Get historical UV data
- **GET /actual/archive**: Get archived Open-Meteo data

### Weather Station

- **POST /weatherstation**: Submit Raspberry Pi data; API-key authentication is required
- **GET /weatherstation**: Get weather-station data for a time range
- **GET /weatherstation/ceilometer**: Get ceilometer data for a time range
- **GET /weatherstation/uv**: Get UV data for a time range

The weather-station time range uses `start` and `stop` in UTC format:
`YYYY-MM-DDTHH:MM:SSZ`.

UV values are optional in a station request. Supported fields include
`uv_index` and `uv_irradiance`; compatible aliases such as `uv`, `uvi`,
`uv_radiation` and `uv_power_density` are also accepted.

### Utility Endpoints

- **GET /health-check**: Check whether the backend is available
- **GET /dwd-proxy**: Proxy requests to the DWD

## Raspberry Pi Data and Fallback System

The backend stores direct Raspberry Pi measurements in InfluxDB. The
Cronjob-Service uses these data together with DWD data to provide fallback
values when station data is missing. The primary fallback model is a Basic
LSTM; a linear DWD correlation is used as a safety fallback. Fallback values
are marked separately from measured values by the API and the frontend.

## Optional CSV Backup

The CSV backup is disabled by default. To enable it in a production
environment, configure a persistent host directory in the production `.env`:

```env
RASPI_BACKUP_ENABLED=true
RASPI_BACKUP_DIR=/var/lib/fogcast/raspi-backup
RASPI_BACKUP_HOST_DIR=/var/lib/fogcast/raspi-backup
```

The Compose configuration mounts the host directory into the container:

```yaml
volumes:
  - ${RASPI_BACKUP_HOST_DIR:-./raspi-backup}:/var/lib/fogcast/raspi-backup
```

Daily files are written below:

```text
/var/lib/fogcast/raspi-backup/current/weatherstation_YYYY-MM-DD.csv
```

The backup contains direct Raspberry Pi measurements and remains separate from
the primary InfluxDB storage. The host directory must be persistent and should
be included in the server backup.

## InfluxDB Measurements

| Bucket | Measurement | Content |
|---|---|---|
| `WeatherData` | `weather_station` | Temperature, humidity and water temperature |
| `WeatherData` | `ceilometer` | Ceilometer values |
| `WeatherData` | `uv` | UV index and optional irradiance |
| `WeatherForecast` | `forecast` | Weather forecasts |
| `WeatherForecast` | `water_level` | Water-level data |
| `WeatherForecast` | `benchmarking` | Model metrics |

## Diagnostics

Useful diagnostic tools are located in `tests/diagnostics/`:

- `check_raspi_data.py`: Check Raspberry Pi data in InfluxDB
- `diagnose_raspi_issue.py`: Check production data and backend connectivity
- `diagnose_timezone.py`: Check UTC and timezone handling
- `download_historical_data.py`: Export historical station data
- `quick_api_check.py`: Run a read-only API check
- `raspi_diagnose.sh`: Diagnose the Raspberry Pi system

The Raspberry Pi is usually reachable only through the HTWG network or VPN.
Do not put API keys, passwords or tokens into logs or support messages.

## Data Sources

- **DWD**: German Weather Service
- **Open-Meteo**: Weather forecasts and archive data
- **PegelOnline**: Water-level data
- **InfluxDB**: Time-series storage
- **Raspberry Pi Weather Station**: Local measurements in Konstanz

## Security

- Never commit `.env` files, API keys or tokens.
- Do not reinitialize a production InfluxDB without a confirmed backup.
- Use HTTPS and valid certificate verification in production.
- Keep the CSV backup directory outside the container and protect its access.

## Future Work

- Add SolarLog data and compare it with DWD sunshine measurements.
- Automate development and production deployment with CI/CD pipelines.
