from datetime import UTC, datetime
from typing import Any
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from jav_metadatahub.db.models import SourceRecord
from jav_metadatahub.repositories.source_records import SourceRecordRepository


def make_repository() -> tuple[SourceRecordRepository, Mock]:
    session = Mock(spec=Session)
    return SourceRecordRepository(session), session


def test_create_stores_raw_payloads_and_flushes_without_commit() -> None:
    repository, session = make_repository()
    fetched_at = datetime(2026, 6, 22, 12, 0, tzinfo=UTC)

    record = repository.create(
        source=" fanza ",
        source_key=" cid-001 ",
        record_type=" work ",
        source_url="https://example.test/work/cid-001",
        raw_json={"items": [{"content_id": "cid-001"}]},
        raw_html="<html></html>",
        raw_text="plain text",
        http_status=500,
        fetch_status="failed",
        error_message="upstream error",
        parser_version="parser-v1",
        checksum="sha256:test",
        collector_run_id=123,
        fetched_at=fetched_at,
    )

    assert record.source == "fanza"
    assert record.source_key == "cid-001"
    assert record.record_type == "work"
    assert record.payload_type == "json"
    assert record.raw_json == {"items": [{"content_id": "cid-001"}]}
    assert record.raw_html == "<html></html>"
    assert record.raw_text == "plain text"
    assert record.http_status == 500
    assert record.fetch_status == "failed"
    assert record.error_message == "upstream error"
    assert record.parser_version == "parser-v1"
    assert record.checksum == "sha256:test"
    assert record.collector_run_id == 123
    assert record.fetched_at == fetched_at
    session.add.assert_called_once_with(record)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()


def test_create_accepts_list_raw_json() -> None:
    repository, _session = make_repository()

    record = repository.create(
        source="r18",
        source_key="dump-row-1",
        record_type="work",
        raw_json=[{"content_id": "abc"}, {"content_id": "def"}],
    )

    assert record.raw_json == [{"content_id": "abc"}, {"content_id": "def"}]


def test_create_accepts_not_found_record_without_raw_json() -> None:
    repository, session = make_repository()

    record = repository.create(
        source="fanza",
        source_key="missing-cid",
        record_type="work",
        raw_json=None,
        http_status=404,
        fetch_status="not_found",
        error_message="not found",
    )

    assert record.raw_json is None
    assert record.http_status == 404
    assert record.fetch_status == "not_found"
    assert record.error_message == "not found"
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()


def test_get_by_id_uses_session_get() -> None:
    repository, session = make_repository()
    expected = SourceRecord(source="fanza", source_key="cid-001", record_type="work")
    session.get.return_value = expected

    assert repository.get_by_id(42) is expected

    session.get.assert_called_once_with(SourceRecord, 42)


def test_get_by_source_key_strips_values_and_uses_scalar() -> None:
    repository, session = make_repository()
    expected = SourceRecord(source="fanza", source_key="cid-001", record_type="work")
    session.scalar.return_value = expected

    result = repository.get_by_source_key(" fanza ", " cid-001 ", " work ")

    assert result is expected
    statement = session.scalar.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "source_records.source = %(source_1)s" in sql
    assert "source_records.source_key = %(source_key_1)s" in sql
    assert "source_records.record_type = %(record_type_1)s" in sql
    assert compiled.params == {
        "source_1": "fanza",
        "source_key_1": "cid-001",
        "record_type_1": "work",
    }


def test_list_records_filters_success_records_with_offset_pagination() -> None:
    repository, session = make_repository()
    expected = [SourceRecord(source="fanza", source_key="cid-001", record_type="work")]
    scalar_result = Mock()
    scalar_result.all.return_value = expected
    session.scalars.return_value = scalar_result

    result = repository.list_records(" fanza ", " work ", limit=50, offset=10)

    assert result == expected
    statement = session.scalars.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "source_records.source = %(source_1)s" in sql
    assert "source_records.record_type = %(record_type_1)s" in sql
    assert "source_records.fetch_status = %(fetch_status_1)s" in sql
    assert "ORDER BY javhub.source_records.fetched_at DESC, javhub.source_records.id DESC" in sql
    assert "LIMIT %(param_1)s OFFSET %(param_2)s" in sql
    assert compiled.params == {
        "source_1": "fanza",
        "record_type_1": "work",
        "fetch_status_1": "success",
        "param_1": 50,
        "param_2": 10,
    }
    session.commit.assert_not_called()


def test_list_records_can_disable_fetch_status_filter() -> None:
    repository, session = make_repository()
    scalar_result = Mock()
    scalar_result.all.return_value = []
    session.scalars.return_value = scalar_result

    repository.list_records("fanza", "work", fetch_status=None)

    statement = session.scalars.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "source_records.fetch_status =" not in sql
    assert compiled.params == {
        "source_1": "fanza",
        "record_type_1": "work",
        "param_1": 100,
        "param_2": 0,
    }


