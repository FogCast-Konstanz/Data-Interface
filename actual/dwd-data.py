from wetterdienst import Settings
from wetterdienst.provider.dwd.observation import DwdObservationRequest
import pandas as pd
from datetime import datetime
from objects.GenericResponseObject import GenericResponseObject
from enum import Enum


class DWD:
    """
    Class to interact with the DWD API to get actual weather data for the station in Konstanz.
    """

    def __init__(self):
        """
        Initialize the DWD class with the settings and station ID.
        """
        self.settings = Settings(
            ts_shape="long", ts_humanize=True, ts_convert_units=True
        )
        # string format of datetime objects
        self.date_str_format = r"%Y-%m-%d"
        # Station ID for Konstanz DWD station
        self.station_id = 2712

    class Params(Enum):
        """
        Enum class to define the parameters that can be requested from the DWD API.
        """
        cloud_cover = "cloud_cover_total"
        humidity = "humidity"
        wind_speed = "wind_speed"
        fog_count = "count_weather_type_fog"
        temperature = "temperature_air_mean_2m"

    class Dataset(Enum):
        """
        Enum class to define the datasets that can be requested from the DWD API.
        """
        climate_summary = "climate_summary"
        weather_phenomena = "weather_phenomena"

    def get_temperature(self, utc_start: datetime, utc_end: datetime) -> list[GenericResponseObject]:
        """
        Get the temperature data from the DWD API for the given time range.
        :param utc_start: Start date for the data request.
        :param utc_end: End date for the data request.
        :return: DataFrame with the temperature data.
        """
        request = self.__make_dwd_observation_request(
            self.Params.temperature,
            self.Dataset.climate_summary,
            self.Frequency.daily,
            utc_start,
            utc_end,
        )

        values = request.values.all().df.to_pandas()
        return self.__df_to_generic_response_object(values)
    
    def __df_to_generic_response_object(self, df: pd.DataFrame):
        """
        Convert the DataFrame to a list of GenericResponseObject.
        :param df: DataFrame with the data.
        :return: List of GenericResponseObject.
        """
        return [
            GenericResponseObject(
                date=row["date"],
                value=row["value"],
                quality=row["quality"],
            )
            for index, row in df.iterrows()
        ]

    class Frequency(Enum):
        daily = "daily"
        monthly = "monthly"
        yearly = "annual"

    def get_fog_day_count(self, utc_start: datetime, utc_end: datetime, frequency) -> list[GenericResponseObject]:
        request = self.__make_dwd_observation_request(
            self.Params.fog_count,
            self.Dataset.weather_phenomena,
            frequency,
            utc_start,
            utc_end,
        )
        df: pd.DataFrame = request.values.all().df.to_pandas()
        return self.__df_to_generic_response_object(df)

    def __make_dwd_observation_request(
        self,
        parameters: Params,
        dataset: Dataset,
        frequency: Frequency,
        start_date: datetime,
        end_date: datetime,
    ):
        return DwdObservationRequest(
            parameters=[
                (frequency.value, dataset.value, parameters.value),
            ],
            start_date=start_date.strftime(self.date_str_format),
            end_date=end_date.strftime(self.date_str_format),
            settings=self.settings,
        ).filter_by_station_id(station_id=(self.station_id,))


dwd = DWD()
print("##### temperature #####")
values = dwd.get_temperature(datetime(1990, 10, 1), datetime(2025, 2, 5))
print(values)

print("##### fog day count #####")
values2 = dwd.get_fog_day_count(
    datetime(1990, 10, 1), datetime(2025, 2, 5), DWD.Frequency.yearly
)
print(values2)
exit(0)
