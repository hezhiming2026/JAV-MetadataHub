from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from jav_metadatahub.api.dependencies import get_db_session
from jav_metadatahub.api.schemas import ListResponse, TagResponse
from jav_metadatahub.repositories import TagRepository

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=ListResponse[TagResponse])
def list_tags(
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListResponse[TagResponse]:
    items, total = TagRepository(session).list_page(limit=limit, offset=offset)
    data = [TagResponse.model_validate(item) for item in items]
    return ListResponse[TagResponse](data=data, limit=limit, offset=offset, total=total)


@router.get("/{tag_id}", response_model=TagResponse)
def get_tag(
    tag_id: int,
    session: Annotated[Session, Depends(get_db_session)],
) -> TagResponse:
    item = TagRepository(session).get_by_id(tag_id)
    if item is None:
        raise HTTPException(status_code=404, detail="tag not found")
    return TagResponse.model_validate(item)
