from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from jav_metadatahub.db.models import FieldObservation, SourceRecord, Work
from jav_metadatahub.normalizers import normalize_code
from jav_metadatahub.repositories import (
    FieldObservationRepository,
    SourceRecordRepository,
    WorkExternalIdRepository,
    WorkRepository,
)

SOURCE = "fanza"
ENTITY_TYPE = "fanza_work"
PROMOTION_CONFIDENCE = Decimal("0.950")
PRIMARY_ID_TYPES = ("content_id", "product_id", "dvd_id")
WORK_FIELD_NAMES = (
    "code_original",
    "code_norm",
    "code_prefix",
    "code_number",
    "title_ja",
    "release_date",
    "runtime_minutes",
)

type ObservationValue = dict[str, Any] | list[Any] | str | int | float | bool | None


@dataclass(frozen=True)
class WorkPromotionError:
    entity_id: int
    error_class: str
    error_message: str


@dataclass(frozen=True)
class WorkPromotionResult:
    scanned_count: int = 0
    promoted_count: int = 0
    skipped_count: int = 0
    duplicate_count: int = 0
    failed_count: int = 0
    created_work_count: int = 0
    created_external_id_count: int = 0
    updated_work_count: int = 0
    conflict_count: int = 0
    invalid_field_count: int = 0
    errors: list[WorkPromotionError] = field(default_factory=list)

    @property
    def errors_count(self) -> int:
        return len(self.errors)


@dataclass(frozen=True)
class PromotionIdentity:
    id_type: str
    external_id: str


@dataclass(frozen=True)
class PromotionCandidate:
    entity_id: int
    source_record: SourceRecord
    work_values: dict[str, object]
    identities: list[PromotionIdentity]
    external_url: str | None
    confidence: Decimal
    invalid_field_count: int


@dataclass
class _MutableResult:
    scanned_count: int = 0
    promoted_count: int = 0
    skipped_count: int = 0
    duplicate_count: int = 0
    failed_count: int = 0
    created_work_count: int = 0
    created_external_id_count: int = 0
    updated_work_count: int = 0
    conflict_count: int = 0
    invalid_field_count: int = 0
    errors: list[WorkPromotionError] = field(default_factory=list)

    def freeze(self) -> WorkPromotionResult:
        return WorkPromotionResult(
            scanned_count=self.scanned_count,
            promoted_count=self.promoted_count,
            skipped_count=self.skipped_count,
            duplicate_count=self.duplicate_count,
            failed_count=self.failed_count,
            created_work_count=self.created_work_count,
            created_external_id_count=self.created_external_id_count,
            updated_work_count=self.updated_work_count,
            conflict_count=self.conflict_count,
            invalid_field_count=self.invalid_field_count,
            errors=self.errors,
        )


