from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock

from jav_metadatahub.db.models import FieldObservation, SourceRecord, Work, WorkExternalId
from jav_metadatahub.repositories import (
    FieldObservationRepository,
    SourceRecordRepository,
    WorkExternalIdRepository,
    WorkRepository,
)
from jav_metadatahub.services.work_promotion import WorkPromotionService

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)


def observation(entity_id: int, field_name: str, value: object) -> FieldObservation:
    return FieldObservation(
        id=entity_id * 100,
        entity_type="fanza_work",
        entity_id=entity_id,
        field_name=field_name,
        field_value=value,
        field_value_text=str(value),
        source="fanza",
        source_record_id=entity_id,
        confidence=Decimal("0.950"),
        observation_status="active",
        observed_at=NOW,
        created_at=NOW,
    )


def source_record(record_id: int) -> SourceRecord:
    return SourceRecord(
        id=record_id,
        source="fanza",
        source_key=f"cid-{record_id:03d}",
        record_type="work",
        source_url=f"https://example.test/{record_id}",
        raw_json={"content_id": f"cid-{record_id:03d}"},
        fetched_at=NOW,
    )


def work(work_id: int, **overrides: object) -> Work:
    values: dict[str, object] = {
        "id": work_id,
        "code_original": "ABP-00477",
        "code_norm": "ABP00477",
        "code_prefix": "ABP",
        "code_number": "477",
        "title_ja": "Existing",
        "release_date": None,
        "runtime_minutes": None,
        "primary_source": "fanza",
        "confidence": Decimal("0.950"),
        "is_active": True,
    }
    values.update(overrides)
    return Work(**values)


def external_id(work_id: int, id_type: str = "content_id") -> WorkExternalId:
    return WorkExternalId(
        id=work_id * 100,
        work_id=work_id,
        source="fanza",
        external_id=f"{id_type}-value",
        id_type=id_type,
        confidence=Decimal("0.950"),
    )


def make_service(
    *,
    entity_ids: list[int] | None = None,
    observations: list[FieldObservation] | None = None,
) -> tuple[WorkPromotionService, Mock, Mock, Mock, Mock]:
    field_observations = Mock(spec=FieldObservationRepository)
    field_observations.list_active_fanza_work_entity_ids.return_value = (entity_ids or [1], 1)
    field_observations.list_active_fanza_work_observations.return_value = observations or []
    source_records = Mock(spec=SourceRecordRepository)
    source_records.get_by_id.side_effect = lambda entity_id: source_record(entity_id)
    works = Mock(spec=WorkRepository)
    works.create.return_value = work(10)
    works.compute_fillable_fields.return_value = {}
    work_external_ids = Mock(spec=WorkExternalIdRepository)
    work_external_ids.get_by_source_external_id.return_value = None
    return (
        WorkPromotionService(
            field_observations=field_observations,
            source_records=source_records,
            works=works,
            work_external_ids=work_external_ids,
        ),
        field_observations,
        source_records,
        works,
        work_external_ids,
    )


def fanza_work_observations(entity_id: int = 1) -> list[FieldObservation]:
    return [
        observation(entity_id, "content_id", "cid-001"),
        observation(entity_id, "product_id", "product-001"),
        observation(entity_id, "dvd_id", "DVD-001"),
        observation(entity_id, "code_original", "ABP-00477"),
        observation(entity_id, "code_norm", "ABP00477"),
        observation(entity_id, "code_prefix", "ABP"),
        observation(entity_id, "code_number", "477"),
        observation(entity_id, "title_ja", "サンプル作品"),
        observation(entity_id, "release_date", "2020-01-02"),
        observation(entity_id, "runtime_minutes", 120),
        observation(entity_id, "actresses", ["Alice"]),
    ]


def test_promotes_fanza_observations_into_work_and_external_ids() -> None:
    service, _field_observations, _source_records, works, work_external_ids = make_service(
        observations=fanza_work_observations()
    )

    result = service.promote_fanza_works()

    assert result.promoted_count == 1
    assert result.created_work_count == 1
    assert result.created_external_id_count == 3
    assert result.failed_count == 0
    works.create.assert_called_once()
    create_kwargs = works.create.call_args.kwargs
    assert create_kwargs["code_original"] == "ABP-00477"
    assert create_kwargs["code_norm"] == "ABP00477"
    assert create_kwargs["code_prefix"] == "ABP"
    assert create_kwargs["code_number"] == "477"
    assert create_kwargs["title_ja"] == "サンプル作品"
    assert create_kwargs["runtime_minutes"] == 120
    assert create_kwargs["primary_source"] == "fanza"
    assert [call.kwargs["id_type"] for call in work_external_ids.create.call_args_list] == [
        "content_id",
        "product_id",
        "dvd_id",
    ]


