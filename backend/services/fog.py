import pandas as pd


def add_fog(df: pd.DataFrame) -> pd.DataFrame:
    if "weather_code" in df.columns:
        return add_fog_based_on_weather_code(df)

    required_columns = ["temperature_2m", "dew_point_2m",
                        "relative_humidity_2m", "wind_speed_10m"]

    if all(col in df.columns for col in required_columns):
        return add_fog_based_on_conditions(df)

    return df


def add_fog_based_on_conditions(df: pd.DataFrame) -> pd.DataFrame:
    def is_fog(temp, dew_point, humidity, wind_speed):
        return (temp - dew_point <= 2) and (humidity >= 90) and (wind_speed <= 5)

    df["fog"] = df.apply(
        lambda row: is_fog(row["temperature_2m"], row["dew_point_2m"], row["relative_humidity_2m"], row["wind_speed_10m"]), axis=1
    )
    return df


def add_fog_based_on_weather_code(df: pd.DataFrame) -> pd.DataFrame:
    df["fog"] = df.apply(lambda row: 1 if row["weather_code"] in [
                         45, 48] else 0, axis=1)
    return df
