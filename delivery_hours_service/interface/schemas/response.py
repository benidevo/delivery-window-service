from enum import Enum

from pydantic import BaseModel, Field


class Weekday(str, Enum):
    """Days of the week."""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class TimeRange(BaseModel):
    """A time range with start and end times in HH:MM format."""

    start: str = Field(
        ..., examples=["08:00"], description="Start time in HH:MM format"
    )
    end: str = Field(..., examples=["20:00"], description="End time in HH:MM format")


class DeliveryHoursResponse(BaseModel):
    """
    Response schema for the delivery hours endpoint.

    Contains the calculated delivery hours for a venue.
    """

    delivery_hours: dict[str, str] = Field(
        ..., description="Available delivery hours for each day of the week"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "delivery_hours": {
                    "Monday": "09-12, 13:30-22",
                    "Tuesday": "16:45-02",
                    "Wednesday": "Closed",
                    "Thursday": "Closed",
                    "Friday": "Closed",
                    "Saturday": "Closed",
                    "Sunday": "Closed",
                }
            }
        }
    }


class ErrorResponse(BaseModel):
    """
    Standard error response model.

    Used for all error responses from the API to ensure a consistent format.
    """

    detail: str = Field(..., description="Human-readable error message")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"detail": "Service temporarily unavailable"},
                {"detail": "The requested venue was not found"},
                {"detail": "An error occurred while processing your request"},
            ]
        }
    }
