from typing import get_args, get_origin
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal


def custom_value_serialize(value, output_type):
    try:
        if value is None:
            return None
        if output_type is datetime:
            return value.strftime('%Y-%m-%d %H:%M:%S')
        if output_type is date:
            return value.isoformat()
        if output_type is UUID:
            return str(value)
        if output_type is Decimal:
            return str(value)
        if output_type is int:
            return int(value)
        return value
    except Exception as e:
        raise ValueError(f"Error serializing value '{value}' of type '{output_type}': {e}")


def json_serializer(cls):
    """
    json_serializer(cls)

    Annotates a class with a `to_json` method for serialization, transforming the
    class's attributes into a dictionary format while accounting for specific custom
    serialization logic. This function dynamically adds the `to_json` method via
    `setattr`.

    Parameters:
        cls (type): The class to which the `to_json` method will be added.

    Returns:
        type: The input class with an added `to_json` method.


    to_json(self)

    Serializes an instance of the class into a dictionary, considering special
    treatment for specific types such as lists or objects with their own `to_json`
    methods. Handles both primitive and complex data types with optional custom
    serialization logic.

    Attributes:
        __annotations__ (dict): A dictionary of attribute names and their respective
        types, as defined in the class being serialized.

    Raises:
        ValueError: If there is an error processing an attribute, indicating either a
        mismatched type or missing value for a specific field.

    Returns:
        dict: A dictionary where keys are attribute names and values are their
        serialized representations.
    """

    def to_json(self):
        result = {}
        for field_key, field_type in self.__annotations__.items():
            try:
                field = getattr(self, field_key)

                # list processing
                if get_origin(field_type) is list:
                    # identify list object type
                    type_args = get_args(field_type)
                    if type_args:
                        element_type = type_args[0]
                        # check if object supports to_json()
                        if hasattr(element_type, "to_json"):
                            value = None if field is None else [entry.to_json() for entry in field]
                        else:
                            value = None if field is None else [custom_value_serialize(entry, element_type) for entry in
                                                                field]
                    else:
                        value = field
                # uses own to_json implementation
                elif hasattr(field, "to_json"):
                    value = field.to_json()
                # processing of primitive datatypes
                else:
                    value = custom_value_serialize(field, field_type)

                result[field_key] = value
            except AttributeError as e:
                raise ValueError(f"Error occurred while processing '{field_key}'") from e
            except Exception as e:
                raise ValueError(f"Error occurred while processing '{field_key}' with value '{field}'") from e

        return result

    setattr(cls, "to_json", to_json)
    return cls