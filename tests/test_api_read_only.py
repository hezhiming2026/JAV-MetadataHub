from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from jav_metadatahub.api.dependencies import get_db_session
from jav_metadatahub.api.main import create_app
from jav_metadatahub.db.models import (
    Company,
    FieldObservation,
    Person,
    Series,
    SourceRecord,
    Tag,
    Work,
)

NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)


def make_client(session: Mock) -> TestClient:
    app = create_app()

    def override_session() -> Any:
        yield session

    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app)


def scalar_result(items: list[Any]) -> Mock:
    result = Mock()
    result.all.return_value = items
    return result


def work() -> Work:
    return Work(
        id=1,
        code_original="ABP-477",
        code_norm="ABP477",
        code_prefix="ABP",
        code_number="477",
        title_ja="タイトル",
        title_en=None,
        title_zh=None,
        release_date=date(2020, 1, 2),
        runtime_minutes=120,
        censor_type="censored",
        work_type="movie",
        primary_source="fanza",
        confidence=Decimal("0.950"),
        is_active=True,
        notes=None,
        created_at=NOW,
        updated_at=NOW,
    )


def person() -> Person:
    return Person(
        id=1,
        canonical_name="Actor",
        name_ja="女優",
        name_en="Actor",
        name_zh=None,
        name_kana=None,
        person_type="actor",
        gender_role="female",
        primary_source="fanza",
        confidence=Decimal("0.900"),
        is_active=True,
        notes=None,
        created_at=NOW,
        updated_at=NOW,
    )


def company() -> Company:
    return Company(
        id=1,
        name="Maker",
        name_norm="maker",
        company_type="maker",
        primary_source="fanza",
        confidence=Decimal("0.900"),
        notes=None,
        created_at=NOW,
        updated_at=NOW,
    )


def series() -> Series:
    return Series(
        id=1,
        name="Series",
        name_norm="series",
        primary_source="fanza",
        confidence=Decimal("0.900"),
        notes=None,
        created_at=NOW,
        updated_at=NOW,
    )


def tag() -> Tag:
    return Tag(
        id=1,
        name="Drama",
        name_norm="drama",
        tag_type="genre",
        language="en",
        source="fanza",
        confidence=Decimal("0.900"),
        created_at=NOW,
        updated_at=NOW,
    )


def source_record() -> SourceRecord:
    return SourceRecord(
        id=1,
        source="fanza",
        source_key="cid-001",
        source_url="https://example.test/item/cid-001",
        record_type="work",
        payload_type="json",
        raw_json={"content_id": "cid-001"},
        raw_html=None,
        raw_text=None,
        http_status=200,
        fetch_status="success",
        error_message=None,
        parser_version=None,
        checksum="sha256:test",
        collector_run_id=None,
        fetched_at=NOW,
        created_at=NOW,
    )


def observation() -> FieldObservation:
    return FieldObservation(
        id=1,
        entity_type="fanza_work",
        entity_id=10,
        field_name="content_id",
        field_value="cid-001",
        field_value_text="cid-001",
        source="fanza",
        source_record_id=1,
        confidence=Decimal("0.950"),
        observation_status="active",
        rejection_reason=None,
        observed_at=NOW,
        created_at=NOW,
    )


def test_health() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_app_registers_read_only_routes() -> None:
    app = create_app()
    routes = set(app.openapi()["paths"])

    assert {
        "/health",
        "/works",
        "/works/{work_id}",
        "/people",
        "/people/{person_id}",
        "/companies",
        "/companies/{company_id}",
        "/series",
        "/series/{series_id}",
        "/tags",
        "/tags/{tag_id}",
        "/observations",
        "/source-records",
        "/source-records/{record_id}",
    }.issubset(routes)


