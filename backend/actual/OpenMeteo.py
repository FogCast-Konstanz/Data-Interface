import pandas as pd
from datetime import datetime

import openmeteo_requests
import requests_cache
from retry_requests import retry

class OpenMeteo:

    def get_measured(self, start_date: datetime, current_date:datetime) -> pd.DataFrame:
        """
        Fetches actual observed weather data from the Open-Meteo API.

        Args:
        - start_date (str): Start date for the query.
        - current_date (str): End date for the query.

        Returns:
        - DataFrame: Measured weather data for comparison with forecasts.
        """
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)

        # API request parameters
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 47.6952,
            "longitude": 9.1307,
            "hourly": ["temperature_2m", "surface_pressure", "cloud_cover", "precipitation", "relative_humidity_2m",
                       "dew_point_2m"],
            "timezone": "Europe/Berlin",
            "start_date": datetime.fromisoformat(start_date).date(),
            "end_date": datetime.fromisoformat(current_date).date(),
            "models": ['icon_seamless', 'dmi_seamless', 'bom_access_global']
        }

        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        # Extract hourly data
        hourly = response.Hourly()
        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            ),
            "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
            "relative_humidity_2m": hourly.Variables(4).ValuesAsNumpy(),
            "surface_pressure": hourly.Variables(1).ValuesAsNumpy(),
            "cloud_cover": hourly.Variables(2).ValuesAsNumpy(),
            "precipitation": hourly.Variables(3).ValuesAsNumpy(),
            "dew_point_2m": hourly.Variables(5).ValuesAsNumpy()
        }

        return pd.DataFrame(data=hourly_data)

open_meteo = OpenMeteo()
print(open_meteo.get_measured(datetime.isoformat(datetime(2020, 1, 1)), datetime.isoformat(datetime.now())))