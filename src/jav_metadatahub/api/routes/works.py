from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from jav_metadatahub.api.dependencies import get_db_session
from jav_metadatahub.api.schemas import ListResponse, WorkResponse
from jav_metadatahub.repositories import WorkRepository

router = APIRouter(prefix="/works", tags=["works"])


@router.get("", response_model=ListResponse[WorkResponse])
def list_works(
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListResponse[WorkResponse]:
    items, total = WorkRepository(session).list_page(limit=limit, offset=offset)
    data = [WorkResponse.model_validate(item) for item in items]
    return ListResponse[WorkResponse](data=data, limit=limit, offset=offset, total=total)


@router.get("/{work_id}", response_model=WorkResponse)
def get_work(
    work_id: int,
    session: Annotated[Session, Depends(get_db_session)],
) -> WorkResponse:
    item = WorkRepository(session).get_by_id(work_id)
    if item is None:
        raise HTTPException(status_code=404, detail="work not found")
    return WorkResponse.model_validate(item)
