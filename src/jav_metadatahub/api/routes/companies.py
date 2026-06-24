from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from jav_metadatahub.api.dependencies import get_db_session
from jav_metadatahub.api.schemas import CompanyResponse, ListResponse
from jav_metadatahub.repositories import CompanyRepository

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=ListResponse[CompanyResponse])
def list_companies(
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListResponse[CompanyResponse]:
    items, total = CompanyRepository(session).list_page(limit=limit, offset=offset)
    data = [CompanyResponse.model_validate(item) for item in items]
    return ListResponse[CompanyResponse](data=data, limit=limit, offset=offset, total=total)


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    session: Annotated[Session, Depends(get_db_session)],
) -> CompanyResponse:
    item = CompanyRepository(session).get_by_id(company_id)
    if item is None:
        raise HTTPException(status_code=404, detail="company not found")
    return CompanyResponse.model_validate(item)
