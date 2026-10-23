import csv
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

_write_lock = Lock()
_FIELDS = (
    "timestamp",
    "temperature",
    "humidity",
    "water_temperature",
    "ceilometer",
    "uv_index",
    "uv_irradiance",
    "source",
)


def write_raspi_backup(data: dict) -> None:
    """Append one direct Raspberry-Pi measurement to the configured daily CSV."""
    if os.getenv("RASPI_BACKUP_ENABLED", "false").lower() != "true":
        return

    backup_root = os.getenv("RASPI_BACKUP_DIR")
    if not backup_root:
        raise RuntimeError("RASPI_BACKUP_ENABLED is true but RASPI_BACKUP_DIR is missing")

    timestamp = _parse_timestamp(data["timestamp"])
    day_path = (
        Path(backup_root)
        / "current"
        / f"weatherstation_{timestamp.date().isoformat()}.csv"
    )
    day_path.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "temperature": data.get("temperature"),
        "humidity": data.get("humidity"),
        "water_temperature": data.get("water_temperature"),
        "ceilometer": data.get("ceilometer"),
        "uv_index": data.get("uv_index"),
        "uv_irradiance": data.get("uv_irradiance"),
        "source": "raspberry_pi",
    }

    with _write_lock:
        file_exists = day_path.exists() and day_path.stat().st_size > 0
        with day_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)


def _parse_timestamp(value: str) -> datetime:
    timestamp = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    return timestamp.replace(tzinfo=timezone.utc)