class WorkPromotionService:
    def __init__(
        self,
        *,
        field_observations: FieldObservationRepository,
        source_records: SourceRecordRepository,
        works: WorkRepository,
        work_external_ids: WorkExternalIdRepository,
    ) -> None:
        self.field_observations = field_observations
        self.source_records = source_records
        self.works = works
        self.work_external_ids = work_external_ids

    def promote_fanza_works(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        dry_run: bool = False,
        continue_on_error: bool = True,
    ) -> WorkPromotionResult:
        entity_ids, _total = self.field_observations.list_active_fanza_work_entity_ids(
            limit=limit,
            offset=offset,
        )
        observations = self.field_observations.list_active_fanza_work_observations(entity_ids)
        observations_by_entity = _group_observations(observations)
        result = _MutableResult(scanned_count=len(entity_ids))

        for entity_id in entity_ids:
            try:
                candidate = self._candidate(entity_id, observations_by_entity.get(entity_id, []))
                result.invalid_field_count += candidate.invalid_field_count
                if not candidate.identities:
                    result.skipped_count += 1
                    continue
                self._promote_candidate(candidate, result=result, dry_run=dry_run)
            except Exception as exc:  # noqa: BLE001 - per-group promotion errors are reported.
                result.failed_count += 1
                result.errors.append(
                    WorkPromotionError(
                        entity_id=entity_id,
                        error_class=exc.__class__.__name__,
                        error_message=str(exc),
                    )
                )
                if not continue_on_error:
                    break

        return result.freeze()

    def _candidate(
        self,
        entity_id: int,
        observations: list[FieldObservation],
    ) -> PromotionCandidate:
        source_record = self.source_records.get_by_id(entity_id)
        if source_record is None:
            raise ValueError("source record for staging entity was not found")
        field_values = _latest_field_values(observations)
        values, invalid_field_count = _work_values(field_values)
        identities = _identity_candidates(field_values)
        external_url = _string_value(field_values.get("source_url")) or source_record.source_url
        return PromotionCandidate(
            entity_id=entity_id,
            source_record=source_record,
            work_values=values,
            identities=identities,
            external_url=external_url,
            confidence=PROMOTION_CONFIDENCE,
            invalid_field_count=invalid_field_count,
        )

    def _promote_candidate(
        self,
        candidate: PromotionCandidate,
        *,
        result: _MutableResult,
        dry_run: bool,
    ) -> None:
        existing_work, should_skip = self._matched_work(candidate, result)
        if should_skip:
            return

        if existing_work is None:
            result.promoted_count += 1
            result.created_work_count += 1
            if dry_run:
                result.created_external_id_count += len(candidate.identities)
                return
            work = self.works.create(
                code_original=_optional_str(candidate.work_values.get("code_original")),
                code_norm=_optional_str(candidate.work_values.get("code_norm")),
                code_prefix=_optional_str(candidate.work_values.get("code_prefix")),
                code_number=_optional_str(candidate.work_values.get("code_number")),
                title_ja=_optional_str(candidate.work_values.get("title_ja")),
                release_date=_optional_date(candidate.work_values.get("release_date")),
                runtime_minutes=_optional_int(candidate.work_values.get("runtime_minutes")),
                censor_type="unknown",
                work_type="unknown",
                primary_source=SOURCE,
                confidence=candidate.confidence,
                is_active=True,
            )
        else:
            result.promoted_count += 1
            result.duplicate_count += 1
            result.conflict_count += _count_field_conflicts(existing_work, candidate.work_values)
            fillable_fields = self.works.compute_fillable_fields(
                existing_work,
                {**candidate.work_values, "primary_source": SOURCE},
            )
            if fillable_fields:
                result.updated_work_count += 1
                if not dry_run:
                    self.works.apply_fillable_fields(existing_work, fillable_fields)
            work = existing_work

        self._ensure_external_ids(candidate, work=work, result=result, dry_run=dry_run)

    def _matched_work(
        self,
        candidate: PromotionCandidate,
        result: _MutableResult,
    ) -> tuple[Work | None, bool]:
        matched_work_ids: set[int] = set()
        for identity in candidate.identities:
            external_id = self.work_external_ids.get_by_source_external_id(
                source=SOURCE,
                external_id=identity.external_id,
                id_type=identity.id_type,
            )
            if external_id is not None:
                matched_work_ids.add(external_id.work_id)

        if len(matched_work_ids) > 1:
            result.conflict_count += 1
            result.skipped_count += 1
            return None, True
        if not matched_work_ids:
            return None, False

        work_id = next(iter(matched_work_ids))
        work = self.works.get_by_id(work_id)
        if work is None:
            raise ValueError(f"work_external_ids points to missing work_id={work_id}")
        return work, False

    def _ensure_external_ids(
        self,
        candidate: PromotionCandidate,
        *,
        work: Work,
        result: _MutableResult,
        dry_run: bool,
    ) -> None:
        for identity in candidate.identities:
            existing = self.work_external_ids.get_by_source_external_id(
                source=SOURCE,
                external_id=identity.external_id,
                id_type=identity.id_type,
            )
            if existing is not None:
                if existing.work_id != work.id:
                    result.conflict_count += 1
                continue
            result.created_external_id_count += 1
            if dry_run:
                continue
            self.work_external_ids.create(
                work_id=work.id,
                source=SOURCE,
                external_id=identity.external_id,
                id_type=identity.id_type,
                external_url=candidate.external_url,
                confidence=candidate.confidence,
                source_record_id=candidate.source_record.id,
                fetched_at=candidate.source_record.fetched_at,
            )


