from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ValueType = Literal["string", "number", "integer", "boolean", "object", "array", "any"]
TakeMode = Literal["all", "first", "latest"]
SortOrder = Literal["asc", "desc"]


class ArraySelection(BaseModel):
    filter: dict[str, Any] | None = None
    sort_by: str | None = None
    order: SortOrder = "asc"
    take: TakeMode = "all"
    time_from: str | None = None
    time_to: str | None = None

    @model_validator(mode="after")
    def validate_selection(self) -> "ArraySelection":
        if self.take in {"first", "latest"} and not self.sort_by:
            raise ValueError("sort_by is required when take is first or latest")
        if self.time_from and self.time_to:
            self._compare_boundaries()
        if (self.time_from or self.time_to) and not self.sort_by:
            raise ValueError("sort_by is required for a time window")
        return self

    def _compare_boundaries(self) -> None:
        try:
            if _parse_order_value(self.time_from) > _parse_order_value(self.time_to):
                raise ValueError("time_from must not be after time_to")
        except (TypeError, ValueError) as exc:
            if str(exc) == "time_from must not be after time_to":
                raise


class ExtractionField(BaseModel):
    alias: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, pattern=r"^\$")
    type: ValueType = "any"
    required: bool = False
    default: Any = None
    array: ArraySelection | None = None


class ExtractionGroup(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=255)
    fields: list[ExtractionField]
    required: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_required_aliases(self) -> "ExtractionGroup":
        aliases = {field.alias for field in self.fields}
        if len(aliases) != len(self.fields):
            raise ValueError("field aliases must be unique within a group")
        unknown = set(self.required) - aliases
        if unknown:
            raise ValueError(f"required aliases are not defined: {sorted(unknown)}")
        return self


class ExtractionConfig(BaseModel):
    groups: list[ExtractionGroup]


class SufficiencyResult(BaseModel):
    status: Literal["sufficient", "insufficient"]
    missing_required: list[str] = Field(default_factory=list)
    error_count: int = 0


class ExtractionPreview(BaseModel):
    groups: dict[str, dict[str, Any]]
    missing: dict[str, list[str]]
    sufficiency: dict[str, SufficiencyResult]
    errors: dict[str, dict[str, str]]


class ExtractionPreviewRequest(BaseModel):
    payload: dict[str, Any] | None = None
    sample_json: dict[str, Any] | None = None
    config: ExtractionConfig

    @model_validator(mode="after")
    def validate_payload(self) -> "ExtractionPreviewRequest":
        if self.payload is None and self.sample_json is None:
            raise ValueError("payload or sample_json is required")
        return self

    def resolved_payload(self) -> dict[str, Any]:
        return self.payload if self.payload is not None else self.sample_json or {}


def _parse_order_value(value: Any) -> datetime | float | str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
    raise TypeError("time values must be ISO dates, numbers, or strings")