def test_list_page_supports_optional_api_filters_and_total() -> None:
    repository, session = make_repository()
    expected = [SourceRecord(source="fanza", source_key="cid-001", record_type="work")]
    scalar_result = Mock()
    scalar_result.all.return_value = expected
    session.scalar.return_value = 12
    session.scalars.return_value = scalar_result

    result, total = repository.list_page(
        limit=20,
        offset=5,
        source=" fanza ",
        record_type=" work ",
        fetch_status=" success ",
    )

    assert result == expected
    assert total == 12
    count_statement = session.scalar.call_args.args[0]
    data_statement = session.scalars.call_args.args[0]
    count_sql = str(count_statement.compile(dialect=postgresql.dialect()))
    compiled = data_statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "count(*)" in count_sql
    assert "source_records.source = %(source_1)s" in sql
    assert "source_records.record_type = %(record_type_1)s" in sql
    assert "source_records.fetch_status = %(fetch_status_1)s" in sql
    assert "ORDER BY javhub.source_records.created_at DESC, javhub.source_records.id DESC" in sql
    assert compiled.params == {
        "source_1": "fanza",
        "record_type_1": "work",
        "fetch_status_1": "success",
        "param_1": 20,
        "param_2": 5,
    }


def test_upsert_executes_postgresql_on_conflict_and_returns_scalar_one() -> None:
    repository, session = make_repository()
    expected = SourceRecord(source="fanza", source_key="cid-001", record_type="work")
    execute_result = Mock()
    execute_result.scalar_one.return_value = expected
    session.execute.return_value = execute_result

    result = repository.upsert(
        source=" fanza ",
        source_key=" cid-001 ",
        record_type=" work ",
        payload_type=" json ",
        raw_json={"content_id": "cid-001"},
        fetch_status="success",
    )

    assert result is expected
    statement = session.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "ON CONFLICT (source, source_key, record_type) DO UPDATE" in sql
    assert "now()" in sql
    assert "fetched_at = NULL" not in sql
    execute_result.scalar_one.assert_called_once_with()
    session.commit.assert_not_called()


def test_upsert_uses_explicit_fetched_at_when_provided() -> None:
    repository, session = make_repository()
    expected = SourceRecord(source="fanza", source_key="cid-001", record_type="work")
    execute_result = Mock()
    execute_result.scalar_one.return_value = expected
    session.execute.return_value = execute_result
    fetched_at = datetime(2026, 6, 22, 12, 30, tzinfo=UTC)

    repository.upsert(
        source="fanza",
        source_key="cid-001",
        record_type="work",
        fetched_at=fetched_at,
    )

    statement = session.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert compiled.params["fetched_at"] == fetched_at


@pytest.mark.parametrize(
    "method_name",
    ["create", "get_by_source_key", "upsert"],
)
@pytest.mark.parametrize("field_name", ["source", "source_key", "record_type"])
@pytest.mark.parametrize("bad_value", [None, "", "   "])
def test_required_unique_key_fields_are_validated(
    method_name: str,
    field_name: str,
    bad_value: str | None,
) -> None:
    repository, _session = make_repository()
    kwargs: dict[str, Any] = {
        "source": "fanza",
        "source_key": "cid-001",
        "record_type": "work",
    }
    kwargs[field_name] = bad_value

    with pytest.raises(ValueError, match=field_name):
        getattr(repository, method_name)(**kwargs)


@pytest.mark.parametrize("field_name", ["source", "record_type"])
@pytest.mark.parametrize("bad_value", [None, "", "   "])
def test_list_records_required_fields_are_validated(
    field_name: str,
    bad_value: str | None,
) -> None:
    repository, _session = make_repository()
    source: str | None = "fanza"
    record_type: str | None = "work"
    if field_name == "source":
        source = bad_value
    else:
        record_type = bad_value

    with pytest.raises(ValueError, match=field_name):
        repository.list_records(source, record_type)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"limit": 0}, "limit"),
        ({"limit": -1}, "limit"),
        ({"offset": -1}, "offset"),
    ],
)
def test_list_records_validates_limit_and_offset(kwargs: dict[str, int], match: str) -> None:
    repository, _session = make_repository()

    with pytest.raises(ValueError, match=match):
        repository.list_records("fanza", "work", **kwargs)


@pytest.mark.parametrize("method_name", ["create", "upsert"])
@pytest.mark.parametrize("bad_value", [None, "", "   "])
def test_payload_type_is_validated_for_writes(
    method_name: str,
    bad_value: str | None,
) -> None:
    repository, _session = make_repository()

    with pytest.raises(ValueError, match="payload_type"):
        getattr(repository, method_name)(
            source="fanza",
            source_key="cid-001",
            record_type="work",
            payload_type=bad_value,
        )
