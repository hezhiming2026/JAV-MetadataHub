from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from jav_metadatahub.api.dependencies import get_db_session
from jav_metadatahub.api.schemas import ListResponse, ObservationResponse
from jav_metadatahub.repositories import FieldObservationRepository
from jav_metadatahub.services.observations import FieldObservationService

router = APIRouter(prefix="/observations", tags=["observations"])


@router.get("", response_model=ListResponse[ObservationResponse])
def list_observations(
    session: Annotated[Session, Depends(get_db_session)],
    entity_type: str | None = None,
    entity_id: Annotated[int | None, Query(ge=1)] = None,
    field: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListResponse[ObservationResponse]:
    service = FieldObservationService(FieldObservationRepository(session))
    items, total = service.list_observations(
        entity_type=entity_type,
        entity_id=entity_id,
        field_name=field,
        limit=limit,
        offset=offset,
    )
    data = [ObservationResponse.model_validate(item) for item in items]
    return ListResponse[ObservationResponse](data=data, limit=limit, offset=offset, total=total)
