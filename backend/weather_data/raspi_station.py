from datetime import datetime
import influxdb_client
import influxdb_client.client
import influxdb_client.client.write_api
from config import influx_client, INFLUXDB_ORG

BUCKET = "WeatherData"

def save_station_data_to_influxdb(data):
    """
    Save station data to InfluxDB.
    """
    # Check data format
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")

    required_fields = ["timestamp", "temperature", "water_temperature", "humidity"]
    if not all(field in data for field in required_fields):
        raise ValueError(f"Data must contain the following fields: {', '.join(required_fields)}")
    
    # Check types
    if isinstance(data["timestamp"], str):
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
    else:
        raise ValueError("Timestamp must be a string in the format YYYY-MM-DDTHH:MM:SSZ") 

    if not isinstance(data["temperature"], (int, float)):
        raise ValueError("Temperature must be an integer or float")
    if not isinstance(data["water_temperature"], (int, float)):
        raise ValueError("Water temperature must be an integer or float")
    if not isinstance(data["humidity"], (int, float)):
        raise ValueError("Humidity must be an integer or float")
    
    write_api = influx_client.write_api(write_options=influxdb_client.client.write_api.SYNCHRONOUS)

    # Create a point
    point = influxdb_client.Point("weather_station") \
            .field("temperature", float(data["temperature"])) \
            .field("water_temperature", float(data["water_temperature"])) \
            .field("humidity", float(data["humidity"])) \
            .time(data["timestamp"].isoformat())
    
    # Write the point to InfluxDB
    write_api.write(bucket=BUCKET, org=INFLUXDB_ORG, record=point)
    write_api.close()