from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from jav_metadatahub.api.dependencies import get_db_session
from jav_metadatahub.api.schemas import ListResponse, SeriesResponse
from jav_metadatahub.repositories import SeriesRepository

router = APIRouter(prefix="/series", tags=["series"])


@router.get("", response_model=ListResponse[SeriesResponse])
def list_series(
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListResponse[SeriesResponse]:
    items, total = SeriesRepository(session).list_page(limit=limit, offset=offset)
    data = [SeriesResponse.model_validate(item) for item in items]
    return ListResponse[SeriesResponse](data=data, limit=limit, offset=offset, total=total)


@router.get("/{series_id}", response_model=SeriesResponse)
def get_series(
    series_id: int,
    session: Annotated[Session, Depends(get_db_session)],
) -> SeriesResponse:
    item = SeriesRepository(session).get_by_id(series_id)
    if item is None:
        raise HTTPException(status_code=404, detail="series not found")
    return SeriesResponse.model_validate(item)
