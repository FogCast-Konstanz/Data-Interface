from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

@dataclass(init=True)
class GenericResponseObject:
    """
    GenericResponseObject is a generic representation of the data, received from the DWD API.
    Attributes:
        date (datetime.date): The date of the measured occurrence.
        value (Decimal): The measurement of the occurrence.
        quality (Decimal): The quality rating of the measurement.
    """
    date: datetime.date
    value: Decimal
    quality: Decimal