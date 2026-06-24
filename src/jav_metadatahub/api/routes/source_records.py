from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from jav_metadatahub.api.dependencies import get_db_session
from jav_metadatahub.api.schemas import ListResponse, SourceRecordResponse
from jav_metadatahub.repositories import SourceRecordRepository

router = APIRouter(prefix="/source-records", tags=["source-records"])


@router.get("", response_model=ListResponse[SourceRecordResponse])
def list_source_records(
    session: Annotated[Session, Depends(get_db_session)],
    source: str | None = None,
    record_type: str | None = None,
    fetch_status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListResponse[SourceRecordResponse]:
    items, total = SourceRecordRepository(session).list_page(
        limit=limit,
        offset=offset,
        source=source,
        record_type=record_type,
        fetch_status=fetch_status,
    )
    data = [SourceRecordResponse.model_validate(item) for item in items]
    return ListResponse[SourceRecordResponse](data=data, limit=limit, offset=offset, total=total)


@router.get("/{record_id}", response_model=SourceRecordResponse)
def get_source_record(
    record_id: int,
    session: Annotated[Session, Depends(get_db_session)],
) -> SourceRecordResponse:
    item = SourceRecordRepository(session).get_by_id(record_id)
    if item is None:
        raise HTTPException(status_code=404, detail="source record not found")
    return SourceRecordResponse.model_validate(item)
