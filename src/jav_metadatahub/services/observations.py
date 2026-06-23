from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from jav_metadatahub.db.models import FieldObservation
from jav_metadatahub.repositories.field_observations import (
    ALLOWED_OBSERVATION_STATUSES,
    FieldObservationRepository,
    ObservationValue,
)


def _clean_required_string(value: str | None, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")

    return cleaned


def _validate_positive_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _validate_optional_positive_int(value: int | None, field_name: str) -> int | None:
    if value is None:
        return None
    return _validate_positive_int(value, field_name)


def _normalize_confidence(value: Decimal | str | int | float) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("confidence must be between 0 and 1")

    try:
        confidence = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("confidence must be between 0 and 1") from exc

    if confidence < Decimal("0") or confidence > Decimal("1"):
        raise ValueError("confidence must be between 0 and 1")

    return confidence


def _normalize_status(value: str | None) -> str:
    status = _clean_required_string(value, "observation_status")
    if status not in ALLOWED_OBSERVATION_STATUSES:
        raise ValueError("observation_status must be active, rejected, or superseded")
    return status


def _field_value_text(value: ObservationValue) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except TypeError as exc:
        raise TypeError("field_value must be JSON-compatible") from exc
    except ValueError as exc:
        raise ValueError("field_value must be JSON-compatible") from exc


class FieldObservationService:
    def __init__(self, repository: FieldObservationRepository) -> None:
        self.repository = repository

    def record_observation(
        self,
        *,
        entity_type: str | None,
        entity_id: int,
        field_name: str | None,
        field_value: ObservationValue,
        source: str | None,
        source_record_id: int | None = None,
        confidence: Decimal | str | int | float = Decimal("0.000"),
        observation_status: str | None = "active",
        rejection_reason: str | None = None,
        observed_at: datetime | None = None,
        idempotent: bool = True,
    ) -> FieldObservation:
        cleaned_entity_type = _clean_required_string(entity_type, "entity_type")
        cleaned_entity_id = _validate_positive_int(entity_id, "entity_id")
        cleaned_field_name = _clean_required_string(field_name, "field_name")
        cleaned_source = _clean_required_string(source, "source")
        cleaned_source_record_id = _validate_optional_positive_int(
            source_record_id, "source_record_id"
        )
        cleaned_confidence = _normalize_confidence(confidence)
        cleaned_status = _normalize_status(observation_status)
        value_text = _field_value_text(field_value)

        if idempotent and cleaned_status == "active":
            existing = self.repository.find_duplicate(
                entity_type=cleaned_entity_type,
                entity_id=cleaned_entity_id,
                field_name=cleaned_field_name,
                source=cleaned_source,
                source_record_id=cleaned_source_record_id,
                field_value=field_value,
            )
            if existing is not None:
                return existing

        return self.repository.create(
            entity_type=cleaned_entity_type,
            entity_id=cleaned_entity_id,
            field_name=cleaned_field_name,
            field_value=field_value,
            field_value_text=value_text,
            source=cleaned_source,
            source_record_id=cleaned_source_record_id,
            confidence=cleaned_confidence,
            observation_status=cleaned_status,
            rejection_reason=rejection_reason,
            observed_at=observed_at,
        )