def test_code_norm_fallback_is_only_used_without_primary_ids() -> None:
    service, _field_observations, _source_records, _works, work_external_ids = make_service(
        observations=[
            observation(1, "code_original", "ABP-00477"),
            observation(1, "code_norm", "ABP00477"),
        ]
    )

    result = service.promote_fanza_works()

    assert result.promoted_count == 1
    assert result.created_external_id_count == 1
    # code_norm is a FANZA source-scoped MVP fallback key, not cross-source entity resolution.
    work_external_ids.create.assert_called_once()
    assert work_external_ids.create.call_args.kwargs["id_type"] == "code_norm"


def test_repeated_promotion_is_idempotent_for_existing_external_ids() -> None:
    existing_work = work(10)
    service, _field_observations, _source_records, works, work_external_ids = make_service(
        observations=fanza_work_observations()
    )
    work_external_ids.get_by_source_external_id.return_value = external_id(10)
    works.get_by_id.return_value = existing_work

    result = service.promote_fanza_works()

    assert result.promoted_count == 1
    assert result.duplicate_count == 1
    assert result.created_work_count == 0
    assert result.created_external_id_count == 0
    works.create.assert_not_called()
    work_external_ids.create.assert_not_called()


def test_existing_work_field_conflict_does_not_skip_group() -> None:
    existing_work = work(10, title_ja="既存タイトル")
    service, _field_observations, _source_records, works, _work_external_ids = make_service(
        observations=fanza_work_observations()
    )
    service.work_external_ids.get_by_source_external_id.return_value = external_id(10)
    works.get_by_id.return_value = existing_work

    result = service.promote_fanza_works()

    assert result.promoted_count == 1
    assert result.skipped_count == 0
    assert result.conflict_count >= 1
    assert existing_work.title_ja == "既存タイトル"


def test_identity_candidates_matching_different_works_skip_group() -> None:
    service, _field_observations, _source_records, works, work_external_ids = make_service(
        observations=fanza_work_observations()
    )
    work_external_ids.get_by_source_external_id.side_effect = [
        external_id(10, "content_id"),
        external_id(11, "product_id"),
        None,
    ]

    result = service.promote_fanza_works()

    assert result.promoted_count == 0
    assert result.skipped_count == 1
    assert result.conflict_count == 1
    works.create.assert_not_called()
    work_external_ids.create.assert_not_called()


def test_external_id_owned_by_other_work_counts_conflict_without_rebinding() -> None:
    existing_work = work(10, title_ja="サンプル作品")
    service, _field_observations, _source_records, works, work_external_ids = make_service(
        observations=fanza_work_observations()
    )
    work_external_ids.get_by_source_external_id.side_effect = [
        external_id(10, "content_id"),
        None,
        None,
        external_id(10, "content_id"),
        external_id(99, "product_id"),
        None,
    ]
    works.get_by_id.return_value = existing_work

    result = service.promote_fanza_works()

    assert result.promoted_count == 1
    assert result.conflict_count == 1
    created_id_types = [call.kwargs["id_type"] for call in work_external_ids.create.call_args_list]
    assert created_id_types == ["dvd_id"]


def test_missing_identity_is_skipped() -> None:
    service, _field_observations, _source_records, works, work_external_ids = make_service(
        observations=[observation(1, "title_ja", "No identity")]
    )

    result = service.promote_fanza_works()

    assert result.promoted_count == 0
    assert result.skipped_count == 1
    works.create.assert_not_called()
    work_external_ids.create.assert_not_called()


def test_dry_run_does_not_create_apply_or_mutate_existing_work() -> None:
    existing_work = work(10, title_ja=None)
    service, _field_observations, _source_records, works, work_external_ids = make_service(
        observations=fanza_work_observations()
    )
    work_external_ids.get_by_source_external_id.return_value = external_id(10)
    works.get_by_id.return_value = existing_work
    works.compute_fillable_fields.return_value = {"title_ja": "サンプル作品"}

    result = service.promote_fanza_works(dry_run=True)

    assert result.promoted_count == 1
    assert result.updated_work_count == 1
    assert existing_work.title_ja is None
    works.create.assert_not_called()
    works.apply_fillable_fields.assert_not_called()
    work_external_ids.create.assert_not_called()
