import requests
from .objects.GenericResponseObject import GenericResponseObject
from enum import Enum
from datetime import datetime
from dateutil import parser
import pytz

def to_generic_response(data: list[dict]) -> list[GenericResponseObject]:
    """
    Convert a list of dictionary data entries into a list of GenericResponseObject instances.

    This function iterates over a list of dictionaries, extracting specific information
    from each dictionary element and creating a new GenericResponseObject instance. It
    structures the data in a normalized format for further use.

    Arguments:
        data: list[dict]
            A list of dictionary entries, where each dictionary contains a "timestamp",
            "value", and possibly other keys.

    Returns:
        list[GenericResponseObject]
            A list of GenericResponseObject instances, each initialized with data extracted
            from the corresponding dictionary entry.
    """
    result: list[GenericResponseObject] = []
    for entry in data:
        timestamp_str = entry["timestamp"]
        dt_local = parser.isoparse(timestamp_str)
        dt_utc = dt_local.astimezone(pytz.UTC)

        result.append(GenericResponseObject(
            name="water_level",
            date=dt_utc,
            value=entry["value"],
            unit="cm",
            quality=2.0
        ))
    return result

class PegelOnline:
    """
    Represents a system to interact with Pegel Online services.

    This class is designed to retrieve and process data from Pegel Online, a platform
    that provides water level and related hydrological information. The class includes
    methods for fetching and parsing data.
    """

    class Period(Enum):
        """
        Represents ISO_8601 periods.
        """
        last_24_hours = "P1D"
        last_31_days = "P31D"

    def __init__(self, station_uuid="aa9179c1-17ef-4c61-a48a-74193fa7bfdf"):
        self.base_url = f"https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/{station_uuid}/W/measurements.json?"
        self.station_uuid = station_uuid

    def get_water_level_measurements(self, period: Period):
        """
        Fetches water level measurement data for a specified time period.

        This method retrieves a list of measurement records corresponding to the given
        time period.

        Args:
            period (str): The time period for which measurements are to be retrieved.
                          It should be specified in a format recognized by the system.

        Returns:
            list: A list of measurement records for the specified time period.

        Raises:
            ValueError: If the provided period format is incorrect or unrecognized.
        """
        url = self.base_url + f"start={period.value}"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return to_generic_response(response.json())
        else:
            raise ValueError(f"Failed to retrieve data for period {period}. Status code: {response.status_code}")