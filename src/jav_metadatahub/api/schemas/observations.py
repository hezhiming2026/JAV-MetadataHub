from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

type JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class ObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    field_name: str
    field_value: JsonValue
    field_value_text: str | None
    source: str
    source_record_id: int | None
    confidence: Decimal
    observation_status: str
    rejection_reason: str | None
    observed_at: datetime
    created_at: datetime
