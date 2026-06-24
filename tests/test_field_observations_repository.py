from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from jav_metadatahub.db.models import FieldObservation
from jav_metadatahub.repositories.field_observations import FieldObservationRepository


def make_repository() -> tuple[FieldObservationRepository, Mock]:
    session = Mock(spec=Session)
    return FieldObservationRepository(session), session


def compile_sql(statement: Any) -> tuple[str, dict[str, Any]]:
    compiled = statement.compile(dialect=postgresql.dialect())
    return str(compiled), compiled.params


def duplicate_statement(field_value: Any) -> Any:
    repository, session = make_repository()
    repository.find_duplicate(
        entity_type="work",
        entity_id=1,
        field_name="title_ja",
        source="fanza",
        source_record_id=10,
        field_value=field_value,
    )
    return session.scalar.call_args.args[0]


def test_create_stores_observation_and_flushes_without_commit() -> None:
    repository, session = make_repository()
    observed_at = datetime(2026, 6, 22, 12, 0, tzinfo=UTC)

    observation = repository.create(
        entity_type=" work ",
        entity_id=100,
        field_name=" title_ja ",
        field_value={"title": "  padded source value  "},
        field_value_text='{"title":"  padded source value  "}',
        source=" fanza ",
        source_record_id=200,
        confidence=Decimal("0.950"),
        observation_status=" active ",
        rejection_reason=None,
        observed_at=observed_at,
    )

    assert observation.entity_type == "work"
    assert observation.entity_id == 100
    assert observation.field_name == "title_ja"
    assert observation.field_value == {"title": "  padded source value  "}
    assert observation.field_value_text == '{"title":"  padded source value  "}'
    assert observation.source == "fanza"
    assert observation.source_record_id == 200
    assert observation.confidence == Decimal("0.950")
    assert observation.observation_status == "active"
    assert observation.rejection_reason is None
    assert observation.observed_at == observed_at
    session.add.assert_called_once_with(observation)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()


def test_get_by_id_uses_session_get() -> None:
    repository, session = make_repository()
    expected = FieldObservation(entity_type="work", entity_id=1, field_name="title", source="r18")
    session.get.return_value = expected

    assert repository.get_by_id(42) is expected

    session.get.assert_called_once_with(FieldObservation, 42)


def test_list_for_entity_filters_and_orders_results() -> None:
    repository, session = make_repository()
    expected = [FieldObservation(entity_type="work", entity_id=1, field_name="title", source="r18")]
    session.scalars.return_value.all.return_value = expected

    result = repository.list_for_entity(
        " work ",
        1,
        field_name=" title_ja ",
        source=" fanza ",
        observation_status=" active ",
    )

    assert result == expected
    statement = session.scalars.call_args.args[0]
    sql, params = compile_sql(statement)
    assert "field_observations.entity_type = %(entity_type_1)s" in sql
    assert "field_observations.entity_id = %(entity_id_1)s" in sql
    assert "field_observations.field_name = %(field_name_1)s" in sql
    assert "field_observations.source = %(source_1)s" in sql
    assert "field_observations.observation_status = %(observation_status_1)s" in sql
    assert "ORDER BY javhub.field_observations.observed_at DESC" in sql
    assert params == {
        "entity_type_1": "work",
        "entity_id_1": 1,
        "field_name_1": "title_ja",
        "source_1": "fanza",
        "observation_status_1": "active",
    }


def test_list_for_field_filters_by_field_and_source() -> None:
    repository, session = make_repository()
    session.scalars.return_value.all.return_value = []

    repository.list_for_field("work", 1, "runtime_minutes", source="r18")

    statement = session.scalars.call_args.args[0]
    sql, params = compile_sql(statement)
    assert "field_observations.entity_type = %(entity_type_1)s" in sql
    assert "field_observations.entity_id = %(entity_id_1)s" in sql
    assert "field_observations.field_name = %(field_name_1)s" in sql
    assert "field_observations.source = %(source_1)s" in sql
    assert params["entity_type_1"] == "work"
    assert params["entity_id_1"] == 1
    assert params["field_name_1"] == "runtime_minutes"
    assert params["source_1"] == "r18"


