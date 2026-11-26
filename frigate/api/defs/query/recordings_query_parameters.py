from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema


class MediaRecordingsSummaryQueryParams(BaseModel):
    timezone: str = "utc"
    cameras: str | None = "all"


class MediaRecordingsAvailabilityQueryParams(BaseModel):
    cameras: str = "all"
    before: float | SkipJsonSchema[None] = None
    after: float | SkipJsonSchema[None] = None
    scale: int = Field(default=30, gt=0)


class RecordingsDeleteQueryParams(BaseModel):
    keep: str | None = None
    cameras: str | None = "all"
