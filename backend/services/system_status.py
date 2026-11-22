
"""Read-only system health checks for FogCast.

All reported timestamps are UTC.
Database availability and data freshness are checked separately.
"""

from datetime import datetime, timezone
from threading import Lock
from time import monotonic

from config import INFLUXDB_ORG, INFLUXDB_TOKEN, INFLUXDB_URL


# Vorläufige Grenzwerte für den Prototyp
STATION_OK_MINUTES = 10
STATION_WARNING_MINUTES = 30

FORECAST_OK_MINUTES = 180
FORECAST_WARNING_MINUTES = 360

CACHE_SECONDS = 30

_cache_lock = Lock()
_cached = None
_expires_at = 0.0


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def _component(status, message, latest_at=None, age_minutes=None):
    return {
        "status": status,
        "message": message,
        "latest_at": _iso(latest_at) if latest_at else None,
        "age_minutes": (
            round(age_minutes, 1)
            if age_minutes is not None
            else None
        ),
    }


def _latest_time(tables):
    """Find the newest timestamp across all returned tables."""
    candidates = [
        record.get_time()
        for table in tables
        for record in table.records
    ]

    candidates = [
        value
        for value in candidates
        if isinstance(value, datetime)
    ]

    if not candidates:
        return None

    return max(candidates)


def _freshness(latest, now, good_minutes, warning_minutes, noun):
    if latest is None:
        return _component(
            "unknown",
            f"Keine {noun} im abgefragten Zeitraum gefunden."
        )

    if latest.tzinfo is None:
        return _component(
            "unknown",
            f"Zeitstempel der {noun} enthält keine Zeitzone."
        )

    age = (
        now - latest.astimezone(timezone.utc)
    ).total_seconds() / 60

    if age < -2:
        return _component(
            "unknown",
            f"Zeitstempel der {noun} liegt in der Zukunft.",
            latest
        )

    if age <= good_minutes:
        return _component(
            "ok",
            f"{noun.capitalize()} aktuell.",
            latest,
            max(age, 0)
        )

    if age <= warning_minutes:
        return _component(
            "warning",
            f"{noun.capitalize()} verzögert.",
            latest,
            age
        )

    return _component(
        "error",
        f"{noun.capitalize()} veraltet.",
        latest,
        age
    )


# Echte Stationsmessungen:
# Fallback-Werte werden ausdrücklich ausgeschlossen.

STATION_QUERY = """
from(bucket: "WeatherData")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "weather_station")
  |> pivot(
      rowKey: ["_time"],
      columnKey: ["_field"],
      valueColumn: "_value"
  )
  |> filter(fn: (r) =>
      exists r.temperature and
      (not exists r.is_fallback or r.is_fallback != true)
  )
  |> group()
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 1)
"""


# Bei Prognosen ist _time der Schreibzeitpunkt.
# forecast_date beschreibt den vorhergesagten Zeitpunkt.

FORECAST_QUERY = """
from(bucket: "WeatherForecast")
  |> range(start: -14d)
  |> filter(fn: (r) => r._measurement == "forecast")
  |> filter(fn: (r) => r._field == "temperature_2m")
  |> filter(fn: (r) => exists r.forecast_date)
  |> filter(fn: (r) => time(v: r.forecast_date) >= now())
  |> group()
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 1)
"""


READ_CHECK_QUERY = """
from(bucket: "WeatherData")
  |> range(start: -1m)
  |> limit(n: 1)
"""


def build_system_status(now=None, execute_query=None):
    """Build the system status report."""

    now = now or datetime.now(timezone.utc)

    result = {
        "checked_at": _iso(now),
        "components": {
            "api": _component(
                "ok",
                "Flask-API beantwortet die Statusanfrage."
            ),
            "influxdb": _component(
                "unknown", "Noch nicht geprüft."
            ),
            "station": _component(
                "unknown", "Noch nicht geprüft."
            ),
            "forecasts": _component(
                "unknown", "Noch nicht geprüft."
            ),
        },
    }

    try:
        if execute_query is None:
            from influxdb_client import InfluxDBClient

            with InfluxDBClient(
                url=INFLUXDB_URL,
                token=INFLUXDB_TOKEN,
                org=INFLUXDB_ORG,
                timeout=4000,
                verify_ssl=False,
            ) as client:
                query_api = client.query_api()

                return _run_queries(
                    result,
                    now,
                    lambda q: query_api.query(
                        q, org=INFLUXDB_ORG
                    )
                )

        return _run_queries(result, now, execute_query)

    except Exception:
        result["components"]["influxdb"] = _component(
            "error",
            "Datenbank-Leseprüfung fehlgeschlagen."
        )
        result["components"]["station"] = _component(
            "unknown",
            "Ohne Datenbankprüfung nicht prüfbar."
        )
        result["components"]["forecasts"] = _component(
            "unknown",
            "Ohne Datenbankprüfung nicht prüfbar."
        )

        return result


def _run_queries(result, now, query):
    components = result["components"]

    # 1. Datenbank-Lesbarkeit prüfen
    try:
        query(READ_CHECK_QUERY)

        components["influxdb"] = _component(
            "ok",
            "InfluxDB-Leseabfrage erfolgreich."
        )

    except Exception:
        components["influxdb"] = _component(
            "error",
            "InfluxDB-Leseabfrage fehlgeschlagen."
        )
        components["station"] = _component(
            "unknown",
            "Ohne Datenbankprüfung nicht prüfbar."
        )
        components["forecasts"] = _component(
            "unknown",
            "Ohne Datenbankprüfung nicht prüfbar."
        )

        return result

    # 2. Letzte echte Stationsmessung prüfen
    try:
        latest = _latest_time(query(STATION_QUERY))

        components["station"] = _freshness(
            latest,
            now,
            STATION_OK_MINUTES,
            STATION_WARNING_MINUTES,
            "echte Stationsmessung"
        )

    except Exception:
        components["station"] = _component(
            "unknown",
            "Stationsdaten konnten nicht ausgewertet werden."
        )

    # 3. Aktualität der Prognosen prüfen
    try:
        latest = _latest_time(query(FORECAST_QUERY))

        components["forecasts"] = _freshness(
            latest,
            now,
            FORECAST_OK_MINUTES,
            FORECAST_WARNING_MINUTES,
            "Prognosen"
        )

    except Exception:
        components["forecasts"] = _component(
            "unknown",
            "Prognosedaten konnten nicht ausgewertet werden."
        )

    return result


def get_cached_system_status():
    """Cache results to avoid excessive database queries."""

    global _cached, _expires_at

    with _cache_lock:
        if _cached is None or monotonic() >= _expires_at:
            _cached = build_system_status()
            _expires_at = monotonic() + CACHE_SECONDS

        return _cached