def test_list_by_source_filters_by_source_field_and_status() -> None:
    repository, session = make_repository()
    session.scalars.return_value.all.return_value = []

    repository.list_by_source(" fanza ", field_name=" title_ja ", observation_status="active")

    statement = session.scalars.call_args.args[0]
    sql, params = compile_sql(statement)
    assert "field_observations.source = %(source_1)s" in sql
    assert "field_observations.field_name = %(field_name_1)s" in sql
    assert "field_observations.observation_status = %(observation_status_1)s" in sql
    assert params == {
        "source_1": "fanza",
        "field_name_1": "title_ja",
        "observation_status_1": "active",
    }


def test_list_page_filters_counts_and_orders_results() -> None:
    repository, session = make_repository()
    expected = [
        FieldObservation(entity_type="fanza_work", entity_id=1, field_name="title", source="fanza")
    ]
    session.scalar.return_value = 3
    session.scalars.return_value.all.return_value = expected

    result, total = repository.list_page(
        entity_type=" fanza_work ",
        entity_id=1,
        field_name=" title ",
        limit=20,
        offset=5,
    )

    assert result == expected
    assert total == 3
    count_statement = session.scalar.call_args.args[0]
    data_statement = session.scalars.call_args.args[0]
    count_sql, count_params = compile_sql(count_statement)
    sql, params = compile_sql(data_statement)
    assert "count(*)" in count_sql
    assert count_params == {
        "entity_type_1": "fanza_work",
        "entity_id_1": 1,
        "field_name_1": "title",
    }
    assert "field_observations.entity_type = %(entity_type_1)s" in sql
    assert "field_observations.entity_id = %(entity_id_1)s" in sql
    assert "field_observations.field_name = %(field_name_1)s" in sql
    assert "ORDER BY javhub.field_observations.created_at DESC" in sql
    assert params == {
        "entity_type_1": "fanza_work",
        "entity_id_1": 1,
        "field_name_1": "title",
        "param_1": 20,
        "param_2": 5,
    }


def test_find_duplicate_matches_active_without_status_in_fact_key() -> None:
    repository, session = make_repository()
    expected = FieldObservation(entity_type="work", entity_id=1, field_name="title", source="r18")
    session.scalar.return_value = expected

    result = repository.find_duplicate(
        entity_type=" work ",
        entity_id=1,
        field_name=" title_ja ",
        source=" fanza ",
        source_record_id=10,
        field_value={"title": "value"},
    )

    assert result is expected
    statement = session.scalar.call_args.args[0]
    sql, params = compile_sql(statement)
    assert "field_observations.observation_status = %(observation_status_1)s" in sql
    assert "field_observations.source_record_id = %(source_record_id_1)s" in sql
    assert "field_observations.field_value = %(field_value)s::JSONB" in sql
    assert params["observation_status_1"] == "active"
    assert params["source_record_id_1"] == 10
    assert params["field_value"] == {"title": "value"}


def test_find_duplicate_binds_string_field_value_as_jsonb() -> None:
    statement = duplicate_statement("cid-001")
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert "field_observations.field_value = %(field_value)s::JSONB" in sql
    assert "::VARCHAR" not in sql
    assert compiled.params["field_value"] == "cid-001"
    assert isinstance(compiled.binds["field_value"].type, postgresql.JSONB)


@pytest.mark.parametrize("field_value", [{"content_id": "cid-001"}, ["Alice", "Beth"]])
def test_find_duplicate_binds_collection_field_value_as_jsonb(field_value: Any) -> None:
    statement = duplicate_statement(field_value)
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert "field_observations.field_value = %(field_value)s::JSONB" in sql
    assert compiled.params["field_value"] == field_value
    assert isinstance(compiled.binds["field_value"].type, postgresql.JSONB)


