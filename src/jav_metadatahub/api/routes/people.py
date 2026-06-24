from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from jav_metadatahub.api.dependencies import get_db_session
from jav_metadatahub.api.schemas import ListResponse, PersonResponse
from jav_metadatahub.repositories import PersonRepository

router = APIRouter(prefix="/people", tags=["people"])


@router.get("", response_model=ListResponse[PersonResponse])
def list_people(
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListResponse[PersonResponse]:
    items, total = PersonRepository(session).list_page(limit=limit, offset=offset)
    data = [PersonResponse.model_validate(item) for item in items]
    return ListResponse[PersonResponse](data=data, limit=limit, offset=offset, total=total)


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(
    person_id: int,
    session: Annotated[Session, Depends(get_db_session)],
) -> PersonResponse:
    item = PersonRepository(session).get_by_id(person_id)
    if item is None:
        raise HTTPException(status_code=404, detail="person not found")
    return PersonResponse.model_validate(item)
