
"""Offline tests for FogCast system status."""

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


# Testkonfiguration ohne echte Zugangsdaten
FAKE_CONFIG = types.ModuleType("config")
FAKE_CONFIG.INFLUXDB_ORG = "FogCast"
FAKE_CONFIG.INFLUXDB_TOKEN = "not-a-real-secret"
FAKE_CONFIG.INFLUXDB_URL = "http://localhost:8086"

with patch.dict(sys.modules, {"config": FAKE_CONFIG}):
    path = (
        Path(__file__).resolve().parents[2]
        / "backend"
        / "services"
        / "system_status.py"
    )

    spec = importlib.util.spec_from_file_location(
        "system_status_tested", path
    )
    status = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(status)


NOW = datetime(2026, 11, 19, 15, 0, tzinfo=timezone.utc)


class Record:
    def __init__(self, dt):
        self.dt = dt

    def get_time(self):
        return self.dt


class Table:
    def __init__(self, *dates):
        self.records = [Record(dt) for dt in dates]


def query_with(station_minutes=2, forecast_minutes=30, fail=None):
    def query(flux):
        if fail == "db" or (
            fail == "station" and flux == status.STATION_QUERY
        ):
            raise RuntimeError("Simulated test failure")

        if flux == status.STATION_QUERY:
            if station_minutes is None:
                return []
            return [
                Table(NOW - timedelta(minutes=station_minutes))
            ]

        if flux == status.FORECAST_QUERY:
            if forecast_minutes is None:
                return []
            return [
                Table(NOW - timedelta(minutes=forecast_minutes))
            ]

        return []

    return query


class HealthTests(unittest.TestCase):

    def test_recent_data_are_green(self):
        result = status.build_system_status(
            NOW, query_with()
        )["components"]

        for component in (
            "api", "influxdb", "station", "forecasts"
        ):
            self.assertEqual(
                result[component]["status"], "ok"
            )

    def test_station_late_and_stale(self):
        warning = status.build_system_status(
            NOW, query_with(station_minutes=20)
        )
        error = status.build_system_status(
            NOW, query_with(station_minutes=45)
        )

        self.assertEqual(
            warning["components"]["station"]["status"],
            "warning"
        )
        self.assertEqual(
            error["components"]["station"]["status"],
            "error"
        )

    def test_missing_data_are_not_green(self):
        result = status.build_system_status(
            NOW, query_with(None, None)
        )["components"]

        self.assertEqual(
            result["station"]["status"], "unknown"
        )
        self.assertEqual(
            result["forecasts"]["status"], "unknown"
        )

    def test_database_failure(self):
        result = status.build_system_status(
            NOW, query_with(fail="db")
        )["components"]

        self.assertEqual(
            result["influxdb"]["status"], "error"
        )
        self.assertEqual(
            result["station"]["status"], "unknown"
        )
        self.assertEqual(
            result["forecasts"]["status"], "unknown"
        )

    def test_fallback_and_forecast_query(self):
        self.assertIn(
            "r.is_fallback != true",
            status.STATION_QUERY
        )
        self.assertIn(
            "exists r.temperature",
            status.STATION_QUERY
        )
        self.assertIn(
            "time(v: r.forecast_date) >= now()",
            status.FORECAST_QUERY
        )

    def test_invalid_timestamps(self):
        future = status._freshness(
            NOW + timedelta(minutes=10),
            NOW, 10, 30, "Messung"
        )

        naive = status._freshness(
            NOW.replace(tzinfo=None),
            NOW, 10, 30, "Messung"
        )

        self.assertEqual(future["status"], "unknown")
        self.assertEqual(naive["status"], "unknown")

    def test_station_query_error(self):
        result = status.build_system_status(
            NOW, query_with(fail="station")
        )["components"]

        self.assertEqual(
            result["influxdb"]["status"], "ok"
        )
        self.assertEqual(
            result["station"]["status"], "unknown"
        )
        self.assertEqual(
            result["forecasts"]["status"], "ok"
        )


if __name__ == "__main__":
    unittest.main()
