from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class WorkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code_original: str | None
    code_norm: str | None
    code_prefix: str | None
    code_number: str | None
    title_ja: str | None
    title_en: str | None
    title_zh: str | None
    release_date: date | None
    runtime_minutes: int | None
    censor_type: str
    work_type: str
    primary_source: str | None
    confidence: Decimal
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PersonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    canonical_name: str
    name_ja: str | None
    name_en: str | None
    name_zh: str | None
    name_kana: str | None
    person_type: str
    gender_role: str
    primary_source: str | None
    confidence: Decimal
    is_active: bool | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_norm: str | None
    company_type: str
    primary_source: str | None
    confidence: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime


class SeriesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_norm: str | None
    primary_source: str | None
    confidence: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_norm: str | None
    tag_type: str
    language: str
    source: str
    confidence: Decimal
    created_at: datetime
    updated_at: datetime