@pytest.mark.parametrize(
    ("path", "item_factory", "expected_key"),
    [
        ("/works", work, "code_norm"),
        ("/people", person, "canonical_name"),
        ("/companies", company, "name"),
        ("/series", series, "name"),
        ("/tags", tag, "name"),
    ],
)
def test_canonical_list_pagination_shape(
    path: str,
    item_factory: Any,
    expected_key: str,
) -> None:
    session = Mock(spec=Session)
    session.scalar.return_value = 1
    session.scalars.return_value = scalar_result([item_factory()])
    client = make_client(session)

    response = client.get(f"{path}?limit=1&offset=2")

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 1
    assert body["offset"] == 2
    assert body["total"] == 1
    assert len(body["data"]) == 1
    assert expected_key in body["data"][0]


@pytest.mark.parametrize(
    ("path", "item_factory"),
    [
        ("/works/1", work),
        ("/people/1", person),
        ("/companies/1", company),
        ("/series/1", series),
        ("/tags/1", tag),
    ],
)
def test_canonical_detail(path: str, item_factory: Any) -> None:
    session = Mock(spec=Session)
    session.get.return_value = item_factory()
    client = make_client(session)

    response = client.get(path)

    assert response.status_code == 200
    assert response.json()["id"] == 1


@pytest.mark.parametrize(
    "path", ["/works/404", "/people/404", "/companies/404", "/series/404", "/tags/404"]
)
def test_canonical_detail_404(path: str) -> None:
    session = Mock(spec=Session)
    session.get.return_value = None
    client = make_client(session)

    response = client.get(path)

    assert response.status_code == 404


def test_observations_filter_and_pagination() -> None:
    session = Mock(spec=Session)
    session.scalar.return_value = 1
    session.scalars.return_value = scalar_result([observation()])
    client = make_client(session)

    response = client.get(
        "/observations?entity_type=fanza_work&entity_id=10&field=content_id&limit=1&offset=0"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["data"][0]["field_name"] == "content_id"
    statement = session.scalars.call_args.args[0]
    compiled_params = statement.compile().params
    assert compiled_params["entity_type_1"] == "fanza_work"
    assert compiled_params["entity_id_1"] == 10
    assert compiled_params["field_name_1"] == "content_id"


def test_source_records_list_and_detail() -> None:
    session = Mock(spec=Session)
    session.scalar.return_value = 1
    session.scalars.return_value = scalar_result([source_record()])
    client = make_client(session)

    list_response = client.get("/source-records?source=fanza&record_type=work&fetch_status=success")
    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["source_key"] == "cid-001"

    session.get.return_value = source_record()
    detail_response = client.get("/source-records/1")
    assert detail_response.status_code == 200
    assert detail_response.json()["raw_json"] == {"content_id": "cid-001"}


def test_source_record_detail_404() -> None:
    session = Mock(spec=Session)
    session.get.return_value = None
    client = make_client(session)

    response = client.get("/source-records/404")

    assert response.status_code == 404


def test_empty_list_response() -> None:
    session = Mock(spec=Session)
    session.scalar.return_value = 0
    session.scalars.return_value = scalar_result([])
    client = make_client(session)

    response = client.get("/works")

    assert response.status_code == 200
    assert response.json() == {"data": [], "limit": 20, "offset": 0, "total": 0}


@pytest.mark.parametrize("path", ["/works?limit=101", "/works?limit=0", "/works?offset=-1"])
def test_pagination_validation(path: str) -> None:
    session = Mock(spec=Session)
    client = make_client(session)

    response = client.get(path)

    assert response.status_code == 422


def test_get_db_session_closes_session(monkeypatch: pytest.MonkeyPatch) -> None:
    from jav_metadatahub.api import dependencies

    session = Mock(spec=Session)
    monkeypatch.setattr(dependencies, "SessionLocal", Mock(return_value=session))

    dependency = dependencies.get_db_session()
    assert next(dependency) is session

    with pytest.raises(StopIteration):
        next(dependency)
    session.close.assert_called_once_with()
