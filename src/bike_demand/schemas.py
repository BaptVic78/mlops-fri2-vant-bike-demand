"""Request contract for the Lab 4 bike-demand prediction API."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

NormalizedWeather = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class PredictionRequest(BaseModel):
    """The twelve training features, without target columns or extra fields.

    Strict validation rejects coerced strings and booleans. Weather values use
    the dataset's normalized scale, rather than Celsius or percentages.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    season: int = Field(ge=1, le=4)
    yr: int = Field(ge=0, le=1)
    mnth: int = Field(ge=1, le=12)
    hr: int = Field(ge=0, le=23)
    holiday: int = Field(ge=0, le=1)
    weekday: int = Field(ge=0, le=6)
    workingday: int = Field(ge=0, le=1)
    weathersit: int = Field(ge=1, le=4)
    temp: NormalizedWeather
    atemp: NormalizedWeather
    hum: NormalizedWeather
    windspeed: NormalizedWeather