def test_find_duplicate_uses_is_null_for_none_field_value() -> None:
    statement = duplicate_statement(None)
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert "field_observations.field_value IS NULL" in sql
    assert "field_observations.field_value = " not in sql
    assert "field_value" not in compiled.params


def test_find_duplicate_uses_is_null_for_missing_source_record_id() -> None:
    repository, session = make_repository()
    session.scalar.return_value = None

    repository.find_duplicate(
        entity_type="work",
        entity_id=1,
        field_name="title_ja",
        source="r18",
        source_record_id=None,
        field_value="title",
    )

    statement = session.scalar.call_args.args[0]
    sql, params = compile_sql(statement)
    assert "field_observations.source_record_id IS NULL" in sql
    assert params["observation_status_1"] == "active"


def test_set_status_updates_observation_and_flushes_without_commit() -> None:
    repository, session = make_repository()
    observation = FieldObservation(
        entity_type="work",
        entity_id=1,
        field_name="title_ja",
        source="r18",
        observation_status="active",
    )
    session.get.return_value = observation

    result = repository.set_status(
        42,
        " rejected ",
        rejection_reason=" source conflict ",
    )

    assert result is observation
    assert observation.observation_status == "rejected"
    assert observation.rejection_reason == " source conflict "
    session.get.assert_called_once_with(FieldObservation, 42)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()


def test_set_status_returns_none_when_observation_is_missing() -> None:
    repository, session = make_repository()
    session.get.return_value = None

    assert repository.set_status(42, "superseded") is None

    session.flush.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("method_name", "field_name", "bad_value"),
    [
        ("create", "entity_type", None),
        ("create", "entity_type", ""),
        ("create", "entity_type", "   "),
        ("create", "field_name", None),
        ("create", "field_name", ""),
        ("create", "field_name", "   "),
        ("create", "source", None),
        ("create", "source", ""),
        ("create", "source", "   "),
        ("list_for_entity", "entity_type", None),
        ("list_for_entity", "entity_type", ""),
        ("list_for_entity", "entity_type", "   "),
        ("list_for_entity", "field_name", ""),
        ("list_for_entity", "field_name", "   "),
        ("list_for_field", "entity_type", None),
        ("list_for_field", "entity_type", ""),
        ("list_for_field", "entity_type", "   "),
        ("list_for_field", "field_name", None),
        ("list_for_field", "field_name", ""),
        ("list_for_field", "field_name", "   "),
    ],
)
def test_required_strings_are_validated(
    method_name: str,
    field_name: str,
    bad_value: str | None,
) -> None:
    repository, _session = make_repository()
    kwargs: dict[str, Any] = {
        "entity_type": "work",
        "entity_id": 1,
        "field_name": "title_ja",
    }
    if method_name == "create":
        kwargs.update({"field_value": "title", "field_value_text": "title", "source": "r18"})
    elif method_name == "list_for_field":
        kwargs.update({"source": "r18"})
    kwargs[field_name] = bad_value

    with pytest.raises(ValueError, match=field_name):
        getattr(repository, method_name)(**kwargs)


@pytest.mark.parametrize("bad_status", ["accepted", None, "", "   "])
def test_status_values_are_validated(bad_status: str | None) -> None:
    repository, _session = make_repository()

    with pytest.raises(ValueError, match="observation_status"):
        repository.set_status(1, bad_status)


@pytest.mark.parametrize("bad_value", [0, -1])
def test_entity_id_must_be_positive(bad_value: int) -> None:
    repository, _session = make_repository()

    with pytest.raises(ValueError, match="entity_id"):
        repository.list_for_entity("work", bad_value)


@pytest.mark.parametrize("bad_value", [0, -1])
def test_source_record_id_must_be_positive_when_provided(bad_value: int) -> None:
    repository, _session = make_repository()

    with pytest.raises(ValueError, match="source_record_id"):
        repository.find_duplicate(
            entity_type="work",
            entity_id=1,
            field_name="title_ja",
            source="r18",
            source_record_id=bad_value,
            field_value="title",
        )