def _group_observations(
    observations: list[FieldObservation],
) -> dict[int, list[FieldObservation]]:
    grouped: dict[int, list[FieldObservation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.entity_id].append(observation)
    return grouped


def _latest_field_values(observations: list[FieldObservation]) -> dict[str, ObservationValue]:
    values: dict[str, ObservationValue] = {}
    for observation in observations:
        values.setdefault(observation.field_name, observation.field_value)
    return values


def _work_values(field_values: dict[str, ObservationValue]) -> tuple[dict[str, object], int]:
    invalid_field_count = 0
    code_original = _string_value(field_values.get("code_original"))
    code_norm = _string_value(field_values.get("code_norm"))
    code_prefix = _string_value(field_values.get("code_prefix"))
    code_number = _string_value(field_values.get("code_number"))
    if code_original is not None and (
        code_norm is None or code_prefix is None or code_number is None
    ):
        normalized = normalize_code(code_original)
        code_norm = code_norm or normalized.norm
        code_prefix = code_prefix or normalized.prefix
        code_number = code_number or normalized.number

    release_date_value = None
    release_date_text = _string_value(field_values.get("release_date"))
    if release_date_text is not None:
        try:
            release_date_value = date.fromisoformat(release_date_text)
        except ValueError:
            invalid_field_count += 1

    runtime_minutes, invalid_runtime = _runtime_minutes(field_values.get("runtime_minutes"))
    invalid_field_count += invalid_runtime

    values: dict[str, object] = {
        "code_original": code_original,
        "code_norm": code_norm,
        "code_prefix": code_prefix,
        "code_number": code_number,
        "title_ja": _string_value(field_values.get("title_ja")),
        "release_date": release_date_value,
        "runtime_minutes": runtime_minutes,
    }
    return {key: value for key, value in values.items() if value is not None}, invalid_field_count


def _identity_candidates(field_values: dict[str, ObservationValue]) -> list[PromotionIdentity]:
    primary_identities = [
        PromotionIdentity(id_type=id_type, external_id=external_id)
        for id_type in PRIMARY_ID_TYPES
        if (external_id := _string_value(field_values.get(id_type))) is not None
    ]
    if primary_identities:
        return primary_identities

    code_norm = _string_value(field_values.get("code_norm"))
    if code_norm is None:
        return []
    # This is a FANZA source-scoped MVP idempotency fallback, not cross-source entity resolution.
    return [PromotionIdentity(id_type="code_norm", external_id=code_norm)]


def _string_value(value: ObservationValue) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _runtime_minutes(value: ObservationValue) -> tuple[int | None, int]:
    if isinstance(value, bool) or value is None:
        return None, 0
    if isinstance(value, int):
        return (value, 0) if value >= 0 else (None, 1)
    return None, 1


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_date(value: object) -> date | None:
    return value if isinstance(value, date) else None


def _count_field_conflicts(work: Work, incoming_values: dict[str, object]) -> int:
    conflict_count = 0
    for field_name in WORK_FIELD_NAMES:
        incoming = incoming_values.get(field_name)
        existing = getattr(work, field_name)
        if incoming is not None and existing is not None and existing != incoming:
            conflict_count += 1
    return conflict_count


__all__ = [
    "ENTITY_TYPE",
    "SOURCE",
    "WorkPromotionError",
    "WorkPromotionResult",
    "WorkPromotionService",
]
