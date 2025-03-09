from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ..decorators import to_json


@dataclass(init=True)
@to_json.json_serializer
class GenericResponseObject:
    """
    GenericResponseObject is a generic representation of the data, received from the DWD API.
    Attributes:
        name (str): The name of the measured occurrence.
        date (datetime.date): The date of the measured occurrence.
        value (Decimal): The measurement of the occurrence.
        quality (Decimal): The quality rating of the measurement.
    """
    name: str
    date: datetime
    value: Decimal
    quality: Decimal
