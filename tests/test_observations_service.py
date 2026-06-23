from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import Mock

import pytest

from jav_metadatahub.db.models import FieldObservation
from jav_metadatahub.repositories.field_observations import FieldObservationRepository
from jav_metadatahub.services.observations import FieldObservationService


def make_service() -> tuple[FieldObservationService, Mock]:
    repository = Mock(spec=FieldObservationRepository)
    return FieldObservationService(repository), repository


def test_record_observation_creates_active_observation_with_text_value_preserved() -> None:
    service, repository = make_service()
    expected = FieldObservation(
        entity_type="work",
        entity_id=1,
        field_name="title_ja",
        source="r18",
    )
    repository.find_duplicate.return_value = None
    repository.create.return_value = expected
    observed_at = datetime(2026, 6, 22, 12, 0, tzinfo=UTC)

    result = service.record_observation(
        entity_type=" work ",
        entity_id=1,
        field_name=" title_ja ",
        field_value="  source title  ",
        source=" r18 ",
        source_record_id=10,
        confidence="0.850",
        observed_at=observed_at,
    )

    assert result is expected
    repository.find_duplicate.assert_called_once_with(
        entity_type="work",
        entity_id=1,
        field_name="title_ja",
        source="r18",
        source_record_id=10,
        field_value="  source title  ",
    )
    repository.create.assert_called_once_with(
        entity_type="work",
        entity_id=1,
        field_name="title_ja",
        field_value="  source title  ",
        field_value_text="  source title  ",
        source="r18",
        source_record_id=10,
        confidence=Decimal("0.850"),
        observation_status="active",
        rejection_reason=None,
        observed_at=observed_at,
    )


@pytest.mark.parametrize(
    ("field_value", "expected_text"),
    [
        (None, None),
        ({"b": 2, "a": 1}, '{"a":1,"b":2}'),
        ([{"name": "明日花"}, True], '[{"name":"明日花"},true]'),
        (120, "120"),
        (3.5, "3.5"),
        (False, "false"),
        ("前後 空格", "前後 空格"),
    ],
)
def test_record_observation_generates_field_value_text(
    field_value: Any,
    expected_text: str | None,
) -> None:
    service, repository = make_service()
    expected = FieldObservation(entity_type="work", entity_id=1, field_name="value", source="r18")
    repository.find_duplicate.return_value = None
    repository.create.return_value = expected

    service.record_observation(
        entity_type="work",
        entity_id=1,
        field_name="value",
        field_value=field_value,
        source="r18",
    )

    assert repository.create.call_args.kwargs["field_value_text"] == expected_text


def test_record_observation_returns_active_duplicate_without_creating() -> None:
    service, repository = make_service()
    existing = FieldObservation(
        entity_type="work",
        entity_id=1,
        field_name="title_ja",
        field_value="title",
        source="r18",
        observation_status="active",
    )
    repository.find_duplicate.return_value = existing

    result = service.record_observation(
        entity_type="work",
        entity_id=1,
        field_name="title_ja",
        field_value="title",
        source="r18",
    )

    assert result is existing
    repository.create.assert_not_called()


def test_record_observation_creates_when_existing_duplicate_is_not_active() -> None:
    service, repository = make_service()
    expected = FieldObservation(
        entity_type="work",
        entity_id=1,
        field_name="title_ja",
        field_value="title",
        source="r18",
        observation_status="active",
    )
    repository.find_duplicate.return_value = None
    repository.create.return_value = expected

    result = service.record_observation(
        entity_type="work",
        entity_id=1,
        field_name="title_ja",
        field_value="title",
        source="r18",
    )

    assert result is expected
    repository.find_duplicate.assert_called_once()
    repository.create.assert_called_once()


