from datetime import datetime
from enum import Enum

import pandas as pd
from wetterdienst import Settings, Period
from wetterdienst.provider.dwd.observation import DwdObservationRequest
from flask import current_app as app
from .objects.GenericResponseObject import GenericResponseObject

def df_to_generic_response_object(df: pd.DataFrame, occurrence_name: str):
    """
    Converts a pandas DataFrame containing weather-related data into a list of
    GenericResponseObject, where each object represents a row in the DataFrame.

    The method ensures that each row of the provided DataFrame is translated
    into a generic, structured response object, using specific columns from
    the DataFrame for attributes such as date, value, and quality.

    Parameters:
        df (pd.DataFrame): The DataFrame containing weather data, which must
            include "date", "value", and "quality" columns.
        occurrence_name (str): The name associated with the occurrence or
            dataset for which the data is being processed.

    Returns:
        list[GenericResponseObject]: A list of objects representing each row
            of the DataFrame in a structured, generic response format.
    """
    return [GenericResponseObject(
        name=occurrence_name,
        date=pd.Timestamp(row["date"]).to_pydatetime(),
        value=row["value"],
        quality=row["quality"]
    ) for index, row in df.iterrows()]


class DWD:
    """
    Class to interact with the DWD API to get actual weather data for the station in Konstanz.
    """

    def __init__(self):
        """
        Initialize the DWD class with the settings and station ID.
        """
        self.settings = Settings(ts_shape="long", ts_humanize=True, ts_convert_units=True)
        # string format of datetime objects
        self.date_str_format = r"%Y-%m-%d"
        # Station ID for Konstanz DWD station
        self.station_id = 2712

    class Frequency(Enum):
        ten_minutes = "10_minutes"
        # Documentation for all hourly requests: https://github.com/earthobservations/wetterdienst/blob/276e524975b507c92868bafaf3603f438b04bfcc/docs/data/provider/dwd/observation/hourly.md
        hourly = "hourly"
        # Documentation for all daily requests: https://github.com/earthobservations/wetterdienst/blob/276e524975b507c92868bafaf3603f438b04bfcc/docs/data/provider/dwd/observation/daily.md
        daily = "daily"
        # Documentation for all monthly requests: https://github.com/earthobservations/wetterdienst/blob/276e524975b507c92868bafaf3603f438b04bfcc/docs/data/provider/dwd/observation/monthly.md
        monthly = "monthly"
        # Documentation for all yearly requests: https://github.com/earthobservations/wetterdienst/blob/276e524975b507c92868bafaf3603f438b04bfcc/docs/data/provider/dwd/observation/annual.md
        yearly = "annual"

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
        temperature_air = "temperature_air"
        wind = "wind"
        precipitation = "precipitation"

    def get_temperature(self, utc_start: datetime, utc_end: datetime, frequency: Frequency) -> list[
        GenericResponseObject]:
        """
        Retrieves temperature data based on the specified time range and frequency. The method
        supports fetching data in daily or hourly intervals, aligning with the parameters and
        datasets for each respective frequency. The response is formatted into a list of
        GenericResponseObject for consistency and ease of further processing.

        Parameters:
            utc_start (datetime): The start of the time range for which temperature data
                needs to be retrieved, specified in UTC.
            utc_end (datetime): The end of the time range for which temperature data
                needs to be retrieved, specified in UTC.
            frequency (Frequency): The frequency of the requested temperature data.
                Can either be daily or hourly.

        Returns:
            list[GenericResponseObject]: A list of GenericResponseObject containing the
                retrieved temperature data aligned with the specified request parameters.

        Raises:
            NotImplementedError: Raised if the provided frequency is not supported.
                Only daily and hourly frequencies are implemented for temperature requests.
        """
        if frequency == self.Frequency.daily:

            request = self.__create_dwd_historical_observation_request(parameters=self.Params.temperature,
                                                                       dataset=self.Dataset.climate_summary,
                                                                       frequency=self.Frequency.daily,
                                                                       start_date=utc_start, end_date=utc_end)
            return df_to_generic_response_object(request.values.all().df.to_pandas(), "temperature_air")
        elif frequency == self.Frequency.hourly or frequency == self.Frequency.ten_minutes:
            request = self.__create_dwd_historical_observation_request(parameters=self.Params.temperature,
                                                                       dataset=self.Dataset.temperature_air,
                                                                       frequency=frequency, start_date=utc_start,
                                                                       end_date=utc_end)
            return df_to_generic_response_object(request.values.all().df.to_pandas(), "temperature_air")
        else:
            raise NotImplementedError("Only daily and hourly requests are supported for temperature yet.")

    def get_fog_count(self, utc_start: datetime, utc_end: datetime, frequency: Frequency) -> list[
        GenericResponseObject]:
        """
        Fetches the fog count data within a specified date range and at a specified frequency
        (monthly or yearly) from the DWD observation dataset. The method constructs an
        observation request based on the parameters and processes the retrieved data into a
        list of GenericResponseObject instances. For now, only monthly and yearly frequency
        requests are supported; any other frequency will result in a NotImplementedError being raised.

        Args:
            utc_start (datetime): The starting datetime from which fog count data is requested.
            utc_end (datetime): The ending datetime until which fog count data is requested.
            frequency (Frequency): The frequency of data aggregation, supports only
                Frequency.monthly or Frequency.yearly.

        Returns:
            list[GenericResponseObject]: A list containing the processed fog count aggregated
            as per the requested frequency.

        Raises:
            NotImplementedError: If frequency is not monthly or yearly.
        """
        if frequency == self.Frequency.monthly or frequency == self.Frequency.yearly:
            request = self.__create_dwd_historical_observation_request(self.Params.fog_count,
                                                                       self.Dataset.weather_phenomena, frequency,
                                                                       utc_start, utc_end)
            return df_to_generic_response_object(request.values.all().df.to_pandas(), "days_with_fog")
        else:
            raise NotImplementedError("Only monthly and yearly requests are supported for fog_count yet.")

    def __create_dwd_historical_observation_request(self, parameters: Params, dataset: Dataset, frequency: Frequency,
                                                    start_date: datetime, end_date: datetime, ):
        """
        Creates a historical observation request for the DWD service.

        Parameters:
            parameters (Params): The parameters defining the type of observations to be requested.
            dataset (Dataset): The dataset to be used for the historical observation request.
            frequency (Frequency): The frequency of the requested historical data.
            start_date (datetime): The starting date for the observation period.
            end_date (datetime): The ending date for the observation period.

        Returns:
            DwdObservationRequest: A request object configured with specified parameters, filtered by station ID.
        """
        data = DwdObservationRequest(parameters=[frequency.value, dataset.value, parameters.value],
                                     start_date=start_date.strftime(self.date_str_format),
                                     end_date=end_date.strftime(self.date_str_format),
                                     settings=self.settings, ).filter_by_station_id(station_id=(self.station_id,))
        return data

    def __create_dwd_live_observation_request(self, dataset: Dataset, frequency: Frequency):
        """
        Creates a live observation request for the DWD service.

        This method builds and configures a DwdObservationRequest, which is narrowed
        down to the desired station ID. The request focuses on fetching live
        observation data based on the provided parameters, dataset, and frequency.
        It also applies predefined settings and periods to the request.

        Arguments:
            dataset (Dataset): The dataset specifying the kind of data repository
            the observations belong to, such as climate or weather data.

            frequency (Frequency): The frequency or temporal resolution of the live
            observation data, such as hourly or ten-minute intervals.

        Returns:
            DwdObservationRequest: A filtered observation request, scoped to the
            specified station ID with configured parameters, dataset, and frequency.
        """
        return DwdObservationRequest(parameters=[frequency.value, dataset.value], periods=Period.NOW.value,
                                     settings=self.settings, ).filter_by_station_id(station_id=(self.station_id,))

    def get_real_time_data(self):
        """
        Gets real-time weather data from the DWD API.
        """
        result: list = []
        # get wind direction and speed
        request = self.__create_dwd_live_observation_request(dataset=self.Dataset.wind,
                                                             frequency=self.Frequency.ten_minutes)
        wind_data = request.values.all().df.to_pandas()
        latest_wind_direction = wind_data[wind_data["parameter"] == "wind_direction"].nlargest(1, "date")
        latest_wind_speed = wind_data[wind_data["parameter"] == "wind_speed"].nlargest(1, "date")
        result.append(GenericResponseObject(
            name="wind_direction",
            date=latest_wind_direction["date"].values[0].item(),
            value=latest_wind_direction["value"].values[0],
            quality=latest_wind_direction["quality"].values[0],
        ))
        result.append(GenericResponseObject(
            name="wind_speed",
            date=latest_wind_speed["date"].values[0].item(),
            value=latest_wind_speed["value"].values[0],
            quality=latest_wind_speed["quality"].values[0],
        ))

        # get precipitation indicator
        request = self.__create_dwd_live_observation_request(dataset=self.Dataset.precipitation,
                                                             frequency=self.Frequency.ten_minutes)
        precipitation_data = request.values.all().df.to_pandas()
        precipitation_indicator = precipitation_data[precipitation_data["parameter"] == "precipitation_index"].nlargest(1, "date")
        precipitation_indicator_value = 0.0 if precipitation_indicator["value"].values[0] == 0.0 else 1.0
        result.append(GenericResponseObject(
            name="precipitation_indicator",
            date=precipitation_indicator["date"].values[0].item(),
            value=precipitation_indicator_value,
            quality=precipitation_indicator["quality"].values[0],
        ))

        # get humidity, air-pressure and temperature
        request = self.__create_dwd_live_observation_request(dataset=self.Dataset.temperature_air,
                                                             frequency=self.Frequency.ten_minutes)
        climate_data = request.values.all().df.to_pandas()
        humidity = climate_data[climate_data["parameter"] == "humidity"].nlargest(1, "date")
        air_pressure = climate_data[climate_data["parameter"] == "pressure_air_site"].nlargest(1, "date")
        temperature = climate_data[climate_data["parameter"] == "temperature_air_mean_2m"].nlargest(1, "date")
        result.append(GenericResponseObject(
            name="humidity",
            date=humidity["date"].values[0].item(),
            value=humidity["value"].values[0],
            quality=humidity["quality"].values[0],
        ))
        result.append(GenericResponseObject(
            name="air_pressure",
            date=air_pressure["date"].values[0].item(),
            value=air_pressure["value"].values[0],
            quality=air_pressure["quality"].values[0],
        ))
        result.append(GenericResponseObject(
            name="temperature",
            date=temperature["date"].values[0].item(),
            value=temperature["value"].values[0],
            quality=temperature["quality"].values[0],
        ))

        return result