from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

type JsonPayload = dict[str, Any] | list[Any] | None


class SourceRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    source_key: str
    source_url: str | None
    record_type: str
    payload_type: str
    raw_json: JsonPayload
    raw_html: str | None
    raw_text: str | None
    http_status: int | None
    fetch_status: str
    error_message: str | None
    parser_version: str | None
    checksum: str | None
    collector_run_id: int | None
    fetched_at: datetime
    created_at: datetime