def test_record_observation_skips_duplicate_lookup_when_idempotent_is_false() -> None:
    service, repository = make_service()
    expected = FieldObservation(
        entity_type="work",
        entity_id=1,
        field_name="title_ja",
        source="r18",
    )
    repository.create.return_value = expected

    result = service.record_observation(
        entity_type="work",
        entity_id=1,
        field_name="title_ja",
        field_value="title",
        source="r18",
        idempotent=False,
    )

    assert result is expected
    repository.find_duplicate.assert_not_called()
    repository.create.assert_called_once()


def test_record_observation_allows_conflicting_values_to_coexist() -> None:
    service, repository = make_service()
    first = FieldObservation(entity_type="work", entity_id=1, field_name="runtime", source="r18")
    second = FieldObservation(entity_type="work", entity_id=1, field_name="runtime", source="r18")
    repository.find_duplicate.return_value = None
    repository.create.side_effect = [first, second]

    result_one = service.record_observation(
        entity_type="work",
        entity_id=1,
        field_name="runtime",
        field_value=118,
        source="r18",
    )
    result_two = service.record_observation(
        entity_type="work",
        entity_id=1,
        field_name="runtime",
        field_value=120,
        source="r18",
    )

    assert result_one is first
    assert result_two is second
    assert repository.create.call_args_list[0].kwargs["field_value"] == 118
    assert repository.create.call_args_list[1].kwargs["field_value"] == 120


@pytest.mark.parametrize(
    "field_name",
    ["entity_type", "field_name", "source", "observation_status"],
)
@pytest.mark.parametrize("bad_value", [None, "", "   "])
def test_required_strings_are_validated(field_name: str, bad_value: str | None) -> None:
    service, _repository = make_service()
    kwargs: dict[str, Any] = {
        "entity_type": "work",
        "entity_id": 1,
        "field_name": "title_ja",
        "field_value": "title",
        "source": "r18",
        "observation_status": "active",
    }
    kwargs[field_name] = bad_value

    with pytest.raises(ValueError, match=field_name):
        service.record_observation(**kwargs)


@pytest.mark.parametrize("bad_value", [0, -1])
def test_entity_id_must_be_positive(bad_value: int) -> None:
    service, _repository = make_service()

    with pytest.raises(ValueError, match="entity_id"):
        service.record_observation(
            entity_type="work",
            entity_id=bad_value,
            field_name="title_ja",
            field_value="title",
            source="r18",
        )


@pytest.mark.parametrize("bad_value", [0, -1])
def test_source_record_id_must_be_positive_when_provided(bad_value: int) -> None:
    service, _repository = make_service()

    with pytest.raises(ValueError, match="source_record_id"):
        service.record_observation(
            entity_type="work",
            entity_id=1,
            field_name="title_ja",
            field_value="title",
            source="r18",
            source_record_id=bad_value,
        )


@pytest.mark.parametrize("bad_value", [Decimal("-0.001"), Decimal("1.001")])
def test_confidence_must_be_in_range(bad_value: Decimal) -> None:
    service, _repository = make_service()

    with pytest.raises(ValueError, match="confidence"):
        service.record_observation(
            entity_type="work",
            entity_id=1,
            field_name="title_ja",
            field_value="title",
            source="r18",
            confidence=bad_value,
        )


@pytest.mark.parametrize("bad_status", ["accepted", None, "", "   "])
def test_observation_status_is_limited_to_v1_values(bad_status: str | None) -> None:
    service, _repository = make_service()

    with pytest.raises(ValueError, match="observation_status"):
        service.record_observation(
            entity_type="work",
            entity_id=1,
            field_name="title_ja",
            field_value="title",
            source="r18",
            observation_status=bad_status,
        )


@pytest.mark.parametrize(
    "bad_value",
    [
        Decimal("1.2"),
        datetime(2026, 6, 22, tzinfo=UTC),
        {1, 2},
        float("nan"),
    ],
)
def test_non_json_compatible_values_are_rejected(bad_value: Any) -> None:
    service, _repository = make_service()

    with pytest.raises((TypeError, ValueError), match="field_value"):
        service.record_observation(
            entity_type="work",
            entity_id=1,
            field_name="value",
            field_value=bad_value,
            source="r18",
        )
