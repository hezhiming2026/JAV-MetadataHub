from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from jav_metadatahub.db.models import Company, Person, Series, Tag, Work, WorkExternalId
from jav_metadatahub.repositories import (
    CompanyRepository,
    PersonRepository,
    SeriesRepository,
    TagRepository,
    WorkExternalIdRepository,
    WorkRepository,
)


@pytest.mark.parametrize(
    ("repository_class", "model_name"),
    [
        (WorkRepository, "works"),
        (PersonRepository, "people"),
        (CompanyRepository, "companies"),
        (SeriesRepository, "series"),
        (TagRepository, "tags"),
    ],
)
def test_canonical_repository_list_page_counts_and_uses_stable_order(
    repository_class: type[Any],
    model_name: str,
) -> None:
    session = Mock(spec=Session)
    session.scalar.return_value = 0
    session.scalars.return_value.all.return_value = []
    repository = repository_class(session)

    items, total = repository.list_page(limit=20, offset=10)

    assert items == []
    assert total == 0
    statement = session.scalars.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert f"FROM javhub.{model_name}" in sql
    assert f"ORDER BY javhub.{model_name}.created_at DESC, javhub.{model_name}.id DESC" in sql
    assert compiled.params == {"param_1": 20, "param_2": 10}


@pytest.mark.parametrize(
    ("repository_class", "model"),
    [
        (WorkRepository, Work),
        (PersonRepository, Person),
        (CompanyRepository, Company),
        (SeriesRepository, Series),
        (TagRepository, Tag),
    ],
)
def test_canonical_repository_get_by_id_uses_session_get(
    repository_class: type[Any],
    model: type[Work] | type[Person] | type[Company] | type[Series] | type[Tag],
) -> None:
    session = Mock(spec=Session)
    repository = repository_class(session)

    repository.get_by_id(123)

    session.get.assert_called_once_with(model, 123)


def test_work_repository_create_flushes_without_commit() -> None:
    session = Mock(spec=Session)
    repository = WorkRepository(session)

    work = repository.create(code_original="ABP-477", code_norm="ABP477", primary_source="fanza")

    assert work.code_original == "ABP-477"
    assert work.code_norm == "ABP477"
    assert work.primary_source == "fanza"
    session.add.assert_called_once_with(work)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()


def test_work_repository_compute_and_apply_fillable_fields_are_separate() -> None:
    session = Mock(spec=Session)
    repository = WorkRepository(session)
    work = Work(id=1, code_original=None, title_ja="Existing")

    fillable = repository.compute_fillable_fields(
        work,
        {"code_original": "ABP-477", "title_ja": "Incoming"},
    )

    assert fillable == {"code_original": "ABP-477"}
    assert work.code_original is None
    assert work.title_ja == "Existing"
    assert repository.apply_fillable_fields(work, fillable) is True
    assert work.code_original == "ABP-477"
    assert work.title_ja == "Existing"
    session.flush.assert_called_once_with()


def test_work_external_id_repository_get_and_create() -> None:
    session = Mock(spec=Session)
    repository = WorkExternalIdRepository(session)
    expected = WorkExternalId(
        work_id=1,
        source="fanza",
        external_id="cid-001",
        id_type="content_id",
    )
    session.scalar.return_value = expected

    assert (
        repository.get_by_source_external_id(
            source="fanza",
            external_id="cid-001",
            id_type="content_id",
        )
        is expected
    )

    statement = session.scalar.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "work_external_ids.source = %(source_1)s" in sql
    assert "work_external_ids.external_id = %(external_id_1)s" in sql
    assert "work_external_ids.id_type = %(id_type_1)s" in sql

    created = repository.create(
        work_id=1,
        source="fanza",
        external_id="cid-001",
        id_type="content_id",
    )
    assert created.work_id == 1
    assert created.source == "fanza"
    assert created.external_id == "cid-001"
    assert created.id_type == "content_id"
    session.add.assert_called_once_with(created)
    session.flush.assert_called_once_with()
