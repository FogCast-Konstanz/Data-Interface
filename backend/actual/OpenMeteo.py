import pandas as pd
from datetime import datetime
from enum import Enum

import openmeteo_requests
import requests_cache
from retry_requests import retry

class OpenMeteo:

    class OpenMeteoModels(Enum):
        icon_seamless = "icon_seamless"
        dmi_seamless = "dmi_seamless"
        bom_access_global = "bom_access_global"

    def get_measurements(self, model_id: str, timestamp: datetime) -> pd.DataFrame:
        day = timestamp.strftime("%Y-%m-%d")
        cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
        retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
        openmeteo = openmeteo_requests.Client(session = retry_session)

        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": 47.6952,
            "longitude": 9.1307,
            "start_date": day,
            "end_date": day,
            "models": [ model_id ],
            "hourly": [
                "temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature", "precipitation_probability",
                "precipitation", "rain", "showers", "snowfall", "snow_depth", "weather_code", "pressure_msl", "surface_pressure",
                "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high", "visibility", "evapotranspiration",
                "et0_fao_evapotranspiration", "vapour_pressure_deficit", "wind_speed_10m", "wind_speed_80m", "wind_speed_120m",
                "wind_speed_180m", "wind_direction_10m", "wind_direction_80m", "wind_direction_120m", "wind_direction_180m",
                "wind_gusts_10m", "temperature_80m", "temperature_120m", "temperature_180m", "soil_temperature_0cm", "soil_temperature_6cm",
                "soil_temperature_18cm", "soil_temperature_54cm", "soil_moisture_0_to_1cm", "soil_moisture_1_to_3cm", "soil_moisture_3_to_9cm",
                "soil_moisture_9_to_27cm", "soil_moisture_27_to_81cm"
            ]
        }
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
        hourly_dew_point_2m = hourly.Variables(2).ValuesAsNumpy()
        hourly_apparent_temperature = hourly.Variables(3).ValuesAsNumpy()
        hourly_precipitation_probability = hourly.Variables(4).ValuesAsNumpy()
        hourly_precipitation = hourly.Variables(5).ValuesAsNumpy()
        hourly_rain = hourly.Variables(6).ValuesAsNumpy()
        hourly_showers = hourly.Variables(7).ValuesAsNumpy()
        hourly_snowfall = hourly.Variables(8).ValuesAsNumpy()
        hourly_snow_depth = hourly.Variables(9).ValuesAsNumpy()
        hourly_weather_code = hourly.Variables(10).ValuesAsNumpy()
        hourly_pressure_msl = hourly.Variables(11).ValuesAsNumpy()
        hourly_surface_pressure = hourly.Variables(12).ValuesAsNumpy()
        hourly_cloud_cover = hourly.Variables(13).ValuesAsNumpy()
        hourly_cloud_cover_low = hourly.Variables(14).ValuesAsNumpy()
        hourly_cloud_cover_mid = hourly.Variables(15).ValuesAsNumpy()
        hourly_cloud_cover_high = hourly.Variables(16).ValuesAsNumpy()
        hourly_visibility = hourly.Variables(17).ValuesAsNumpy()
        hourly_evapotranspiration = hourly.Variables(18).ValuesAsNumpy()
        hourly_et0_fao_evapotranspiration = hourly.Variables(19).ValuesAsNumpy()
        hourly_vapour_pressure_deficit = hourly.Variables(20).ValuesAsNumpy()
        hourly_wind_speed_10m = hourly.Variables(21).ValuesAsNumpy()
        hourly_wind_speed_80m = hourly.Variables(22).ValuesAsNumpy()
        hourly_wind_speed_120m = hourly.Variables(23).ValuesAsNumpy()
        hourly_wind_speed_180m = hourly.Variables(24).ValuesAsNumpy()
        hourly_wind_direction_10m = hourly.Variables(25).ValuesAsNumpy()
        hourly_wind_direction_80m = hourly.Variables(26).ValuesAsNumpy()
        hourly_wind_direction_120m = hourly.Variables(27).ValuesAsNumpy()
        hourly_wind_direction_180m = hourly.Variables(28).ValuesAsNumpy()
        hourly_wind_gusts_10m = hourly.Variables(29).ValuesAsNumpy()
        hourly_temperature_80m = hourly.Variables(30).ValuesAsNumpy()
        hourly_temperature_120m = hourly.Variables(31).ValuesAsNumpy()
        hourly_temperature_180m = hourly.Variables(32).ValuesAsNumpy()
        hourly_soil_temperature_0cm = hourly.Variables(33).ValuesAsNumpy()
        hourly_soil_temperature_6cm = hourly.Variables(34).ValuesAsNumpy()
        hourly_soil_temperature_18cm = hourly.Variables(35).ValuesAsNumpy()
        hourly_soil_temperature_54cm = hourly.Variables(36).ValuesAsNumpy()
        hourly_soil_moisture_0_to_1cm = hourly.Variables(37).ValuesAsNumpy()
        hourly_soil_moisture_1_to_3cm = hourly.Variables(38).ValuesAsNumpy()
        hourly_soil_moisture_3_to_9cm = hourly.Variables(39).ValuesAsNumpy()
        hourly_soil_moisture_9_to_27cm = hourly.Variables(40).ValuesAsNumpy()
        hourly_soil_moisture_27_to_81cm = hourly.Variables(41).ValuesAsNumpy()

        hourly_data = {"date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ), "temperature_2m": hourly_temperature_2m, "relative_humidity_2m": hourly_relative_humidity_2m,
            "dew_point_2m": hourly_dew_point_2m, "apparent_temperature": hourly_apparent_temperature,
            "precipitation_probability": hourly_precipitation_probability, "precipitation": hourly_precipitation,
            "rain": hourly_rain, "showers": hourly_showers, "snowfall": hourly_snowfall,
            "snow_depth": hourly_snow_depth, "weather_code": hourly_weather_code, "pressure_msl": hourly_pressure_msl,
            "surface_pressure": hourly_surface_pressure, "cloud_cover": hourly_cloud_cover,
            "cloud_cover_low": hourly_cloud_cover_low, "cloud_cover_mid": hourly_cloud_cover_mid,
            "cloud_cover_high": hourly_cloud_cover_high, "visibility": hourly_visibility,
            "evapotranspiration": hourly_evapotranspiration,
            "et0_fao_evapotranspiration": hourly_et0_fao_evapotranspiration,
            "vapour_pressure_deficit": hourly_vapour_pressure_deficit, "wind_speed_10m": hourly_wind_speed_10m,
            "wind_speed_80m": hourly_wind_speed_80m, "wind_speed_120m": hourly_wind_speed_120m,
            "wind_speed_180m": hourly_wind_speed_180m, "wind_direction_10m": hourly_wind_direction_10m,
            "wind_direction_80m": hourly_wind_direction_80m, "wind_direction_120m": hourly_wind_direction_120m,
            "wind_direction_180m": hourly_wind_direction_180m, "wind_gusts_10m": hourly_wind_gusts_10m,
            "temperature_80m": hourly_temperature_80m, "temperature_120m": hourly_temperature_120m,
            "temperature_180m": hourly_temperature_180m, "soil_temperature_0cm": hourly_soil_temperature_0cm,
            "soil_temperature_6cm": hourly_soil_temperature_6cm, "soil_temperature_18cm": hourly_soil_temperature_18cm,
            "soil_temperature_54cm": hourly_soil_temperature_54cm,
            "soil_moisture_0_to_1cm": hourly_soil_moisture_0_to_1cm,
            "soil_moisture_1_to_3cm": hourly_soil_moisture_1_to_3cm,
            "soil_moisture_3_to_9cm": hourly_soil_moisture_3_to_9cm,
            "soil_moisture_9_to_27cm": hourly_soil_moisture_9_to_27cm,
            "soil_moisture_27_to_81cm": hourly_soil_moisture_27_to_81cm}

        hourly_dataframe = pd.DataFrame(data = hourly_data)
        sorted_columns = sorted(hourly_dataframe.columns)
        hourly_dataframe = hourly_dataframe[sorted_columns]
        return hourly_dataframe