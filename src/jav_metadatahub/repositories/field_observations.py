from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import bindparam, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from jav_metadatahub.db.models import FieldObservation

type ObservationValue = dict[str, Any] | list[Any] | str | int | float | bool | None

ALLOWED_OBSERVATION_STATUSES = frozenset({"active", "rejected", "superseded"})


def _clean_required_string(value: str | None, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")

    return cleaned


def _clean_optional_string(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _clean_required_string(value, field_name)


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


def _normalize_optional_status(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_status(value)


def _field_value_predicate(field_value: ObservationValue) -> Any:
    if field_value is None:
        return FieldObservation.field_value.is_(None)
    return FieldObservation.field_value == bindparam(
        "field_value",
        field_value,
        type_=JSONB,
    )


class FieldObservationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        entity_type: str | None,
        entity_id: int,
        field_name: str | None,
        field_value: ObservationValue,
        field_value_text: str | None,
        source: str | None,
        source_record_id: int | None = None,
        confidence: Decimal | str | int | float = Decimal("0.000"),
        observation_status: str | None = "active",
        rejection_reason: str | None = None,
        observed_at: datetime | None = None,
    ) -> FieldObservation:
        record_values: dict[str, Any] = {
            "entity_type": _clean_required_string(entity_type, "entity_type"),
            "entity_id": _validate_positive_int(entity_id, "entity_id"),
            "field_name": _clean_required_string(field_name, "field_name"),
            "field_value": field_value,
            "field_value_text": field_value_text,
            "source": _clean_required_string(source, "source"),
            "source_record_id": _validate_optional_positive_int(
                source_record_id, "source_record_id"
            ),
            "confidence": _normalize_confidence(confidence),
            "observation_status": _normalize_status(observation_status),
            "rejection_reason": rejection_reason,
        }
        if observed_at is not None:
            record_values["observed_at"] = observed_at

        observation = FieldObservation(**record_values)
        self.session.add(observation)
        self.session.flush()
        return observation

    def get_by_id(self, observation_id: int) -> FieldObservation | None:
        return self.session.get(FieldObservation, observation_id)

    def list_for_entity(
        self,
        entity_type: str | None,
        entity_id: int,
        *,
        field_name: str | None = None,
        source: str | None = None,
        observation_status: str | None = None,
    ) -> list[FieldObservation]:
        statement = select(FieldObservation).where(
            FieldObservation.entity_type == _clean_required_string(entity_type, "entity_type"),
            FieldObservation.entity_id == _validate_positive_int(entity_id, "entity_id"),
        )

        cleaned_field_name = _clean_optional_string(field_name, "field_name")
        cleaned_source = _clean_optional_string(source, "source")
        cleaned_status = _normalize_optional_status(observation_status)

        if cleaned_field_name is not None:
            statement = statement.where(FieldObservation.field_name == cleaned_field_name)
        if cleaned_source is not None:
            statement = statement.where(FieldObservation.source == cleaned_source)
        if cleaned_status is not None:
            statement = statement.where(FieldObservation.observation_status == cleaned_status)

        statement = statement.order_by(
            FieldObservation.observed_at.desc(),
            FieldObservation.id.desc(),
        )
        return list(self.session.scalars(statement).all())

    def list_for_field(
        self,
        entity_type: str | None,
        entity_id: int,
        field_name: str | None,
        *,
        source: str | None = None,
        observation_status: str | None = None,
    ) -> list[FieldObservation]:
        return self.list_for_entity(
            entity_type,
            entity_id,
            field_name=_clean_required_string(field_name, "field_name"),
            source=source,
            observation_status=observation_status,
        )

    def list_by_source(
        self,
        source: str | None,
        *,
        field_name: str | None = None,
        observation_status: str | None = None,
    ) -> list[FieldObservation]:
        statement = select(FieldObservation).where(
            FieldObservation.source == _clean_required_string(source, "source")
        )

        cleaned_field_name = _clean_optional_string(field_name, "field_name")
        cleaned_status = _normalize_optional_status(observation_status)

        if cleaned_field_name is not None:
            statement = statement.where(FieldObservation.field_name == cleaned_field_name)
        if cleaned_status is not None:
            statement = statement.where(FieldObservation.observation_status == cleaned_status)

        statement = statement.order_by(
            FieldObservation.observed_at.desc(),
            FieldObservation.id.desc(),
        )
        return list(self.session.scalars(statement).all())

    def find_duplicate(
        self,
        *,
        entity_type: str | None,
        entity_id: int,
        field_name: str | None,
        source: str | None,
        source_record_id: int | None,
        field_value: ObservationValue,
    ) -> FieldObservation | None:
        cleaned_source_record_id = _validate_optional_positive_int(
            source_record_id, "source_record_id"
        )
        statement = select(FieldObservation).where(
            FieldObservation.entity_type == _clean_required_string(entity_type, "entity_type"),
            FieldObservation.entity_id == _validate_positive_int(entity_id, "entity_id"),
            FieldObservation.field_name == _clean_required_string(field_name, "field_name"),
            FieldObservation.source == _clean_required_string(source, "source"),
            _field_value_predicate(field_value),
            FieldObservation.observation_status == "active",
        )

        if cleaned_source_record_id is None:
            statement = statement.where(FieldObservation.source_record_id.is_(None))
        else:
            statement = statement.where(
                FieldObservation.source_record_id == cleaned_source_record_id
            )

        statement = statement.order_by(
            FieldObservation.observed_at.desc(),
            FieldObservation.id.desc(),
        ).limit(1)
        return self.session.scalar(statement)

    def set_status(
        self,
        observation_id: int,
        observation_status: str | None,
        *,
        rejection_reason: str | None = None,
    ) -> FieldObservation | None:
        cleaned_status = _normalize_status(observation_status)
        observation = self.session.get(FieldObservation, observation_id)
        if observation is None:
            return None

        observation.observation_status = cleaned_status
        observation.rejection_reason = rejection_reason
        self.session.flush()
        return observation
